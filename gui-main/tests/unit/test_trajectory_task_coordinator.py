from types import SimpleNamespace

from robot_sim.presentation.coordinators.trajectory_task_coordinator import TrajectoryTaskCoordinator


class DummyStore:
    def __init__(self):
        self.patched = {}

    def patch(self, **kwargs):
        self.patched.update(kwargs)


class DummyThreader:
    def __init__(self):
        self.started = None

    def start(self, **kwargs):
        self.started = kwargs
        return SimpleNamespace(task_id='task-1', task_kind=kwargs['task_kind'])


class DummyWindow:
    def __init__(self):
        self.controller = SimpleNamespace(traj_uc=object(), state_store=DummyStore())
        self.trajectory_facade = SimpleNamespace(trajectory_use_case=object())
        self.threader = DummyThreader()
        self.status_panel = SimpleNamespace(messages=[], append=lambda message: self.status_panel.messages.append(message))
        self._pending_traj_request = None
        self._set_busy_calls = []
        self.read_trajectory_request = lambda: SimpleNamespace()
        self.project_task_started = lambda task_kind, message: (self._set_busy_calls.append((True, task_kind)), self.status_panel.append(message))
        self.project_task_registered = lambda task_id, task_kind: self.controller.state_store.patch(active_task_id=task_id, active_task_kind=task_kind)
        self.on_trajectory_finished = lambda traj: None
        self.on_worker_failed = lambda failure: None
        self.on_worker_cancelled = lambda: None
        self._projected = []
        self._project_exception = lambda exc, title='错误': self._projected.append((title, str(exc)))


def test_trajectory_task_coordinator_starts_worker_and_patches_task_state():
    window = DummyWindow()
    TrajectoryTaskCoordinator(window).run()
    assert window.threader.started['task_kind'] == 'trajectory'
    assert window.controller.state_store.patched['active_task_kind'] == 'trajectory'
    assert window._set_busy_calls == [(True, 'trajectory')]
