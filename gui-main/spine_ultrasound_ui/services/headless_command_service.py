from __future__ import annotations

from typing import Any, Callable

from spine_ultrasound_ui.core.command_journal import summarize_command_payload
from spine_ultrasound_ui.services.core_transport import send_tls_command
from spine_ultrasound_ui.services.ipc_protocol import COMMANDS, ReplyEnvelope, is_write_command, validate_command_payload
from spine_ultrasound_ui.utils import now_ns


class HeadlessCommandService:
    def __init__(
        self,
        *,
        mode: str,
        runtime: Any,
        ssl_context: Any,
        command_host: str,
        command_port: int,
        control_authority: Any,
        current_session_id: Callable[[], str],
        prepare_session_tracking: Callable[[str, dict[str, Any]], None],
        clear_current_session: Callable[[], None],
        remember_recent_command: Callable[[str, dict[str, Any], ReplyEnvelope], None],
        record_command_journal: Callable[[str, dict[str, Any], ReplyEnvelope], None],
        store_runtime_messages: Callable[[list[Any]], None],
        deployment_profile_snapshot: Callable[[], dict[str, Any]],
    ) -> None:
        self.mode = mode
        self.runtime = runtime
        self.ssl_context = ssl_context
        self.command_host = command_host
        self.command_port = command_port
        self.control_authority = control_authority
        self.current_session_id = current_session_id
        self.prepare_session_tracking = prepare_session_tracking
        self.clear_current_session = clear_current_session
        self.remember_recent_command = remember_recent_command
        self.record_command_journal = record_command_journal
        self.store_runtime_messages = store_runtime_messages
        self.deployment_profile_snapshot = deployment_profile_snapshot
        self._recent_commands: list[dict[str, Any]] = []

    def reply_dict(self, reply: ReplyEnvelope) -> dict[str, Any]:
        return {
            "ok": reply.ok,
            "message": reply.message,
            "request_id": reply.request_id,
            "data": dict(reply.data),
            "protocol_version": reply.protocol_version,
        }

    def recent_commands(self) -> dict[str, Any]:
        return {"recent_commands": list(self._recent_commands[-12:]), "backend_mode": self.mode}

    def remember_recent_command_local(self, command: str, payload: dict[str, Any], reply: ReplyEnvelope) -> None:
        context = dict((payload or {}).get("_command_context", {}))
        record = {
            "command": command,
            "payload": summarize_command_payload(payload),
            "ok": bool(reply.ok),
            "message": str(reply.message),
            "request_id": str(reply.request_id),
            "ts_ns": now_ns(),
            "actor_id": str(context.get("actor_id", "")),
            "workspace": str(context.get("workspace", "")),
            "lease_id": str(context.get("lease_id", "")),
            "session_id": str(context.get("session_id", "")),
            "intent": str(context.get("intent", "")),
            "profile": str(context.get("profile", "")),
        }
        self._recent_commands.append(record)
        self._recent_commands = self._recent_commands[-20:]
        self.remember_recent_command(command, payload, reply)

    def command(self, command: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if command not in COMMANDS:
            raise ValueError(f"unsupported command: {command}")
        requested_payload = dict(payload or {})
        validate_command_payload(command, requested_payload)
        write_command = is_write_command(command)
        profile = self.deployment_profile_snapshot()
        if write_command:
            authority_decision = self.control_authority.guard_command(command, requested_payload, current_session_id=self.current_session_id(), source="headless")
            normalized_payload = dict(authority_decision.get("normalized_payload", requested_payload))
            allowed_roles = set(profile.get("allowed_write_roles", []))
            context = dict(normalized_payload.get("_command_context", {}))
            role = str(context.get("role", "")).strip().lower()
            if profile.get("review_only") or not profile.get("allows_write_commands", True):
                reply = ReplyEnvelope(ok=False, message="当前部署 profile 为只读，禁止写命令。", data={"deployment_profile": profile})
                self.remember_recent_command_local(command, normalized_payload, reply)
                self.record_command_journal(command, normalized_payload, reply)
                return self.reply_dict(reply)
            if allowed_roles and role and role not in allowed_roles:
                reply = ReplyEnvelope(ok=False, message=f"当前部署 profile 不允许角色 {role} 执行写命令。", data={"deployment_profile": profile})
                self.remember_recent_command_local(command, normalized_payload, reply)
                self.record_command_journal(command, normalized_payload, reply)
                return self.reply_dict(reply)
            if not authority_decision.get("allowed", False):
                reply = ReplyEnvelope(ok=False, message=str(authority_decision.get("message", "控制权检查失败")), data={"control_authority": authority_decision.get("authority", {})})
                self.remember_recent_command_local(command, normalized_payload, reply)
                self.record_command_journal(command, normalized_payload, reply)
                return self.reply_dict(reply)
        else:
            normalized_payload = requested_payload
        self.prepare_session_tracking(command, normalized_payload)
        if self.mode == "mock":
            reply = self.runtime.handle_command(command, normalized_payload)
            self.store_runtime_messages(self.runtime.telemetry_snapshot())
        else:
            reply = send_tls_command(self.command_host, self.command_port, self.ssl_context, command, normalized_payload)
        if reply.ok and command == "lock_session":
            self.control_authority.bind_session(str(normalized_payload.get("session_id", self.current_session_id())))
        if not reply.ok and command == "lock_session":
            self.clear_current_session()
        if command == "disconnect_robot" and reply.ok:
            self.control_authority.clear_session_binding()
            self.clear_current_session()
        self.remember_recent_command_local(command, normalized_payload, reply)
        self.record_command_journal(command, normalized_payload, reply)
        return self.reply_dict(reply)
