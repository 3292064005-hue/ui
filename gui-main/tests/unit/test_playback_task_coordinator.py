from types import SimpleNamespace

from robot_sim.presentation.coordinators.playback_task_coordinator import PlaybackTaskCoordinator


class DummyStore:
    def __init__(self):
        self.patched = {}

    def patch(self, **kwargs):
        self.patched.update(kwargs)


class DummyThreader:
    def __init__(self):
        self.started = None
        self.cancelled = False
        self.stopped = False

    def start(self, **kwargs):
        self.started = kwargs
        return SimpleNamespace(task_id='task-1', task_kind=kwargs['task_kind'])

    def cancel(self):
        self.cancelled = True

    def stop(self, wait=False):
        self.stopped = wait is False


class DummyWindow:
    def __init__(self):
        self.controller = SimpleNamespace(
            state=SimpleNamespace(trajectory=SimpleNamespace()),
            state_store=DummyStore(),
            set_playback_options=lambda **kwargs: self._options.append(kwargs),
        )
        self.runtime_facade = SimpleNamespace(state=SimpleNamespace(trajectory=SimpleNamespace()))
        self.playback_facade = SimpleNamespace(
            ensure_playback_ready=lambda strict=True: None,
            set_playback_options=lambda **kwargs: self._options.append(kwargs),
        )
        self.playback_threader = DummyThreader()
        self._options = []
        self._projected = []
        self._project_exception = lambda exc, title='错误': self._projected.append((title, str(exc)))
        self._set_playback_running_calls = []
        self.on_seek_frame_calls = []
        self.read_playback_launch_options = lambda: {'speed_multiplier': 1.5, 'loop_enabled': True}
        self.project_playback_started = lambda: self._set_playback_running_calls.append(True)
        self.project_playback_stopped = lambda reset_frame=False: (self._set_playback_running_calls.append(False), self.on_seek_frame_calls.append(0) if reset_frame else None)
        self.project_task_registered = lambda task_id, task_kind: self.controller.state_store.patch(active_task_id=task_id, active_task_kind=task_kind)
        self._playback_worker_factory = lambda traj: SimpleNamespace(traj=traj)
        self.on_playback_progress = lambda frame: None
        self.on_playback_finished = lambda state: None
        self.on_playback_failed = lambda msg: None
        self.on_playback_cancelled = lambda: None


def test_playback_task_coordinator_covers_play_pause_stop():
    window = DummyWindow()
    coord = PlaybackTaskCoordinator(window)
    coord.play()
    coord.pause()
    coord.stop()
    assert window.playback_threader.started['task_kind'] == 'playback'
    assert window.playback_threader.cancelled is True
    assert window.playback_threader.stopped is True
    assert window.on_seek_frame_calls == [0]
    assert window._options == [{'speed_multiplier': 1.5, 'loop_enabled': True}]
