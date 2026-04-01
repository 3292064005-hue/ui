from __future__ import annotations
import json
import numpy as np
from robot_sim.application.services.export_service import ExportService
from robot_sim.model.session_state import SessionState
from robot_sim.application.services.robot_registry import RobotRegistry


def test_export_service_session_and_trajectory(project_root, tmp_path):
    exporter = ExportService(tmp_path)
    spec = RobotRegistry(project_root / 'configs' / 'robots').load('planar_2dof')
    state = SessionState(robot_spec=spec, q_current=spec.home_q.copy())
    session_path = exporter.save_session('session.json', state)
    traj_path = exporter.save_trajectory(
        'traj.csv',
        t=np.array([0.0, 1.0]),
        q=np.array([[0.0, 0.0], [1.0, 1.0]]),
        qd=np.array([[0.0, 0.0], [0.0, 0.0]]),
        qdd=np.array([[0.0, 0.0], [0.0, 0.0]]),
    )
    payload = json.loads(session_path.read_text(encoding='utf-8'))
    assert payload['robot_name'] == spec.name
    assert traj_path.exists()
