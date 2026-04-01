from __future__ import annotations

import numpy as np

from robot_sim.core.collision.geometry import AABB, aabb_from_points


def environment_collision_pairs(joint_positions, obstacles: list[tuple[str, AABB]], *, padding: float = 0.02, link_names: list[str] | None = None) -> list[list[tuple[str, str]]]:
    pts = np.asarray(joint_positions, dtype=float)
    if pts.ndim != 3 or pts.shape[1] < 2:
        return [[] for _ in range(int(pts.shape[0]) if pts.ndim >= 1 else 0)]
    names = link_names or [f'link_{i}' for i in range(pts.shape[1] - 1)]
    flags: list[list[tuple[str, str]]] = []
    for frame in pts:
        frame_pairs: list[tuple[str, str]] = []
        for i in range(frame.shape[0] - 1):
            arm_box = aabb_from_points(frame[i:i+2], padding=padding)
            for object_id, obstacle in obstacles:
                if arm_box.intersects(obstacle):
                    frame_pairs.append((str(names[i]), str(object_id)))
        flags.append(frame_pairs)
    return flags


def environment_collision_flags(points, obstacles: list[AABB], *, padding: float = 0.02) -> list[bool]:
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 3:
        return [False] * int(pts.shape[0])
    flags: list[bool] = []
    for frame in pts:
        arm_box = aabb_from_points(frame, padding=padding)
        flags.append(any(arm_box.intersects(ob) for ob in obstacles))
    return flags
