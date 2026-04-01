from __future__ import annotations

from robot_sim.app.bootstrap import get_project_root
from robot_sim.app.container import build_container
from robot_sim.application.dto import FKRequest, IKRequest
from robot_sim.model.solver_config import IKConfig


def test_ik_pipeline_solves_home_pose():
    container = build_container(get_project_root())
    spec = container.robot_registry.load('planar_2dof')
    fk = container.fk_uc.execute(FKRequest(spec=spec, q=spec.home_q))
    result = container.ik_uc.execute(IKRequest(spec=spec, target=fk.ee_pose, q0=spec.home_q, config=IKConfig()))
    assert result.success is True
    assert result.stop_reason in {'converged', 'analytic_exact', 'completed'}
