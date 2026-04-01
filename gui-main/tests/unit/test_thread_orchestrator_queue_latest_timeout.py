from __future__ import annotations

import time

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


class _ManualThread:
    def __init__(self) -> None:
        self.started = _DummySignal()
        self.finished = _DummySignal()

    def start(self) -> None:
        self.started.emit()

    def quit(self) -> None:
        self.finished.emit()

    def wait(self) -> None:
        return None

    def deleteLater(self) -> None:
        return None


class _BlockingWorker(BaseWorker):
    def __init__(self, task_kind: str = 'blocking') -> None:
        super().__init__(task_kind=task_kind)
        self.started_once = False

    def run(self) -> None:
        self.started_once = True
        self.emit_started()


class _FastWorker(BaseWorker):
    def __init__(self, task_kind: str = 'fast') -> None:
        super().__init__(task_kind=task_kind)
        self.ran = False

    def run(self) -> None:
        self.ran = True
        self.emit_started()
        self.emit_finished('done')


def test_queue_latest_runs_pending_task_after_active_finishes(monkeypatch):
    monkeypatch.setattr(mod, 'QThread', _ManualThread)
    orch = ThreadOrchestrator(start_policy='queue_latest')
    first = _BlockingWorker('first')
    second = _FastWorker('second')

    orch.start(first, task_kind='first')
    pending = orch.start(second, task_kind='second')

    assert first.started_once is True
    assert second.ran is False
    assert pending.task_kind == 'second'

    first.emit_finished('done')

    assert second.ran is True
    assert orch.last_terminal_snapshot is not None
    assert orch.last_terminal_snapshot.task_kind == 'second'


def test_timeout_marks_task_failed(monkeypatch):
    monkeypatch.setattr(mod, 'QThread', _ManualThread)
    orch = ThreadOrchestrator()
    worker = _BlockingWorker('timeout')

    orch.start(worker, task_kind='timeout', timeout_ms=20)
    time.sleep(0.08)

    assert orch.last_terminal_snapshot is not None
    assert orch.last_terminal_snapshot.stop_reason == 'timeout'
