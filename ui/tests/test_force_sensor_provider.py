from spine_ultrasound_ui.services.pressure_sensor_service import (
    MockForceSensorProvider,
    SerialForceSensorProvider,
    UnavailableForceSensorProvider,
    create_force_sensor_provider,
)


def test_mock_force_sensor_provider_emits_six_axis_sample():
    provider = MockForceSensorProvider()
    sample = provider.read_sample(contact_active=True, desired_force_n=10.0)
    assert sample.status == "ok"
    assert sample.source == "mock_force_sensor"
    assert len(sample.wrench_n) == 6
    assert sample.ts_ns > 0


def test_unavailable_force_sensor_provider_marks_sample_unavailable():
    provider = UnavailableForceSensorProvider()
    sample = provider.read_sample(contact_active=True, desired_force_n=10.0)
    assert sample.status == "unavailable"
    assert sample.source == "unavailable_force_sensor"
    assert sample.wrench_n == [0.0] * 6


def test_serial_force_sensor_provider_reads_json_replay(tmp_path):
    replay = tmp_path / "force.jsonl"
    replay.write_text('{"ts_ns": 123, "pressure_current": 8.4, "status": "ok"}\n', encoding="utf-8")
    provider = SerialForceSensorProvider(url=str(replay), line_format="json")
    sample = provider.read_sample(contact_active=True, desired_force_n=8.0)
    assert sample.status == "ok"
    assert sample.source == "serial_force_sensor"
    assert sample.ts_ns == 123
    assert sample.wrench_n == [0.0, 0.0, 8.4, 0.0, 0.0, 0.0]
    provider.stop()


def test_serial_force_sensor_provider_factory_accepts_inline_replay_url(tmp_path):
    replay = tmp_path / "force.csv"
    replay.write_text("0,0,7.9,0,0,0\n", encoding="utf-8")
    provider = create_force_sensor_provider(f"serial_force_sensor:{replay}?format=csv")
    sample = provider.read_sample(contact_active=True, desired_force_n=8.0)
    assert isinstance(provider, SerialForceSensorProvider)
    assert sample.status == "ok"
    assert sample.wrench_n[2] == 7.9
    provider.stop()
