from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.presentation.view_contracts import MainWindowLike


class MainWindowActionMixin:
    """Backward-compatible action mixin that delegates orchestration to coordinators."""

    def on_load_robot(self: 'MainWindowLike') -> None:
        """Entry point wired to the robot-load button."""
        self.robot_coordinator.load_robot()

    def _load_robot_impl(self: 'MainWindowLike', name: str | None = None) -> None:
        """Backward-compatible compatibility wrapper for legacy robot-load tests."""
        runner = getattr(getattr(self, 'robot_coordinator', None), 'load_robot_task', None)
        if callable(runner):
            runner(name=name)
            return
        robot_ops = self._robot_ops()
        runtime = self._runtime_ops()

        def action() -> None:
            fk = robot_ops.load_robot(name or self.robot_panel.selected_robot_name())
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

        self._run_presented(action, title='错误')

    def on_save_robot(self: 'MainWindowLike') -> None:
        """Entry point wired to the robot-save button."""
        self.robot_coordinator.save_current_robot()

    def _save_robot_impl(self: 'MainWindowLike') -> None:
        """Backward-compatible compatibility wrapper for legacy robot-save tests."""
        robot_ops = self._robot_ops()

        def action() -> None:
            path = robot_ops.save_current_robot(
                rows=self.robot_panel.edited_rows(),
                home_q=self.robot_panel.edited_home_q(),
                name=self.robot_panel.selected_robot_name(),
            )
            self.status_panel.append(f'机器人配置已保存：{path}')

        self._run_presented(action, title='错误')

    def on_fill_current_pose(self: 'MainWindowLike') -> None:
        """Fill the target pose editor from the latest FK result."""
        fk = self._runtime_ops().state.fk_result
        if fk is None:
            return
        self.target_panel.set_from_pose(fk.ee_pose)
        self.status_panel.append('已用当前位姿填充目标')

    def on_run_fk(self: 'MainWindowLike') -> None:
        """Run a synchronous FK update from the current editor values."""
        robot_ops = self._robot_ops()
        runtime = self._runtime_ops()

        def action() -> None:
            q = np.array(self.robot_panel.edited_home_q(), dtype=float)
            fk = robot_ops.run_fk(q=q)
            self.scene_controller.update_fk_projection(fk, runtime.state.target_pose)
            self.status_panel.summary.setText(f"FK 完成 | p = {np.array2string(fk.ee_pose.p, precision=4)}")
            self.status_panel.append('FK 更新成功')

        self._run_presented(action, title='错误')

    def on_play(self: 'MainWindowLike') -> None:
        """Entry point wired to the playback play button."""
        self.playback_task_coordinator.play()

    def _play_impl(self: 'MainWindowLike') -> None:
        """Backward-compatible compatibility wrapper for legacy playback-start tests."""
        runner = getattr(self.playback_task_coordinator, 'start_task', None)
        if callable(runner):
            runner()
            return
        playback_ops = self._playback_ops()
        runtime = self._runtime_ops()

        def action() -> None:
            traj = runtime.state.trajectory
            if traj is None:
                raise RuntimeError('trajectory not available')
            playback_ops.set_playback_options(
                speed_multiplier=self.playback_panel.speed.value(),
                loop_enabled=self.playback_panel.loop.isChecked(),
            )
            worker = self._playback_worker_factory(traj)
            task = self.playback_threader.start(
                worker=worker,
                on_started=lambda: self._set_playback_running(True),
                on_progress=self.on_playback_progress,
                on_finished=self.on_playback_finished,
                on_failed=self.on_playback_failed,
                on_cancelled=self.on_playback_cancelled,
                task_kind='playback',
            )
            runtime.state_store.patch(active_task_id=task.task_id, active_task_kind=task.task_kind)

        self._run_presented(action, title='错误')

    def on_pause(self: 'MainWindowLike') -> None:
        """Entry point wired to the playback pause button."""
        self.playback_task_coordinator.pause()

    def _pause_impl(self: 'MainWindowLike') -> None:
        """Backward-compatible compatibility wrapper for legacy playback-pause tests."""
        self.playback_threader.cancel()

    def on_stop_playback(self: 'MainWindowLike') -> None:
        """Entry point wired to the playback stop button."""
        self.playback_task_coordinator.stop()

    def _stop_playback_impl(self: 'MainWindowLike') -> None:
        """Backward-compatible compatibility wrapper for legacy playback-stop tests.

        Boundary behavior:
            The compatibility path now mirrors the coordinator path: stop the playback threader and
            project the rewind through ``project_playback_stopped(reset_frame=True)`` instead of
            routing back through ``on_seek_frame(0)``.
        """
        self.playback_threader.stop(wait=False)
        self.project_playback_stopped(reset_frame=True)

    def on_step(self: 'MainWindowLike') -> None:
        """Advance playback by one frame."""
        playback_ops = self._playback_ops()

        def action() -> None:
            frame = playback_ops.next_playback_frame()
            if frame is not None:
                self._schedule_playback_frame(frame, immediate=True)

        self._run_presented(action, title='错误')

    def on_seek_frame(self: 'MainWindowLike', idx: int) -> None:
        """Seek playback to an arbitrary frame index."""
        playback_ops = self._playback_ops()
        runtime = self._runtime_ops()

        def action() -> None:
            if runtime.state.trajectory is None:
                return
            frame = playback_ops.set_playback_frame(int(idx))
            self._schedule_playback_frame(frame, live=False, immediate=False)

        self._run_status_projected(action, prefix='拖动播放游标失败')

    def on_playback_speed_changed(self: 'MainWindowLike', value: float) -> None:
        """Update playback speed from the UI control."""
        self._playback_ops().set_playback_options(speed_multiplier=float(value))
        self.status_panel.set_metrics(playback=self._playback_status_text())

    def on_playback_loop_changed(self: 'MainWindowLike', checked: bool) -> None:
        """Update playback looping from the UI control."""
        self._playback_ops().set_playback_options(loop_enabled=bool(checked))
        self.status_panel.set_metrics(playback=self._playback_status_text())

    def _schedule_playback_frame(self: 'MainWindowLike', frame, *, live: bool = False, immediate: bool = False) -> None:
        """Schedule playback-frame projection through the coalescing render scheduler."""
        scheduler = getattr(self, 'playback_render_scheduler', None)
        if immediate or scheduler is None:
            self.project_playback_frame(frame, live=live)
            return
        scheduler.schedule(frame, live=live)

    def _apply_playback_frame(self: 'MainWindowLike', frame) -> None:
        """Apply a single playback frame to the 3D view and playback widgets.

        Args:
            frame: Playback frame carrying cached geometry.

        Returns:
            None: Updates scene and playback widgets in place.

        Raises:
            RuntimeError: If the frame does not carry the cached geometry required by the
                playback contract.

        Boundary behavior:
            Live playback and seek projection no longer fall back to UI-thread FK evaluation.
            Missing cached geometry is treated as a contract violation and surfaced to the
            presentation error boundary instead of being silently recomputed.
        """
        runtime = self._runtime_ops()
        if getattr(frame, 'joint_positions', None) is None or getattr(frame, 'ee_position', None) is None:
            raise RuntimeError('playback frame missing cached geometry')
        self.scene_controller.update_playback_projection(frame.joint_positions, frame.ee_position, runtime.state.target_pose)
        runtime.state_store.patch(q_current=np.asarray(frame.q, dtype=float).copy())
        total = runtime.state.playback.total_frames
        self.playback_panel.set_frame(frame.frame_idx, total)
        if hasattr(self.plots_manager, 'set_cursor'):
            self.plots_manager.set_cursor('joint_position', float(frame.t))
            self.plots_manager.set_cursor('joint_velocity', float(frame.t))
            self.plots_manager.set_cursor('joint_acceleration', float(frame.t))

    def on_playback_progress(self: 'MainWindowLike', frame) -> None:
        """Project a streamed playback frame into the coalescing render scheduler."""
        self._schedule_playback_frame(frame, live=True, immediate=False)

    def on_playback_finished(self: 'MainWindowLike', final_state) -> None:
        """Project playback completion into the UI state."""
        runtime = self._runtime_ops()
        self._set_playback_running(False)
        runtime.state_store.patch(playback=final_state.pause())
        self.status_panel.append('播放完成')
        self.status_panel.set_metrics(playback=self._playback_status_text())

    def on_playback_cancelled(self: 'MainWindowLike') -> None:
        """Project playback cancellation into the UI state."""
        runtime = self._runtime_ops()
        self._set_playback_running(False)
        if runtime.state.playback.total_frames > 0:
            runtime.state_store.patch(playback=runtime.state.playback.with_frame(runtime.state.playback.frame_idx).pause())
        self.status_panel.append('播放已停止')
        self.status_panel.set_metrics(playback=self._playback_status_text())

    def on_playback_failed(self: 'MainWindowLike', message: str) -> None:
        """Project playback failure through the shared error boundary."""
        self._set_playback_running(False)
        self._project_exception(message, title='播放失败')

    def on_fit_scene(self: 'MainWindowLike') -> None:
        """Entry point wired to the scene-fit toolbar action."""
        self.scene_coordinator.fit()

    def _fit_scene_impl(self: 'MainWindowLike') -> None:
        """Backward-compatible compatibility wrapper for legacy scene-fit tests."""
        self.project_scene_fit()

    def on_clear_scene_path(self: 'MainWindowLike') -> None:
        """Entry point wired to the scene clear-path toolbar action."""
        self.scene_coordinator.clear_path()

    def _clear_scene_path_impl(self: 'MainWindowLike') -> None:
        """Backward-compatible compatibility wrapper for legacy scene-clear tests."""
        self.project_scene_path_cleared()

    def on_capture_scene(self: 'MainWindowLike') -> None:
        """Entry point wired to the screenshot toolbar action."""
        self.scene_coordinator.capture()

    def _capture_scene_impl(self: 'MainWindowLike') -> None:
        """Backward-compatible compatibility wrapper for legacy capture-scene tests."""
        runtime = self._runtime_ops()

        def action() -> None:
            path = Path(runtime.export_root) / 'scene_capture.png'
            result = self.scene_widget.capture_screenshot(path)
            self.status_panel.append(f'场景截图已导出：{result}')

        self._run_presented(action, title='截图失败')

    def on_export_trajectory(self: 'MainWindowLike') -> None:
        """Entry point wired to the trajectory-export button."""
        self.export_task_coordinator.export_trajectory()

    def _export_trajectory_impl(self: 'MainWindowLike') -> None:
        """Backward-compatible compatibility wrapper for legacy trajectory-export tests."""
        export_ops = self._export_ops()
        runtime = self._runtime_ops()

        def action() -> None:
            path = export_ops.export_trajectory()
            metrics = self.metrics_service.summarize_trajectory(runtime.state.trajectory)
            metrics_path = export_ops.export_trajectory_metrics('trajectory_metrics.json', metrics)
            self.status_panel.append(f'轨迹已导出：{path}')
            self.status_panel.append(f'轨迹指标已导出：{metrics_path}')

        self._run_presented(action, title='导出失败')

    def on_export_session(self: 'MainWindowLike') -> None:
        """Entry point wired to the session-export button."""
        self.export_task_coordinator.export_session()

    def _export_session_impl(self: 'MainWindowLike') -> None:
        """Backward-compatible compatibility wrapper for legacy session-export tests."""
        export_ops = self._export_ops()

        def action() -> None:
            path = export_ops.export_session()
            self.status_panel.append(f'会话已导出：{path}')

        self._run_presented(action, title='导出失败')

    def on_export_package(self: 'MainWindowLike') -> None:
        """Entry point wired to the package-export button."""
        self.export_task_coordinator.export_package()

    def _export_package_impl(self: 'MainWindowLike') -> None:
        """Backward-compatible compatibility wrapper for legacy package-export tests."""
        export_ops = self._export_ops()

        def action() -> None:
            path = export_ops.export_package()
            self.status_panel.append(f'完整导出包已生成：{path}')

        self._run_presented(action, title='导出失败')

    def on_export_benchmark(self: 'MainWindowLike') -> None:
        """Entry point wired to the benchmark-export button."""
        self.export_task_coordinator.export_benchmark()

    def _export_benchmark_impl(self: 'MainWindowLike') -> None:
        """Backward-compatible compatibility wrapper for legacy benchmark-export tests."""
        export_ops = self._export_ops()

        def action() -> None:
            json_path = export_ops.export_benchmark()
            csv_path = export_ops.export_benchmark_cases_csv()
            self.status_panel.append(f'Benchmark 报告已导出：{json_path}')
            self.status_panel.append(f'Benchmark 明细已导出：{csv_path}')

        self._run_presented(action, title='导出失败')
