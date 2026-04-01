from __future__ import annotations

import numpy as np

from robot_sim.application.dto import IKRequest
from robot_sim.app.container import build_container
from robot_sim.domain.enums import IKSolverMode
from robot_sim.model.solver_config import IKConfig
from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver


def test_analytic_6r_solver_converges_on_puma_target(project_root, puma_spec):
    container = build_container(project_root)
    fk = ForwardKinematicsSolver()
    target_q = np.array([0.2, -0.6, 0.7, 0.3, 0.4, -0.2], dtype=float)
    target_pose = fk.solve(puma_spec, target_q).ee_pose
    req = IKRequest(
        spec=puma_spec,
        target=target_pose,
        q0=np.asarray(puma_spec.home_q, dtype=float).copy(),
        config=IKConfig(mode=IKSolverMode.ANALYTIC_6R, pos_tol=1.0e-8, ori_tol=1.0e-8),
    )
    result = container.ik_uc.execute(req)
    assert result.success
    assert result.final_pos_err < 1.0e-8
    assert result.final_ori_err < 1.0e-8
    assert result.diagnostics['analytic_family'] == 'spherical_wrist_6r'


def test_analytic_6r_solver_rejects_unsupported_structure(planar_spec):
    from robot_sim.core.ik.analytic_6r import Analytic6RSphericalWristIKSolver

    fk = ForwardKinematicsSolver()
    target_pose = fk.solve(planar_spec, np.asarray(planar_spec.home_q, dtype=float)).ee_pose
    result = Analytic6RSphericalWristIKSolver().solve(
        planar_spec,
        target_pose,
        np.asarray(planar_spec.home_q, dtype=float),
        IKConfig(mode=IKSolverMode.ANALYTIC_6R),
    )
    assert not result.success
    assert result.stop_reason == 'analytic_structure_unsupported'
