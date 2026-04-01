from __future__ import annotations

import json

from robot_sim.application.services.export_service import ExportService
from robot_sim.core.collision.allowed_collisions import AllowedCollisionMatrix
from robot_sim.core.collision.geometry import aabb_from_points
from robot_sim.core.collision.scene import PlanningScene, SceneObject
from robot_sim.model.session_state import SessionState
import numpy as np


def test_session_export_includes_planning_scene(tmp_path):
    exporter = ExportService(tmp_path)
    obstacle = SceneObject('fixture', aabb_from_points(np.array([[0, 0, 0], [1, 1, 1]], dtype=float)))
    scene = PlanningScene(obstacles=(obstacle,), revision=4, allowed_collision_matrix=AllowedCollisionMatrix.from_pairs([('link_1', 'fixture')]))
    state = SessionState(planning_scene=scene)
    path = exporter.save_session('scene_session.json', state)
    payload = json.loads(path.read_text(encoding='utf-8'))
    assert payload['planning_scene']['revision'] == 4
    assert payload['planning_scene']['obstacle_ids'] == ['fixture']
