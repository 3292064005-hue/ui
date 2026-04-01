from __future__ import annotations

from robot_sim.core.math.so3 import rotation_error as so3_rotation_error
from robot_sim.domain.types import FloatArray


def orientation_error(R_target: FloatArray, R_current: FloatArray) -> FloatArray:
    """Canonical orientation error used across IK, validation, and diagnostics."""
    return so3_rotation_error(R_target, R_current)


rotation_error = orientation_error
