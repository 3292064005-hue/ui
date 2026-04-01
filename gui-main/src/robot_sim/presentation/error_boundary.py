from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, TypeVar

from robot_sim.domain.error_projection import TaskErrorMapper

_T = TypeVar('_T')


class StateStoreProtocol(Protocol):
    """Minimal state-store contract required by :class:`PresentationErrorBoundary`."""

    def patch_error(self, presentation) -> None:
        """Persist a structured error presentation into the UI state store."""


@dataclass
class PresentationErrorBoundary:
    """Shared exception boundary for presentation callbacks.

    Args:
        mapper: Canonical task-error mapper used for exception projection.
        state_store: Presentation state store updated with projected errors.
        dialog_sink: UI dialog sink used for blocking error presentation.
        status_sink: Status sink used for non-blocking error summaries.
    """

    mapper: TaskErrorMapper
    state_store: StateStoreProtocol
    dialog_sink: Callable[[str, str], None]
    status_sink: Callable[[str], None]

    def project_exception(self, exc: Exception | str, *, title: str = '错误') -> None:
        """Project an exception through the canonical mapper into dialog UI.

        Args:
            exc: Exception instance or fallback textual message.
            title: Fallback dialog title used when the projection has no title.

        Returns:
            None: Updates the state store and displays a blocking dialog.

        Raises:
            None: All failures are normalized into presentation data.
        """
        normalized = exc if isinstance(exc, Exception) else Exception(str(exc))
        presentation = self.mapper.map_exception(normalized)
        self.state_store.patch_error(presentation)
        self.dialog_sink(presentation.title or title, presentation.user_message)

    def append_projected_error(self, prefix: str, exc: Exception | str) -> None:
        """Project an exception into a non-blocking status-line summary.

        Args:
            prefix: Status-line prefix describing the failed action.
            exc: Exception instance or fallback textual message.

        Returns:
            None: Updates the state store and appends a status-line error summary.

        Raises:
            None: All failures are normalized into presentation data.
        """
        normalized = exc if isinstance(exc, Exception) else Exception(str(exc))
        presentation = self.mapper.map_exception(normalized)
        self.state_store.patch_error(presentation)
        self.status_sink(f'{prefix}：{presentation.user_message}')

    def run_presented(self, callback: Callable[[], _T], *, title: str = '错误') -> _T | None:
        """Execute a presentation callback under the shared dialog error boundary.

        Args:
            callback: Zero-argument callback to execute.
            title: Fallback dialog title for unexpected failures.

        Returns:
            Optional callback result when execution succeeds.

        Raises:
            None: Exceptions are projected into the UI boundary and swallowed.
        """
        try:
            return callback()
        except Exception as exc:
            self.project_exception(exc, title=title)
            return None

    def run_status_projected(self, callback: Callable[[], _T], *, prefix: str) -> _T | None:
        """Execute a callback and append projected failures to the status panel.

        Args:
            callback: Zero-argument callback to execute.
            prefix: Leading status text for projected failures.

        Returns:
            Optional callback result when execution succeeds.

        Raises:
            None: Exceptions are projected into the status panel and swallowed.
        """
        try:
            return callback()
        except Exception as exc:
            self.append_projected_error(prefix, exc)
            return None
