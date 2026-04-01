from __future__ import annotations

from dataclasses import dataclass, field

from robot_sim.model.pose import Pose


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    target: Pose
    position_only: bool = False
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class BenchmarkCaseResult:
    case: BenchmarkCase
    success: bool
    stop_reason: str
    final_pos_err: float
    final_ori_err: float
    elapsed_ms: float
    restarts_used: int
