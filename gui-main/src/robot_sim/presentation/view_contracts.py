from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RuntimeViewContract(Protocol):
    """Minimal runtime projection/read contract required by coordinators."""

    @property
    def state(self) -> Any: ...

    @property
    def state_store(self) -> Any: ...

    @property
    def export_root(self) -> Any: ...

    @property
    def task_error_mapper(self) -> Any: ...


@runtime_checkable
class RobotFacadeContract(Protocol):
    def robot_entries(self) -> Any: ...
    def load_robot(self, name: str) -> Any: ...
    def save_current_robot(self, rows=None, home_q=None, name: str | None = None) -> Any: ...
    def run_fk(self, q=None) -> Any: ...


@runtime_checkable
class SolverFacadeContract(Protocol):
    ik_use_case: Any

    def solver_defaults(self) -> dict[str, object]: ...
    def build_target_pose(self, values6, orientation_mode: str = 'rvec') -> Any: ...
    def build_ik_request(self, values6, **kwargs) -> Any: ...
    def apply_ik_result(self, req, result) -> None: ...


@runtime_checkable
class TrajectoryFacadeContract(Protocol):
    trajectory_use_case: Any

    def trajectory_defaults(self) -> dict[str, object]: ...
    def build_trajectory_request(self, **kwargs) -> Any: ...
    def apply_trajectory(self, traj) -> None: ...


@runtime_checkable
class PlaybackFacadeContract(Protocol):
    playback_service: Any

    def set_playback_frame(self, frame_idx: int) -> Any: ...
    def next_playback_frame(self) -> Any: ...
    def set_playback_options(self, *, speed_multiplier=None, loop_enabled=None) -> None: ...
    def ensure_playback_ready(self, strict: bool = True) -> None: ...


@runtime_checkable
class BenchmarkFacadeContract(Protocol):
    benchmark_use_case: Any

    def build_benchmark_config(self, **kwargs) -> Any: ...


@runtime_checkable
class ExportFacadeContract(Protocol):
    def export_trajectory(self, name: str = 'trajectory.csv') -> Any: ...
    def export_trajectory_metrics(self, name: str = 'trajectory_metrics.json', metrics: dict[str, object] | None = None) -> Any: ...
    def export_session(self, name: str = 'session.json') -> Any: ...
    def export_package(self, name: str = 'robot_sim_package.zip') -> Any: ...
    def export_benchmark(self, name: str = 'benchmark_report.json') -> Any: ...
    def export_benchmark_cases_csv(self, name: str = 'benchmark_cases.csv') -> Any: ...


@runtime_checkable
class MainWindowLike(Protocol):
    """Structural contract shared by coordinators, mixins, and GUI tests.

    The protocol now focuses on explicit façade injection and stable view-projection surfaces.
    Legacy tests may still attach ``controller`` to dummy windows, but coordinator/mixin primary
    paths are expected to consume the injected façade contracts below.
    """

    runtime_facade: RuntimeViewContract
    robot_facade: RobotFacadeContract
    solver_facade: SolverFacadeContract
    trajectory_facade: TrajectoryFacadeContract
    playback_facade: PlaybackFacadeContract
    benchmark_facade: BenchmarkFacadeContract
    export_facade: ExportFacadeContract
    metrics_service: Any
    threader: Any
    playback_threader: Any
    status_panel: Any
    benchmark_panel: Any
    solver_panel: Any
    playback_panel: Any
    target_panel: Any
    robot_panel: Any
    scene_controller: Any
    scene_widget: Any
    plots_manager: Any
    playback_render_scheduler: Any
    _pending_ik_request: Any
    _pending_traj_request: Any
