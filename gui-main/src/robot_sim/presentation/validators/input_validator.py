from __future__ import annotations
import numpy as np
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.dh_row import DHRow


class InputValidator:
    @staticmethod
    def validate_joint_vector(spec: RobotSpec, q, *, clamp: bool = False) -> np.ndarray:
        arr = np.asarray(q, dtype=float)
        if arr.shape != (spec.dof,):
            raise ValueError(f"joint vector shape mismatch, expected {(spec.dof,)}, got {arr.shape}")
        if not np.all(np.isfinite(arr)):
            raise ValueError("joint vector contains non-finite values")
        if clamp:
            mins = np.array([row.q_min for row in spec.dh_rows], dtype=float)
            maxs = np.array([row.q_max for row in spec.dh_rows], dtype=float)
            arr = np.clip(arr, mins, maxs)
        return arr

    @staticmethod
    def validate_home_q(rows: list[DHRow] | tuple[DHRow, ...], home_q) -> np.ndarray:
        arr = np.asarray(home_q, dtype=float)
        dof = len(rows)
        if arr.shape != (dof,):
            raise ValueError(f"home_q shape mismatch, expected {(dof,)}, got {arr.shape}")
        if not np.all(np.isfinite(arr)):
            raise ValueError("home_q contains non-finite values")
        mins = np.array([row.q_min for row in rows], dtype=float)
        maxs = np.array([row.q_max for row in rows], dtype=float)
        if np.any(arr < mins) or np.any(arr > maxs):
            raise ValueError("home_q exceeds joint limits")
        return arr

    @staticmethod
    def validate_target_values(values6) -> np.ndarray:
        arr = np.asarray(values6, dtype=float)
        if arr.shape != (6,):
            raise ValueError(f"target pose must have 6 values, got shape {arr.shape}")
        if not np.all(np.isfinite(arr)):
            raise ValueError("target pose contains non-finite values")
        return arr

    @staticmethod
    def validate_duration_and_dt(duration: float, dt: float) -> tuple[float, float]:
        duration = float(duration)
        dt = float(dt)
        if duration <= 0.0:
            raise ValueError("duration must be positive")
        if dt <= 0.0:
            raise ValueError("dt must be positive")
        if dt > duration:
            raise ValueError("dt must not exceed duration")
        return duration, dt
