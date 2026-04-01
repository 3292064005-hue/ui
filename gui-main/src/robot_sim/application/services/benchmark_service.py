from __future__ import annotations

from collections.abc import Callable

import numpy as np

from robot_sim.application.dto import IKRequest
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver
from robot_sim.core.math.so3 import exp_so3
from robot_sim.domain.errors import CancelledTaskError
from robot_sim.model.benchmark_case import BenchmarkCase, BenchmarkCaseResult
from robot_sim.model.pose import Pose
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.solver_config import IKConfig
from robot_sim.model.version_catalog import VersionCatalog, current_version_catalog


class BenchmarkService:
    """Service that executes benchmark cases and aggregates solver metrics."""

    def __init__(self, run_ik_uc: RunIKUseCase, version_catalog: VersionCatalog | None = None) -> None:
        """Create the benchmark service.

        Args:
            run_ik_uc: IK use case used for each benchmark case.
            version_catalog: Optional version catalog used for manifest metadata.

        Returns:
            None: Initializes benchmark dependencies only.

        Raises:
            ValueError: If ``run_ik_uc`` is not provided.
        """
        if run_ik_uc is None:
            raise ValueError('BenchmarkService requires an explicit IK use case')
        self._fk = ForwardKinematicsSolver()
        self._ik_uc = run_ik_uc
        self._versions = version_catalog or current_version_catalog()

    def default_cases(self, spec: RobotSpec) -> list[BenchmarkCase]:
        """Build the default benchmark-suite case list for a robot spec."""
        home_q = np.asarray(spec.home_q, dtype=float)
        q_mid = np.asarray(spec.q_mid(), dtype=float)
        home_fk = self._fk.solve(spec, home_q)
        mid_fk = self._fk.solve(spec, q_mid)
        q_min = np.array([row.q_min for row in spec.dh_rows], dtype=float)
        q_max = np.array([row.q_max for row in spec.dh_rows], dtype=float)
        near_limit_q = np.clip(q_mid * 1.15, q_min, q_max)
        near_limit_fk = self._fk.solve(spec, near_limit_q)
        singular_probe_q = np.clip(home_q * 0.25 + q_mid * 0.75, q_min, q_max)
        singular_fk = self._fk.solve(spec, singular_probe_q)
        unreachable_offset = np.array([self._rough_radius(spec) * 1.25, 0.0, 0.0], dtype=float)
        pack_version = self._versions.benchmark_pack_version
        return [
            BenchmarkCase('home_pose', home_fk.ee_pose, metadata={'seed': 'home_q', 'pack_version': pack_version}),
            BenchmarkCase('mid_pose', mid_fk.ee_pose, metadata={'seed': 'q_mid', 'pack_version': pack_version}),
            BenchmarkCase(
                'orientation_shifted',
                Pose(p=home_fk.ee_pose.p + np.array([0.05, 0.02, 0.0]), R=home_fk.ee_pose.R @ exp_so3(np.array([0.0, 0.0, 0.25]))),
                metadata={'seed': 'home_q', 'pack_version': pack_version},
            ),
            BenchmarkCase(
                'position_only_hard',
                Pose(p=mid_fk.ee_pose.p + np.array([0.02, -0.03, 0.01]), R=np.eye(3)),
                position_only=True,
                metadata={'seed': 'home_q', 'pack_version': pack_version},
            ),
            BenchmarkCase('near_limit_pose', near_limit_fk.ee_pose, metadata={'seed': 'q_mid', 'pack_version': pack_version}),
            BenchmarkCase('near_singular_pose', singular_fk.ee_pose, metadata={'seed': 'q_mid', 'pack_version': pack_version}),
            BenchmarkCase(
                'unreachable_far',
                Pose(p=np.asarray(spec.base_T[:3, 3], dtype=float) + unreachable_offset, R=np.eye(3)),
                metadata={'seed': 'home_q', 'pack_version': pack_version},
            ),
        ]

    def run(
        self,
        spec: RobotSpec,
        config: IKConfig,
        cases: list[BenchmarkCase] | None = None,
        *,
        baseline: dict[str, object] | None = None,
        cancel_flag: Callable[[], bool] | None = None,
        progress_cb: Callable[[float, str, dict[str, object] | None], None] | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, object]:
        """Execute a benchmark suite and return a structured payload."""
        cases = list(cases) if cases is not None else self.default_cases(spec)
        results: list[BenchmarkCaseResult] = []
        elapsed_ms_values: list[float] = []
        pos_err_values: list[float] = []
        ori_err_values: list[float] = []
        restart_values: list[int] = []
        stop_reason_hist: dict[str, int] = {}
        total_cases = max(len(cases), 1)
        for idx, case in enumerate(cases):
            if cancel_flag is not None and bool(cancel_flag()):
                raise CancelledTaskError(
                    'benchmark cancelled',
                    metadata={
                        'completed_cases': len(results),
                        'total_cases': len(cases),
                        'correlation_id': str(correlation_id or ''),
                    },
                )
            q0 = self._seed_for_case(spec, case)
            cfg = config if not case.position_only else IKConfig(**{**config.__dict__, 'position_only': True})
            result = self._ik_uc.execute(
                IKRequest(spec=spec, target=case.target, q0=q0, config=cfg),
                cancel_flag=cancel_flag,
                progress_cb=None,
                correlation_id=correlation_id,
            )
            elapsed_ms_values.append(float(result.elapsed_ms))
            pos_err_values.append(float(result.final_pos_err))
            ori_err_values.append(float(result.final_ori_err))
            restart_values.append(int(result.restarts_used))
            stop_reason_hist[result.stop_reason or 'unknown'] = stop_reason_hist.get(result.stop_reason or 'unknown', 0) + 1
            results.append(
                BenchmarkCaseResult(
                    case=case,
                    success=bool(result.success),
                    stop_reason=result.stop_reason,
                    final_pos_err=float(result.final_pos_err),
                    final_ori_err=float(result.final_ori_err),
                    elapsed_ms=float(result.elapsed_ms),
                    restarts_used=int(result.restarts_used),
                )
            )
            if progress_cb is not None:
                progress_cb(
                    float(((idx + 1) / total_cases) * 100.0),
                    f'completed benchmark case {idx + 1}/{len(cases)}',
                    {
                        'case_name': case.name,
                        'completed_cases': idx + 1,
                        'total_cases': len(cases),
                        'correlation_id': str(correlation_id or ''),
                    },
                )
        success_vector = np.array([1.0 if item.success else 0.0 for item in results], dtype=float)
        aggregate = {
            'p50_elapsed_ms': float(np.percentile(elapsed_ms_values, 50)) if elapsed_ms_values else 0.0,
            'p95_elapsed_ms': float(np.percentile(elapsed_ms_values, 95)) if elapsed_ms_values else 0.0,
            'mean_final_pos_err': float(np.mean(pos_err_values)) if pos_err_values else float('nan'),
            'mean_final_ori_err': float(np.mean(ori_err_values)) if ori_err_values else float('nan'),
            'mean_restarts_used': float(np.mean(restart_values)) if restart_values else 0.0,
            'stop_reason_histogram': dict(stop_reason_hist),
        }
        comparison = self._comparison_payload(aggregate, baseline=baseline)
        return {
            'robot': str(getattr(spec, 'label', '') or spec.name),
            'num_cases': len(results),
            'success_rate': float(success_vector.mean()) if success_vector.size else 0.0,
            'cases': [
                {
                    'name': item.case.name,
                    'position_only': bool(item.case.position_only),
                    'success': bool(item.success),
                    'stop_reason': item.stop_reason,
                    'final_pos_err': float(item.final_pos_err),
                    'final_ori_err': float(item.final_ori_err),
                    'elapsed_ms': float(item.elapsed_ms),
                    'restarts_used': int(item.restarts_used),
                    'metadata': dict(item.case.metadata),
                }
                for item in results
            ],
            'aggregate': aggregate,
            'metadata': {
                'suite_metadata': {
                    'producer_version': self._versions.app_version,
                    'pack_version': self._versions.benchmark_pack_version,
                    'correlation_id': str(correlation_id or ''),
                },
                'baseline_present': bool(baseline),
                'correlation_id': str(correlation_id or ''),
            },
            'comparison': comparison,
        }

    def _comparison_payload(self, aggregate: dict[str, object], *, baseline: dict[str, object] | None) -> dict[str, object]:
        if not baseline:
            return {'regressed': False, 'baseline_present': False}
        baseline_aggregate = dict(baseline.get('aggregate', {}))
        current_elapsed = float(aggregate.get('p95_elapsed_ms', 0.0) or 0.0)
        baseline_elapsed = float(baseline_aggregate.get('p95_elapsed_ms', 0.0) or 0.0)
        current_pos = float(aggregate.get('mean_final_pos_err', 0.0) or 0.0)
        baseline_pos = float(baseline_aggregate.get('mean_final_pos_err', 0.0) or 0.0)
        regressed = False
        if baseline_elapsed > 0.0 and current_elapsed > baseline_elapsed * 1.1:
            regressed = True
        if baseline_pos > 0.0 and current_pos > baseline_pos * 1.1:
            regressed = True
        return {
            'regressed': regressed,
            'baseline_present': True,
            'baseline_p95_elapsed_ms': baseline_elapsed,
            'baseline_mean_final_pos_err': baseline_pos,
        }

    def _seed_for_case(self, spec: RobotSpec, case: BenchmarkCase) -> np.ndarray:
        seed_name = str(case.metadata.get('seed', 'home_q'))
        if seed_name == 'q_mid':
            return np.asarray(spec.q_mid(), dtype=float)
        return np.asarray(spec.home_q, dtype=float)

    def _rough_radius(self, spec: RobotSpec) -> float:
        total = 0.0
        for row in spec.dh_rows:
            try:
                total += abs(float(row.a)) + abs(float(row.d))
            except (TypeError, ValueError):
                continue
        return total if total > 0.0 else 1.0
