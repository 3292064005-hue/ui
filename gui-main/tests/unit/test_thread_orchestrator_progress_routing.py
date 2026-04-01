from __future__ import annotations

from robot_sim.application.workers.base import BaseWorker
from robot_sim.presentation import thread_orchestrator as mod
from robot_sim.presentation.thread_orchestrator import ThreadOrchestrator


class _DummySignal:
    def __init__(self) -> None:
        self._callbacks: list[object] = []

    def connect(self, callback, *args, **kwargs) -> None:
        self._callbacks.append(callback)

    def emit(self, *args, **kwargs) -> None:
        for callback in list(self._callbacks):
            callback(*args, **kwargs)


class _InlineThread:
    def __init__(self) -> None:
        self.started = _DummySignal()
        self.finished = _DummySignal()
        self._quit_called = False

    def start(self) -> None:
        self.started.emit()
        if self._quit_called:
            self.finished.emit()

    def quit(self) -> None:
        self._quit_called = True

    def wait(self) -> None:
        return None

    def deleteLater(self) -> None:
        return None


class _EventWorker(BaseWorker):
    def __init__(self) -> None:
        super().__init__(task_kind='event')

    def run(self) -> None:
        self.emit_started()
        self.emit_progress(stage='tick', percent=50.0, message='half', payload={'value': 123})
        self.emit_finished('done')


class _LegacyProgressWorker(BaseWorker):
    def __init__(self) -> None:
        super().__init__(task_kind='legacy')

    def run(self) -> None:
        self.emit_started()
        self.progress.emit('frame-7')
        self.emit_finished('done')


def test_thread_orchestrator_routes_baseworker_emit_progress_to_callback(monkeypatch):
    monkeypatch.setattr(mod, 'QThread', _InlineThread)
    orch = ThreadOrchestrator()
    seen: list[object] = []
    orch.start(_EventWorker(), on_progress=seen.append, task_kind='event')
    assert seen == [123]


def test_thread_orchestrator_routes_legacy_progress_signal_to_callback(monkeypatch):
    monkeypatch.setattr(mod, 'QThread', _InlineThread)
    orch = ThreadOrchestrator()
    seen: list[object] = []
    orch.start(_LegacyProgressWorker(), on_progress=seen.append, task_kind='legacy')
    assert seen == ['frame-7']
