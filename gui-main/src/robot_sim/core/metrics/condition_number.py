from __future__ import annotations
from robot_sim.core.math.linalg import safe_condition_number
from robot_sim.domain.types import FloatArray

def condition_number(J: FloatArray) -> float:
    return safe_condition_number(J)
