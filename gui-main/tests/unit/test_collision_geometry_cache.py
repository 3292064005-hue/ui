from __future__ import annotations

import numpy as np

from robot_sim.application.validators import collision_validator as collision_validator_module
from robot_sim.application.validators.collision_validator import evaluate_collision_summary
from robot_sim.core.collision.geometry import aabb_from_points
from robot_sim.core.collision.scene import PlanningScene, SceneObject
from robot_sim.model.trajectory import JointTrajectory


def _trajectory() -> JointTrajectory:
    joint_positions = np.array([
        [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0.2, 0.1, 0]],
        [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0.2, 0.1, 0]],
    ], dtype=float)
    return JointTrajectory(
        t=np.array([0.0, 1.0]),
        q=np.zeros((2, 3)),
        qd=np.zeros((2, 3)),
        qdd=np.zeros((2, 3)),
        joint_positions=joint_positions,
        ee_positions=np.array([[0, 0, 0], [1, 0, 0]], dtype=float),
    )


def test_scene_revision_change_reuses_geometry_cache_but_not_result_cache():
    collision_validator_module._COLLISION_CACHE._entries.clear()
    collision_validator_module._GEOMETRY_CACHE._entries.clear()
    traj = _trajectory()
    obstacle = SceneObject('wall', aabb_from_points(np.array([[0.0, -0.1, -0.1], [1.1, 0.2, 0.1]], dtype=float), padding=0.0))
    scene_v1 = PlanningScene(obstacles=(obstacle,), revision=10)
    scene_v2 = PlanningScene(obstacles=(obstacle,), revision=11)

    _, first_summary = evaluate_collision_summary(traj, planning_scene=scene_v1)
    _, second_summary = evaluate_collision_summary(traj, planning_scene=scene_v2)

    assert first_summary['cache_hit'] is False
    assert first_summary['geometry_cache_hit'] is False
    assert second_summary['cache_hit'] is False
    assert second_summary['geometry_cache_hit'] is True
    assert first_summary['trajectory_digest'] == second_summary['trajectory_digest'] == traj.trajectory_digest
