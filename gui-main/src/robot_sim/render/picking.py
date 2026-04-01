from __future__ import annotations

import numpy as np


class PickingController:
    def __init__(self) -> None:
        self._last_point: np.ndarray | None = None
        self._pose_hint: object | None = None

    @property
    def last_point(self):
        return None if self._last_point is None else self._last_point.copy()

    @property
    def pose_hint(self):
        return self._pose_hint

    def set_point(self, point) -> None:
        self._last_point = np.asarray(point, dtype=float).reshape(3)

    def set_pose_hint(self, pose) -> None:
        self._pose_hint = pose

    def clear(self) -> None:
        self._last_point = None
        self._pose_hint = None

    def to_target_pose_request(self):
        if self._last_point is None:
            return None
        if self._pose_hint is not None:
            return self._pose_hint
        return np.asarray(self._last_point, dtype=float).copy()
