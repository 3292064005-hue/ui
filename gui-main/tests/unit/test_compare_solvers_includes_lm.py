from __future__ import annotations

import numpy as np

from robot_sim.application.dto import IKRequest
from robot_sim.application.use_cases.compare_solvers import CompareSolversUseCase
from robot_sim.app.container import build_container
from robot_sim.model.solver_config import IKConfig
from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver


def test_compare_solvers_uses_registered_solver_ids(project_root, planar_spec):
    container = build_container(project_root)
    fk = ForwardKinematicsSolver()
    target_pose = fk.solve(planar_spec, np.array([0.2, -0.2], dtype=float)).ee_pose
    req = IKRequest(spec=planar_spec, target=target_pose, q0=np.zeros(2, dtype=float), config=IKConfig())
    rows = CompareSolversUseCase(container.ik_uc).execute(req)
    solver_ids = {row['solver_id'] for row in rows}
    assert {'pinv', 'dls', 'lm'}.issubset(solver_ids)
