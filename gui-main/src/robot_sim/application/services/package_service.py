from __future__ import annotations

from dataclasses import asdict
import json
import zipfile
from pathlib import Path

from robot_sim.application.services.manifest_builder import ManifestBuilder
from robot_sim.model.export_manifest import ExportManifest
from robot_sim.model.version_catalog import VersionCatalog, current_version_catalog


class PackageService:
    """Create release bundles together with their manifest payloads."""

    def __init__(self, export_dir: str | Path, version_catalog: VersionCatalog | None = None) -> None:
        """Create the package service.

        Args:
            export_dir: Destination directory for generated package archives.
            version_catalog: Optional version catalog used for manifest metadata.

        Returns:
            None: Initializes export destinations only.

        Raises:
            OSError: If the export directory cannot be created.
        """
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self._versions = version_catalog or current_version_catalog()
        self._manifest_builder = ManifestBuilder(self._versions)

    def build_manifest(self, *, robot_id: str | None = None, solver_id: str | None = None, planner_id: str | None = None, files: list[str] | None = None, reproducibility_seed: int | None = None, metadata: dict[str, object] | None = None, correlation_id: str | None = None) -> ExportManifest:
        """Build the canonical package-export manifest."""
        return self._manifest_builder.build_manifest(
            robot_id=robot_id,
            solver_id=solver_id,
            planner_id=planner_id,
            files=files,
            reproducibility_seed=reproducibility_seed,
            metadata=metadata,
            correlation_id=correlation_id,
        )

    def export_package(self, name: str, files: list[Path], manifest: ExportManifest) -> Path:
        """Build a zip package containing exported artifacts and the manifest."""
        path = self.export_dir / name
        if path.suffix.lower() != '.zip':
            path = path.with_suffix('.zip')
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for file in files:
                if file.exists():
                    zf.write(file, arcname=file.name)
            zf.writestr('manifest.json', json.dumps(asdict(manifest), ensure_ascii=False, indent=2))
        return path
