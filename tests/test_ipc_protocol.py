from spine_ultrasound_ui.services.ipc_protocol import CommandEnvelope, PROTOCOL_VERSION, ReplyEnvelope, TelemetryEnvelope


def test_command_envelope_json_roundtrip():
    env = CommandEnvelope(command="connect_robot", payload={"a": 1}, request_id="r1")
    parsed = CommandEnvelope.from_json(env.to_json())
    assert parsed.command == "connect_robot"
    assert parsed.request_id == "r1"
    assert parsed.protocol_version == PROTOCOL_VERSION


def test_reply_from_json():
    rep = ReplyEnvelope.from_json('{"ok": true, "message": "ok", "request_id": "1", "data": {"x": 1}, "protocol_version": 1}')
    assert rep.ok is True
    assert rep.data["x"] == 1
    assert rep.protocol_version == PROTOCOL_VERSION


def test_telemetry_from_json():
    tel = TelemetryEnvelope.from_json('{"topic": "core_state", "ts_ns": 10, "data": {"execution_state": "AUTO_READY"}, "protocol_version": 1}')
    assert tel.topic == "core_state"
    assert tel.data["execution_state"] == "AUTO_READY"
