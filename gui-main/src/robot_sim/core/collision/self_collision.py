from __future__ import annotations

import numpy as np

from robot_sim.core.collision.aabb import broad_phase_intersections
from robot_sim.core.collision.geometry import aabb_from_points


def self_collision_pairs(joint_positions, *, link_padding: float = 0.03, ignore_adjacent: bool = True, link_names: list[str] | None = None) -> list[list[tuple[str, str]]]:
    joint_positions = np.asarray(joint_positions, dtype=float)
    if joint_positions.ndim != 3 or joint_positions.shape[1] < 2:
        return [[] for _ in range(int(joint_positions.shape[0]) if joint_positions.ndim >= 1 else 0)]
    names = link_names or [f'link_{i}' for i in range(joint_positions.shape[1] - 1)]
    all_pairs: list[list[tuple[str, str]]] = []
    for frame in joint_positions:
        aabbs = [aabb_from_points(frame[i:i+2], padding=link_padding) for i in range(frame.shape[0] - 1)]
        pairs_idx = broad_phase_intersections(aabbs)
        if ignore_adjacent:
            pairs_idx = [(i, j) for i, j in pairs_idx if abs(i - j) > 1]
        frame_pairs = [(str(names[i]), str(names[j])) for i, j in pairs_idx]
        all_pairs.append(frame_pairs)
    return all_pairs


def self_collision_flags(joint_positions, *, link_padding: float = 0.03, ignore_adjacent: bool = True) -> list[bool]:
    return [bool(pairs) for pairs in self_collision_pairs(joint_positions, link_padding=link_padding, ignore_adjacent=ignore_adjacent)]
