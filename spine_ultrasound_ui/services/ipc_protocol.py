from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

PROTOCOL_VERSION = 1

COMMANDS = {
    "connect_robot",
    "disconnect_robot",
    "power_on",
    "power_off",
    "set_auto_mode",
    "set_manual_mode",
    "validate_setup",
    "lock_session",
    "load_scan_plan",
    "approach_prescan",
    "seek_contact",
    "start_scan",
    "pause_scan",
    "resume_scan",
    "safe_retreat",
    "go_home",
    "clear_fault",
    "emergency_stop",
}

TELEMETRY_TOPICS = {
    "core_state",
    "robot_state",
    "contact_state",
    "scan_progress",
    "device_health",
    "safety_status",
    "recording_status",
    "alarm_event",
    "quality_feedback",
}


@dataclass
class CommandEnvelope:
    command: str
    payload: Dict[str, Any] = field(default_factory=dict)
    request_id: str = ""
    protocol_version: int = PROTOCOL_VERSION

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @staticmethod
    def from_json(line: str) -> "CommandEnvelope":
        obj = json.loads(line)
        return CommandEnvelope(
            command=str(obj.get("command", "")),
            payload=dict(obj.get("payload", {})),
            request_id=str(obj.get("request_id", "")),
            protocol_version=int(obj.get("protocol_version", PROTOCOL_VERSION)),
        )


@dataclass
class ReplyEnvelope:
    ok: bool
    message: str = ""
    request_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    protocol_version: int = PROTOCOL_VERSION

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @staticmethod
    def from_json(line: str) -> "ReplyEnvelope":
        obj = json.loads(line)
        return ReplyEnvelope(
            ok=bool(obj.get("ok", False)),
            message=str(obj.get("message", "")),
            request_id=str(obj.get("request_id", "")),
            data=dict(obj.get("data", {})),
            protocol_version=int(obj.get("protocol_version", PROTOCOL_VERSION)),
        )


@dataclass
class TelemetryEnvelope:
    topic: str
    data: Dict[str, Any] = field(default_factory=dict)
    ts_ns: Optional[int] = None
    protocol_version: int = PROTOCOL_VERSION

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @staticmethod
    def from_json(line: str) -> "TelemetryEnvelope":
        obj = json.loads(line)
        return TelemetryEnvelope(
            topic=str(obj.get("topic", "unknown")),
            data=dict(obj.get("data", {})),
            ts_ns=obj.get("ts_ns"),
            protocol_version=int(obj.get("protocol_version", PROTOCOL_VERSION)),
        )
