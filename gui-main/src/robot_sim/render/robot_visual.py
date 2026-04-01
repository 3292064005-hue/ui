from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RobotVisualConfig:
    line_width: float = 5.0
    joint_point_size: float = 12.0
    use_tube: bool = False
    tube_radius: float = 0.018


class RobotVisual:
    def __init__(self, config: RobotVisualConfig | None = None) -> None:
        self.config = config or RobotVisualConfig()
        self._cache_key: bytes | None = None
        self._cached_payload: dict[str, tuple[object, dict[str, object]]] | None = None

    def build(self, points) -> dict[str, tuple[object, dict[str, object]]]:
        import pyvista as pv

        pts = np.asarray(points, dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] != 3:
            raise ValueError('robot visual requires an (N, 3) point array with N >= 2')
        cache_key = pts.tobytes()
        if self._cache_key == cache_key and self._cached_payload is not None:
            return self._cached_payload
        line_mesh = pv.lines_from_points(pts)
        if self.config.use_tube:
            line_mesh = line_mesh.tube(radius=float(self.config.tube_radius))
        joints_mesh = pv.PolyData(pts)
        payload = {
            'robot_lines': (line_mesh, {'line_width': float(self.config.line_width)}),
            'robot_joints': (
                joints_mesh,
                {
                    'point_size': float(self.config.joint_point_size),
                    'render_points_as_spheres': True,
                },
            ),
        }
        self._cache_key = cache_key
        self._cached_payload = payload
        return payload
