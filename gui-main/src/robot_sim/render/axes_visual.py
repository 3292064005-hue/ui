from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AxisVisualConfig:
    scale: float = 0.12


def pose_axes_segments(origin, rotation, *, scale: float = 0.12) -> dict[str, np.ndarray]:
    origin_arr = np.asarray(origin, dtype=float).reshape(3)
    rotation_arr = np.asarray(rotation, dtype=float).reshape(3, 3)
    length = max(float(scale), 1.0e-6)
    return {
        axis_name: np.vstack([origin_arr, origin_arr + rotation_arr[:, idx] * length])
        for idx, axis_name in enumerate(('x', 'y', 'z'))
    }


def build_axes_meshes(origin, rotation, *, scale: float = 0.12):
    import pyvista as pv

    return {
        axis_name: pv.lines_from_points(points)
        for axis_name, points in pose_axes_segments(origin, rotation, scale=scale).items()
    }
