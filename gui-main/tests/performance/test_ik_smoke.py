from __future__ import annotations

import numpy as np

from robot_sim.application.dto import IKRequest
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.core.ik.registry import DefaultSolverRegistry
from robot_sim.model.pose import Pose
from robot_sim.model.solver_config import IKConfig


def test_ik_smoke_produces_elapsed_ms(planar_spec):
    req = IKRequest(spec=planar_spec, target=Pose(p=np.array([1.3, 0.2, 0.0]), R=np.eye(3)), q0=planar_spec.home_q.copy(), config=IKConfig())
    result = RunIKUseCase(DefaultSolverRegistry()).execute(req)
    assert result.elapsed_ms >= 0.0
