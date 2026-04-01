from __future__ import annotations

from robot_sim.presentation.threading.qt_compat import QThread


class QtThreadRuntimeBridge:
    """Bridge responsible for QThread lifecycle operations."""

    def create_thread(self):
        """Create a worker thread instance.

        Returns:
            object: A fresh QThread-compatible instance.

        Raises:
            None: Thin construction wrapper only.
        """
        return QThread()

    def start(self, thread) -> None:
        """Start the supplied worker thread.

        Args:
            thread: QThread-compatible worker thread.

        Returns:
            None: Starts the thread in place.

        Raises:
            RuntimeError: Propagated by the underlying Qt runtime if start fails.
        """
        thread.start()

    def stop(self, thread, *, wait: bool) -> None:
        """Request worker-thread shutdown.

        Args:
            thread: QThread-compatible worker thread.
            wait: Whether to block until the thread exits.

        Returns:
            None: Requests shutdown in place.

        Raises:
            RuntimeError: Propagated by the underlying Qt runtime if shutdown fails.
        """
        thread.quit()
        if wait:
            thread.wait()
