from __future__ import annotations

from dataclasses import dataclass, field
from robot_sim.domain.types import FloatArray


@dataclass(frozen=True)
class IKIterationLog:
    iter_idx: int
    pos_err_norm: float
    ori_err_norm: float
    cond_number: float
    manipulability: float
    dq_norm: float = 0.0
    elapsed_ms: float = 0.0
    effective_mode: str = ""
    attempt_idx: int = 0
    damping_lambda: float = 0.0
    score: float = 0.0
    step_clipped: bool = False


@dataclass(frozen=True)
class IKResult:
    success: bool
    q_sol: FloatArray
    logs: tuple[IKIterationLog, ...]
    message: str
    final_pos_err: float = float("nan")
    final_ori_err: float = float("nan")
    final_cond: float = float("nan")
    final_manipulability: float = float("nan")
    final_dq_norm: float = 0.0
    elapsed_ms: float = 0.0
    effective_mode: str = ""
    stop_reason: str = ""
    best_q: FloatArray | None = None
    restarts_used: int = 0
    diagnostics: dict[str, object] = field(default_factory=dict)
