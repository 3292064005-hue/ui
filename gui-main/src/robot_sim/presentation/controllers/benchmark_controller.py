from __future__ import annotations

import numpy as np

from robot_sim.application.use_cases.run_benchmark import RunBenchmarkUseCase
from robot_sim.model.benchmark_report import BenchmarkReport
from robot_sim.model.solver_config import IKConfig
from robot_sim.presentation.state_store import StateStore


class BenchmarkController:
    def __init__(self, state_store: StateStore, benchmark_uc: RunBenchmarkUseCase, ik_builder) -> None:
        self._state_store = state_store
        self._benchmark_uc = benchmark_uc
        self._ik_builder = ik_builder

    def build_benchmark_config(self, **kwargs) -> IKConfig:
        dummy_pose = self._state_store.state.fk_result.ee_pose if self._state_store.state.fk_result is not None else None
        if dummy_pose is None:
            values6 = [0.0] * 6
        else:
            values6 = list(np.asarray(dummy_pose.p, dtype=float)) + [0.0, 0.0, 0.0]
        req = self._ik_builder(values6, **kwargs)
        return req.config

    def run_benchmark(self, config: IKConfig | None = None) -> BenchmarkReport:
        spec = self._state_store.state.robot_spec
        if spec is None:
            raise RuntimeError('robot not loaded')
        config = config or self.build_benchmark_config()
        report = self._benchmark_uc.execute(spec, config)
        self._state_store.patch(benchmark_report=report)
        return report
