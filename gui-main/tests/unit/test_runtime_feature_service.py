from pathlib import Path

from robot_sim.application.services.config_service import ConfigService
from robot_sim.application.services.module_status_service import ModuleStatusService
from robot_sim.application.services.runtime_feature_service import RuntimeFeatureService
from robot_sim.application.services.capability_service import CapabilityService
from robot_sim.domain.enums import ModuleStatus


def test_runtime_feature_policy_and_services_follow_profile_flags(tmp_path: Path):
    config_dir = tmp_path / 'configs'
    profiles = config_dir / 'profiles'
    profiles.mkdir(parents=True)
    (profiles / 'default.yaml').write_text(
        'features:\n'
        '  experimental_modules_enabled: false\n'
        '  experimental_backends_enabled: false\n'
        '  plugin_discovery_enabled: false\n',
        encoding='utf-8',
    )
    (profiles / 'research.yaml').write_text(
        'features:\n'
        '  experimental_modules_enabled: true\n'
        '  experimental_backends_enabled: true\n'
        '  plugin_discovery_enabled: true\n',
        encoding='utf-8',
    )
    config_service = ConfigService(config_dir, profile='research')
    policy = RuntimeFeatureService(config_service).load_policy()
    assert policy.experimental_modules_enabled is True
    assert policy.plugin_discovery_enabled is True

    module_statuses = ModuleStatusService(runtime_feature_policy=policy).snapshot_details()
    assert module_statuses['presentation.widgets.collision_panel']['enabled'] is True

    capability_service = CapabilityService(runtime_feature_policy=policy)
    scene_features = {descriptor.key: descriptor for descriptor in capability_service._scene_features()}
    assert scene_features['collision_backend_capsule'].status is ModuleStatus.EXPERIMENTAL
    assert scene_features['collision_backend_capsule'].metadata['availability'] == 'enabled'
