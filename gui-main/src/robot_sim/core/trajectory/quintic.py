from __future__ import annotations

import math
import numpy as np

from robot_sim.model.trajectory import JointTrajectory
from robot_sim.domain.types import FloatArray


class QuinticTrajectoryPlanner:
    def plan(self, q_start: FloatArray, q_goal: FloatArray, duration: float, dt: float) -> JointTrajectory:
        q_start = np.asarray(q_start, dtype=float)
        q_goal = np.asarray(q_goal, dtype=float)
        if duration <= 0.0:
            raise ValueError("duration must be positive")
        if dt <= 0.0:
            raise ValueError("dt must be positive")
        num_steps = max(int(math.ceil(duration / dt)), 1)
        t = np.linspace(0.0, duration, num_steps + 1, dtype=float)
        n = q_start.size
        q = np.zeros((t.size, n), dtype=float)
        qd = np.zeros_like(q)
        qdd = np.zeros_like(q)

        T = duration
        dq = q_goal - q_start
        a0 = q_start
        a1 = np.zeros(n, dtype=float)
        a2 = np.zeros(n, dtype=float)
        a3 = 10.0 * dq / (T ** 3)
        a4 = -15.0 * dq / (T ** 4)
        a5 = 6.0 * dq / (T ** 5)

        for i, ti in enumerate(t):
            q[i] = a0 + a1 * ti + a2 * (ti ** 2) + a3 * (ti ** 3) + a4 * (ti ** 4) + a5 * (ti ** 5)
            qd[i] = a1 + 2 * a2 * ti + 3 * a3 * (ti ** 2) + 4 * a4 * (ti ** 3) + 5 * a5 * (ti ** 4)
            qdd[i] = 2 * a2 + 6 * a3 * ti + 12 * a4 * (ti ** 2) + 20 * a5 * (ti ** 3)

        return JointTrajectory(t=t, q=q, qd=qd, qdd=qdd)
