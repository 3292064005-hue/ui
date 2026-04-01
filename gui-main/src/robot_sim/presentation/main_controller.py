from __future__ import annotations

from pathlib import Path

from robot_sim.app.contracts import MainControllerContainerProtocol
from robot_sim.domain.capabilities import CapabilityDescriptor
from robot_sim.model.session_state import SessionState
from robot_sim.presentation.controllers.benchmark_controller import BenchmarkController
from robot_sim.presentation.controllers.diagnostics_controller import DiagnosticsController
from robot_sim.presentation.controllers.export_controller import ExportController
from robot_sim.presentation.controllers.ik_controller import IKController
from robot_sim.presentation.controllers.playback_controller import PlaybackController
from robot_sim.presentation.controllers.robot_controller import RobotController
from robot_sim.presentation.controllers.trajectory_controller import TrajectoryController
from robot_sim.presentation.facades import (
    BenchmarkFacade,
    ExportFacade,
    PlaybackFacade,
    RobotFacade,
    RuntimeFacade,
    SolverFacade,
    TrajectoryFacade,
)
from robot_sim.presentation.state_store import StateStore


class MainController:
    """Facade that exposes application services to the Qt layer.

    The controller now owns a set of narrower façades used by the main window and task
    coordinators. Legacy methods remain available and delegate to those façades to preserve
    backward compatibility with existing tests and call sites.
    """

    def __init__(self, project_root: str | Path, *, container: MainControllerContainerProtocol) -> None:
        """Create the main presentation controller.

        Args:
            project_root: Project root used to resolve configuration and exports.
            container: Explicitly built application container.

        Returns:
            None: Initializes controller collaborators and state.

        Raises:
            ValueError: If ``container`` is not provided.
        """
        if container is None:
            raise ValueError('MainController requires an explicit application container')
        self.project_root = Path(project_root)
        self.container = container
        self.runtime_paths = getattr(self.container, 'runtime_paths', None)
        self.config_service = self.container.config_service
        self.app_settings = self.config_service.load_app_settings()
        self.solver_settings = self.config_service.load_solver_settings()
        self.app_config = self.app_settings.as_dict()
        self.solver_config = self.solver_settings.as_dict()
        self.registry = self.container.robot_registry
        self.exporter = self.container.export_service
        self.metrics_service = self.container.metrics_service
        self.capability_service = self.container.capability_matrix_service
        self.module_status_service = self.container.module_status_service
        self.task_error_mapper = self.container.task_error_mapper
        self.export_report_uc = self.container.export_report_uc
        self.state_store = StateStore(SessionState())
        self.fk_uc = self.container.fk_uc
        self.ik_uc = self.container.ik_uc
        self.traj_uc = self.container.traj_uc
        self.benchmark_uc = self.container.benchmark_uc
        self.save_session_uc = self.container.save_session_uc
        self.playback_service = self.container.playback_service
        self.playback_uc = self.container.playback_uc
        self.export_package_uc = self.container.export_package_uc
        self.import_robot_uc = self.container.import_robot_uc
        self.diagnostics_controller = DiagnosticsController(self.state_store, self.metrics_service)

        self.robot_controller = RobotController(self.state_store, self.registry, self.fk_uc)
        self.ik_controller = IKController(self.state_store, self.solver_settings.ik.as_dict(), self.fk_uc, self.ik_uc)
        self.trajectory_controller = TrajectoryController(
            self.state_store,
            self.traj_uc,
            self.playback_service,
            self.ik_controller.build_ik_request,
        )
        self.playback_controller = PlaybackController(self.state_store, self.playback_service, self.playback_uc)
        self.benchmark_controller = BenchmarkController(self.state_store, self.benchmark_uc, self.ik_controller.build_ik_request)
        self.export_controller = ExportController(
            self.state_store,
            self.exporter,
            self.export_report_uc,
            self.save_session_uc,
            self.export_package_uc,
        )

        resource_root = self.project_root if self.runtime_paths is None else self.runtime_paths.resource_root
        config_root = self.project_root / 'configs' if self.runtime_paths is None else self.runtime_paths.config_root
        export_root = self.project_root / 'exports' if self.runtime_paths is None else self.runtime_paths.export_root
        self.runtime_facade = RuntimeFacade(
            project_root=self.project_root,
            resource_root=resource_root,
            config_root=config_root,
            export_root=export_root,
            app_config=self.app_config,
            app_settings=self.app_settings,
            state_store=self.state_store,
            metrics_service=self.metrics_service,
            task_error_mapper=self.task_error_mapper,
            capability_service=self.capability_service,
            module_status_service=self.module_status_service,
        )
        self.robot_facade = RobotFacade(self.registry, self.robot_controller)
        self.solver_facade = SolverFacade(self.solver_config, self.solver_settings, self.ik_controller, self.ik_uc)
        self.trajectory_facade = TrajectoryFacade(self.solver_config, self.solver_settings, self.trajectory_controller, self.traj_uc)
        self.playback_facade = PlaybackFacade(self.playback_controller, self.playback_service)
        self.benchmark_facade = BenchmarkFacade(self.benchmark_controller, self.benchmark_uc)
        self.export_facade = ExportFacade(self.export_controller)

        capability_matrix = self.capability_service.build_matrix(
            solver_registry=self.container.solver_registry,
            planner_registry=self.container.planner_registry,
            importer_registry=self.container.importer_registry,
        )
        self.state_store.patch_capabilities(capability_matrix)
        self.state_store.patch(module_statuses=self.module_status_service.snapshot())

    @property
    def state(self) -> SessionState:
        """Return the current presentation session state snapshot."""
        return self.state_store.state

    def capabilities(self) -> list[CapabilityDescriptor]:
        """Build capability descriptors for the current runtime container."""
        matrix = self.capability_service.build_matrix(
            solver_registry=self.container.solver_registry,
            planner_registry=self.container.planner_registry,
            importer_registry=self.container.importer_registry,
        )
        return [
            CapabilityDescriptor(
                'ik_solvers',
                'IK solvers',
                metadata={
                    'ids': self.container.solver_registry.ids(),
                    'descriptors': [
                        {
                            'id': desc.solver_id,
                            'aliases': list(desc.aliases),
                            'metadata': dict(desc.metadata),
                            'source': getattr(desc, 'source', ''),
                        }
                        for desc in self.container.solver_registry.descriptors()
                    ],
                    'matrix': matrix.as_dict()['solvers'],
                },
            ),
            CapabilityDescriptor(
                'trajectory_planners',
                'Trajectory planners',
                metadata={
                    'ids': self.container.planner_registry.ids(),
                    'descriptors': [
                        {
                            'id': desc.planner_id,
                            'aliases': list(desc.aliases),
                            'metadata': dict(desc.metadata),
                            'source': getattr(desc, 'source', ''),
                        }
                        for desc in self.container.planner_registry.descriptors()
                    ],
                    'matrix': matrix.as_dict()['planners'],
                },
            ),
            CapabilityDescriptor(
                'robot_importers',
                'Robot importers',
                metadata={
                    'ids': self.container.importer_registry.ids(),
                    'descriptors': [
                        {
                            'id': desc.importer_id,
                            'aliases': list(desc.aliases),
                            'metadata': dict(desc.metadata),
                        }
                        for desc in self.container.importer_registry.descriptors()
                    ],
                    'matrix': matrix.as_dict()['importers'],
                },
            ),
            CapabilityDescriptor('package_export', 'Package export'),
        ]

    def robot_names(self) -> list[str]:
        return self.robot_facade.robot_names()

    def robot_entries(self):
        return self.robot_facade.robot_entries()

    def available_specs(self):
        return self.robot_facade.available_specs()

    def solver_defaults(self) -> dict[str, object]:
        return self.solver_settings.ik.as_dict()

    def trajectory_defaults(self) -> dict[str, object]:
        return self.solver_settings.trajectory.as_dict()

    def import_robot(self, source: str, importer_id: str | None = None):
        return self.import_robot_uc.execute(source, importer_id=importer_id)

    def load_robot(self, name: str):
        return self.robot_facade.load_robot(name)

    def build_robot_from_editor(self, existing_spec, rows, home_q):
        return self.robot_facade.build_robot_from_editor(existing_spec, rows, home_q)

    def save_current_robot(self, rows=None, home_q=None, name: str | None = None):
        return self.robot_facade.save_current_robot(rows=rows, home_q=home_q, name=name)

    def run_fk(self, q=None):
        return self.robot_facade.run_fk(q=q)

    def sample_ee_positions(self, q_samples):
        return self.robot_facade.sample_ee_positions(q_samples)

    def build_target_pose(self, values6, orientation_mode: str = 'rvec'):
        return self.solver_facade.build_target_pose(values6, orientation_mode=orientation_mode)

    def build_ik_request(self, values6, **kwargs):
        return self.solver_facade.build_ik_request(values6, **kwargs)

    def apply_ik_result(self, req, result) -> None:
        self.solver_facade.apply_ik_result(req, result)

    def run_ik(self, values6, **kwargs):
        return self.solver_facade.run_ik(values6, **kwargs)

    def build_benchmark_config(self, **kwargs):
        return self.benchmark_facade.build_benchmark_config(**kwargs)

    def run_benchmark(self, config=None):
        return self.benchmark_facade.run_benchmark(config=config)

    def trajectory_goal_or_raise(self):
        return self.trajectory_facade.trajectory_goal_or_raise()

    def build_trajectory_request(self, **kwargs):
        return self.trajectory_facade.build_trajectory_request(**kwargs)

    def plan_trajectory(self, **kwargs):
        return self.trajectory_facade.plan_trajectory(**kwargs)

    def apply_trajectory(self, traj) -> None:
        self.trajectory_facade.apply_trajectory(traj)

    def current_playback_frame(self):
        return self.playback_facade.current_playback_frame()

    def set_playback_frame(self, frame_idx: int):
        return self.playback_facade.set_playback_frame(frame_idx)

    def next_playback_frame(self):
        return self.playback_facade.next_playback_frame()

    def set_playback_options(self, *, speed_multiplier=None, loop_enabled=None) -> None:
        self.playback_facade.set_playback_options(speed_multiplier=speed_multiplier, loop_enabled=loop_enabled)

    def export_trajectory(self, name: str = 'trajectory.csv'):
        return self.export_facade.export_trajectory(name=name)

    def export_trajectory_bundle(self, name: str = 'trajectory_bundle.npz'):
        return self.export_facade.export_trajectory_bundle(name=name)

    def export_trajectory_metrics(self, name: str = 'trajectory_metrics.json', metrics: dict[str, object] | None = None):
        return self.export_facade.export_trajectory_metrics(name=name, metrics=metrics)

    def export_benchmark(self, name: str = 'benchmark_report.json'):
        return self.export_facade.export_benchmark(name=name)

    def export_benchmark_cases_csv(self, name: str = 'benchmark_cases.csv'):
        return self.export_facade.export_benchmark_cases_csv(name=name)

    def export_session(self, name: str = 'session.json'):
        return self.export_facade.export_session(name=name)

    def export_package(self, name: str = 'robot_sim_package.zip'):
        return self.export_facade.export_package(name=name)
