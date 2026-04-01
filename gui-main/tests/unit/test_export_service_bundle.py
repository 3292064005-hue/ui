from __future__ import annotations

import json
import numpy as np

from robot_sim.application.services.export_service import ExportService
from robot_sim.model.trajectory import JointTrajectory


def test_export_service_saves_trajectory_bundle(tmp_path):
    exporter = ExportService(tmp_path)
    traj = JointTrajectory(
        t=np.array([0.0, 0.5, 1.0]),
        q=np.array([[0.0], [0.5], [1.0]]),
        qd=np.zeros((3, 1)),
        qdd=np.zeros((3, 1)),
        ee_positions=np.array([[0.0, 0.0, 0.0], [0.5, 0.0, 0.0], [1.0, 0.0, 0.0]]),
        metadata={'mode': 'joint_space'},
    )
    path = exporter.save_trajectory_bundle('demo.csv', traj)
    data = np.load(path, allow_pickle=False)
    assert path.suffix == '.npz'
    assert np.allclose(data['q'], traj.q)
    assert json.loads(str(data['metadata_json']))['mode'] == 'joint_space'
