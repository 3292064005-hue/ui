from __future__ import annotations

from threading import Timer
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from PySide6.QtCore import QObject, QTimer, Signal
else:
    try:
        from PySide6.QtCore import QObject, QTimer, Signal
    except Exception:  # pragma: no cover
        class QObject:
            def __init__(self, *args, **kwargs): ...

        class _DummySignalInstance:
            def __init__(self) -> None:
                self._callbacks: list[object] = []

            def emit(self, *args, **kwargs) -> None:
                for callback in list(self._callbacks):
                    callback(*args, **kwargs)

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

        class QTimer:
            def __init__(self, *args, **kwargs) -> None:
                self.timeout = _DummySignalInstance()
                self._timer: Timer | None = None
                self._active = False

            def setSingleShot(self, single_shot: bool) -> None:
                del single_shot

            def isActive(self) -> bool:
                return self._active

            def start(self, interval_ms: int) -> None:
                self.stop()
                self._active = True
                self._timer = Timer(max(float(interval_ms), 0.0) / 1000.0, self._emit_timeout)
                self._timer.daemon = True
                self._timer.start()

            def _emit_timeout(self) -> None:
                self._active = False
                self.timeout.emit()

            def stop(self) -> None:
                if self._timer is not None:
                    self._timer.cancel()
                    self._timer = None
                self._active = False

            def deleteLater(self) -> None:
                self.stop()


class PlaybackRenderScheduler(QObject):  # pragma: no cover - GUI shell
    """Throttle playback/seek projection to a single latest-frame render stream.

    The scheduler coalesces high-frequency seek/playback updates and projects only
    the newest frame on each timer tick. This keeps scene, plots, and status
    updates aligned under one rendering boundary instead of allowing fragmented
    immediate UI writes from multiple callers.
    """

    flushed = Signal(object, bool)

    def __init__(self, parent=None, *, max_fps: float = 60.0) -> None:
        super().__init__(parent)
        fps = max(float(max_fps), 1.0)
        self._interval_ms = max(int(round(1000.0 / fps)), 1)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.flush)
        self._pending_frame = None
        self._pending_live = False

    def schedule(self, frame, *, live: bool = False, immediate: bool = False) -> None:
        """Queue a frame for projection.

        Args:
            frame: Playback frame or compatible payload to project.
            live: Whether the frame comes from live playback rather than scrubbing.
            immediate: Whether to bypass timer coalescing and flush now.

        Returns:
            None: The newest frame is stored and emitted on the next flush.

        Raises:
            None: Scheduling is tolerant of missing Qt event loops.
        """
        self._pending_frame = frame
        self._pending_live = bool(live)
        if immediate:
            self.flush()
            return
        if not self._timer.isActive():
            self._timer.start(self._interval_ms)

    def flush(self) -> None:
        """Emit the newest queued frame, if any."""
        frame = self._pending_frame
        if frame is None:
            return
        live = bool(self._pending_live)
        self._pending_frame = None
        self._pending_live = False
        self.flushed.emit(frame, live)

    def clear(self) -> None:
        """Drop pending frames without emitting them."""
        self._timer.stop()
        self._pending_frame = None
        self._pending_live = False
