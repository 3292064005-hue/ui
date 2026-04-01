from __future__ import annotations

from pathlib import Path
import struct
import zlib

import numpy as np

from robot_sim.domain.errors import ExportRobotError
from robot_sim.render.robot_visual import RobotVisual
from robot_sim.render.target_visual import TargetVisual
from robot_sim.render.trajectory_visual import TrajectoryVisual


class ScreenshotService:
    def __init__(self) -> None:
        self._robot_visual = RobotVisual()
        self._target_visual = TargetVisual()
        self._trajectory_visual = TrajectoryVisual()

    def capture(self, scene_widget, path: str | Path):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        plotter = getattr(scene_widget, 'plotter', None)
        if plotter is not None and hasattr(plotter, 'screenshot'):
            plotter.screenshot(str(target))
            self._ensure_non_empty(target)
            return target

        snapshot_fn = getattr(scene_widget, 'scene_snapshot', None)
        snapshot = snapshot_fn() if callable(snapshot_fn) else None
        if snapshot:
            self._capture_from_snapshot(snapshot, target)
            self._ensure_non_empty(target)
            return target

        raise ExportRobotError(
            'scene capture backend is unavailable',
            error_code='unsupported_capture_backend',
            remediation_hint='安装 pyvista/pyvistaqt，或在产生场景数据后再执行截图。',
            metadata={'path': str(target)},
        )

    def _capture_from_snapshot(self, snapshot: dict[str, object], target: Path) -> None:
        robot_points = self._as_points(snapshot.get('robot_points'))
        trajectory_points = self._as_points(snapshot.get('trajectory_points'))
        playback_marker = self._as_point(snapshot.get('playback_marker'))
        target_pose = snapshot.get('target_pose')
        target_point = self._as_point(getattr(target_pose, 'p', None)) if target_pose is not None else None
        target_rotation = np.asarray(getattr(target_pose, 'R', np.eye(3)), dtype=float) if target_pose is not None else np.eye(3)
        show_target_axes = bool(snapshot.get('target_axes_visible', True))
        title = str(snapshot.get('title') or 'Robot Sim Engine')

        if robot_points is None and trajectory_points is None and playback_marker is None and target_point is None:
            raise ExportRobotError(
                'scene snapshot did not contain any drawable data',
                error_code='render_unavailable',
                remediation_hint='先执行 FK / IK / 轨迹规划，确保场景中存在机械臂、目标位姿或轨迹。',
                metadata={'path': str(target)},
            )

        canvas = np.full((480, 640, 3), 255, dtype=np.uint8)
        all_points = [arr for arr in (robot_points, trajectory_points) if arr is not None]
        if playback_marker is not None:
            all_points.append(playback_marker.reshape(1, 3))
        if target_point is not None:
            all_points.append(target_point.reshape(1, 3))
            if show_target_axes:
                axis_len = 0.12
                axes = np.stack(
                    [
                        target_point,
                        target_point + target_rotation[:, 0] * axis_len,
                        target_point,
                        target_point + target_rotation[:, 1] * axis_len,
                        target_point,
                        target_point + target_rotation[:, 2] * axis_len,
                    ],
                    axis=0,
                )
                all_points.append(axes)
        stacked = np.vstack(all_points)
        projected = self._project_points(stacked, canvas.shape[1], canvas.shape[0])
        cursor = 0

        if robot_points is not None:
            rp = projected[cursor: cursor + len(robot_points)]
            cursor += len(robot_points)
            self._draw_polyline(canvas, rp, color=(40, 90, 180), thickness=4)
            self._draw_points(canvas, rp, color=(20, 20, 20), radius=4)

        if trajectory_points is not None:
            tp = projected[cursor: cursor + len(trajectory_points)]
            cursor += len(trajectory_points)
            self._draw_polyline(canvas, tp, color=(220, 110, 30), thickness=2)
            self._draw_points(canvas, tp[-1:], color=(220, 110, 30), radius=4)

        if playback_marker is not None:
            pm = projected[cursor]
            cursor += 1
            self._draw_points(canvas, np.asarray([pm]), color=(180, 40, 40), radius=6)

        if target_point is not None:
            tg = projected[cursor]
            cursor += 1
            self._draw_cross(canvas, tg, color=(30, 160, 60), size=8, thickness=2)
            if show_target_axes:
                axis_pts = projected[cursor: cursor + 6]
                cursor += 6
                self._draw_segment(canvas, axis_pts[0], axis_pts[1], color=(230, 70, 70), thickness=2)
                self._draw_segment(canvas, axis_pts[2], axis_pts[3], color=(70, 180, 70), thickness=2)
                self._draw_segment(canvas, axis_pts[4], axis_pts[5], color=(70, 70, 230), thickness=2)

        self._draw_title_bar(canvas, title)
        self._write_png(target, canvas)

    @staticmethod
    def _as_points(value: object) -> np.ndarray | None:
        if value is None:
            return None
        arr = np.asarray(value, dtype=float)
        if arr.ndim != 2 or arr.shape[1] != 3 or arr.size == 0:
            return None
        return arr

    @staticmethod
    def _as_point(value: object) -> np.ndarray | None:
        if value is None:
            return None
        arr = np.asarray(value, dtype=float).reshape(-1)
        if arr.shape != (3,):
            return None
        return arr

    @staticmethod
    def _project_points(points: np.ndarray, width: int, height: int) -> np.ndarray:
        xy = np.column_stack([points[:, 0], -points[:, 2] - 0.35 * points[:, 1]])
        lo = xy.min(axis=0)
        hi = xy.max(axis=0)
        span = np.maximum(hi - lo, 1e-6)
        scale = min((width * 0.75) / span[0], (height * 0.68) / span[1])
        center = (lo + hi) * 0.5
        canvas_center = np.asarray([width * 0.5, height * 0.56], dtype=float)
        projected = (xy - center) * scale + canvas_center
        return np.rint(projected).astype(int)

    @staticmethod
    def _draw_title_bar(canvas: np.ndarray, title: str) -> None:
        canvas[:32, :, :] = np.array([245, 247, 250], dtype=np.uint8)
        hash_value = zlib.crc32(title.encode('utf-8'))
        accent = np.array([
            40 + (hash_value & 0x3F),
            90 + ((hash_value >> 6) & 0x3F),
            150 + ((hash_value >> 12) & 0x3F),
        ], dtype=np.uint8)
        canvas[8:24, 12:28, :] = accent
        canvas[12:20, 34:300, :] = np.array([70, 78, 92], dtype=np.uint8)
        title_width = min(240, max(60, len(title) * 6))
        canvas[14:18, 40:40 + title_width, :] = np.array([255, 255, 255], dtype=np.uint8)

    @classmethod
    def _draw_polyline(cls, canvas: np.ndarray, points: np.ndarray, *, color: tuple[int, int, int], thickness: int) -> None:
        if len(points) < 2:
            return
        for start, end in zip(points[:-1], points[1:]):
            cls._draw_segment(canvas, start, end, color=color, thickness=thickness)

    @classmethod
    def _draw_cross(cls, canvas: np.ndarray, point: np.ndarray, *, color: tuple[int, int, int], size: int, thickness: int) -> None:
        cls._draw_segment(canvas, point + np.array([-size, 0]), point + np.array([size, 0]), color=color, thickness=thickness)
        cls._draw_segment(canvas, point + np.array([0, -size]), point + np.array([0, size]), color=color, thickness=thickness)

    @staticmethod
    def _draw_points(canvas: np.ndarray, points: np.ndarray, *, color: tuple[int, int, int], radius: int) -> None:
        for px, py in points:
            y0 = max(py - radius, 0)
            y1 = min(py + radius + 1, canvas.shape[0])
            x0 = max(px - radius, 0)
            x1 = min(px + radius + 1, canvas.shape[1])
            if y0 >= y1 or x0 >= x1:
                continue
            yy, xx = np.ogrid[y0:y1, x0:x1]
            mask = (xx - px) ** 2 + (yy - py) ** 2 <= radius ** 2
            canvas[y0:y1, x0:x1][mask] = np.asarray(color, dtype=np.uint8)

    @staticmethod
    def _draw_segment(canvas: np.ndarray, start: np.ndarray, end: np.ndarray, *, color: tuple[int, int, int], thickness: int) -> None:
        start = np.asarray(start, dtype=int)
        end = np.asarray(end, dtype=int)
        delta = end - start
        steps = int(max(abs(delta[0]), abs(delta[1]), 1))
        xs = np.rint(np.linspace(start[0], end[0], steps + 1)).astype(int)
        ys = np.rint(np.linspace(start[1], end[1], steps + 1)).astype(int)
        half = max(thickness // 2, 0)
        color_arr = np.asarray(color, dtype=np.uint8)
        for x, y in zip(xs, ys):
            y0 = max(y - half, 0)
            y1 = min(y + half + 1, canvas.shape[0])
            x0 = max(x - half, 0)
            x1 = min(x + half + 1, canvas.shape[1])
            if y0 < y1 and x0 < x1:
                canvas[y0:y1, x0:x1] = color_arr

    @staticmethod
    def _write_png(path: Path, canvas: np.ndarray) -> None:
        if canvas.dtype != np.uint8 or canvas.ndim != 3 or canvas.shape[2] != 3:
            raise ExportRobotError(
                'invalid screenshot raster payload',
                error_code='invalid_screenshot_raster',
                remediation_hint='检查截图渲染阶段是否产生了 HxWx3 uint8 图像。',
                metadata={'shape': tuple(canvas.shape)},
            )
        height, width, _ = canvas.shape
        raw = b''.join(b'\x00' + canvas[row].tobytes() for row in range(height))
        compressed = zlib.compress(raw, level=9)
        ihdr = struct.pack('!IIBBBBB', width, height, 8, 2, 0, 0, 0)

        def chunk(tag: bytes, data: bytes) -> bytes:
            return struct.pack('!I', len(data)) + tag + data + struct.pack('!I', zlib.crc32(tag + data) & 0xFFFFFFFF)

        png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')
        path.write_bytes(png)

    @staticmethod
    def _ensure_non_empty(path: Path) -> None:
        if not path.exists() or path.stat().st_size <= 0:
            raise ExportRobotError(
                f'empty screenshot artifact was produced: {path}',
                error_code='empty_screenshot_artifact',
                remediation_hint='检查渲染后端是否可用，并确认场景中存在可绘制对象。',
            )
