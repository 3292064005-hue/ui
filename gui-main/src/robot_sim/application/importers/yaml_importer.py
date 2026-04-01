from __future__ import annotations

from pathlib import Path

from robot_sim.domain.enums import ImporterFidelity
from robot_sim.model.robot_geometry import RobotGeometry
from robot_sim.model.robot_model_bundle import RobotModelBundle


class YAMLRobotImporter:
    importer_id = 'yaml'

    def __init__(self, robot_registry) -> None:
        self._robot_registry = robot_registry

    def capabilities(self) -> dict[str, object]:
        return {
            'source_format': 'yaml',
            'fidelity': ImporterFidelity.NATIVE.value,
            'family': 'config',
        }

    def load(self, source, **kwargs):
        path = Path(source)
        import yaml
        data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        spec = self._robot_registry.from_dict(data)
        geometry = RobotGeometry.simple_capsules(spec.dof)
        return RobotModelBundle(
            spec=spec,
            geometry=geometry,
            fidelity=ImporterFidelity.NATIVE.value,
            warnings=(),
            source_path=str(path),
            importer_id=self.importer_id,
            metadata={'source_format': 'yaml'},
        )
