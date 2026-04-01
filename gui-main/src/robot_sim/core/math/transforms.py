from __future__ import annotations
import math
import numpy as np
from robot_sim.domain.types import FloatArray

def rot_x(a: float) -> FloatArray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=float)

def rot_y(a: float) -> FloatArray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=float)

def rot_z(a: float) -> FloatArray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=float)

def make_transform(R: FloatArray, p: FloatArray) -> FloatArray:
    T = np.eye(4, dtype=float)
    T[:3, :3] = R
    T[:3, 3] = p
    return T

def translation(x: float, y: float, z: float) -> FloatArray:
    T = np.eye(4, dtype=float)
    T[:3, 3] = [x, y, z]
    return T
