from __future__ import annotations

import numpy as np

from robot_sim.render.actor_manager import ActorManager
from robot_sim.render.robot_visual import RobotVisual
from robot_sim.render.screenshot_service import ScreenshotService
from robot_sim.render.target_visual import TargetVisual
from robot_sim.render.trajectory_visual import TrajectoryVisual

try:
    from PySide6.QtWidgets import QWidget
except Exception:  # pragma: no cover
    QWidget = object  # type: ignore


class Scene3DWidget(QWidget):  # pragma: no cover - GUI shell
    def __init__(self, parent=None):
        try:
            super().__init__(parent)
        except TypeError:  # pragma: no cover - non-Qt fallback
            super().__init__()
        self.plotter = None
        self.actor_manager = ActorManager()
        self.screenshot_service = ScreenshotService()
        self.robot_visual = RobotVisual()
        self.target_visual = TargetVisual()
        self.trajectory_visual = TrajectoryVisual()
        self._robot_points: np.ndarray | None = None
        self._trajectory_points: np.ndarray | None = None
        self._playback_marker: np.ndarray | None = None
        self._target_pose = None
        self._target_axes_visible = True
        self._trajectory_visible = True
        self._scene_title = 'Robot Sim Engine'
        self._robot_geometry = None
        self._scene_obstacles: list[object] = []
        self._attached_objects: list[object] = []
        self._overlay_text = self._scene_title
        try:
            from PySide6.QtWidgets import QLabel, QVBoxLayout
            layout = QVBoxLayout(self)
            try:
                from pyvistaqt import QtInteractor
                self.plotter = QtInteractor(self)
                layout.addWidget(self.plotter.interactor)
                self.plotter.set_background('white')
                self.plotter.add_axes()
                self._set_plotter_overlay_text(self._overlay_text)
            except Exception as exc:
                label = QLabel(
                    "3D 视图依赖未安装或初始化失败，当前为占位视图。\n"
                    "请在项目目录执行: pip install -e .[gui]\n"
                    f"详细信息: {exc.__class__.__name__}: {exc}"
                )
                label.setWordWrap(True)
                layout.addWidget(label)
        except Exception:
            self.plotter = None

    def _set_plotter_overlay_text(self, text: str) -> None:
        if self.plotter is None:
            return
        self.actor_manager.remove(self.plotter, 'scene_overlay')
        try:
            actor = self.plotter.add_text(text, font_size=10, name='scene_overlay')
            self.actor_manager.set('scene_overlay', actor)
        except Exception:
            actor = self.plotter.add_text(text, font_size=10)
            self.actor_manager.set('scene_overlay', actor)

    def _update_mesh(self, name: str, mesh, **kwargs) -> None:
        if self.plotter is None:
            return
        actor = self.actor_manager.get(name)
        if actor is None:
            actor = self.plotter.add_mesh(mesh, **kwargs)
            self.actor_manager.set(name, actor)
        else:
            mapper = actor.GetMapper()
            if mapper is not None:
                mapper.SetInputData(mesh)

    def _remove_mesh(self, name: str) -> None:
        self.actor_manager.remove(self.plotter, name)

    def _render(self) -> None:
        if self.plotter is None:
            return
        self.plotter.reset_camera_clipping_range()
        self.plotter.render()

    def set_robot_geometry(self, robot_geometry) -> None:
        self._robot_geometry = robot_geometry

    def set_scene_obstacles(self, obstacles) -> None:
        self._scene_obstacles = list(obstacles or [])

    def set_attached_objects(self, attached_objects) -> None:
        self._attached_objects = list(attached_objects or [])

    def set_overlay_text(self, text: str) -> None:
        self._overlay_text = str(text)
        self._set_plotter_overlay_text(self._overlay_text)
        self._render()

    def set_robot_lines(self, points: np.ndarray) -> None:
        pts = np.asarray(points, dtype=float)
        self._robot_points = pts.copy()
        if self.plotter is None or len(pts) < 2:
            return
        for name, (mesh, kwargs) in self.robot_visual.build(pts).items():
            self._update_mesh(name, mesh, **kwargs)
        self._render()

    def set_target_pose(self, pose) -> None:
        self._target_pose = pose
        if self.plotter is None:
            return
        payload = self.target_visual.build(pose, show_axes=self._target_axes_visible)
        for name, (mesh, kwargs) in payload.items():
            self._update_mesh(name, mesh, **kwargs)
        if not self._target_axes_visible:
            for axis_name in ('x', 'y', 'z'):
                self._remove_mesh(f'target_axis_{axis_name}')
        self._render()

    def set_trajectory(self, points: np.ndarray) -> None:
        if points is None:
            self.clear_trajectory()
            return
        pts = np.asarray(points, dtype=float)
        self._trajectory_points = pts.copy()
        if self.plotter is None or len(pts) < 2 or not self._trajectory_visible:
            return
        for name, (mesh, kwargs) in self.trajectory_visual.build(pts).items():
            self._update_mesh(name, mesh, **kwargs)
        self._render()

    def clear_trajectory(self) -> None:
        self._trajectory_points = None
        self._remove_mesh('trajectory')
        self._render()

    def set_playback_marker(self, point: np.ndarray) -> None:
        point_arr = np.asarray(point, dtype=float).reshape(3)
        self._playback_marker = point_arr.copy()
        if self.plotter is None:
            return
        import pyvista as pv

        marker = pv.PolyData(np.asarray([point_arr], dtype=float))
        self._update_mesh('playback_marker', marker, point_size=15, render_points_as_spheres=True)
        self._render()

    def fit_camera(self) -> None:
        if self.plotter is None:
            return
        self.plotter.reset_camera()
        self._render()

    def set_target_axes_visible(self, visible: bool) -> None:
        self._target_axes_visible = bool(visible)
        if self._target_pose is None:
            return
        if not self._target_axes_visible:
            for axis_name in ('x', 'y', 'z'):
                self._remove_mesh(f'target_axis_{axis_name}')
            self._render()
            return
        self.set_target_pose(self._target_pose)

    def set_trajectory_visible(self, visible: bool) -> None:
        self._trajectory_visible = bool(visible)
        if not visible:
            self._remove_mesh('trajectory')
            self._render()
            return
        if self._trajectory_points is not None:
            self.set_trajectory(self._trajectory_points)

    def scene_snapshot(self) -> dict[str, object]:
        return {
            'title': self._scene_title,
            'overlay_text': self._overlay_text,
            'robot_points': None if self._robot_points is None else self._robot_points.copy(),
            'trajectory_points': None if self._trajectory_points is None else self._trajectory_points.copy(),
            'playback_marker': None if self._playback_marker is None else self._playback_marker.copy(),
            'target_pose': self._target_pose,
            'target_axes_visible': bool(self._target_axes_visible),
            'trajectory_visible': bool(self._trajectory_visible),
            'robot_geometry': self._robot_geometry,
            'scene_obstacles': list(self._scene_obstacles),
            'attached_objects': list(self._attached_objects),
        }

    def capture_screenshot(self, path):
        return self.screenshot_service.capture(self, path)
