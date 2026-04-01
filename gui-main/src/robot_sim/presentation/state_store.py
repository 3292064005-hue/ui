from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from robot_sim.model.session_state import SessionState


StateSubscriber = Callable[[SessionState], None]


class StateStore:
    """Observable mutable state container for the GUI layer."""

    def __init__(self, state: SessionState | None = None) -> None:
        self._state = state or SessionState()
        self._subscribers: list[StateSubscriber] = []

    @property
    def state(self) -> SessionState:
        """Return the current mutable application session state."""
        return self._state

    def subscribe(self, callback: StateSubscriber, *, emit_current: bool = False) -> Callable[[], None]:
        """Register a state subscriber.

        Args:
            callback: Callback invoked whenever the state changes.
            emit_current: Whether to emit the current state immediately.

        Returns:
            Callable that unsubscribes the callback.
        """
        self._subscribers.append(callback)
        if emit_current:
            callback(self._state)

        def _unsubscribe() -> None:
            self.unsubscribe(callback)

        return _unsubscribe

    def unsubscribe(self, callback: StateSubscriber) -> None:
        """Remove a previously registered subscriber."""
        try:
            self._subscribers.remove(callback)
        except ValueError:
            pass

    def notify(self) -> SessionState:
        """Notify subscribers and return the current state."""
        for subscriber in tuple(self._subscribers):
            subscriber(self._state)
        return self._state

    def patch(self, **kwargs: Any) -> SessionState:
        """Patch arbitrary session state fields and notify subscribers."""
        for key, value in kwargs.items():
            setattr(self._state, key, value)
        return self.notify()

    def patch_task(self, snapshot) -> SessionState:
        """Patch the active task snapshot fields."""
        return self.patch(
            active_task_snapshot=snapshot,
            active_task_id=getattr(snapshot, 'task_id', ''),
            active_task_kind=getattr(snapshot, 'task_kind', ''),
            task_state=getattr(snapshot, 'state', ''),
            task_stop_reason=getattr(snapshot, 'stop_reason', ''),
            task_correlation_id=getattr(snapshot, 'correlation_id', ''),
        )

    def patch_error(self, error_presentation) -> SessionState:
        """Patch the last structured error presentation."""
        return self.patch(
            last_error=getattr(error_presentation, 'user_message', ''),
            last_error_payload=dict(getattr(error_presentation, 'log_payload', {}) or {}),
            last_error_code=str(getattr(error_presentation, 'error_code', '') or ''),
            last_error_title=str(getattr(error_presentation, 'title', '') or ''),
            last_error_severity=str(getattr(error_presentation, 'severity', '') or ''),
            last_error_hint=str(getattr(error_presentation, 'remediation_hint', '') or ''),
        )

    def patch_warning(self, code: str, message: str) -> SessionState:
        """Patch warning state while preserving prior warning history."""
        codes = tuple(dict.fromkeys((*self._state.active_warning_codes, str(code))))
        warnings = tuple(dict.fromkeys((*self._state.warnings, str(message))))
        return self.patch(active_warning_codes=codes, warnings=warnings, last_warning=str(message))

    def patch_scene(self, scene_summary: dict[str, object], *, planning_scene: object | None = None, scene_revision: int | None = None) -> SessionState:
        """Patch planning scene projection state."""
        kwargs: dict[str, object] = {'scene_summary': dict(scene_summary)}
        if planning_scene is not None:
            kwargs['planning_scene'] = planning_scene
        if scene_revision is not None:
            kwargs['scene_revision'] = int(scene_revision)
        return self.patch(**kwargs)

    def patch_capabilities(self, capability_matrix) -> SessionState:
        """Patch capability matrix state from a structured capability object."""
        payload = capability_matrix.as_dict() if hasattr(capability_matrix, 'as_dict') else dict(capability_matrix)
        return self.patch(capability_matrix=payload)

    def replace(self, state: SessionState) -> SessionState:
        """Replace the entire session state and notify subscribers."""
        self._state = state
        return self.notify()

    def snapshot(self) -> SessionState:
        """Return a deep copy of the current state for serialization or tests."""
        return deepcopy(self._state)
