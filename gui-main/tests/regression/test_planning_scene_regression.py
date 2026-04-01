from __future__ import annotations

from robot_sim.core.collision.allowed_collisions import AllowedCollisionMatrix
from robot_sim.core.collision.geometry import aabb_from_points
from robot_sim.core.collision.scene import PlanningScene, SceneObject
import numpy as np


def test_planning_scene_revision_and_object_ids_regression():
    obstacle = SceneObject('fixture', aabb_from_points(np.array([[0, 0, 0], [1, 1, 1]], dtype=float)))
    scene = PlanningScene(obstacles=(obstacle,), revision=9)
    assert scene.revision == 9
    assert scene.obstacle_ids == ('fixture',)


def test_allowed_collision_matrix_regression():
    acm = AllowedCollisionMatrix.from_pairs([('link_1', 'fixture')])
    assert acm.allows('fixture', 'link_1')
    assert not acm.allows('fixture', 'link_2')
