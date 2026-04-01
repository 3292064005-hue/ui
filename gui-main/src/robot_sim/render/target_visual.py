from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from robot_sim.render.axes_visual import build_axes_meshes


@dataclass(frozen=True)
class TargetVisualConfig:
    point_size: float = 18.0
    axes_scale: float = 0.12
    axis_line_width: float = 3.0


class TargetVisual:
    def __init__(self, config: TargetVisualConfig | None = None) -> None:
        self.config = config or TargetVisualConfig()

    def build(self, pose, *, show_axes: bool = True) -> dict[str, tuple[object, dict[str, object]]]:
        import pyvista as pv

        point = pv.PolyData(np.asarray([pose.p], dtype=float))
        payload: dict[str, tuple[object, dict[str, object]]] = {
            'target_point': (
                point,
                {
                    'point_size': float(self.config.point_size),
                    'render_points_as_spheres': True,
                },
            )
        }
        if show_axes:
            axes_meshes = build_axes_meshes(pose.p, pose.R, scale=float(self.config.axes_scale))
            for axis_name, mesh in axes_meshes.items():
                payload[f'target_axis_{axis_name}'] = (mesh, {'line_width': float(self.config.axis_line_width)})
        return payload
