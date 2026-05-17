from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.runtime_source_policy_service import RuntimeSourcePolicyService


def test_research_profile_blocks_synthetic_guidance_and_mock_force():
    cfg = RuntimeConfig(camera_guidance_input_mode='synthetic', force_sensor_provider='mock_force_sensor')
    svc = RuntimeSourcePolicyService({'SPINE_DEPLOYMENT_PROFILE': 'research'})
    snapshot = svc.build_snapshot(config=cfg, guidance_source_type='fallback_simulated')
    assert snapshot.preview_ready is False
    assert snapshot.session_lock_ready is False
    assert snapshot.execution_write_ready is False
    assert snapshot.blockers


def test_dev_profile_warns_but_allows_preview():
    cfg = RuntimeConfig(camera_guidance_input_mode='synthetic', force_sensor_provider='mock_force_sensor')
    snapshot = RuntimeSourcePolicyService({'SPINE_DEPLOYMENT_PROFILE': 'dev'}).build_snapshot(config=cfg)
    assert snapshot.preview_ready is True
    assert snapshot.warnings


def test_lab_profile_accepts_realsense_and_serial_force_hardware_sources():
    cfg = RuntimeConfig(camera_guidance_input_mode='realsense_d435i', force_sensor_provider='serial_force_sensor:/dev/ttyUSB0')
    snapshot = RuntimeSourcePolicyService({'SPINE_DEPLOYMENT_PROFILE': 'lab'}).build_snapshot(
        config=cfg,
        guidance_source_type='camera_ultrasound_fusion',
    )
    assert snapshot.camera_source_tier == 'live'
    assert snapshot.force_source_tier == 'live'
    assert snapshot.session_lock_ready is True
    assert snapshot.execution_write_ready is True


def test_file_backed_serial_force_provider_is_replay_tier():
    cfg = RuntimeConfig(camera_guidance_input_mode='filesystem', force_sensor_provider='serial_force_sensor:file:/tmp/force.jsonl')
    snapshot = RuntimeSourcePolicyService({'SPINE_DEPLOYMENT_PROFILE': 'lab'}).build_snapshot(config=cfg, guidance_source_type='camera_only')
    assert snapshot.camera_source_tier == 'replay'
    assert snapshot.force_source_tier == 'replay'
    assert snapshot.session_lock_ready is True
