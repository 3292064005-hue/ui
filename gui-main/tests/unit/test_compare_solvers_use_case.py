from __future__ import annotations

import numpy as np

from robot_sim.application.dto import IKRequest
from robot_sim.application.use_cases.compare_solvers import CompareSolversUseCase
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.core.ik.registry import DefaultSolverRegistry
from robot_sim.model.pose import Pose
from robot_sim.model.solver_config import IKConfig


def test_compare_solvers_use_case_returns_rows(planar_spec):
    uc = CompareSolversUseCase(RunIKUseCase(DefaultSolverRegistry()), ['pinv', 'dls'])
    req = IKRequest(spec=planar_spec, target=Pose(p=np.array([1.5, 0.2, 0.0]), R=np.eye(3)), q0=planar_spec.home_q.copy(), config=IKConfig())
    rows = uc.execute(req)
    assert {row['solver_id'] for row in rows} == {'pinv', 'dls'}
