from robot_sim.core.collision.geometry import AABB
from robot_sim.core.collision.scene import PlanningScene


def test_planning_scene_v2_falls_back_from_capsule_backend_and_keeps_attached_objects():
    scene = PlanningScene().with_collision_backend('capsule').attach_object('tool', AABB([0,0,0],[1,1,1]))
    assert scene.collision_backend == 'aabb'
    assert scene.metadata['requested_collision_backend'] == 'capsule'
    assert 'collision_backend_warning' in scene.metadata
    assert len(scene.attached_objects) == 1
