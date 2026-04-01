from __future__ import annotations
import numpy as np
from robot_sim.core.math.transforms import rot_z
from robot_sim.core.rotation.quaternion import from_matrix, to_matrix, normalize_quaternion

def test_quaternion_roundtrip():
    R = rot_z(0.7)
    q = from_matrix(R)
    assert np.allclose(np.linalg.norm(q), 1.0, atol=1e-8)
    R2 = to_matrix(q)
    assert np.allclose(R, R2, atol=1e-8)

def test_quaternion_normalize_zero():
    q = normalize_quaternion(np.zeros(4))
    assert np.allclose(q, np.array([1.0, 0.0, 0.0, 0.0]))
