from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class AABB:
    minimum: np.ndarray
    maximum: np.ndarray

    def intersects(self, other: 'AABB') -> bool:
        return bool(np.all(self.maximum >= other.minimum) and np.all(other.maximum >= self.minimum))

    def distance(self, other: 'AABB') -> float:
        left_gap = other.minimum - self.maximum
        right_gap = self.minimum - other.maximum
        separation = np.maximum(np.maximum(left_gap, right_gap), 0.0)
        return float(np.linalg.norm(separation))


def aabb_from_points(points, padding: float = 0.0) -> AABB:
    pts = np.asarray(points, dtype=float)
    if pts.ndim == 1:
        pts = pts[None, :]
    pad = float(max(padding, 0.0))
    return AABB(minimum=np.min(pts, axis=0) - pad, maximum=np.max(pts, axis=0) + pad)
