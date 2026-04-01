from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExportManifest:
    app_name: str
    app_version: str
    schema_version: str
    export_version: str = ''
    producer_version: str = ''
    compatibility_notes: tuple[str, ...] = ()
    migration_aliases: dict[str, str] = field(default_factory=dict)
    correlation_id: str = ''
    robot_id: str | None = None
    solver_id: str | None = None
    planner_id: str | None = None
    timestamp_utc: str = ""
    reproducibility_seed: int | None = None
    files: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)
