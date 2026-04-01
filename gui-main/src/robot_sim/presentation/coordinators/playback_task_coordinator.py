from __future__ import annotations

from robot_sim.presentation.coordinators._helpers import require_dependency, require_view, run_presented


class PlaybackTaskCoordinator:
    """Own playback task orchestration for the main window."""

    def __init__(self, window, *, runtime=None, playback=None, playback_threader=None) -> None:
        self.window = window
        self.runtime = require_dependency(runtime if runtime is not None else getattr(window, 'runtime_facade', None), 'runtime_facade')
        self.playback = require_dependency(playback if playback is not None else getattr(window, 'playback_facade', None), 'playback_facade')
        self.playback_threader = require_dependency(playback_threader if playback_threader is not None else getattr(window, 'playback_threader', None), 'playback_threader')

    def play(self) -> None:
        self.start_task()

    def start_task(self) -> None:
        def action() -> None:
            traj = self.runtime.state.trajectory
            if traj is None:
                raise RuntimeError('trajectory not available')
            ensure_ready = getattr(self.playback, 'ensure_playback_ready', None)
            if callable(ensure_ready):
                ensure_ready(strict=True)
            playback_options = require_view(self.window, 'read_playback_launch_options')
            self.playback.set_playback_options(
                speed_multiplier=float(playback_options['speed_multiplier']),
                loop_enabled=bool(playback_options['loop_enabled']),
            )
            worker = self.window._playback_worker_factory(traj)
            task = self.playback_threader.start(
                worker=worker,
                on_started=lambda: require_view(self.window, 'project_playback_started'),
                on_progress=self.window.on_playback_progress,
                on_finished=self.window.on_playback_finished,
                on_failed=self.window.on_playback_failed,
                on_cancelled=self.window.on_playback_cancelled,
                task_kind='playback',
            )
            require_view(self.window, 'project_task_registered', task.task_id, task.task_kind)

        run_presented(self.window, action, title='错误')

    def pause(self) -> None:
        self.playback_threader.cancel()

    def stop(self) -> None:
        self.playback_threader.stop(wait=False)
        require_view(self.window, 'project_playback_stopped', reset_frame=True)
