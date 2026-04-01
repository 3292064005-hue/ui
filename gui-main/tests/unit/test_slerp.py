from __future__ import annotations
import numpy as np
from robot_sim.core.rotation.slerp import slerp

def test_slerp_endpoints():
    q0 = np.array([1.0, 0.0, 0.0, 0.0])
    q1 = np.array([0.0, 0.0, 0.0, 1.0])
    qs = slerp(q0, q1, np.array([0.0, 1.0]))
    assert np.allclose(qs[0], q0, atol=1e-8)
    assert np.allclose(np.abs(qs[1]), np.abs(q1), atol=1e-8)
