from __future__ import annotations

from robot_sim.app.bootstrap import get_project_root
from robot_sim.app.container import build_container
from robot_sim.core.collision.geometry import AABB
from robot_sim.core.collision.scene import PlanningScene


def test_imported_robot_bundle_can_seed_planning_scene():
    root = get_project_root()
    container = build_container(root)
    bundle = container.import_robot_uc.execute_bundle(root / 'configs' / 'robots' / 'planar_2dof.yaml')
    scene = PlanningScene(geometry_source='bundle').add_obstacle('box', AABB([-0.1, -0.1, -0.1], [0.1, 0.1, 0.1]))
    assert bundle.spec.dof == 2
    assert bundle.geometry is not None
    assert scene.geometry_source == 'bundle'
    assert scene.obstacle_ids == ('box',)
