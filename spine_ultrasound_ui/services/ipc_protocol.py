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

try:
    from . import ipc_messages_pb2
except Exception as exc:  # pragma: no cover - exercised only when protobuf runtime is absent
    ipc_messages_pb2 = None
    _PROTO_IMPORT_ERROR = exc
else:  # pragma: no cover - trivial assignment
    _PROTO_IMPORT_ERROR = None


def _require_proto():
    if ipc_messages_pb2 is None:
        raise RuntimeError(
            "protobuf transport is unavailable. Install the Python 'protobuf' package "
            "from requirements.txt before using the core backend."
        ) from _PROTO_IMPORT_ERROR
    return ipc_messages_pb2


def _loads_object(raw: str) -> Dict[str, Any]:
    if not raw:
        return {}
    value = json.loads(raw)
    if isinstance(value, dict):
        return value
    raise ValueError(f"expected JSON object payload, got {type(value).__name__}")


@dataclass
class CommandEnvelope:
    command: str
    payload: Dict[str, Any] = field(default_factory=dict)
    request_id: str = ""
    protocol_version: int = PROTOCOL_VERSION

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    def to_protobuf(self):
        proto = _require_proto().Command()
        proto.protocol_version = self.protocol_version
        proto.command = self.command
        proto.payload_json = json.dumps(self.payload, ensure_ascii=False, sort_keys=True)
        proto.request_id = self.request_id
        return proto

    @staticmethod
    def from_json(line: str) -> "CommandEnvelope":
        obj = json.loads(line)
        return CommandEnvelope(
            command=str(obj.get("command", "")),
            payload=dict(obj.get("payload", {})),
            request_id=str(obj.get("request_id", "")),
            protocol_version=int(obj.get("protocol_version", PROTOCOL_VERSION)),
        )

    @staticmethod
    def from_protobuf(proto) -> "CommandEnvelope":
        return CommandEnvelope(
            command=str(proto.command),
            payload=_loads_object(getattr(proto, "payload_json", "{}")),
            request_id=str(proto.request_id),
            protocol_version=int(proto.protocol_version or PROTOCOL_VERSION),
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

    def to_protobuf(self):
        proto = _require_proto().Reply()
        proto.protocol_version = self.protocol_version
        proto.ok = self.ok
        proto.message = self.message
        proto.request_id = self.request_id
        proto.data_json = json.dumps(self.data, ensure_ascii=False, sort_keys=True)
        return proto

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

    @staticmethod
    def from_protobuf(proto) -> "ReplyEnvelope":
        return ReplyEnvelope(
            ok=bool(proto.ok),
            message=str(proto.message),
            request_id=str(proto.request_id),
            data=_loads_object(getattr(proto, "data_json", "{}")),
            protocol_version=int(proto.protocol_version or PROTOCOL_VERSION),
        )


@dataclass
class TelemetryEnvelope:
    topic: str
    data: Dict[str, Any] = field(default_factory=dict)
    ts_ns: Optional[int] = None
    protocol_version: int = PROTOCOL_VERSION

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    def to_protobuf(self):
        proto = _require_proto().TelemetryEnvelope()
        proto.protocol_version = self.protocol_version
        proto.topic = self.topic
        proto.ts_ns = int(self.ts_ns or 0)
        proto.data_json = json.dumps(self.data, ensure_ascii=False, sort_keys=True)
        return proto

    @staticmethod
    def from_json(line: str) -> "TelemetryEnvelope":
        obj = json.loads(line)
        return TelemetryEnvelope(
            topic=str(obj.get("topic", "unknown")),
            data=dict(obj.get("data", {})),
            ts_ns=obj.get("ts_ns"),
            protocol_version=int(obj.get("protocol_version", PROTOCOL_VERSION)),
        )

    @staticmethod
    def from_protobuf(proto) -> "TelemetryEnvelope":
        return TelemetryEnvelope(
            topic=str(proto.topic),
            data=_loads_object(getattr(proto, "data_json", "{}")),
            ts_ns=int(proto.ts_ns) if getattr(proto, "ts_ns", 0) else None,
            protocol_version=int(proto.protocol_version or PROTOCOL_VERSION),
        )
