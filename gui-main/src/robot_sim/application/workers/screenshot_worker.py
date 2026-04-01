from __future__ import annotations

import inspect
from typing import Any

from robot_sim.application.workers.base import BaseWorker, Slot
from robot_sim.domain.errors import CancelledTaskError


class ScreenshotWorker(BaseWorker):
    """Qt worker wrapper for screenshot capture operations."""

    def __init__(self, func, *args, **kwargs):
        """Create a screenshot worker.

        Args:
            func: Callable that performs screenshot capture.
            *args: Positional arguments forwarded to ``func``.
            **kwargs: Keyword arguments forwarded to ``func``.
        """
        super().__init__(task_kind='screenshot')
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def _invoke_with_control(self) -> Any:
        """Invoke the capture callable while preserving backward compatibility."""
        kwargs = dict(self._kwargs)
        try:
            signature = inspect.signature(self._func)
        except (TypeError, ValueError):
            signature = None
        accepted = set(signature.parameters) if signature is not None else set()
        if 'cancel_flag' in accepted:
            kwargs.setdefault('cancel_flag', self.is_cancel_requested)
        if 'progress_cb' in accepted:
            kwargs.setdefault(
                'progress_cb',
                lambda percent, message='', payload=None: self.emit_progress(
                    stage='screenshot',
                    percent=float(percent),
                    message=str(message),
                    payload=dict(payload or {}),
                ),
            )
        if 'correlation_id' in accepted:
            kwargs.setdefault('correlation_id', self.correlation_id)
        return self._func(*self._args, **kwargs)

    @Slot()
    def run(self):
        """Execute the screenshot callable and emit terminal worker events."""
        self.emit_started()
        try:
            if self.is_cancelled():
                self.emit_cancelled(stop_reason='cancelled')
                return
            path = self._invoke_with_control()
            if self.is_cancelled():
                self.emit_cancelled(stop_reason='cancelled')
                return
            self.emit_finished(path)
        except CancelledTaskError as exc:
            self.emit_cancelled(stop_reason='cancelled', message=str(exc), metadata=exc.to_dict())
        except Exception as exc:
            self.emit_failed(exc)
