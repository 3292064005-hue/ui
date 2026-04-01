from __future__ import annotations

from robot_sim.core.collision.geometry import AABB


def broad_phase_intersections(aabbs: list[AABB]) -> list[tuple[int, int]]:
    hits: list[tuple[int, int]] = []
    for i in range(len(aabbs)):
        for j in range(i + 1, len(aabbs)):
            if aabbs[i].intersects(aabbs[j]):
                hits.append((i, j))
    return hits
