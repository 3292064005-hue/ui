from __future__ import annotations

from pathlib import Path

from robot_sim.app.container import AppContainer
from robot_sim.presentation.coordinators import (
    BenchmarkTaskCoordinator,
    ExportTaskCoordinator,
    IKTaskCoordinator,
    PlaybackTaskCoordinator,
    RobotCoordinator,
    SceneCoordinator,
    StatusCoordinator,
    TrajectoryTaskCoordinator,
)
from robot_sim.presentation.main_controller import MainController
from robot_sim.presentation.main_window_actions import MainWindowActionMixin
from robot_sim.presentation.main_window_tasks import MainWindowTaskMixin
from robot_sim.presentation.main_window_ui import MainWindowUIMixin
from robot_sim.presentation.playback_render_scheduler import PlaybackRenderScheduler
from robot_sim.presentation.thread_orchestrator import ThreadOrchestrator

try:
    from PySide6.QtWidgets import QMainWindow
except Exception as exc:  # pragma: no cover
    raise RuntimeError('PySide6 is required to launch the GUI.') from exc


class MainWindow(QMainWindow, MainWindowTaskMixin, MainWindowActionMixin, MainWindowUIMixin):  # pragma: no cover - GUI shell
    """Top-level Qt window for the simulator UI."""

    def __init__(self, project_root: str | Path, *, container: AppContainer) -> None:
        """Create the top-level simulator window.

        Args:
            project_root: Project root used to resolve runtime resources.
            container: Explicitly built dependency container.

        Returns:
            None: Initializes the Qt window, façades, and application state.

        Raises:
            ValueError: If ``container`` is not provided.
        """
        super().__init__()
        if container is None:
            raise ValueError('MainWindow requires an explicit application container')
        self.controller = MainController(project_root, container=container)
        self.runtime_facade = self.controller.runtime_facade
        self.robot_facade = self.controller.robot_facade
        self.solver_facade = self.controller.solver_facade
        self.trajectory_facade = self.controller.trajectory_facade
        self.playback_facade = self.controller.playback_facade
        self.benchmark_facade = self.controller.benchmark_facade
        self.export_facade = self.controller.export_facade
        self.metrics_service = self.runtime_facade.metrics_service
        self.threader = ThreadOrchestrator(self)
        self.playback_threader = ThreadOrchestrator(self, start_policy='queue_latest')
        self.playback_render_scheduler = PlaybackRenderScheduler(self)
        self.robot_coordinator = RobotCoordinator(self, robot=self.robot_facade)
        self.ik_task_coordinator = IKTaskCoordinator(self, solver=self.solver_facade, threader=self.threader)
        self.trajectory_task_coordinator = TrajectoryTaskCoordinator(self, trajectory=self.trajectory_facade, threader=self.threader)
        self.benchmark_task_coordinator = BenchmarkTaskCoordinator(
            self,
            runtime=self.runtime_facade,
            benchmark=self.benchmark_facade,
            threader=self.threader,
        )
        self.playback_task_coordinator = PlaybackTaskCoordinator(
            self,
            runtime=self.runtime_facade,
            playback=self.playback_facade,
            playback_threader=self.playback_threader,
        )
        self.export_task_coordinator = ExportTaskCoordinator(self, runtime=self.runtime_facade, export=self.export_facade)
        self.scene_coordinator = SceneCoordinator(self, runtime=self.runtime_facade)
        self.status_coordinator = StatusCoordinator(self, runtime=self.runtime_facade)
        self._pending_ik_request = None
        self._pending_traj_request = None

        self.window_cfg = dict(self.runtime_facade.app_config.get('window', {}))
        self.setWindowTitle(str(self.window_cfg.get('title', 'Robot Sim Engine')))

        self._build_ui()
        self._wire_signals()
        self._wire_task_signals()
        self.playback_render_scheduler.flushed.connect(self.project_playback_frame)

        self.resize(int(self.window_cfg.get('width', 1680)), int(self.window_cfg.get('height', 980)))
        if self.robot_facade.robot_entries():
            self.on_load_robot()
