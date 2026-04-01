from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from robot_sim.model.robot_geometry import RobotGeometry
from robot_sim.model.robot_model_bundle import RobotModelBundle


class ImportRobotUseCase:
    def __init__(self, importer_registry) -> None:
        self._importers = importer_registry

    def execute_bundle(self, source: str | Path, importer_id: str | None = None, **kwargs) -> RobotModelBundle:
        path = Path(source)
        importer_id = importer_id or path.suffix.lower().lstrip('.')
        if importer_id == 'yml':
            importer_id = 'yaml'
        canonical_id = self._importers.resolve_id(importer_id)
        importer = self._importers.get(canonical_id)
        loaded = importer.load(path, **kwargs)
        if isinstance(loaded, RobotModelBundle):
            return loaded
        geometry = RobotGeometry.simple_capsules(getattr(loaded, 'dof', 0))
        return RobotModelBundle(
            spec=loaded,
            geometry=geometry,
            fidelity=str(getattr(loaded, 'metadata', {}).get('import_fidelity', 'native')),
            warnings=tuple(str(item) for item in getattr(loaded, 'metadata', {}).get('warnings', ())),
            source_path=str(path),
            importer_id=str(canonical_id),
            metadata={'legacy_adapter': True},
        )

    def execute(self, source: str | Path, importer_id: str | None = None, **kwargs):
        path = Path(source)
        requested_id = importer_id or path.suffix.lower().lstrip('.')
        if requested_id == 'yml':
            requested_id = 'yaml'
        bundle = self.execute_bundle(path, importer_id=requested_id, **kwargs)
        metadata = dict(getattr(bundle.spec, 'metadata', {}) or {})
        metadata.setdefault('importer_requested', str(requested_id))
        metadata.setdefault('importer_resolved', str(bundle.importer_id or requested_id))
        metadata.setdefault('import_fidelity', str(bundle.fidelity or metadata.get('import_fidelity', 'unknown')))
        metadata.setdefault('geometry_available', bool(bundle.geometry is not None))
        metadata.setdefault('geometry_ref', 'bundle.geometry' if bundle.geometry is not None else '')
        if bundle.warnings:
            notes = list(metadata.get('warnings', []))
            for warning in bundle.warnings:
                if warning not in notes:
                    notes.append(warning)
            metadata['warnings'] = notes
        if bundle.importer_id == 'urdf_skeleton':
            metadata.setdefault('import_family', 'approximate_tree_import')
        return replace(bundle.spec, metadata=metadata)
