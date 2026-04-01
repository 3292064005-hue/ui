from __future__ import annotations

import pytest
import yaml

from robot_sim.application.services.robot_registry import RobotRegistry


def test_robot_registry_rejects_invalid_joint_limits(tmp_path):
    registry = RobotRegistry(tmp_path)
    payload = {
        'name': 'Bad Robot',
        'home_q': [0.0],
        'dh_rows': [
            {'a': 1.0, 'alpha': 0.0, 'd': 0.0, 'theta_offset': 0.0, 'joint_type': 'revolute', 'q_min': 1.0, 'q_max': -1.0},
        ],
    }
    (tmp_path / 'bad_robot.yaml').write_text(yaml.safe_dump(payload), encoding='utf-8')
    with pytest.raises(ValueError):
        registry.load('bad_robot')
