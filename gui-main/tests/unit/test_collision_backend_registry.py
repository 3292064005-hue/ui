from __future__ import annotations

from robot_sim.application.services.capability_service import CapabilityService
from robot_sim.application.services.runtime_feature_service import RuntimeFeaturePolicy
from robot_sim.core.collision.scene import PlanningScene
from robot_sim.domain.collision_backends import default_collision_backend_registry


def test_collision_backend_registry_normalizes_unknown_and_profile_gated_backends():
    registry = default_collision_backend_registry()

    resolved_unknown, payload_unknown = registry.normalize_backend('unknown_backend')
    assert resolved_unknown == 'aabb'
    assert payload_unknown['requested_collision_backend'] == 'unknown_backend'
    assert payload_unknown['resolved_collision_backend'] == 'aabb'

    resolved_capsule, payload_capsule = registry.normalize_backend('capsule', experimental_enabled=False)
    assert resolved_capsule == 'aabb'
    assert payload_capsule['requested_collision_backend'] == 'capsule'
    assert payload_capsule['resolved_collision_backend'] == 'aabb'
    assert 'disabled by active profile' in payload_capsule['collision_backend_warning']


def test_planning_scene_uses_registry_normalization_for_collision_backend():
    scene = PlanningScene().with_collision_backend('capsule')
    assert scene.collision_backend == 'aabb'
    assert scene.metadata['requested_collision_backend'] == 'capsule'
    assert scene.metadata['resolved_collision_backend'] == 'aabb'


def test_capability_service_renders_backend_registry_availability():
    capability_service = CapabilityService(
        runtime_feature_policy=RuntimeFeaturePolicy(active_profile='research', experimental_backends_enabled=True)
    )
    features = {descriptor.key: descriptor for descriptor in capability_service._scene_features()}
    assert features['planning_scene'].metadata['fallback_backend'] == 'aabb'
    assert features['collision_backend_capsule'].metadata['availability'] == 'enabled'
