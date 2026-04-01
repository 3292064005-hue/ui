from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from robot_sim.application.workers.benchmark_worker import BenchmarkWorker
from robot_sim.application.workers.ik_worker import IKWorker
from robot_sim.application.workers.playback_worker import PlaybackWorker
from robot_sim.application.workers.trajectory_worker import TrajectoryWorker
from robot_sim.presentation.coordinators._helpers import require_dependency

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.presentation.view_contracts import MainWindowLike


class MainWindowTaskMixin:
    """Backward-compatible task mixin that delegates orchestration to coordinators."""

    def _playback_worker_factory(self: 'MainWindowLike', traj):
        """Create the playback worker used by the playback coordinator."""
        playback_ops = self._playback_ops()
        runtime = self._runtime_ops()
        return PlaybackWorker(traj, runtime.state.playback, playback_ops.playback_service)

    def _build_ik_request(self: 'MainWindowLike'):
        """Build the current IK request from visible UI state."""
        values = self.target_panel.values6()
        return self._solver_ops().build_ik_request(values, **self._build_solver_kwargs())

    def on_run_ik(self: 'MainWindowLike') -> None:
        """Entry point wired to the IK run button."""
        self.ik_task_coordinator.run()

    def _run_ik_impl(self: 'MainWindowLike') -> None:
        """Backward-compatible compatibility wrapper for legacy IK launch tests."""
        runner = getattr(self.ik_task_coordinator, 'start_task', None)
        if callable(runner):
            runner()
            return
        solver_ops = self._solver_ops()
        runtime = self._runtime_ops()

        def action() -> None:
            req = self._build_ik_request()
            ik_use_case = require_dependency(getattr(solver_ops, 'ik_use_case', None), 'solver_facade.ik_use_case')
            worker = IKWorker(req, ik_use_case)
            self._pending_ik_request = req
            self._set_busy(True, 'ik')
            self.status_panel.append('IK 任务已启动')
            task = self.threader.start(
                worker=worker,
                on_progress=self.on_ik_progress,
                on_finished=self.on_ik_finished,
                on_failed=self.on_worker_failed,
                on_cancelled=self.on_worker_cancelled,
                task_kind='ik',
            )
            runtime.state_store.patch(active_task_id=task.task_id, active_task_kind=task.task_kind)

        self._run_presented(action, title='错误')

    def on_cancel_ik(self: 'MainWindowLike') -> None:
        """Request cooperative cancellation for the active IK task."""
        self.threader.cancel()
        self.status_panel.append('正在请求取消 IK')

    def on_ik_progress(self: 'MainWindowLike', log) -> None:
        """Project incremental IK diagnostics into the status panel."""
        self.status_panel.set_metrics(
            iterations=f"A{log.attempt_idx + 1} / {log.iter_idx + 1}",
            pos_err=f"{log.pos_err_norm:.4e}",
            ori_err=f"{log.ori_err_norm:.4e}",
            cond=f"{log.cond_number:.4e}",
            manip=f"{log.manipulability:.4e}",
            dq_norm=f"{log.dq_norm:.4e}",
            mode=log.effective_mode or '-',
            damping=f"{log.damping_lambda:.3e}",
            elapsed=f"{log.elapsed_ms:.1f}",
        )

    def on_ik_finished(self: 'MainWindowLike', result) -> None:
        """Handle the terminal IK result via the task coordinator."""
        handler = getattr(self.ik_task_coordinator, 'handle_finished', None)
        if callable(handler):
            handler(result)
            return
        self._set_busy(False)
        solver_ops = self._solver_ops()
        runtime = self._runtime_ops()

        def action() -> None:
            solver_ops.apply_ik_result(self._pending_ik_request, result)
            fk = runtime.state.fk_result
            self.scene_controller.update_fk_projection(fk, runtime.state.target_pose)
            summary = self.metrics_service.summarize_ik(result)
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
            if result.logs:
                x = np.array([log.iter_idx + log.attempt_idx * 1e-3 for log in result.logs], dtype=float)
                pos = np.array([log.pos_err_norm for log in result.logs], dtype=float)
                ori = np.array([log.ori_err_norm for log in result.logs], dtype=float)
                cond = np.array([log.cond_number for log in result.logs], dtype=float)
                manip = np.array([log.manipulability for log in result.logs], dtype=float)
                self.plots_manager.clear('ik_error')
                self.plots_manager.clear('condition')
                self.plots_manager.set_curve('ik_error', 'position_error', x, pos)
                self.plots_manager.set_curve('ik_error', 'orientation_error', x, ori)
                self.plots_manager.set_curve('condition', 'condition_number', x, cond)
                self.plots_manager.set_curve('condition', 'manipulability', x, manip)

        self._run_presented(action, title='错误')

    def _build_trajectory_request(self: 'MainWindowLike'):
        """Build the current trajectory request from visible UI state."""
        return self._trajectory_ops().build_trajectory_request(
            duration=self.solver_panel.traj_duration.value(),
            dt=self.solver_panel.traj_dt.value(),
            mode=self.solver_panel.traj_mode.currentText(),
            target_values6=self.target_panel.values6(),
            orientation_mode=self.target_panel.orientation_mode.currentText(),
            ik_kwargs=self._build_solver_kwargs(),
        )

    def on_plan(self: 'MainWindowLike') -> None:
        """Entry point wired to the trajectory-planning button."""
        self.trajectory_task_coordinator.run()

    def _run_traj_impl(self: 'MainWindowLike') -> None:
        """Backward-compatible compatibility wrapper for legacy trajectory launch tests."""
        runner = getattr(self.trajectory_task_coordinator, 'start_task', None)
        if callable(runner):
            runner()
            return
        runtime = self._runtime_ops()

        def action() -> None:
            req = self._build_trajectory_request()
            self._pending_traj_request = req
            self._set_busy(True, 'trajectory')
            self.status_panel.append('轨迹任务已启动')
            trajectory_use_case = require_dependency(
                getattr(self._trajectory_ops(), 'trajectory_use_case', None),
                'trajectory_facade.trajectory_use_case',
            )
            task = self.threader.start(
                worker=TrajectoryWorker(req, trajectory_use_case),
                on_finished=self.on_trajectory_finished,
                on_failed=self.on_worker_failed,
                on_cancelled=self.on_worker_cancelled,
                task_kind='trajectory',
            )
            runtime.state_store.patch(active_task_id=task.task_id, active_task_kind=task.task_kind)

        self._run_presented(action, title='错误')

    def on_trajectory_finished(self: 'MainWindowLike', traj) -> None:
        """Handle the terminal trajectory result via the task coordinator."""
        handler = getattr(self.trajectory_task_coordinator, 'handle_finished', None)
        if callable(handler):
            handler(traj)
            return
        self._set_busy(False)
        trajectory_ops = self._trajectory_ops()

        def action() -> None:
            trajectory_ops.apply_trajectory(traj)
            metrics = self.metrics_service.summarize_trajectory(traj)
            ee_points = getattr(traj, 'ee_positions', None)
            self.project_trajectory_result(traj, metrics, ee_points)
            self.plots_manager.clear('joint_position')
            self.plots_manager.clear('joint_velocity')
            self.plots_manager.clear('joint_acceleration')
            for i in range(traj.q.shape[1]):
                self.plots_manager.set_curve('joint_position', f'q{i}', traj.t, traj.q[:, i])
                self.plots_manager.set_curve('joint_velocity', f'qd{i}', traj.t, traj.qd[:, i])
                self.plots_manager.set_curve('joint_acceleration', f'qdd{i}', traj.t, traj.qdd[:, i])

        self._run_presented(action, title='错误')

    def on_run_benchmark(self: 'MainWindowLike') -> None:
        """Entry point wired to the benchmark button."""
        self.benchmark_task_coordinator.run()

    def _run_benchmark_impl(self: 'MainWindowLike') -> None:
        """Backward-compatible compatibility wrapper for legacy benchmark launch tests."""
        runner = getattr(self.benchmark_task_coordinator, 'start_task', None)
        if callable(runner):
            runner()
            return
        runtime = self._runtime_ops()
        benchmark_ops = self._benchmark_ops()

        def action() -> None:
            spec = runtime.state.robot_spec
            if spec is None:
                raise RuntimeError('robot not loaded')
            config = benchmark_ops.build_benchmark_config(**self._build_solver_kwargs())
            self._set_busy(True, 'benchmark')
            self.status_panel.append('Benchmark 已启动')
            task = self.threader.start(
                worker=BenchmarkWorker(
                    spec,
                    config,
                    require_dependency(getattr(benchmark_ops, 'benchmark_use_case', None), 'benchmark_facade.benchmark_use_case'),
                ),
                on_finished=self.on_benchmark_finished,
                on_failed=self.on_worker_failed,
                on_cancelled=self.on_worker_cancelled,
                task_kind='benchmark',
            )
            runtime.state_store.patch(active_task_id=task.task_id, active_task_kind=task.task_kind)

        self._run_presented(action, title='错误')

    def on_benchmark_finished(self: 'MainWindowLike', report) -> None:
        """Handle the terminal benchmark result via the task coordinator."""
        handler = getattr(self.benchmark_task_coordinator, 'handle_finished', None)
        if callable(handler):
            handler(report)
            return
        self._set_busy(False)
        runtime = self._runtime_ops()

        def action() -> None:
            runtime.state_store.patch(benchmark_report=report)
            summary = self.metrics_service.summarize_benchmark(report)
            self.benchmark_panel.set_report({'num_cases': report.num_cases, 'success_rate': report.success_rate, 'cases': list(report.cases)})
            self._update_diagnostics_from_benchmark(summary)
            self.status_panel.summary.setText(
                f"Benchmark 完成 | cases={summary['num_cases']} | success={summary['success_rate']:.1%}"
            )
            self.status_panel.append('Benchmark 运行完成')

        self._run_presented(action, title='错误')

    def _on_task_state_changed(self: 'MainWindowLike', snapshot) -> None:
        """Route structured task snapshots through the status coordinator."""
        self.status_coordinator.apply_task_snapshot(snapshot)

    def on_worker_failed(self: 'MainWindowLike', failure) -> None:
        """Route worker failures through the status coordinator."""
        self._set_busy(False)
        handler = getattr(self.status_coordinator, 'handle_worker_failure', None)
        if callable(handler):
            handler(failure)
            return
        self._project_exception(failure, title='任务失败')

    def on_worker_cancelled(self: 'MainWindowLike') -> None:
        """Project cooperative task cancellation into the UI state."""
        self._set_busy(False)
        self.status_panel.append('任务已取消')
