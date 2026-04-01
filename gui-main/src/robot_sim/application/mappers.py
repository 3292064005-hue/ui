from __future__ import annotations

from robot_sim.model.benchmark_report import BenchmarkReport
from robot_sim.model.trajectory import JointTrajectory


def benchmark_report_to_dict(report: BenchmarkReport) -> dict[str, object]:
    return {
        'robot': report.robot,
        'num_cases': report.num_cases,
        'success_rate': report.success_rate,
        'cases': list(report.cases),
        'aggregate': dict(report.aggregate),
        'metadata': dict(report.metadata),
        'comparison': dict(report.comparison),
    }


def trajectory_summary_to_dict(trajectory: JointTrajectory) -> dict[str, object]:
    return {
        'num_samples': int(trajectory.t.shape[0]),
        'dof': int(trajectory.q.shape[1]),
        'metadata': dict(trajectory.metadata),
        'quality': dict(trajectory.quality),
        'feasibility': dict(trajectory.feasibility),
    }
