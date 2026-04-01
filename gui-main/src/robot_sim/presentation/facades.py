from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from robot_sim.application.services.capability_service import CapabilityService
from robot_sim.application.services.metrics_service import MetricsService
from robot_sim.application.services.module_status_service import ModuleStatusService
from robot_sim.application.services.playback_service import PlaybackService
from robot_sim.application.services.robot_registry import RobotRegistry
from robot_sim.domain.error_projection import TaskErrorMapper
from robot_sim.model.app_config import AppConfig
from robot_sim.model.solver_config import SolverSettings
from robot_sim.presentation.controllers.benchmark_controller import BenchmarkController
from robot_sim.presentation.controllers.export_controller import ExportController
from robot_sim.presentation.controllers.ik_controller import IKController
from robot_sim.presentation.controllers.playback_controller import PlaybackController
from robot_sim.presentation.controllers.robot_controller import RobotController
from robot_sim.presentation.controllers.trajectory_controller import TrajectoryController
from robot_sim.presentation.state_store import StateStore


@dataclass(frozen=True)
class RuntimeFacade:
    """Narrow runtime surface exposed to the Qt shell."""

    project_root: Path
    resource_root: Path
    config_root: Path
    export_root: Path
    app_config: Mapping[str, object]
    app_settings: AppConfig
    state_store: StateStore
    metrics_service: MetricsService
    task_error_mapper: TaskErrorMapper
    capability_service: CapabilityService
    module_status_service: ModuleStatusService

    @property
    def state(self):
        """Return the live presentation session state.

        Returns:
            object: Shared presentation state snapshot.

        Raises:
            None: Thin property over the backing state store.
        """
        return self.state_store.state


@dataclass(frozen=True)
class RobotFacade:
    """Robot-library and forward-kinematics façade for the window shell."""

    registry: RobotRegistry
    controller: RobotController

    def robot_names(self) -> list[str]:
        return self.registry.list_names()

    def robot_entries(self):
        return self.registry.list_entries()

    def available_specs(self):
        return self.registry.list_specs()

    def load_robot(self, name: str):
        return self.controller.load_robot(name)

    def build_robot_from_editor(self, existing_spec, rows, home_q):
        return self.controller.build_robot_from_editor(existing_spec, rows, home_q)

    def save_current_robot(self, rows=None, home_q=None, name: str | None = None):
        return self.controller.save_current_robot(rows=rows, home_q=home_q, name=name)

    def run_fk(self, q=None):
        return self.controller.run_fk(q=q)

    def sample_ee_positions(self, q_samples):
        return self.controller.sample_ee_positions(q_samples)


@dataclass(frozen=True)
class SolverFacade:
    """Inverse-kinematics and solver-configuration façade."""

    solver_config: Mapping[str, object]
    solver_settings: SolverSettings
    controller: IKController
    ik_use_case: object

    def solver_defaults(self) -> dict[str, object]:
        return self.solver_settings.ik.as_dict()

    def build_target_pose(self, values6, orientation_mode: str = 'rvec'):
        return self.controller.build_target_pose(values6, orientation_mode=orientation_mode)

    def build_ik_request(self, values6, **kwargs):
        return self.controller.build_ik_request(values6, **kwargs)

    def apply_ik_result(self, req, result) -> None:
        self.controller.apply_ik_result(req, result)

    def run_ik(self, values6, **kwargs):
        return self.controller.run_ik(values6, **kwargs)


@dataclass(frozen=True)
class TrajectoryFacade:
    """Trajectory planning façade used by the task layer and widgets."""

    solver_config: Mapping[str, object]
    solver_settings: SolverSettings
    controller: TrajectoryController
    trajectory_use_case: object

    def trajectory_defaults(self) -> dict[str, object]:
        return self.solver_settings.trajectory.as_dict()

    def trajectory_goal_or_raise(self):
        return self.controller.trajectory_goal_or_raise()

    def build_trajectory_request(self, **kwargs):
        return self.controller.build_trajectory_request(**kwargs)

    def plan_trajectory(self, **kwargs):
        return self.controller.plan_trajectory(**kwargs)

    def apply_trajectory(self, traj) -> None:
        self.controller.apply_trajectory(traj)


@dataclass(frozen=True)
class PlaybackFacade:
    """Playback façade used by render/projection flows."""

    controller: PlaybackController
    playback_service: PlaybackService

    def current_playback_frame(self):
        return self.controller.current_playback_frame()

    def set_playback_frame(self, frame_idx: int):
        return self.controller.set_playback_frame(frame_idx)

    def next_playback_frame(self):
        return self.controller.next_playback_frame()

    def set_playback_options(self, *, speed_multiplier=None, loop_enabled=None) -> None:
        self.controller.set_playback_options(speed_multiplier=speed_multiplier, loop_enabled=loop_enabled)

    def ensure_playback_ready(self, *, strict: bool = True) -> None:
        self.controller.ensure_playback_ready(strict=strict)


@dataclass(frozen=True)
class BenchmarkFacade:
    """Benchmark façade exposed to the background task layer."""

    controller: BenchmarkController
    benchmark_use_case: object

    def build_benchmark_config(self, **kwargs):
        return self.controller.build_benchmark_config(**kwargs)

    def run_benchmark(self, config=None):
        return self.controller.run_benchmark(config=config)


@dataclass(frozen=True)
class ExportFacade:
    """Export façade for reports, sessions, metrics, and packages."""

    controller: ExportController

    def export_trajectory(self, name: str = 'trajectory.csv'):
        return self.controller.export_trajectory(name=name)

    def export_trajectory_bundle(self, name: str = 'trajectory_bundle.npz'):
        return self.controller.export_trajectory_bundle(name=name)

    def export_trajectory_metrics(self, name: str = 'trajectory_metrics.json', metrics: dict[str, object] | None = None):
        return self.controller.export_trajectory_metrics(name=name, metrics=metrics)

    def export_benchmark(self, name: str = 'benchmark_report.json'):
        return self.controller.export_benchmark(name=name)

    def export_benchmark_cases_csv(self, name: str = 'benchmark_cases.csv'):
        return self.controller.export_benchmark_cases_csv(name=name)

    def export_session(self, name: str = 'session.json'):
        return self.controller.export_session(name=name)

    def export_package(self, name: str = 'robot_sim_package.zip'):
        return self.controller.export_package(name=name)
