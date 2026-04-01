from __future__ import annotations

from dataclasses import dataclass, field

from robot_sim.model.robot_geometry import RobotGeometry
from robot_sim.model.robot_spec import RobotSpec


@dataclass(frozen=True)
class RobotModelBundle:
    spec: RobotSpec
    geometry: RobotGeometry | None = None
    fidelity: str = ''
    warnings: tuple[str, ...] = ()
    source_path: str = ''
    importer_id: str = ''
    metadata: dict[str, object] = field(default_factory=dict)
