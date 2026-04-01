from __future__ import annotations

from threading import Timer
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from PySide6.QtCore import QObject, QThread, QTimer, QCoreApplication, Signal
else:
    try:
        from PySide6.QtCore import QObject, QThread, QTimer, QCoreApplication, Signal
    except ImportError:  # pragma: no cover
        class QObject:
            def __init__(self, *args, **kwargs): ...

        class QThread:
            def __init__(self, *args, **kwargs): ...
            def started(self): ...

        class _DummySignalInstance:
            def __init__(self) -> None:
                self._callbacks: list[object] = []

            def emit(self, *args, **kwargs) -> None:
                for cb in list(self._callbacks):
                    cb(*args, **kwargs)

            def connect(self, callback, *args, **kwargs) -> None:
                self._callbacks.append(callback)

        class Signal:
            def __init__(self, *args, **kwargs) -> None:
                self._name = ''

            def __set_name__(self, owner, name) -> None:
                self._name = f'__signal_{name}'

            def __get__(self, instance, owner):
                if instance is None:
                    return self
                signal = instance.__dict__.get(self._name)
                if signal is None:
                    signal = _DummySignalInstance()
                    instance.__dict__[self._name] = signal
                return signal

        class QCoreApplication:
            @staticmethod
            def instance():
                return None

        class QTimer:
            def __init__(self, *args, **kwargs) -> None:
                self.timeout = _DummySignalInstance()
                self._timer: Timer | None = None
                self._single_shot = False
                self._interval_ms = 0

            def setSingleShot(self, single_shot: bool) -> None:
                self._single_shot = bool(single_shot)

            def start(self, interval_ms: int) -> None:
                self.stop()
                self._interval_ms = int(interval_ms)
                self._timer = Timer(float(self._interval_ms) / 1000.0, self.timeout.emit)
                self._timer.daemon = True
                self._timer.start()

            def stop(self) -> None:
                if self._timer is not None:
                    self._timer.cancel()
                    self._timer = None

            def deleteLater(self) -> None:
                self.stop()
