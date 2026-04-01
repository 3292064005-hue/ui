# mypy: disable-error-code="attr-defined,no-redef,arg-type"
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar


try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox, QSplitter, QTabWidget, QVBoxLayout, QWidget
except Exception:  # pragma: no cover
    Qt = type('Qt', (), {'Horizontal': 1, 'Vertical': 2})()

    class QWidget:
        def __init__(self, *args, **kwargs):
            pass

    class QSplitter:
        def __init__(self, *args, **kwargs):
            self.widgets = []

        def addWidget(self, widget):
            self.widgets.append(widget)

        def setSizes(self, sizes):
            self.sizes = list(sizes)

    class QVBoxLayout:
        def __init__(self, *args, **kwargs):
            self.children = []

        def addWidget(self, widget):
            self.children.append(widget)

    class QTabWidget(QWidget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.tabs = []

        def addTab(self, widget, label):
            self.tabs.append((widget, label))

    class QMessageBox:
        @staticmethod
        def critical(*args, **kwargs):
            return None

from robot_sim.presentation.app_state import state_for_busy_reason
from robot_sim.presentation.coordinators._helpers import require_dependency
from robot_sim.presentation.error_boundary import PresentationErrorBoundary
from robot_sim.presentation.widgets.benchmark_panel import BenchmarkPanel
from robot_sim.presentation.widgets.diagnostics_panel import DiagnosticsPanel
from robot_sim.presentation.widgets.playback_panel import PlaybackPanel
from robot_sim.presentation.widgets.plots_panel import PlotsPanel
from robot_sim.presentation.widgets.robot_config_panel import RobotConfigPanel
from robot_sim.presentation.widgets.scene_toolbar import SceneToolbar
from robot_sim.presentation.widgets.solver_panel import SolverPanel
from robot_sim.presentation.widgets.status_panel import StatusPanel
from robot_sim.presentation.widgets.target_pose_panel import TargetPosePanel
from robot_sim.render.plots_manager import PlotsManager
from robot_sim.render.scene_3d_widget import Scene3DWidget
from robot_sim.render.scene_controller import SceneController

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.presentation.view_contracts import MainWindowLike

_T = TypeVar('_T')


class MainWindowUIMixin:
    """UI-shell helpers and view-boundary projection methods."""

    def _runtime_ops(self: 'MainWindowLike'):
        """Return the required runtime façade injected by the main window shell."""
        return require_dependency(getattr(self, 'runtime_facade', None), 'runtime_facade')

    def _robot_ops(self: 'MainWindowLike'):
        """Return the required robot façade injected by the main window shell."""
        return require_dependency(getattr(self, 'robot_facade', None), 'robot_facade')

    def _solver_ops(self: 'MainWindowLike'):
        """Return the required solver façade injected by the main window shell."""
        return require_dependency(getattr(self, 'solver_facade', None), 'solver_facade')

    def _trajectory_ops(self: 'MainWindowLike'):
        """Return the required trajectory façade injected by the main window shell."""
        return require_dependency(getattr(self, 'trajectory_facade', None), 'trajectory_facade')

    def _playback_ops(self: 'MainWindowLike'):
        """Return the required playback façade injected by the main window shell."""
        return require_dependency(getattr(self, 'playback_facade', None), 'playback_facade')

    def _benchmark_ops(self: 'MainWindowLike'):
        """Return the required benchmark façade injected by the main window shell."""
        return require_dependency(getattr(self, 'benchmark_facade', None), 'benchmark_facade')

    def _export_ops(self: 'MainWindowLike'):
        """Return the required export façade injected by the main window shell."""
        return require_dependency(getattr(self, 'export_facade', None), 'export_facade')

    def _presentation_error_boundary(self: 'MainWindowLike') -> PresentationErrorBoundary:
        """Return the lazily constructed presentation error boundary."""
        boundary = getattr(self, '_error_boundary', None)
        if boundary is None:
            runtime = self._runtime_ops()
            boundary = PresentationErrorBoundary(
                mapper=runtime.task_error_mapper,
                state_store=runtime.state_store,
                dialog_sink=self._show_error,
                status_sink=self.status_panel.append,
            )
            self._error_boundary = boundary
        return boundary
    def _build_ui(self: 'MainWindowLike') -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)

        top_split = QSplitter(Qt.Horizontal)
        top_split.addWidget(self._build_left_column())
        top_split.addWidget(self._build_center_column())
        top_split.addWidget(self._build_right_column())
        top_split.setSizes([int(v) for v in self.window_cfg.get('splitter_sizes', [420, 820, 360])])

        self.plots_panel = PlotsPanel()
        self.plots_manager = PlotsManager(getattr(self.plots_panel, 'plot_widgets', None))

        v_split = QSplitter(Qt.Vertical)
        v_split.addWidget(top_split)
        v_split.addWidget(self.plots_panel)
        v_split.setSizes([int(v) for v in self.window_cfg.get('vertical_splitter_sizes', [700, 260])])
        root_layout.addWidget(v_split)

    def _build_left_column(self: 'MainWindowLike') -> QWidget:
        left = QWidget()
        left_layout = QVBoxLayout(left)
        robot_ops = self._robot_ops()
        solver_ops = self._solver_ops()
        trajectory_ops = self._trajectory_ops()
        self.robot_panel = RobotConfigPanel(robot_ops.robot_entries())
        self.target_panel = TargetPosePanel()
        self.solver_panel = SolverPanel()
        self.solver_panel.apply_defaults(solver_ops.solver_defaults())
        self.solver_panel.apply_trajectory_defaults(trajectory_ops.trajectory_defaults())
        left_layout.addWidget(self.robot_panel)
        left_layout.addWidget(self.target_panel)
        left_layout.addWidget(self.solver_panel)
        return left

    def _build_center_column(self: 'MainWindowLike') -> QWidget:
        center = QWidget()
        center_layout = QVBoxLayout(center)
        self.scene_widget = Scene3DWidget()
        self.scene_toolbar = SceneToolbar()
        self.scene_controller = SceneController(self.scene_widget)
        self.playback_panel = PlaybackPanel()
        center_layout.addWidget(self.scene_toolbar)
        center_layout.addWidget(self.scene_widget)
        center_layout.addWidget(self.playback_panel)
        return center

    def _build_right_column(self: 'MainWindowLike') -> QWidget:
        self.status_panel = StatusPanel()
        self.diagnostics_panel = DiagnosticsPanel()
        self.benchmark_panel = BenchmarkPanel()
        self.right_tabs = QTabWidget()
        self.right_tabs.addTab(self.status_panel, '状态')
        self.right_tabs.addTab(self.diagnostics_panel, '诊断')
        self.right_tabs.addTab(self.benchmark_panel, 'Benchmark')
        return self.right_tabs

    def _wire_signals(self: 'MainWindowLike') -> None:
        self.robot_panel.load_button.clicked.connect(self.on_load_robot)
        self.robot_panel.save_button.clicked.connect(self.on_save_robot)
        self.target_panel.fill_current_btn.clicked.connect(self.on_fill_current_pose)
        self.solver_panel.run_fk_btn.clicked.connect(self.on_run_fk)
        self.solver_panel.run_ik_btn.clicked.connect(self.on_run_ik)
        self.solver_panel.cancel_btn.clicked.connect(self.on_cancel_ik)
        self.solver_panel.plan_btn.clicked.connect(self.on_plan)
        self.playback_panel.play_btn.clicked.connect(self.on_play)
        self.playback_panel.pause_btn.clicked.connect(self.on_pause)
        self.playback_panel.stop_btn.clicked.connect(self.on_stop_playback)
        self.playback_panel.step_btn.clicked.connect(self.on_step)
        self.playback_panel.slider.valueChanged.connect(self.on_seek_frame)
        self.playback_panel.speed.valueChanged.connect(self.on_playback_speed_changed)
        self.playback_panel.loop.toggled.connect(self.on_playback_loop_changed)
        self.playback_panel.export_btn.clicked.connect(self.on_export_trajectory)
        self.playback_panel.session_btn.clicked.connect(self.on_export_session)
        self.playback_panel.package_btn.clicked.connect(self.on_export_package)
        self.scene_toolbar.fit_requested.connect(self.on_fit_scene)
        self.scene_toolbar.clear_path_requested.connect(self.on_clear_scene_path)
        self.scene_toolbar.screenshot_requested.connect(self.on_capture_scene)
        self.scene_toolbar.target_axes_toggled.connect(self.scene_widget.set_target_axes_visible)
        self.scene_toolbar.trajectory_toggled.connect(self.scene_widget.set_trajectory_visible)
        self.benchmark_panel.run_btn.clicked.connect(self.on_run_benchmark)
        self.benchmark_panel.export_btn.clicked.connect(self.on_export_benchmark)

    def _wire_task_signals(self: 'MainWindowLike') -> None:
        self.threader.task_state_changed.connect(self._on_task_state_changed)
        self.playback_threader.task_state_changed.connect(self._on_task_state_changed)

    def _show_error(self: 'MainWindowLike', title: str, exc: Exception | str) -> None:
        QMessageBox.critical(self, title, str(exc))

    def _project_exception(self: 'MainWindowLike', exc: Exception | str, *, title: str = '错误') -> None:
        """Project a presentation-layer exception through the structured error mapper.

        Args:
            exc: Exception instance or message raised at the presentation boundary.
            title: Fallback dialog title when no structured title is available.

        Returns:
            None: Updates state and shows a user-facing error dialog.

        Raises:
            None: Errors are converted into presentation data.
        """
        self._presentation_error_boundary().project_exception(exc, title=title)

    def _run_presented(self: 'MainWindowLike', callback: Callable[[], _T], *, title: str = '错误') -> _T | None:
        """Run a presentation-bound callback under the shared error projection boundary.

        Args:
            callback: Side-effecting UI callback to execute.
            title: Fallback title for unexpected failures.

        Returns:
            Optional callback result when the action succeeds.

        Raises:
            None: All exceptions are normalized through ``_project_exception``.
        """
        return self._presentation_error_boundary().run_presented(callback, title=title)

    def _append_projected_error(self: 'MainWindowLike', prefix: str, exc: Exception | str) -> None:
        """Append a structured presentation error to the status panel without showing a dialog.

        Args:
            prefix: Leading status text for the projected error.
            exc: Exception instance or message raised at the presentation boundary.

        Returns:
            None: Updates state and appends a status-row error summary.

        Raises:
            None: Errors are converted into presentation data.
        """
        self._presentation_error_boundary().append_projected_error(prefix, exc)


    def _run_status_projected(self: 'MainWindowLike', callback: Callable[[], _T], *, prefix: str) -> _T | None:
        """Run a callback and append a structured error summary to the status panel on failure.

        Args:
            callback: Side-effecting UI callback to execute.
            prefix: Leading status-row text for projected failures.

        Returns:
            Optional callback result when the action succeeds.

        Raises:
            None: All exceptions are normalized through ``_append_projected_error``.
        """
        return self._presentation_error_boundary().run_status_projected(callback, prefix=prefix)

    def _set_busy(self: 'MainWindowLike', busy: bool, reason: str = '') -> None:
        runtime = self._runtime_ops()
        next_state = state_for_busy_reason(reason) if busy else (
            runtime.state.app_state
            if runtime.state.robot_spec is None
            else state_for_busy_reason('', default=runtime.state.app_state)
        )
        if not busy and runtime.state.robot_spec is not None:
            from robot_sim.domain.enums import AppExecutionState

            next_state = AppExecutionState.ROBOT_READY if runtime.state.last_error == '' else runtime.state.app_state
        runtime.state_store.patch(
            is_busy=busy,
            busy_reason=reason,
            app_state=next_state,
            active_task_kind=reason if busy else '',
            active_task_id='' if not busy else runtime.state.active_task_id,
        )
        self.solver_panel.set_running(busy)
        self.benchmark_panel.set_running(busy)
        if not busy:
            self.status_panel.set_metrics(playback=self._playback_status_text())

    def _set_playback_running(self: 'MainWindowLike', running: bool) -> None:
        self.playback_panel.set_running(running)
        runtime = self._runtime_ops()
        playback = runtime.state.playback.play() if running else runtime.state.playback.pause()
        from robot_sim.domain.enums import AppExecutionState

        runtime.state_store.patch(
            playback=playback,
            app_state=AppExecutionState.PLAYING if running else (
                AppExecutionState.ROBOT_READY if runtime.state.robot_spec is not None else AppExecutionState.IDLE
            ),
            active_task_kind='playback' if running else '',
            active_task_id=runtime.state.active_task_id if running else '',
        )
        self.status_panel.set_metrics(playback=self._playback_status_text())

    def _playback_status_text(self: 'MainWindowLike') -> str:
        pb = self._runtime_ops().state.playback
        if pb.total_frames <= 0:
            return '无轨迹'
        return f"{'播放中' if pb.is_playing else '就绪'} @ {pb.speed_multiplier:.1f}x"

    def _build_solver_kwargs(self: 'MainWindowLike') -> dict[str, object]:
        return dict(
            orientation_mode=self.target_panel.orientation_mode.currentText(),
            mode=self.solver_panel.mode_combo.currentText(),
            max_iters=self.solver_panel.max_iters.value(),
            step_scale=self.solver_panel.step_scale.value(),
            damping=self.solver_panel.damping.value(),
            enable_nullspace=self.solver_panel.enable_nullspace.isChecked(),
            position_only=self.solver_panel.position_only.isChecked(),
            pos_tol=self.solver_panel.pos_tol.value(),
            ori_tol=self.solver_panel.ori_tol.value(),
            max_step_norm=self.solver_panel.max_step_norm.value(),
            auto_fallback=self.solver_panel.auto_fallback.isChecked(),
            reachability_precheck=self.solver_panel.reachability_precheck.isChecked(),
            retry_count=self.solver_panel.retry_count.value(),
            joint_limit_weight=self.solver_panel.joint_limit_weight.value(),
            manipulability_weight=self.solver_panel.manipulability_weight.value(),
            orientation_weight=self.solver_panel.orientation_weight.value(),
            adaptive_damping=self.solver_panel.adaptive_damping.isChecked(),
            use_weighted_least_squares=self.solver_panel.weighted_ls.isChecked(),
        )

    def _update_diagnostics_from_trajectory(self: 'MainWindowLike', metrics: dict[str, object]) -> None:
        self.diagnostics_panel.set_values(
            traj_mode=metrics.get('mode', '-'),
            traj_feasible='是' if metrics.get('feasible', True) else '否',
            traj_reasons=metrics.get('feasibility_reasons', '-') or '-',
            path_length=f"{float(metrics.get('path_length', 0.0) or 0.0):.4f}",
            jerk_proxy=f"{float(metrics.get('jerk_proxy', 0.0) or 0.0):.4e}",
        )

    def _update_diagnostics_from_benchmark(self: 'MainWindowLike', summary: dict[str, object]) -> None:
        self.diagnostics_panel.set_values(
            bench_success=f"{float(summary.get('success_rate', 0.0) or 0.0):.1%}",
            bench_p95=f"{float(summary.get('p95_elapsed_ms', 0.0) or 0.0):.1f}",
            bench_restarts=f"{float(summary.get('mean_restarts_used', 0.0) or 0.0):.2f}",
        )

    def _sync_status_after_snapshot(self: 'MainWindowLike') -> None:
        self.status_panel.set_metrics(playback=self._playback_status_text())

    def project_task_started(self: 'MainWindowLike', task_kind: str, message: str) -> None:
        """Project a newly started background task into busy state and status text."""
        self._set_busy(True, str(task_kind))
        self.status_panel.append(str(message))

    def project_task_registered(self: 'MainWindowLike', task_id: str, task_kind: str) -> None:
        """Project the active task identity into the shared state store."""
        self._runtime_ops().state_store.patch(active_task_id=str(task_id), active_task_kind=str(task_kind))

    def project_task_snapshot(self: 'MainWindowLike', snapshot) -> None:
        """Project a structured task snapshot into the state store and status strip."""
        self._runtime_ops().state_store.patch_task(snapshot)
        self._sync_status_after_snapshot()

    def project_busy_state(self: 'MainWindowLike', busy: bool, reason: str = '') -> None:
        """Project busy/idle state into the shell status."""
        self._set_busy(bool(busy), str(reason or ''))

    def read_selected_robot_name(self: 'MainWindowLike') -> str:
        """Read the currently selected robot identifier from the view."""
        return str(self.robot_panel.selected_robot_name())

    def read_robot_editor_state(self: 'MainWindowLike') -> dict[str, object]:
        """Read the editable robot-configuration payload from the view."""
        return {
            'rows': self.robot_panel.edited_rows(),
            'home_q': self.robot_panel.edited_home_q(),
            'name': self.robot_panel.selected_robot_name(),
        }

    def read_solver_kwargs(self: 'MainWindowLike') -> dict[str, object]:
        """Read the current solver keyword arguments from the view shell."""
        return self._build_solver_kwargs()

    def read_ik_request(self: 'MainWindowLike'):
        """Read the current IK request assembled from UI state."""
        return self._build_ik_request()

    def read_trajectory_request(self: 'MainWindowLike'):
        """Read the current trajectory-planning request assembled from UI state."""
        return self._build_trajectory_request()

    def read_playback_launch_options(self: 'MainWindowLike') -> dict[str, object]:
        """Read the current playback launch options from the UI controls."""
        return {
            'speed_multiplier': float(self.playback_panel.speed.value()),
            'loop_enabled': bool(self.playback_panel.loop.isChecked()),
        }

    def project_playback_started(self: 'MainWindowLike') -> None:
        """Project playback start into the visible UI state."""
        self._set_playback_running(True)

    def project_playback_stopped(self: 'MainWindowLike', *, reset_frame: bool = False) -> None:
        """Project playback stop/pause state into the visible UI shell.

        Args:
            reset_frame: Whether to rewind the visible playback cursor to frame zero.

        Returns:
            None: Updates visible playback state in place.

        Raises:
            RuntimeError: Propagates playback-cache contract violations when rewinding a
                non-playable trajectory.

        Boundary behavior:
            The rewind path applies the first cached playback frame directly instead of routing
            back through ``on_seek_frame``. This avoids action-loop re-entry and preserves a
            strict cached-geometry requirement for playback projection.
        """
        scheduler = getattr(self, 'playback_render_scheduler', None)
        if scheduler is not None:
            scheduler.flush()
        self._set_playback_running(False)
        if reset_frame:
            runtime = self._runtime_ops()
            traj = runtime.state.trajectory
            if traj is not None and bool(getattr(traj, 'is_playback_ready', False)):
                frame = self._playback_ops().set_playback_frame(0)
                self._schedule_playback_frame(frame, live=False, immediate=True)

    def project_playback_frame(self: 'MainWindowLike', frame, live: bool = False) -> None:
        """Project a coalesced playback/seek frame into the UI shell."""
        del live
        self._apply_playback_frame(frame)

    def project_worker_failure(self: 'MainWindowLike', presentation) -> None:
        """Project a structured worker failure presentation into state and dialog UI."""
        runtime = self._runtime_ops()
        runtime.state_store.patch_error(presentation)
        from robot_sim.domain.enums import AppExecutionState

        runtime.state_store.patch(app_state=AppExecutionState.ERROR)
        self._show_error(presentation.title, presentation.user_message)

    def project_robot_loaded(self: 'MainWindowLike', fk) -> None:
        """Project a freshly loaded robot into the visible UI panels."""
        runtime = self._runtime_ops()
        self.robot_panel.set_robot_spec(runtime.state.robot_spec)
        self.scene_controller.reset_path()
        self.scene_controller.update_fk_projection(fk)
        self.target_panel.set_from_pose(fk.ee_pose)
        self.playback_panel.set_total_frames(0)
        self.benchmark_panel.summary.setText('尚未运行 benchmark')
        self.benchmark_panel.log.clear()
        self.status_panel.summary.setText(f"已加载机器人：{runtime.state.robot_spec.label}")
        self.status_panel.set_metrics(playback=self._playback_status_text())
        self.status_panel.append('机器人加载完成')

    def project_robot_saved(self: 'MainWindowLike', path) -> None:
        """Project a successful robot-save result into the status panel."""
        self.status_panel.append(f'机器人配置已保存：{path}')

    def project_ik_result(self: 'MainWindowLike', result, summary: dict[str, object]) -> None:
        """Project a completed IK solve into summary widgets."""
        runtime = self._runtime_ops()
        fk = runtime.state.fk_result
        self.scene_controller.update_fk_projection(fk, runtime.state.target_pose)
        self.status_panel.summary.setText(
            f"IK {'收敛' if result.success else '失败'} | iters={summary['iterations']} | pos={summary['final_pos_err']:.3e}"
        )
        self.status_panel.set_metrics(
            iterations=summary['iterations'],
            pos_err=f"{summary['final_pos_err']:.4e}",
            ori_err=f"{summary['final_ori_err']:.4e}",
            cond=f"{summary['final_cond']:.4e}",
            manip=f"{summary['final_manipulability']:.4e}",
            dq_norm=f"{summary['final_dq_norm']:.4e}",
            mode=summary['effective_mode'] or '-',
            damping=f"{summary['final_damping']:.3e}",
            stop_reason=summary['stop_reason'] or '-',
            elapsed=f"{summary['elapsed_ms']:.1f}",
            playback=self._playback_status_text(),
        )
        self.status_panel.append(result.message)

    def project_trajectory_result(self: 'MainWindowLike', traj, metrics: dict[str, object], ee_points) -> None:
        """Project a completed trajectory into playback widgets and diagnostics.

        Args:
            traj: Planned trajectory already committed into presentation state.
            metrics: Summarized trajectory metrics for status and diagnostics.
            ee_points: Cached end-effector samples when available.

        Returns:
            None: Updates widgets and diagnostics in place.

        Raises:
            RuntimeError: Does not fabricate missing playback caches; unplayable trajectories are
                left in a non-playing state with an explicit status message.

        Boundary behavior:
            This method never triggers action-layer seek callbacks. When playback caches are
            complete it applies frame zero directly; otherwise it keeps the cursor reset without
            performing UI-thread FK recomputation.
        """
        self.playback_panel.set_total_frames(traj.t.shape[0])
        self.playback_panel.set_frame(0, traj.t.shape[0])
        if ee_points is not None:
            import numpy as np

            arr = np.asarray(ee_points, dtype=float)
            if arr.size:
                self.scene_controller.set_trajectory_from_fk_samples(arr)
        self.status_panel.append(f'轨迹已生成：{traj.q.shape[0]} 个采样点')
        self.status_panel.summary.setText(
            f"轨迹完成 | mode={metrics['mode']} | samples={metrics['num_samples']} | duration={metrics['duration']:.2f}s"
        )
        self.status_panel.set_metrics(playback=self._playback_status_text())
        self._update_diagnostics_from_trajectory(metrics)
        if bool(getattr(traj, 'is_playback_ready', False)):
            frame = self._playback_ops().set_playback_frame(0)
            self._schedule_playback_frame(frame, live=False, immediate=True)
        else:
            self.status_panel.append('轨迹已生成，但播放缓存未准备完成；已禁止实时播放。')

    def project_benchmark_result(self: 'MainWindowLike', report, summary: dict[str, object]) -> None:
        """Project a completed benchmark report into diagnostics widgets."""
        self.benchmark_panel.set_report({'num_cases': report.num_cases, 'success_rate': report.success_rate, 'cases': list(report.cases)})
        self._update_diagnostics_from_benchmark(summary)
        self.status_panel.summary.setText(
            f"Benchmark 完成 | cases={summary['num_cases']} | success={summary['success_rate']:.1%}"
        )
        self.status_panel.append('Benchmark 运行完成')

    def project_export_messages(self: 'MainWindowLike', *messages: str) -> None:
        """Append one or more export-status messages to the status panel."""
        for message in messages:
            self.status_panel.append(str(message))

    def project_scene_fit(self: 'MainWindowLike') -> None:
        """Project a scene-fit action into the UI."""
        self.scene_widget.fit_camera()
        self.status_panel.append('3D 视图已适配到当前场景')

    def project_scene_path_cleared(self: 'MainWindowLike') -> None:
        """Project a cleared transient scene path into the UI."""
        self.scene_controller.clear_transient_visuals()
        self.scene_widget.clear_trajectory()
        self.status_panel.append('末端轨迹显示已清空')

    def capture_scene_screenshot(self: 'MainWindowLike', path) -> object:
        """Capture the current 3D scene to ``path`` through the view shell."""
        return self.scene_widget.capture_screenshot(path)

    def project_scene_capture(self: 'MainWindowLike', result) -> None:
        """Project a saved scene capture into the status panel."""
        self.status_panel.append(f'场景截图已导出：{result}')
