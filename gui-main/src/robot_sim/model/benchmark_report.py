from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BenchmarkReport:
    robot: str
    num_cases: int
    success_rate: float
    cases: tuple[dict[str, object], ...] = ()
    aggregate: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)
    comparison: dict[str, object] = field(default_factory=dict)
