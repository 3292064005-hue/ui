from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from robot_sim.model.export_manifest import ExportManifest
from robot_sim.model.version_catalog import VersionCatalog, current_version_catalog


class ManifestBuilder:
    """Canonical builder for export and package manifests."""

    def __init__(self, version_catalog: VersionCatalog | None = None) -> None:
        self._versions = version_catalog or current_version_catalog()

    def build_manifest(
        self,
        *,
        robot_id: str | None = None,
        solver_id: str | None = None,
        planner_id: str | None = None,
        reproducibility_seed: int | None = None,
        files: list[str] | None = None,
        metadata: dict[str, object] | None = None,
        schema_version: str | None = None,
        export_version: str | None = None,
        correlation_id: str | None = None,
        timestamp_utc: str | None = None,
    ) -> ExportManifest:
        """Build the canonical export/package manifest.

        Args:
            robot_id: Optional robot identifier.
            solver_id: Optional solver identifier.
            planner_id: Optional planner identifier.
            reproducibility_seed: Optional reproducibility seed.
            files: Optional manifest file list.
            metadata: Optional metadata payload.
            schema_version: Optional schema-version override.
            export_version: Optional export-version override.
            correlation_id: Optional correlation identifier propagated from task lifecycle.
            timestamp_utc: Optional explicit timestamp override used by tests.

        Returns:
            ExportManifest: Immutable manifest payload.

        Raises:
            None: Manifest generation is deterministic.
        """
        return ExportManifest(
            app_name=self._versions.app_name,
            app_version=self._versions.app_version,
            schema_version=str(schema_version or self._versions.export_schema_version),
            export_version=str(export_version or self._versions.export_schema_version),
            producer_version=self._versions.app_version,
            compatibility_notes=(
                'goal_position_error is canonical; endpoint_position_error is a legacy alias.',
                'goal_orientation_error is canonical; endpoint_orientation_error is a legacy alias.',
            ),
            migration_aliases={
                'endpoint_position_error': 'goal_position_error',
                'endpoint_orientation_error': 'goal_orientation_error',
            },
            correlation_id=str(correlation_id or ''),
            robot_id=robot_id,
            solver_id=solver_id,
            planner_id=planner_id,
            timestamp_utc=str(timestamp_utc or datetime.now(timezone.utc).isoformat()),
            reproducibility_seed=reproducibility_seed,
            files=tuple(files or ()),
            metadata=dict(metadata or {}),
        )


def export_manifest_as_dict(manifest: ExportManifest) -> dict[str, object]:
    """Serialize an :class:`ExportManifest` into a JSON-friendly mapping."""
    payload = asdict(manifest)
    payload['compatibility_notes'] = list(manifest.compatibility_notes)
    payload['files'] = list(manifest.files)
    return payload
