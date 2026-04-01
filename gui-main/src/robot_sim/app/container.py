from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from robot_sim.app.plugin_loader import PluginLoader
from robot_sim.app.registry_factory import build_importer_registry, build_planner_registry, build_solver_registry
from robot_sim.app.runtime_paths import RuntimePaths, resolve_runtime_paths
from robot_sim.app.service_factory import (
    build_benchmark_service,
    build_capability_service,
    build_export_service,
    build_metrics_service,
    build_module_status_service,
    build_package_service,
    build_playback_service,
    build_runtime_feature_service,
)
from robot_sim.app.use_case_factory import UseCaseBundle, build_use_case_bundle
from robot_sim.application.registries.importer_registry import ImporterRegistry
from robot_sim.application.registries.planner_registry import PlannerRegistry
from robot_sim.application.registries.solver_registry import SolverRegistry
from robot_sim.application.services.benchmark_service import BenchmarkService
from robot_sim.application.services.capability_service import CapabilityService
from robot_sim.application.services.config_service import ConfigService
from robot_sim.application.services.export_service import ExportService
from robot_sim.application.services.metrics_service import MetricsService
from robot_sim.application.services.module_status_service import ModuleStatusService
from robot_sim.application.services.package_service import PackageService
from robot_sim.application.services.playback_service import PlaybackService
from robot_sim.application.services.runtime_feature_service import RuntimeFeaturePolicy
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


@dataclass
class AppContainer:
    """Application dependency container.

    Attributes:
        project_root: Compatibility project root retained for existing callers.
        runtime_paths: Explicit runtime filesystem layout used by startup, config, and export flows.
        config_service: Configuration loader for app and solver defaults.
        robot_registry: Persistent robot library registry.
        metrics_service: Metrics helper used by diagnostics and exports.
        export_service: Export facade for reports, sessions, and bundles.
        package_service: Release/package generation service.
        solver_registry: Registered IK solver catalogue.
        planner_registry: Registered trajectory planner catalogue.
        importer_registry: Registered robot importer catalogue.
        capability_matrix_service: Capability matrix builder.
        module_status_service: Module status snapshot service.
        task_error_mapper: Structured task error projection helper.
    """

    project_root: Path
    runtime_paths: RuntimePaths
    config_service: ConfigService
    robot_registry: RobotRegistry
    metrics_service: MetricsService
    export_service: ExportService
    package_service: PackageService
    solver_registry: SolverRegistry
    planner_registry: PlannerRegistry
    importer_registry: ImporterRegistry
    capability_matrix_service: CapabilityService
    module_status_service: ModuleStatusService
    task_error_mapper: TaskErrorMapper
    runtime_feature_policy: RuntimeFeaturePolicy
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
    startup_summary: dict[str, object] | None = None
    runtime_context: dict[str, object] | None = None


def _attach_use_cases(container_kwargs: dict[str, object], bundle: UseCaseBundle) -> dict[str, object]:
    """Attach the constructed use-case bundle to container keyword arguments.

    Args:
        container_kwargs: Mutable container constructor arguments.
        bundle: Built use-case bundle to merge into the container payload.

    Returns:
        dict[str, object]: Updated constructor keyword arguments.

    Raises:
        None: This helper only mutates the supplied mapping in place.
    """
    container_kwargs.update(
        fk_uc=bundle.fk_uc,
        ik_uc=bundle.ik_uc,
        traj_uc=bundle.traj_uc,
        benchmark_uc=bundle.benchmark_uc,
        save_session_uc=bundle.save_session_uc,
        playback_uc=bundle.playback_uc,
        export_report_uc=bundle.export_report_uc,
        export_package_uc=bundle.export_package_uc,
        import_robot_uc=bundle.import_robot_uc,
    )
    return container_kwargs


def build_container(project_root: str | Path | RuntimePaths) -> AppContainer:
    """Build the application dependency container.

    Args:
        project_root: Compatibility project root or pre-resolved runtime path bundle.

    Returns:
        AppContainer: Fully wired dependency container for the application runtime.

    Raises:
        Exception: Propagates configuration, registry, or service construction failures.
    """
    runtime_paths = project_root if isinstance(project_root, RuntimePaths) else resolve_runtime_paths(project_root)
    active_profile = str(os.environ.get('ROBOT_SIM_PROFILE', ConfigService.DEFAULT_PROFILE) or ConfigService.DEFAULT_PROFILE)
    config_service = ConfigService(runtime_paths.config_root, profile=active_profile)
    robot_registry = RobotRegistry(runtime_paths.robot_root)
    metrics_service = build_metrics_service()
    export_service = build_export_service(runtime_paths.export_root)
    package_service = build_package_service(runtime_paths.export_root)
    playback_service = build_playback_service()
    task_error_mapper = TaskErrorMapper()
    runtime_feature_service = build_runtime_feature_service(config_service)
    runtime_feature_policy = runtime_feature_service.load_policy()
    plugin_loader = PluginLoader(runtime_paths.plugin_manifest_path, policy=runtime_feature_policy)
    capability_matrix_service = build_capability_service(runtime_feature_policy=runtime_feature_policy)
    module_status_service = build_module_status_service(runtime_feature_policy=runtime_feature_policy)

    solver_registry = build_solver_registry(plugin_loader=plugin_loader)
    seed_ik_uc = RunIKUseCase(solver_registry)
    planner_registry = build_planner_registry(seed_ik_uc, plugin_loader=plugin_loader)
    importer_registry = build_importer_registry(robot_registry, plugin_loader=plugin_loader)
    benchmark_service: BenchmarkService = build_benchmark_service(seed_ik_uc)
    use_cases = build_use_case_bundle(
        solver_registry=solver_registry,
        planner_registry=planner_registry,
        importer_registry=importer_registry,
        benchmark_service=benchmark_service,
        export_service=export_service,
        package_service=package_service,
        playback_service=playback_service,
    )

    container_kwargs: dict[str, object] = dict(
        project_root=runtime_paths.project_root,
        runtime_paths=runtime_paths,
        config_service=config_service,
        robot_registry=robot_registry,
        metrics_service=metrics_service,
        export_service=export_service,
        package_service=package_service,
        solver_registry=solver_registry,
        planner_registry=planner_registry,
        importer_registry=importer_registry,
        capability_matrix_service=capability_matrix_service,
        module_status_service=module_status_service,
        task_error_mapper=task_error_mapper,
        runtime_feature_policy=runtime_feature_policy,
        playback_service=playback_service,
    )
    container = AppContainer(**_attach_use_cases(container_kwargs, use_cases))
    container.runtime_context = {
        'project_root': str(runtime_paths.project_root),
        'resource_root': str(runtime_paths.resource_root),
        'config_root': str(runtime_paths.config_root),
        'robot_root': str(runtime_paths.robot_root),
        'profiles_root': str(runtime_paths.profiles_root),
        'plugin_manifest_path': str(runtime_paths.plugin_manifest_path),
        'export_root': str(runtime_paths.export_root),
        'runtime_feature_policy': runtime_feature_policy.as_dict(),
        'profiles': config_service.available_profiles(),
        'plugin_discovery_enabled': runtime_feature_policy.plugin_discovery_enabled,
        'source_layout_available': runtime_paths.source_layout_available,
    }
    return container
