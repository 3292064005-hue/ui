from __future__ import annotations

import numpy as np


class SceneController:  # pragma: no cover - GUI shell
    """Imperative adapter that applies state changes to the 3D scene widget."""

    def __init__(self, widget) -> None:
        self.widget = widget
        self._ee_path: list[np.ndarray] = []

    def reset_path(self) -> None:
        self._ee_path.clear()

    def clear_transient_visuals(self) -> None:
        self.reset_path()
        self.widget.clear_trajectory()

    def update_fk_projection(self, fk_result, target_pose=None, *, append_path: bool = False) -> None:
        self.widget.set_robot_lines(fk_result.joint_positions)
        if target_pose is not None:
            self.widget.set_target_pose(target_pose)
        ee = np.asarray(fk_result.ee_pose.p, dtype=float)
        self.widget.set_playback_marker(ee)
        if append_path:
            self._ee_path.append(ee)
            if len(self._ee_path) >= 2:
                self.widget.set_trajectory(np.vstack(self._ee_path))

    def update_playback_projection(self, joint_positions: np.ndarray, ee_position: np.ndarray | None = None, target_pose=None) -> None:
        pts = np.asarray(joint_positions, dtype=float)
        self.widget.set_robot_lines(pts)
        if target_pose is not None:
            self.widget.set_target_pose(target_pose)
        ee = np.asarray(ee_position if ee_position is not None else pts[-1], dtype=float)
        self.widget.set_playback_marker(ee)

    def update_planning_scene_projection(self, planning_scene) -> None:
        if planning_scene is None:
            self.widget.set_scene_obstacles([])
            self.widget.set_attached_objects([])
            return
        self.widget.set_scene_obstacles(getattr(planning_scene, 'obstacles', ()))
        self.widget.set_attached_objects(getattr(planning_scene, 'attached_objects', ()))
        revision = getattr(planning_scene, 'revision', 0)
        backend = getattr(planning_scene, 'collision_backend', 'aabb')
        obstacle_count = len(getattr(planning_scene, 'obstacles', ()))
        attached_count = len(getattr(planning_scene, 'attached_objects', ()))
        self.widget.set_overlay_text(
            f'Scene rev={revision} backend={backend} obstacles={obstacle_count} attached={attached_count}'
        )

    def update_fk(self, fk_result, target_pose=None, *, append_path: bool = False) -> None:
        self.update_fk_projection(fk_result, target_pose, append_path=append_path)

    def update_cached_frame(self, joint_positions: np.ndarray, ee_position: np.ndarray | None = None, target_pose=None) -> None:
        self.update_playback_projection(joint_positions, ee_position=ee_position, target_pose=target_pose)

    def set_trajectory_from_fk_samples(self, points: np.ndarray) -> None:
        points_array = np.asarray(points, dtype=float)
        self._ee_path = [np.asarray(p, dtype=float).copy() for p in points_array]
        self.widget.set_trajectory(points_array)
