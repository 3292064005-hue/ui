from __future__ import annotations

from robot_sim.application.services.metrics_service import MetricsService
from robot_sim.presentation.state_store import StateStore


class DiagnosticsController:
    def __init__(self, state_store: StateStore, metrics_service: MetricsService) -> None:
        if metrics_service is None:
            raise ValueError('DiagnosticsController requires an explicit metrics service')
        self._state_store = state_store
        self._metrics = metrics_service

    def snapshot(self) -> dict[str, object]:
        state = self._state_store.state
        payload: dict[str, object] = {}
        if state.ik_result is not None:
            payload['ik'] = self._metrics.summarize_ik(state.ik_result)
        if state.trajectory is not None:
            payload['trajectory'] = self._metrics.summarize_trajectory(state.trajectory)
        if state.benchmark_report is not None:
            payload['benchmark'] = self._metrics.summarize_benchmark(state.benchmark_report)
        return payload
