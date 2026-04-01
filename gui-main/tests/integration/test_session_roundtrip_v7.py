from __future__ import annotations

import json
import numpy as np

from robot_sim.app.bootstrap import get_project_root
from robot_sim.app.container import build_container
from robot_sim.app.version import SESSION_SCHEMA_VERSION
from robot_sim.core.collision.geometry import AABB
from robot_sim.core.collision.scene import PlanningScene
from robot_sim.model.session_state import SessionState


def test_session_export_roundtrip_preserves_v7_manifest(tmp_path):
    container = build_container(get_project_root())
    container.export_service.export_dir = tmp_path
    spec = container.robot_registry.load('planar_2dof')
    state = SessionState(
        robot_spec=spec,
        q_current=np.asarray(spec.home_q, dtype=float),
        planning_scene=PlanningScene().add_obstacle('box', AABB([-0.1, -0.1, -0.1], [0.1, 0.1, 0.1])),
    )
    path = container.save_session_uc.execute('session.json', state)
    payload = json.loads(path.read_text(encoding='utf-8'))
    assert payload['manifest']['schema_version'] == SESSION_SCHEMA_VERSION
    assert payload['robot_name'] == spec.name
    assert payload['planning_scene']['obstacle_ids'] == ['box']
