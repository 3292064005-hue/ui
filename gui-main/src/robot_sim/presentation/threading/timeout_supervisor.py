from __future__ import annotations

from threading import Timer
from typing import Callable

from robot_sim.presentation.threading.qt_compat import QCoreApplication, QTimer


class TimeoutSupervisor:
    """Manage orchestration timeouts using Qt timers when available."""

    def __init__(self, owner) -> None:
        """Initialize timeout supervision state.

        Args:
            owner: QObject owner used for Qt timer lifetime when available.

        Returns:
            None: Initializes timer references only.

        Raises:
            None: Construction is side-effect free.
        """
        self._owner = owner
        self._qt_timer: QTimer | None = None
        self._thread_timer: Timer | None = None
        self._task_id: str = ''

    def arm(self, timeout_ms: int | None, *, task_id: str, callback: Callable[[str], None]) -> None:
        """Arm a timeout for the supplied task identifier.

        Args:
            timeout_ms: Timeout duration in milliseconds or ``None`` to disable timeouts.
            task_id: Active task identifier used to validate callback delivery.
            callback: Callback invoked when the timeout fires.

        Returns:
            None: Schedules a timeout when requested.

        Raises:
            None: Scheduling failures are not surfaced by the compatibility timer path.
        """
        self.cancel()
        if timeout_ms is None or int(timeout_ms) <= 0:
            return
        self._task_id = str(task_id)
        interval_ms = int(timeout_ms)
        if QCoreApplication.instance() is not None:
            timer = QTimer(self._owner)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: callback(self._task_id))
            timer.start(interval_ms)
            self._qt_timer = timer
            return
        timer = Timer(float(interval_ms) / 1000.0, lambda: callback(self._task_id))
        timer.daemon = True
        timer.start()
        self._thread_timer = timer

    def cancel(self) -> None:
        """Cancel any armed timeout.

        Returns:
            None: Stops and clears both Qt and fallback timers.

        Raises:
            None: Safe to call even when no timer is armed.
        """
        if self._qt_timer is not None:
            self._qt_timer.stop()
            self._qt_timer.deleteLater()
            self._qt_timer = None
        if self._thread_timer is not None:
            self._thread_timer.cancel()
            self._thread_timer = None
        self._task_id = ''
