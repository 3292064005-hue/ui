from __future__ import annotations
import math
import numpy as np
from robot_sim.core.rotation.quaternion import normalize_quaternion
from robot_sim.domain.types import FloatArray

def slerp(q0: FloatArray, q1: FloatArray, t: FloatArray) -> FloatArray:
    q0 = normalize_quaternion(q0)
    q1 = normalize_quaternion(q1)
    dot = float(np.dot(q0, q1))
    if dot < 0.0:
        q1 = -q1
        dot = -dot
    dot = min(1.0, max(-1.0, dot))
    if dot > 0.9995:
        out = np.array([(1 - a) * q0 + a * q1 for a in t], dtype=float)
        return np.array([normalize_quaternion(q) for q in out], dtype=float)
    theta_0 = math.acos(dot)
    sin_theta_0 = math.sin(theta_0)
    result = []
    for a in t:
        theta = theta_0 * float(a)
        s0 = math.sin(theta_0 - theta) / sin_theta_0
        s1 = math.sin(theta) / sin_theta_0
        result.append(s0 * q0 + s1 * q1)
    return np.array([normalize_quaternion(q) for q in result], dtype=float)
