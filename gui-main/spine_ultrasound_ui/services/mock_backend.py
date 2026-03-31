from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QPixmap

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.utils import ensure_dir, generate_demo_pixmap

from .backend_base import BackendBase
from .backend_control_plane_service import BackendControlPlaneService
from .ipc_protocol import ReplyEnvelope, TelemetryEnvelope, is_write_command
from .mock_core_runtime import MockCoreRuntime
from .scan_plan_contract import runtime_scan_plan_payload


class MockBackend(QObject, BackendBase):
    telemetry_received = Signal(object)
    log_generated = Signal(str, str)
    camera_pixmap_ready = Signal(QPixmap)
    ultrasound_pixmap_ready = Signal(QPixmap)
    reconstruction_pixmap_ready = Signal(QPixmap)

    def __init__(self, root_dir: Path):
        super().__init__()
        self.root_dir = ensure_dir(root_dir)
        self.runtime = MockCoreRuntime()
        self.config = RuntimeConfig()
        self.runtime.update_runtime_config(self.config)
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self._control_plane_service = BackendControlPlaneService()
        self._recent_commands: list[dict] = []

    def start(self) -> None:
        self.timer.start(120)
        self._emit_telemetry(self.runtime.telemetry_snapshot())

    def update_runtime_config(self, config: RuntimeConfig) -> None:
        self.config = config
        self.runtime.update_runtime_config(config)
        self._emit_telemetry(self.runtime.telemetry_snapshot())

    def send_command(self, command: str, payload: Optional[dict] = None, *, context: Optional[dict] = None) -> ReplyEnvelope:
        request_payload = dict(payload or {})
        if context:
            request_payload.setdefault("_command_context", dict(context))
        reply = self.runtime.handle_command(command, request_payload)
        self._recent_commands.append({"command": command, "ok": bool(reply.ok), "message": str(reply.message)})
        self._recent_commands = self._recent_commands[-12:]
        self.log_generated.emit("INFO" if reply.ok else "ERROR", f"[mock_core] {command}: {reply.message}")
        # Avoid recursive governance refresh loops during read-only asset aggregation.
        # Write commands still publish fresh telemetry immediately; read commands rely on
        # the periodic tick or explicit runtime polling.
        if is_write_command(command):
            self._emit_telemetry(self.runtime.telemetry_snapshot())
        return reply

    def link_snapshot(self) -> dict:
        topics = [{"name": item.topic} for item in self.runtime.telemetry_snapshot()]
        control_plane = self._control_plane_service.build(
            local_config=self.config,
            runtime_config={"runtime_config": self.config.to_dict()},
            schema={"protocol_version": 1},
            status={"protocol_version": 1, "backend_mode": "mock", "execution_state": self.runtime.execution_state.value},
            health={"protocol_version": 1, "adapter_running": True, "telemetry_stale": False, "latest_telemetry_age_ms": 0},
            topic_catalog={"topics": topics},
            recent_commands=list(self._recent_commands),
            control_authority={
                "summary_state": "ready",
                "summary_label": "本地控制权",
                "detail": "single backend owner",
                "owner": {"actor_id": "desktop-local", "workspace": "desktop", "role": "operator", "session_id": ""},
                "active_lease": {"lease_id": "local", "actor_id": "desktop-local", "workspace": "desktop", "role": "operator", "expires_in_s": 9999},
            },
        )
        return {
            "mode": "mock",
            "summary_state": "ready",
            "summary_label": "本地 mock 内联",
            "detail": "桌面与 mock runtime 进程内直连。",
            "command_success_rate": 100,
            "telemetry_connected": True,
            "camera_connected": True,
            "ultrasound_connected": True,
            "rest_reachable": True,
            "using_websocket_telemetry": False,
            "using_websocket_media": False,
            "http_base": "inproc://mock",
            "ws_base": "inproc://mock",
            "blockers": [],
            "warnings": [],
            "control_plane": control_plane,
        }


    def get_final_verdict(self, plan=None, config: RuntimeConfig | None = None) -> dict:
        plan_payload = runtime_scan_plan_payload(plan) or {}
        config_payload = config.to_dict() if config is not None else self.config.to_dict()
        return self.runtime.compile_scan_plan_verdict(plan_payload, config_payload)

    def _tick(self) -> None:
        self.phase += 0.12
        self._emit_telemetry(self.runtime.tick())
        if generate_demo_pixmap is None:
            return
        self.camera_pixmap_ready.emit(generate_demo_pixmap(720, 360, "camera", self.phase))
        self.ultrasound_pixmap_ready.emit(generate_demo_pixmap(720, 360, "ultrasound", self.phase))
        self.reconstruction_pixmap_ready.emit(generate_demo_pixmap(720, 360, "reconstruction", self.phase))

    def _emit_telemetry(self, messages: list[TelemetryEnvelope]) -> None:
        for message in messages:
            if not message.ts_ns:
                message.ts_ns = uuid.uuid4().int % (10**12)
            self.telemetry_received.emit(message)
