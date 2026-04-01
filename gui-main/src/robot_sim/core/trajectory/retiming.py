from __future__ import annotations

import numpy as np

from robot_sim.model.trajectory import JointTrajectory


def suggest_duration(q_start, q_goal, *, max_velocity: float = 1.0, max_acceleration: float = 2.0, minimum: float = 0.2) -> float:
    q_start = np.asarray(q_start, dtype=float)
    q_goal = np.asarray(q_goal, dtype=float)
    delta = np.max(np.abs(q_goal - q_start)) if q_start.size else 0.0
    vel_term = float(delta / max(max_velocity, 1.0e-9))
    acc_term = float((2.0 * delta / max(max_acceleration, 1.0e-9)) ** 0.5) if delta > 0.0 else 0.0
    return max(float(minimum), vel_term * 1.5, acc_term * 2.0)


def retime_trajectory(
    trajectory: JointTrajectory,
    *,
    max_velocity: float | None = None,
    max_acceleration: float | None = None,
) -> JointTrajectory:
    q = np.asarray(trajectory.q, dtype=float)
    qd = np.asarray(trajectory.qd, dtype=float)
    qdd = np.asarray(trajectory.qdd, dtype=float)
    t = np.asarray(trajectory.t, dtype=float)
    if t.size <= 1:
        return trajectory

    scale = 1.0
    if max_velocity is not None and qd.size:
        observed = float(np.max(np.abs(qd)))
        if observed > max(float(max_velocity), 1.0e-12):
            scale = max(scale, observed / max(float(max_velocity), 1.0e-12))
    if max_acceleration is not None and qdd.size:
        observed = float(np.max(np.abs(qdd)))
        if observed > max(float(max_acceleration), 1.0e-12):
            scale = max(scale, np.sqrt(observed / max(float(max_acceleration), 1.0e-12)))
    if scale <= 1.0 + 1.0e-12:
        return trajectory

    t_new = np.asarray(t[0] + (t - t[0]) * scale, dtype=float)
    qd_new = qd / scale
    qdd_new = qdd / (scale * scale)
    metadata = dict(trajectory.metadata)
    metadata['retimed'] = True
    metadata['retime_scale'] = float(scale)
    if max_velocity is not None:
        metadata['requested_max_velocity'] = float(max_velocity)
    if max_acceleration is not None:
        metadata['requested_max_acceleration'] = float(max_acceleration)
    return JointTrajectory(
        t=t_new,
        q=q,
        qd=qd_new,
        qdd=qdd_new,
        ee_positions=trajectory.ee_positions,
        joint_positions=trajectory.joint_positions,
        ee_rotations=trajectory.ee_rotations,
        metadata=metadata,
        feasibility=dict(trajectory.feasibility),
        quality=dict(trajectory.quality),
    )
