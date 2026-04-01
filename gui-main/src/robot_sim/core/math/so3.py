from __future__ import annotations
import math
import numpy as np
from robot_sim.domain.constants import EPS
from robot_sim.domain.types import FloatArray

def skew(v: FloatArray) -> FloatArray:
    x, y, z = v
    return np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]], dtype=float)

def vee(M: FloatArray) -> FloatArray:
    return np.array([M[2, 1], M[0, 2], M[1, 0]], dtype=float)

def log_so3(R: FloatArray) -> FloatArray:
    trace = float(np.trace(R))
    cos_theta = max(-1.0, min(1.0, (trace - 1.0) * 0.5))
    theta = math.acos(cos_theta)
    if theta < 1.0e-9:
        return np.zeros(3, dtype=float)
    if abs(theta - math.pi) < 1.0e-6:
        A = (R + np.eye(3, dtype=float)) * 0.5
        axis = np.array([
            math.sqrt(max(A[0, 0], 0.0)),
            math.sqrt(max(A[1, 1], 0.0)),
            math.sqrt(max(A[2, 2], 0.0)),
        ], dtype=float)
        if R[2, 1] - R[1, 2] < 0:
            axis[0] = -axis[0]
        if R[0, 2] - R[2, 0] < 0:
            axis[1] = -axis[1]
        if R[1, 0] - R[0, 1] < 0:
            axis[2] = -axis[2]
        n = np.linalg.norm(axis)
        if n < EPS:
            return np.zeros(3, dtype=float)
        axis /= n
        return axis * theta
    return vee((R - R.T) * (0.5 * theta / math.sin(theta)))

def exp_so3(w: FloatArray) -> FloatArray:
    theta = float(np.linalg.norm(w))
    if theta < 1.0e-9:
        return np.eye(3, dtype=float) + skew(w)
    K = skew(w / theta)
    return np.eye(3, dtype=float) + math.sin(theta) * K + (1.0 - math.cos(theta)) * (K @ K)

def rotation_error(R_target: FloatArray, R_current: FloatArray) -> FloatArray:
    return log_so3(R_target @ R_current.T)


def orthonormalize_rotation(R: FloatArray) -> FloatArray:
    M = np.asarray(R, dtype=float)
    U, _, Vt = np.linalg.svd(M)
    R_proj = U @ Vt
    if np.linalg.det(R_proj) < 0.0:
        U[:, -1] *= -1.0
        R_proj = U @ Vt
    return R_proj


def is_rotation_matrix(R: FloatArray, *, atol: float = 1.0e-6) -> bool:
    M = np.asarray(R, dtype=float)
    if M.shape != (3, 3):
        return False
    return bool(np.allclose(M.T @ M, np.eye(3, dtype=float), atol=atol) and abs(np.linalg.det(M) - 1.0) <= atol)
