from __future__ import annotations

import numpy as np

from robot_sim.render.picking import PickingController
from robot_sim.render.scene_controller import SceneController
from robot_sim.render.scene_3d_widget import Scene3DWidget


class FakeWidget:
    def __init__(self):
        self.calls = []

    def set_robot_lines(self, points):
        self.calls.append(('robot', np.asarray(points).shape))

    def set_target_pose(self, pose):
        self.calls.append(('target', pose))

    def set_playback_marker(self, point):
        self.calls.append(('marker', tuple(np.asarray(point).tolist())))

    def set_trajectory(self, points):
        self.calls.append(('traj', np.asarray(points).shape))

    def clear_trajectory(self):
        self.calls.append(('clear', None))

    def set_scene_obstacles(self, obstacles):
        self.calls.append(('obstacles', len(list(obstacles))))

    def set_attached_objects(self, attached_objects):
        self.calls.append(('attached', len(list(attached_objects))))

    def set_overlay_text(self, text):
        self.calls.append(('overlay', text))


def test_scene_controller_supports_projection_contracts():
    widget = FakeWidget()
    controller = SceneController(widget)
    fk_result = type('FK', (), {'joint_positions': np.zeros((2, 3)), 'ee_pose': type('P', (), {'p': np.array([1.0, 2.0, 3.0])})()})()
    controller.update_fk_projection(fk_result, target_pose='pose', append_path=True)
    controller.update_playback_projection(np.zeros((2, 3)), np.array([0.0, 0.0, 1.0]), target_pose='pose2')
    controller.update_planning_scene_projection(type('S', (), {'obstacles': [1, 2], 'attached_objects': [3], 'revision': 4, 'collision_backend': 'aabb'})())
    controller.clear_transient_visuals()
    tags = [tag for tag, _ in widget.calls]
    assert 'robot' in tags
    assert 'overlay' in tags
    assert 'clear' in tags


def test_scene_widget_snapshot_tracks_scene_fields():
    widget = Scene3DWidget()
    widget.set_scene_obstacles([{'id': 1}])
    widget.set_attached_objects([{'id': 2}])
    widget.set_overlay_text('hello')
    widget.set_robot_geometry({'links': 1})
    snap = widget.scene_snapshot()
    assert snap['overlay_text'] == 'hello'
    assert snap['scene_obstacles'] == [{'id': 1}]
    assert snap['attached_objects'] == [{'id': 2}]
    assert snap['robot_geometry'] == {'links': 1}


def test_picking_controller_tracks_pose_hint_and_point():
    picking = PickingController()
    picking.set_point([1, 2, 3])
    assert np.allclose(picking.last_point, [1, 2, 3])
    assert np.allclose(picking.to_target_pose_request(), [1, 2, 3])
    picking.set_pose_hint({'pose': True})
    assert picking.to_target_pose_request() == {'pose': True}
    picking.clear()
    assert picking.to_target_pose_request() is None
