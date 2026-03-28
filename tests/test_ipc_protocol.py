from spine_ultrasound_ui.services import ipc_messages_pb2
from spine_ultrasound_ui.services.ipc_protocol import CommandEnvelope, PROTOCOL_VERSION, ReplyEnvelope, TelemetryEnvelope


def test_command_envelope_json_roundtrip():
    env = CommandEnvelope(command="connect_robot", payload={"a": 1}, request_id="r1")
    parsed = CommandEnvelope.from_json(env.to_json())
    assert parsed.command == "connect_robot"
    assert parsed.request_id == "r1"
    assert parsed.protocol_version == PROTOCOL_VERSION


def test_command_envelope_protobuf_roundtrip():
    env = CommandEnvelope(command="lock_session", payload={"session_id": "S1"}, request_id="r1")
    proto = env.to_protobuf()
    parsed = CommandEnvelope.from_protobuf(proto)
    assert parsed.command == "lock_session"
    assert parsed.payload["session_id"] == "S1"
    assert parsed.request_id == "r1"


def test_reply_from_json():
    rep = ReplyEnvelope.from_json('{"ok": true, "message": "ok", "request_id": "1", "data": {"x": 1}, "protocol_version": 1}')
    assert rep.ok is True
    assert rep.data["x"] == 1
    assert rep.protocol_version == PROTOCOL_VERSION


def test_reply_envelope_protobuf_roundtrip():
    rep = ReplyEnvelope(ok=True, message="ok", request_id="r1", data={"safe_to_arm": True})
    proto = rep.to_protobuf()
    parsed = ReplyEnvelope.from_protobuf(proto)
    assert parsed.ok is True
    assert parsed.data["safe_to_arm"] is True


def test_telemetry_from_json():
    tel = TelemetryEnvelope.from_json('{"topic": "core_state", "ts_ns": 10, "data": {"execution_state": "AUTO_READY"}, "protocol_version": 1}')
    assert tel.topic == "core_state"
    assert tel.data["execution_state"] == "AUTO_READY"


def test_telemetry_envelope_protobuf_roundtrip():
    proto = ipc_messages_pb2.TelemetryEnvelope(
        protocol_version=1,
        topic="robot_state",
        ts_ns=42,
        data_json='{"powered": true}',
    )
    tel = TelemetryEnvelope.from_protobuf(proto)
    assert tel.topic == "robot_state"
    assert tel.data["powered"] is True
    assert tel.ts_ns == 42
