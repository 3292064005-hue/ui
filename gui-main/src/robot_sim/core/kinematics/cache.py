from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class FKCacheEntry:
    q: np.ndarray
    joint_positions: np.ndarray
    ee_position: np.ndarray


class FKFrameCache:
    def __init__(self) -> None:
        self._entries: list[FKCacheEntry] = []

    def __len__(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()

    def add(self, q, joint_positions, ee_position) -> None:
        self._entries.append(
            FKCacheEntry(
                q=np.asarray(q, dtype=float).copy(),
                joint_positions=np.asarray(joint_positions, dtype=float).copy(),
                ee_position=np.asarray(ee_position, dtype=float).copy(),
            )
        )

    def to_arrays(self) -> dict[str, np.ndarray] | None:
        if not self._entries:
            return None
        return {
            'q': np.asarray([entry.q for entry in self._entries], dtype=float),
            'joint_positions': np.asarray([entry.joint_positions for entry in self._entries], dtype=float),
            'ee_positions': np.asarray([entry.ee_position for entry in self._entries], dtype=float),
        }
