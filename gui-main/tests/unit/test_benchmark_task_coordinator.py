from types import SimpleNamespace

from robot_sim.presentation.coordinators.benchmark_task_coordinator import BenchmarkTaskCoordinator


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
        self.controller = SimpleNamespace(
            state=SimpleNamespace(robot_spec=object()),
            benchmark_uc=object(),
            build_benchmark_config=lambda **kwargs: kwargs,
            state_store=DummyStore(),
        )
        self.runtime_facade = SimpleNamespace(state=SimpleNamespace(robot_spec=object()), state_store=DummyStore())
        self.benchmark_facade = SimpleNamespace(benchmark_use_case=object(), build_benchmark_config=lambda **kwargs: kwargs)
        self.threader = DummyThreader()
        self.status_panel = SimpleNamespace(messages=[], append=lambda message: self.status_panel.messages.append(message))
        self.read_solver_kwargs = lambda: {'mode': 'dls'}
        self._set_busy_calls = []
        self.project_task_started = lambda task_kind, message: (self._set_busy_calls.append((True, task_kind)), self.status_panel.append(message))
        self.project_task_registered = lambda task_id, task_kind: self.runtime_facade.state_store.patch(active_task_id=task_id, active_task_kind=task_kind)
        self.on_benchmark_finished = lambda report: None
        self.on_worker_failed = lambda failure: None
        self.on_worker_cancelled = lambda: None
        self._projected = []
        self._project_exception = lambda exc, title='错误': self._projected.append((title, str(exc)))


def test_benchmark_task_coordinator_starts_worker_and_patches_task_state():
    window = DummyWindow()
    BenchmarkTaskCoordinator(window).run()
    assert window.threader.started['task_kind'] == 'benchmark'
    assert window.runtime_facade.state_store.patched['active_task_kind'] == 'benchmark'
    assert window._set_busy_calls == [(True, 'benchmark')]
