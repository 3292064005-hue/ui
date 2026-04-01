from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TrajectoryVisualConfig:
    line_width: float = 3.0


class TrajectoryVisual:
    def __init__(self, config: TrajectoryVisualConfig | None = None) -> None:
        self.config = config or TrajectoryVisualConfig()

    def build(self, points) -> dict[str, tuple[object, dict[str, object]]]:
        import pyvista as pv

        pts = np.asarray(points, dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] != 3:
            raise ValueError('trajectory visual requires an (N, 3) point array with N >= 2')
        return {
            'trajectory': (
                pv.lines_from_points(pts),
                {'line_width': float(self.config.line_width)},
            )
        }
