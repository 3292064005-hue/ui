from __future__ import annotations

from robot_sim.application.services.robot_registry import RobotRegistry
from robot_sim.model.robot_spec import RobotSpec


def test_robot_registry_roundtrip_preserves_display_name_and_metadata(project_root, tmp_path):
    src = RobotRegistry(project_root / 'configs' / 'robots')
    dst = RobotRegistry(tmp_path)
    spec = src.load('planar_2dof')
    enriched = RobotSpec(
        name=spec.name,
        dh_rows=spec.dh_rows,
        base_T=spec.base_T,
        tool_T=spec.tool_T,
        home_q=spec.home_q,
        display_name='Planar Demo',
        description='teaching arm',
        metadata={'family': 'planar', 'dof': spec.dof},
    )
    dst.save(enriched)
    loaded = dst.load(spec.name)
    assert loaded.name == spec.name
    assert loaded.label == 'Planar Demo'
    assert loaded.description == 'teaching arm'
    assert loaded.metadata['family'] == 'planar'
