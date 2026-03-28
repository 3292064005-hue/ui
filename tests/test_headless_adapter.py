from __future__ import annotations

import time

from spine_ultrasound_ui.services.headless_adapter import HeadlessAdapter


def test_headless_adapter_mock_command_path_updates_status():
    adapter = HeadlessAdapter(
        mode="mock",
        command_host="127.0.0.1",
        command_port=5656,
        telemetry_host="127.0.0.1",
        telemetry_port=5657,
    )

    assert adapter.command("connect_robot")["ok"] is True
    assert adapter.command("power_on")["ok"] is True
    assert adapter.command("set_auto_mode")["ok"] is True

    status = adapter.status()
    assert status["backend_mode"] == "mock"
    assert status["execution_state"] == "AUTO_READY"
    assert status["powered"] is True


def test_headless_adapter_mock_loop_populates_snapshot_topics():
    adapter = HeadlessAdapter(
        mode="mock",
        command_host="127.0.0.1",
        command_port=5656,
        telemetry_host="127.0.0.1",
        telemetry_port=5657,
    )
    adapter.start()
    try:
        time.sleep(0.15)
        topics = {item["topic"] for item in adapter.snapshot()}
        assert "core_state" in topics
        assert "safety_status" in topics
        assert "recording_status" in topics
    finally:
        adapter.stop()


def test_headless_adapter_rejects_unknown_commands():
    adapter = HeadlessAdapter(
        mode="mock",
        command_host="127.0.0.1",
        command_port=5656,
        telemetry_host="127.0.0.1",
        telemetry_port=5657,
    )
    try:
        adapter.command("definitely_not_a_real_command")
    except ValueError as exc:
        assert "unsupported command" in str(exc)
    else:
        raise AssertionError("unknown commands should be rejected")


def test_headless_adapter_exposes_protocol_schema():
    adapter = HeadlessAdapter(
        mode="mock",
        command_host="127.0.0.1",
        command_port=5656,
        telemetry_host="127.0.0.1",
        telemetry_port=5657,
    )

    schema = adapter.schema()
    assert schema["api_version"] == "v1"
    assert "lock_session" in schema["commands"]
    assert "safety_status" in schema["telemetry_topics"]


def test_headless_adapter_rejects_invalid_lock_session_payload():
    adapter = HeadlessAdapter(
        mode="mock",
        command_host="127.0.0.1",
        command_port=5656,
        telemetry_host="127.0.0.1",
        telemetry_port=5657,
    )
    try:
        adapter.command("lock_session", {"session_id": "S1"})
    except ValueError as exc:
        assert "missing required fields" in str(exc)
    else:
        raise AssertionError("invalid lock_session payload should be rejected before reaching runtime")
