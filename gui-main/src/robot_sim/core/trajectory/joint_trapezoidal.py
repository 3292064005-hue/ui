from __future__ import annotations

import numpy as np

from robot_sim.model.trajectory import JointTrajectory


class TrapezoidalTrajectoryPlanner:
    planner_id = 'joint_trapezoidal'

    def plan(self, q_start: np.ndarray, q_goal: np.ndarray, duration: float, dt: float) -> JointTrajectory:
        q_start = np.asarray(q_start, dtype=float)
        q_goal = np.asarray(q_goal, dtype=float)
        duration = float(duration)
        dt = float(dt)
        n = max(2, int(np.floor(duration / dt)) + 1)
        t = np.linspace(0.0, duration, n)
        tau = np.clip(t / max(duration, 1.0e-9), 0.0, 1.0)
        blend = np.where(tau < 0.5, 2.0 * tau * tau, 1.0 - 2.0 * (1.0 - tau) * (1.0 - tau))
        q = q_start[None, :] + blend[:, None] * (q_goal - q_start)[None, :]
        qd = np.gradient(q, t, axis=0, edge_order=1)
        qdd = np.gradient(qd, t, axis=0, edge_order=1)
        return JointTrajectory(t=t, q=q, qd=qd, qdd=qdd, metadata={'planner_type': self.planner_id})
