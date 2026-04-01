from __future__ import annotations

import numpy as np


def evaluate_timing_summary(t) -> tuple[list[str], dict[str, object]]:
    reasons: list[str] = []
    t = np.asarray(t, dtype=float)
    timing_summary: dict[str, object] = {'num_non_positive_dt': 0, 'monotonic_time': True}
    if t.size >= 2:
        dt = np.diff(t)
        non_positive = int(np.sum(dt <= 0.0))
        timing_summary['num_non_positive_dt'] = non_positive
        timing_summary['monotonic_time'] = non_positive == 0
        if non_positive:
            reasons.append('non_monotonic_time')
    return reasons, timing_summary
