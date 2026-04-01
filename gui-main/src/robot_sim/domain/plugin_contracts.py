from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IKSolverPlugin(Protocol):
    plugin_id: str

    def capabilities(self) -> dict[str, object]: ...

    def solve(self, spec, target, q0, config, *, cancel_flag=None, progress_cb=None, attempt_idx: int = 0): ...


@runtime_checkable
class TrajectoryPlannerPlugin(Protocol):
    planner_id: str

    def capabilities(self) -> dict[str, object]: ...

    def plan(self, req) -> Any: ...


@runtime_checkable
class TrajectoryRetimerPlugin(Protocol):
    plugin_id: str

    def capabilities(self) -> dict[str, object]: ...

    def retime(self, trajectory, *, max_velocity: float | None = None, max_acceleration: float | None = None): ...


@runtime_checkable
class RobotImporterPlugin(Protocol):
    importer_id: str

    def capabilities(self) -> dict[str, object]: ...

    def load(self, source, **kwargs): ...
