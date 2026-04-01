from __future__ import annotations

from robot_sim.model.session_state import SessionState
from robot_sim.presentation.state_store import StateStore


def test_state_store_supports_subscription_and_snapshot():
    store = StateStore(SessionState())
    seen = []
    unsubscribe = store.subscribe(lambda state: seen.append((state.is_busy, state.busy_reason)), emit_current=True)
    store.patch(is_busy=True, busy_reason='ik')
    snap = store.snapshot()
    unsubscribe()
    store.patch(is_busy=False, busy_reason='')

    assert seen[0] == (False, '')
    assert seen[1] == (True, 'ik')
    assert snap.is_busy is True
    assert snap.busy_reason == 'ik'
