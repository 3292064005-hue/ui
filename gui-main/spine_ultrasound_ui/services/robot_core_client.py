from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QObject, Signal

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.utils import ensure_dir, now_text

from .backend_base import BackendBase
from .backend_control_plane_service import BackendControlPlaneService
from .core_transport import parse_telemetry_payload, send_tls_command
from .ipc_protocol import ReplyEnvelope
from .protobuf_transport import DEFAULT_TLS_SERVER_NAME, create_client_ssl_context, recv_length_prefixed_message
from .scan_plan_contract import runtime_scan_plan_payload


class RobotCoreClientBackend(QObject, BackendBase):
    telemetry_received = Signal(object)
    log_generated = Signal(str, str)

    def __init__(
        self,
        root_dir: Path,
        command_host: str = "127.0.0.1",
        command_port: int = 5656,
        telemetry_host: str = "127.0.0.1",
        telemetry_port: int = 5657,
    ) -> None:
        super().__init__()
        self.root_dir = ensure_dir(root_dir)
        self.command_host = command_host
        self.command_port = command_port
        self.telemetry_host = telemetry_host
        self.telemetry_port = telemetry_port
        self.config = RuntimeConfig()
        self._telemetry_thread: Optional[threading.Thread] = None
        self._telemetry_stop = threading.Event()
        self._ssl_context = create_client_ssl_context()
        self._control_plane_service = BackendControlPlaneService()
        self._recent_commands: list[dict[str, Any]] = []
        self._latest_topics: set[str] = set()
        self._latest_telemetry_ns = 0
        self._telemetry_connected = False
        self._reconnect_count = 0
        self._lock = threading.Lock()
        self._control_plane_cache: dict[str, Any] = {}
        self._last_final_verdict: dict[str, Any] = {}

    def start(self) -> None:
        self._start_telemetry_loop()
        self._log(
            "INFO",
            f"RobotCoreClientBackend 已启动，命令通道 {self.command_host}:{self.command_port} (TLS/Protobuf)，遥测通道 {self.telemetry_host}:{self.telemetry_port} (TLS/Protobuf)",
        )

    def update_runtime_config(self, config: RuntimeConfig) -> None:
        self.config = config
        self._log("INFO", "运行时配置已同步到 AppController。")

    def send_command(self, command: str, payload: Optional[dict] = None, *, context: Optional[dict] = None) -> ReplyEnvelope:
        try:
            request_payload = dict(payload or {})
            if context:
                request_payload.setdefault("_command_context", dict(context))
            reply = send_tls_command(self.command_host, self.command_port, self._ssl_context, command, request_payload)
            self._remember_recent_command(command, reply)
            self._capture_reply_contracts(reply)
            self._log("INFO", f"{command}: {reply.message or ('OK' if reply.ok else 'FAILED')}")
            return reply
        except Exception as exc:
            failed = ReplyEnvelope(ok=False, message=str(exc), data={})
            self._remember_recent_command(command, failed)
            self._log("ERROR", f"{command}: {exc}")
            return failed

    def get_final_verdict(self, plan=None, config: RuntimeConfig | None = None) -> dict[str, Any]:
        compile_payload = {
            'scan_plan': runtime_scan_plan_payload(plan),
            'config_snapshot': config.to_dict() if config is not None else self.config.to_dict(),
        }
        for command_name, payload in [('compile_scan_plan', compile_payload), ('query_final_verdict', {})]:
            try:
                reply = self.send_command(command_name, payload)
                verdict = self._extract_final_verdict(reply.data)
                if verdict:
                    return verdict
            except Exception:
                continue
        with self._lock:
            cached = dict(self._last_final_verdict)
            control_plane = dict(self._control_plane_cache)
        return cached or self._extract_final_verdict(control_plane)

    def close(self) -> None:
        self._telemetry_stop.set()
        thread = self._telemetry_thread
        if thread and thread.is_alive():
            thread.join(timeout=1.5)

    def link_snapshot(self) -> dict[str, Any]:
        telemetry_age_ms = None
        if self._latest_telemetry_ns:
            telemetry_age_ms = max(0, int((time.time_ns() - self._latest_telemetry_ns) / 1_000_000))
        control_plane = self._control_plane_service.build(
            local_config=self.config,
            runtime_config={"runtime_config": self.config.to_dict()},
            schema={"protocol_version": 1},
            status={
                "protocol_version": 1,
                "backend_mode": "core",
                "command_endpoint": f"{self.command_host}:{self.command_port}",
                "telemetry_endpoint": f"{self.telemetry_host}:{self.telemetry_port}",
            },
            health={
                "protocol_version": 1,
                "adapter_running": True,
                "telemetry_stale": telemetry_age_ms is None or telemetry_age_ms > 500,
                "latest_telemetry_age_ms": telemetry_age_ms,
            },
            topic_catalog={"topics": [{"name": item} for item in sorted(self._latest_topics)]},
            recent_commands=list(self._recent_commands),
            control_authority={
                "summary_state": "ready",
                "summary_label": "本地控制权",
                "detail": "single backend owner",
                "owner": {"actor_id": "desktop-local", "workspace": "desktop", "role": "operator", "session_id": ""},
                "active_lease": {"lease_id": "local", "actor_id": "desktop-local", "workspace": "desktop", "role": "operator", "expires_in_s": 9999},
            },
        )
        with self._lock:
            if self._last_final_verdict:
                control_plane['control_plane_snapshot'] = {**control_plane.get('control_plane_snapshot', {}), 'model_precheck': dict(self._last_final_verdict)}
            self._control_plane_cache = dict(control_plane)
        blockers = []
        if not self._telemetry_connected:
            blockers.append({"name": "robot_core 遥测未连通", "detail": "尚未收到 TLS/Protobuf 遥测。"})
        blockers.extend(control_plane.get("blockers", []))
        summary_state = "blocked" if blockers else ("degraded" if control_plane.get("warnings") else "ready")
        return {
            "mode": "core",
            "summary_state": summary_state,
            "summary_label": "robot_core 直连" if summary_state == "ready" else ("robot_core 直连阻塞" if summary_state == "blocked" else "robot_core 直连降级"),
            "detail": f"TLS/Protobuf command={self.command_host}:{self.command_port} telemetry={self.telemetry_host}:{self.telemetry_port}",
            "command_success_rate": int(round((sum(1 for item in self._recent_commands if item.get('ok')) / len(self._recent_commands)) * 100)) if self._recent_commands else 100,
            "telemetry_connected": self._telemetry_connected,
            "camera_connected": False,
            "ultrasound_connected": False,
            "rest_reachable": True,
            "using_websocket_telemetry": False,
            "using_websocket_media": False,
            "http_base": f"tls://{self.command_host}:{self.command_port}",
            "ws_base": f"tls://{self.telemetry_host}:{self.telemetry_port}",
            "blockers": blockers,
            "warnings": list(control_plane.get("warnings", [])),
            "reconnect_count": self._reconnect_count,
            "control_plane": control_plane,
        }

    def _start_telemetry_loop(self) -> None:
        if self._telemetry_thread and self._telemetry_thread.is_alive():
            return
        self._telemetry_stop.clear()
        self._telemetry_thread = threading.Thread(target=self._telemetry_loop, daemon=True)
        self._telemetry_thread.start()

    def _telemetry_loop(self) -> None:
        while not self._telemetry_stop.is_set():
            try:
                with socket.create_connection((self.telemetry_host, self.telemetry_port), timeout=1.0) as raw_sock:
                    raw_sock.settimeout(2.0)
                    with self._ssl_context.wrap_socket(raw_sock, server_hostname=DEFAULT_TLS_SERVER_NAME) as tls_sock:
                        self._telemetry_connected = True
                        self._log("INFO", "已连接 robot_core 遥测通道。")
                        while not self._telemetry_stop.is_set():
                            env = parse_telemetry_payload(recv_length_prefixed_message(tls_sock))
                            self._latest_topics.add(env.topic)
                            self._latest_telemetry_ns = int(getattr(env, "ts_ns", 0) or 0)
                            self.telemetry_received.emit(env)
            except OSError:
                self._telemetry_connected = False
                self._reconnect_count += 1
                if not self._telemetry_stop.is_set():
                    time.sleep(1.0)
            except Exception as exc:
                self._telemetry_connected = False
                self._reconnect_count += 1
                if self._telemetry_stop.is_set():
                    break
                self._log("WARN", f"遥测通道异常：{exc}")
                time.sleep(1.0)

    def _remember_recent_command(self, command: str, reply: ReplyEnvelope) -> None:
        self._recent_commands.append({"command": command, "ok": bool(reply.ok), "message": str(reply.message)})
        self._recent_commands = self._recent_commands[-12:]

    def _capture_reply_contracts(self, reply: ReplyEnvelope) -> None:
        verdict = self._extract_final_verdict(reply.data)
        if not verdict:
            return
        with self._lock:
            self._last_final_verdict = verdict

    @staticmethod
    def _extract_final_verdict(payload: dict[str, Any] | None) -> dict[str, Any]:
        data = dict(payload or {})
        if data.get('final_verdict'):
            return data
        nested = dict(data.get('data', {})) if isinstance(data.get('data'), dict) else {}
        if nested.get('final_verdict'):
            return nested.get('final_verdict') if isinstance(nested.get('final_verdict'), dict) and nested['final_verdict'].get('final_verdict') else nested['final_verdict']
        control_plane = dict(data.get('control_plane_snapshot', {}))
        if isinstance(control_plane.get('model_precheck'), dict):
            return dict(control_plane['model_precheck'])
        unified = dict(data.get('unified_snapshot', {}))
        if isinstance(unified.get('model_precheck'), dict):
            return dict(unified['model_precheck'])
        return {}

    def _log(self, level: str, message: str) -> None:
        try:
            self.log_generated.emit(level, f"[{now_text()}] {message}")
        except RuntimeError:
            pass
