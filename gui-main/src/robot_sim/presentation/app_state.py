from __future__ import annotations

from robot_sim.domain.enums import AppExecutionState


APP_STATE_BY_BUSY_REASON: dict[str, AppExecutionState] = {
    'ik': AppExecutionState.SOLVING_IK,
    'trajectory': AppExecutionState.PLANNING_TRAJECTORY,
    'benchmark': AppExecutionState.BENCHMARKING,
    'export': AppExecutionState.EXPORTING,
}


def state_for_busy_reason(reason: str, *, default: AppExecutionState = AppExecutionState.IDLE) -> AppExecutionState:
    return APP_STATE_BY_BUSY_REASON.get(str(reason).strip().lower(), default)


__all__ = ['AppExecutionState', 'APP_STATE_BY_BUSY_REASON', 'state_for_busy_reason']
