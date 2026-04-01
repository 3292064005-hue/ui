from __future__ import annotations
import numpy as np
from robot_sim.domain.types import FloatArray

def manipulability(J: FloatArray) -> float:
    Jv = J[:3, :]
    M = Jv @ Jv.T
    det = max(0.0, float(np.linalg.det(M)))
    return float(np.sqrt(det))
