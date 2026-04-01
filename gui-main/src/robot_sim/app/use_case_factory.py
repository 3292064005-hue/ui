from __future__ import annotations

from dataclasses import dataclass

from robot_sim.application.registries.importer_registry import ImporterRegistry
from robot_sim.application.registries.planner_registry import PlannerRegistry
from robot_sim.application.registries.solver_registry import SolverRegistry
from robot_sim.application.services.benchmark_service import BenchmarkService
from robot_sim.application.services.export_service import ExportService
from robot_sim.application.services.package_service import PackageService
from robot_sim.application.services.playback_service import PlaybackService
from robot_sim.application.use_cases.export_package import ExportPackageUseCase
from robot_sim.application.use_cases.export_report import ExportReportUseCase
from robot_sim.application.use_cases.import_robot import ImportRobotUseCase
from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
from robot_sim.application.use_cases.run_benchmark import RunBenchmarkUseCase
from robot_sim.application.use_cases.run_fk import RunFKUseCase
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.application.use_cases.save_session import SaveSessionUseCase
from robot_sim.application.use_cases.step_playback import StepPlaybackUseCase


@dataclass(frozen=True)
class UseCaseBundle:
    fk_uc: RunFKUseCase
    ik_uc: RunIKUseCase
    traj_uc: PlanTrajectoryUseCase
    benchmark_uc: RunBenchmarkUseCase
    save_session_uc: SaveSessionUseCase
    playback_uc: StepPlaybackUseCase
    export_report_uc: ExportReportUseCase
    export_package_uc: ExportPackageUseCase
    import_robot_uc: ImportRobotUseCase


def build_use_case_bundle(
    *,
    solver_registry: SolverRegistry,
    planner_registry: PlannerRegistry,
    importer_registry: ImporterRegistry,
    benchmark_service: BenchmarkService,
    export_service: ExportService,
    package_service: PackageService,
    playback_service: PlaybackService,
) -> UseCaseBundle:
    fk_uc = RunFKUseCase()
    ik_uc = RunIKUseCase(solver_registry)
    traj_uc = PlanTrajectoryUseCase(planner_registry)
    benchmark_uc = RunBenchmarkUseCase(benchmark_service)
    save_session_uc = SaveSessionUseCase(export_service)
    playback_uc = StepPlaybackUseCase(playback_service)
    export_report_uc = ExportReportUseCase(export_service)
    export_package_uc = ExportPackageUseCase(package_service)
    import_robot_uc = ImportRobotUseCase(importer_registry)
    return UseCaseBundle(
        fk_uc=fk_uc,
        ik_uc=ik_uc,
        traj_uc=traj_uc,
        benchmark_uc=benchmark_uc,
        save_session_uc=save_session_uc,
        playback_uc=playback_uc,
        export_report_uc=export_report_uc,
        export_package_uc=export_package_uc,
        import_robot_uc=import_robot_uc,
    )
