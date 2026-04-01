from __future__ import annotations

from typing import Protocol

from robot_sim.application.registries.importer_registry import ImporterRegistry
from robot_sim.application.registries.planner_registry import PlannerRegistry
from robot_sim.application.registries.solver_registry import SolverRegistry
from robot_sim.application.services.capability_service import CapabilityService
from robot_sim.application.services.config_service import ConfigService
from robot_sim.application.services.export_service import ExportService
from robot_sim.application.services.metrics_service import MetricsService
from robot_sim.application.services.module_status_service import ModuleStatusService
from robot_sim.application.services.playback_service import PlaybackService
from robot_sim.application.services.robot_registry import RobotRegistry
from robot_sim.application.services.task_error_mapper import TaskErrorMapper
from robot_sim.application.use_cases.export_package import ExportPackageUseCase
from robot_sim.application.use_cases.export_report import ExportReportUseCase
from robot_sim.application.use_cases.import_robot import ImportRobotUseCase
from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
from robot_sim.application.use_cases.run_benchmark import RunBenchmarkUseCase
from robot_sim.application.use_cases.run_fk import RunFKUseCase
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.application.use_cases.save_session import SaveSessionUseCase
from robot_sim.application.use_cases.step_playback import StepPlaybackUseCase
from robot_sim.app.runtime_paths import RuntimePaths


class MainControllerContainerProtocol(Protocol):
    """Minimal dependency contract required by ``MainController``.

    The presentation layer still depends on the application composition root for startup,
    but only through this explicit attribute protocol rather than the concrete ``AppContainer``
    implementation.
    """

    config_service: ConfigService
    robot_registry: RobotRegistry
    metrics_service: MetricsService
    export_service: ExportService
    solver_registry: SolverRegistry
    planner_registry: PlannerRegistry
    importer_registry: ImporterRegistry
    capability_matrix_service: CapabilityService
    module_status_service: ModuleStatusService
    task_error_mapper: TaskErrorMapper
    fk_uc: RunFKUseCase
    ik_uc: RunIKUseCase
    traj_uc: PlanTrajectoryUseCase
    benchmark_uc: RunBenchmarkUseCase
    save_session_uc: SaveSessionUseCase
    playback_service: PlaybackService
    playback_uc: StepPlaybackUseCase
    export_report_uc: ExportReportUseCase
    export_package_uc: ExportPackageUseCase
    import_robot_uc: ImportRobotUseCase

    runtime_paths: RuntimePaths
