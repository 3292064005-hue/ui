from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar

_T = TypeVar('_T')


def run_presented(window, callback: Callable[[], _T], *, title: str = '错误') -> _T | None:
    """Execute a coordinator callback under the shared presentation error boundary.

    Falls back to direct execution in narrow coordinator unit tests where the dummy window
    intentionally omits the full main-window mixin API.
    """
    runner = getattr(window, '_run_presented', None)
    if callable(runner):
        return runner(callback, title=title)
    try:
        return callback()
    except Exception as exc:
        projector = getattr(window, '_project_exception', None)
        if callable(projector):
            projector(exc, title=title)
            return None
        raise


def call_view(window, method_name: str, fallback: Callable[[], _T], *args, **kwargs) -> _T:
    """Call a view-projection method when present, otherwise execute a fallback.

    Args:
        window: Window-like object used by coordinator unit tests and the real UI shell.
        method_name: View method to invoke.
        fallback: Fallback implementation used when the view method is unavailable.

    Returns:
        _T: Result returned by the view method or fallback.

    Raises:
        Exception: Propagates failures from the selected execution path.
    """
    method = getattr(window, method_name, None)
    if callable(method):
        return method(*args, **kwargs)
    return fallback()


def set_plot_curves(window, plot_key: str, curves: Iterable[tuple[str, object, object]], *, clear_first: bool = False) -> None:
    """Populate a plot using the batch API when available.

    Args:
        window: Window-like object exposing ``plots_manager``.
        plot_key: Target plot identifier.
        curves: Iterable of ``(curve_name, x, y)`` tuples.
        clear_first: Whether to clear the plot before inserting curves.

    Returns:
        None: Updates plot state in place.

    Raises:
        None: Missing plotting helpers degrade to per-curve updates.
    """
    manager = getattr(window, 'plots_manager', None)
    if manager is None:
        return
    batch = getattr(manager, 'set_curves_batch', None)
    if callable(batch):
        batch(plot_key, curves, clear_first=clear_first)
        return
    if clear_first and hasattr(manager, 'clear'):
        manager.clear(plot_key)
    for curve_name, x, y in curves:
        if hasattr(manager, 'set_curve'):
            manager.set_curve(plot_key, curve_name, x, y)


def require_view(window, method_name: str, *args, **kwargs):
    """Call a required view-boundary method or raise a contract error.

    Args:
        window: Window-like object that should implement the requested method.
        method_name: Required view/read boundary method name.

    Returns:
        object: Return value from the requested view method.

    Raises:
        AttributeError: If the requested boundary method is unavailable.
    """
    method = getattr(window, method_name, None)
    if not callable(method):
        raise AttributeError(f'missing required view contract: {method_name}')
    return method(*args, **kwargs)


def require_dependency(value: _T | None, name: str) -> _T:
    """Return a required injected dependency or raise a contract error.

    Args:
        value: Candidate injected dependency.
        name: Human-readable dependency name for diagnostics.

    Returns:
        _T: The resolved non-null dependency.

    Raises:
        AttributeError: If the dependency is unavailable.
    """
    if value is None:
        raise AttributeError(f'missing required injected dependency: {name}')
    return value
