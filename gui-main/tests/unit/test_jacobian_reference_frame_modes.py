from __future__ import annotations

import numpy as np

from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver
from robot_sim.core.kinematics.jacobian_solver import JacobianSolver
from robot_sim.domain.enums import ReferenceFrame


def test_jacobian_solver_reports_reference_frames(planar_spec):
    q = np.array([0.3, -0.2], dtype=float)
    solver = JacobianSolver()
    fk = ForwardKinematicsSolver().solve(planar_spec, q)

    world = solver.geometric(planar_spec, q, fk=fk, reference_frame=ReferenceFrame.WORLD)
    local = solver.geometric(planar_spec, q, fk=fk, reference_frame=ReferenceFrame.LOCAL)

    assert world.reference_frame is ReferenceFrame.WORLD
    assert local.reference_frame is ReferenceFrame.LOCAL
    assert world.J.shape == local.J.shape == (6, planar_spec.dof)
    assert not np.allclose(world.J, local.J)
