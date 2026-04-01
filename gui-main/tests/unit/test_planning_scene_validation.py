from __future__ import annotations

import numpy as np

from robot_sim.application.use_cases.validate_trajectory import ValidateTrajectoryUseCase
from robot_sim.core.collision.allowed_collisions import AllowedCollisionMatrix
from robot_sim.core.collision.geometry import aabb_from_points
from robot_sim.core.collision.scene import PlanningScene, SceneObject
from robot_sim.model.trajectory import JointTrajectory


def _collision_traj():
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


def test_planning_scene_reports_scene_revision_and_pairs():
    traj = _collision_traj()
    obstacle = SceneObject('wall', aabb_from_points(np.array([[0.0, -0.1, -0.1], [1.1, 0.2, 0.1]], dtype=float), padding=0.0))
    scene = PlanningScene(obstacles=(obstacle,), revision=7)
    report = ValidateTrajectoryUseCase().execute(traj, planning_scene=scene)
    cs = report.metadata['collision_summary']
    assert cs['scene_revision'] == 7
    assert cs['environment_collision'] is True
    assert ('link_0', 'wall') in [tuple(pair) for pair in cs['environment_pairs']]


def test_planning_scene_acm_can_ignore_environment_pair():
    traj = _collision_traj()
    obstacle = SceneObject('wall', aabb_from_points(np.array([[0.0, -0.1, -0.1], [1.1, 0.2, 0.1]], dtype=float), padding=0.0))
    acm = AllowedCollisionMatrix.from_pairs([('link_0', 'wall')])
    scene = PlanningScene(obstacles=(obstacle,), revision=3, allowed_collision_matrix=acm)
    report = ValidateTrajectoryUseCase().execute(traj, planning_scene=scene)
    cs = report.metadata['collision_summary']
    assert ('link_0', 'wall') in [tuple(pair) for pair in cs['ignored_pairs']]
