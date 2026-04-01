from __future__ import annotations
import numpy as np
from robot_sim.application.services.robot_registry import RobotRegistry


def test_robot_registry_roundtrip(project_root, tmp_path):
    src = RobotRegistry(project_root / 'configs' / 'robots')
    dst = RobotRegistry(tmp_path)
    spec = src.load('planar_2dof')
    path = dst.save(spec, name='roundtrip_planar')
    loaded = dst.load('roundtrip_planar')
    assert path.exists()
    assert loaded.name == spec.name
    assert loaded.dof == spec.dof
    assert np.allclose(loaded.home_q, spec.home_q)
