from __future__ import annotations

import numpy as np

from robot_sim.domain.constants import EPS
from robot_sim.domain.types import FloatArray


def pseudo_inverse_svd(A: FloatArray, rcond: float = 1.0e-12) -> FloatArray:
    U, s, Vt = np.linalg.svd(A, full_matrices=False)
    if s.size == 0:
        return np.zeros((A.shape[1], A.shape[0]), dtype=float)
    cutoff = rcond * float(s[0])
    s_inv = np.array([1.0 / x if x > cutoff else 0.0 for x in s], dtype=float)
    return Vt.T @ np.diag(s_inv) @ U.T


def damped_least_squares(A: FloatArray, damping: float) -> FloatArray:
    m, _ = A.shape
    return A.T @ np.linalg.inv(A @ A.T + (damping ** 2) * np.eye(m, dtype=float))


def weighted_damped_least_squares(A: FloatArray, damping: float, joint_weights: FloatArray) -> FloatArray:
    weights = np.asarray(joint_weights, dtype=float).reshape(-1)
    if weights.shape[0] != A.shape[1]:
        raise ValueError(f"joint_weights size mismatch, expected {A.shape[1]}, got {weights.shape[0]}")
    W_inv = np.diag(1.0 / np.maximum(weights, EPS))
    inner = A @ W_inv @ A.T + (damping ** 2) * np.eye(A.shape[0], dtype=float)
    return W_inv @ A.T @ np.linalg.inv(inner)


def levenberg_marquardt_inverse(A: FloatArray, damping: float) -> FloatArray:
    n = A.shape[1]
    hessian = A.T @ A + (damping ** 2) * np.eye(n, dtype=float)
    try:
        return np.linalg.solve(hessian, A.T)
    except np.linalg.LinAlgError:
        return pseudo_inverse_svd(A)


def weighted_levenberg_marquardt_inverse(A: FloatArray, damping: float, joint_weights: FloatArray) -> FloatArray:
    weights = np.asarray(joint_weights, dtype=float).reshape(-1)
    if weights.shape[0] != A.shape[1]:
        raise ValueError(f"joint_weights size mismatch, expected {A.shape[1]}, got {weights.shape[0]}")
    W = np.diag(np.maximum(weights, EPS))
    hessian = A.T @ A + (damping ** 2) * W
    try:
        return np.linalg.solve(hessian, A.T)
    except np.linalg.LinAlgError:
        return levenberg_marquardt_inverse(A, damping)


def adaptive_damping_from_svd(
    A: FloatArray,
    *,
    base_damping: float,
    cond_threshold: float,
    min_damping: float,
    max_damping: float,
) -> float:
    try:
        singular_values = np.linalg.svd(A, compute_uv=False)
    except np.linalg.LinAlgError:
        return float(max_damping)
    if singular_values.size == 0:
        return float(max_damping)
    s_max = float(np.max(singular_values))
    s_min = float(np.min(singular_values))
    if s_max <= EPS:
        return float(max_damping)
    cond = float("inf") if s_min <= EPS else (s_max / s_min)
    damping = float(base_damping)
    if not np.isfinite(cond) or cond >= cond_threshold:
        damping = max(damping, min(max_damping, base_damping * 2.5))
    if s_min < 0.1:
        scale = (0.1 - max(s_min, 0.0)) / 0.1
        damping = max(damping, base_damping + scale * (max_damping - base_damping))
    return float(min(max(damping, min_damping), max_damping))


def safe_condition_number(A: FloatArray) -> float:
    try:
        return float(np.linalg.cond(A))
    except np.linalg.LinAlgError:
        return float("inf")


def clip_norm(v: FloatArray, max_norm: float) -> FloatArray:
    n = float(np.linalg.norm(v))
    if n < EPS or n <= max_norm:
        return v
    return v * (max_norm / n)
