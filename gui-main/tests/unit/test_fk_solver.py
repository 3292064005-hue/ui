from __future__ import annotations
import numpy as np
from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver

def test_planar_fk_zero(planar_spec):
    fk = ForwardKinematicsSolver().solve(planar_spec, np.array([0.0, 0.0], dtype=float))
    assert np.allclose(fk.ee_pose.p, np.array([2.0, 0.0, 0.0]), atol=1e-8)

def test_planar_fk_right_angle(planar_spec):
    fk = ForwardKinematicsSolver().solve(planar_spec, np.array([np.pi/2, 0.0], dtype=float))
    assert np.allclose(fk.ee_pose.p, np.array([0.0, 2.0, 0.0]), atol=1e-8)
