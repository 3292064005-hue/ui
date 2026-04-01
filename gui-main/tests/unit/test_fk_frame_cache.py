from __future__ import annotations

import numpy as np

from robot_sim.core.kinematics.cache import FKFrameCache


def test_fk_frame_cache_accumulates_and_exports_arrays():
    cache = FKFrameCache()
    cache.add([0.0, 1.0], [[0, 0, 0], [1, 0, 0]], [1, 0, 0])
    cache.add([1.0, 2.0], [[0, 0, 0], [2, 0, 0]], [2, 0, 0])
    exported = cache.to_arrays()
    assert exported is not None
    assert exported['q'].shape == (2, 2)
    assert exported['joint_positions'].shape == (2, 2, 3)
    assert np.allclose(exported['ee_positions'][1], [2.0, 0.0, 0.0])
