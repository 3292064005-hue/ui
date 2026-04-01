from __future__ import annotations
import numpy as np
from robot_sim.core.math.so3 import exp_so3, log_so3

def test_exp_log_inverse():
    w = np.array([0.2, -0.3, 0.1], dtype=float)
    R = exp_so3(w)
    w2 = log_so3(R)
    assert np.allclose(w, w2, atol=1e-6)
