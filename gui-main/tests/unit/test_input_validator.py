from __future__ import annotations

import numpy as np
import pytest

from robot_sim.presentation.validators.input_validator import InputValidator


def test_validate_joint_vector_can_clamp(planar_spec):
    q = InputValidator.validate_joint_vector(planar_spec, np.array([99.0, -99.0]), clamp=True)
    assert q[0] <= planar_spec.dh_rows[0].q_max
    assert q[1] >= planar_spec.dh_rows[1].q_min


def test_validate_home_q_rejects_out_of_limit(planar_spec):
    rows = list(planar_spec.dh_rows)
    with pytest.raises(ValueError):
        InputValidator.validate_home_q(rows, np.array([100.0, 0.0]))
