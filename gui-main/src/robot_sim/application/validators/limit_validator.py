from __future__ import annotations

import numpy as np


def evaluate_limit_summary(q, spec) -> tuple[list[str], dict[str, object]]:
    reasons: list[str] = []
    limit_summary: dict[str, object] = {'any_limit_violation': False, 'lower_violations': 0, 'upper_violations': 0}
    if spec is None:
        return reasons, limit_summary
    q = np.asarray(q, dtype=float)
    if q.ndim == 2 and q.shape[0] > 0:
        mins = np.array([row.q_min for row in spec.dh_rows], dtype=float)[None, :]
        maxs = np.array([row.q_max for row in spec.dh_rows], dtype=float)[None, :]
        lower = q < (mins - 1.0e-9)
        upper = q > (maxs + 1.0e-9)
        limit_summary['lower_violations'] = int(np.sum(lower))
        limit_summary['upper_violations'] = int(np.sum(upper))
        limit_summary['any_limit_violation'] = bool(limit_summary['lower_violations'] or limit_summary['upper_violations'])
        if limit_summary['any_limit_violation']:
            reasons.append('joint_limit_violation')
    return reasons, limit_summary
