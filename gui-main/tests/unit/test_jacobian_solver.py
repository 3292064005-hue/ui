from __future__ import annotations
import numpy as np
from robot_sim.core.kinematics.jacobian_solver import JacobianSolver

def test_planar_jacobian_matches_closed_form(planar_spec):
    q = np.array([0.3, -0.4], dtype=float)
    jr = JacobianSolver().geometric(planar_spec, q)
    l1 = l2 = 1.0
    q1, q2 = q
    expected = np.array([
        [-l1*np.sin(q1) - l2*np.sin(q1+q2), -l2*np.sin(q1+q2)],
        [ l1*np.cos(q1) + l2*np.cos(q1+q2),  l2*np.cos(q1+q2)],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [1.0, 1.0],
    ])
    assert np.allclose(jr.J, expected, atol=1e-8)
