# Schema Versions

Current version catalog:

- `app_version`: 0.7.0
- `schema_version`: v7
- `session_schema_version`: session-v7
- `benchmark_pack_version`: v7

## Manifest / export versions

- `schema_version`: payload schema version for the exported artifact.
- `export_version`: version of the export layout used by the writer.
- `producer_version`: application version that generated the payload.

## Migration aliases

Current manifests expose `migration_aliases` so older field names can be mapped to the canonical P0 names.

Current aliases:

- `endpoint_position_error` -> `goal_position_error`
- `endpoint_orientation_error` -> `goal_orientation_error`

## Session payloads

Session exports must include:

- `app_state`
- `active_task_id`
- `active_task_kind`
- `scene_revision`
- `warnings`

These fields are part of the P0 task/state contract and should not be dropped without a schema version bump.


## P1 additions

- Session payload may now include `planning_scene` summary fields: `revision`, `collision_level`, `obstacle_ids`, and `allowed_collision_pairs`.
- Trajectory collision summaries may now include `scene_revision`, `ignored_pairs`, `self_pairs`, and `environment_pairs`.
- Solver schema now accepts `ik.mode = "lm"`.
