from __future__ import annotations

from collections.abc import Callable

from robot_sim.application.services.benchmark_service import BenchmarkService
from robot_sim.model.benchmark_report import BenchmarkReport
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.solver_config import IKConfig


class RunBenchmarkUseCase:
    """Application use case for executing benchmark suites."""

    def __init__(self, service: BenchmarkService) -> None:
        """Create the use case.

        Args:
            service: Benchmark service used to execute the suite.

        Raises:
            ValueError: If ``service`` is not provided.
        """
        if service is None:
            raise ValueError('RunBenchmarkUseCase requires an explicit benchmark service')
        self._service = service

    def execute(
        self,
        spec: RobotSpec,
        config: IKConfig,
        cases=None,
        *,
        baseline: dict[str, object] | None = None,
        cancel_flag: Callable[[], bool] | None = None,
        progress_cb: Callable[[float, str, dict[str, object] | None], None] | None = None,
        correlation_id: str | None = None,
    ) -> BenchmarkReport:
        """Execute a benchmark suite.

        Args:
            spec: Robot specification under test.
            config: IK configuration used for the suite.
            cases: Optional benchmark cases. Defaults to the built-in suite.
            baseline: Optional baseline payload used for comparison.
            cancel_flag: Optional cooperative cancellation callback.
            progress_cb: Optional progress callback receiving percent, message, and payload.
            correlation_id: Optional correlation identifier.

        Returns:
            Structured benchmark report.

        Raises:
            robot_sim.domain.errors.CancelledTaskError: If execution is cancelled.
        """
        payload = self._service.run(
            spec=spec,
            config=config,
            cases=cases,
            baseline=baseline,
            cancel_flag=cancel_flag,
            progress_cb=progress_cb,
            correlation_id=correlation_id,
        )
        return BenchmarkReport(
            robot=str(payload['robot']),
            num_cases=int(payload['num_cases']),
            success_rate=float(payload['success_rate']),
            cases=tuple(payload.get('cases', [])),
            aggregate=dict(payload.get('aggregate', {})),
            metadata=dict(payload.get('metadata', {})),
            comparison=dict(payload.get('comparison', {})),
        )
