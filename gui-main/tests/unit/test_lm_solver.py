from __future__ import annotations

import numpy as np

from robot_sim.application.dto import IKRequest
from robot_sim.app.container import build_container
from robot_sim.domain.enums import IKSolverMode
from robot_sim.model.solver_config import IKConfig
from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver


def test_lm_solver_converges_on_planar_target(project_root, planar_spec):
    container = build_container(project_root)
    fk = ForwardKinematicsSolver()
    target_q = np.array([0.4, -0.3], dtype=float)
    target_pose = fk.solve(planar_spec, target_q).ee_pose
    req = IKRequest(
        spec=planar_spec,
        target=target_pose,
        q0=np.zeros(2, dtype=float),
        config=IKConfig(mode=IKSolverMode.LM, max_iters=200, retry_count=1),
    )
    result = container.ik_uc.execute(req)
    assert result.success
    assert result.final_pos_err < 1e-3


def test_schema_accepts_lm_mode():
    from robot_sim.infra.schema import ConfigSchema
    cfg = ConfigSchema.validate_solver_config({'ik': {'mode': 'lm'}, 'trajectory': {'duration': 1.0, 'dt': 0.1}})
    assert cfg['ik']['mode'] == 'lm'


def test_schema_accepts_analytic_6r_mode():
    from robot_sim.infra.schema import ConfigSchema
    cfg = ConfigSchema.validate_solver_config({'ik': {'mode': 'analytic_6r'}, 'trajectory': {'duration': 1.0, 'dt': 0.1}})
    assert cfg['ik']['mode'] == 'analytic_6r'
