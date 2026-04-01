from __future__ import annotations

def has_converged(pos_err_norm: float, ori_err_norm: float, pos_tol: float, ori_tol: float) -> bool:
    return pos_err_norm <= pos_tol and ori_err_norm <= ori_tol
