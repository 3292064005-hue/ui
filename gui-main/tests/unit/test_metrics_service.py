from __future__ import annotations

import numpy as np

from robot_sim.application.services.metrics_service import MetricsService
from robot_sim.model.trajectory import JointTrajectory


def test_metrics_service_summarizes_trajectory():
    traj = JointTrajectory(
        t=np.array([0.0, 0.5, 1.0]),
        q=np.array([[0.0], [0.5], [1.0]]),
        qd=np.array([[0.0], [1.0], [0.0]]),
        qdd=np.array([[0.0], [0.0], [0.0]]),
    )
    metrics = MetricsService().summarize_trajectory(traj)
    assert metrics['num_samples'] == 3
    assert metrics['duration'] == 1.0
    assert metrics['max_abs_q'] == 1.0
