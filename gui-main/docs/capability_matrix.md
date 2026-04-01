# Capability Matrix

## scene_features
- `planning_scene` [stable]
  - owner: `collision.scene`
  - experimental_backends: `['capsule']`
  - fallback_backend: `aabb`
  - supported_backends: `['aabb', 'capsule']`
- `collision_backend_aabb` [stable]
  - owner: `collision.scene`
  - availability: `enabled`
  - backend_id: `aabb`
  - fallback_backend: `aabb`
  - family: `broad_phase`
  - required_dependencies: `[]`
  - supported_collision_levels: `['aabb']`
- `collision_backend_capsule` [experimental]
  - owner: `collision.scene`
  - availability: `disabled_by_profile`
  - backend_id: `capsule`
  - fallback_backend: `aabb`
  - family: `narrow_phase`
  - required_dependencies: `['capsule_backend']`
  - supported_collision_levels: `['capsule']`
