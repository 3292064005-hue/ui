from __future__ import annotations

import numpy as np

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.registries.planner_registry import build_default_planner_registry
from robot_sim.application.use_cases.plan_cartesian_trajectory import PlanCartesianTrajectoryUseCase
from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.core.ik.registry import DefaultSolverRegistry
from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver
from robot_sim.model.pose import Pose


def test_joint_trajectory_metadata_includes_phase_timings(planar_spec):
    req = TrajectoryRequest(
        q_start=np.array([0.0, 0.0]),
        q_goal=np.array([0.5, -0.2]),
        duration=1.0,
        dt=0.1,
        spec=planar_spec,
    )
    traj = PlanTrajectoryUseCase(build_default_planner_registry(RunIKUseCase(DefaultSolverRegistry()))).execute(req)
    phase_timings = traj.metadata['phase_timings_ms']
    assert set(phase_timings) == {'planner', 'retime', 'validate', 'total'}
    assert phase_timings['total'] >= phase_timings['planner']
    assert traj.feasibility['timing_summary']['phase_timings_ms']['total'] == phase_timings['total']
    assert traj.metadata['trajectory_digest'] == traj.trajectory_digest


def test_cartesian_trajectory_metadata_includes_phase_timings(planar_spec):
    ik_uc = RunIKUseCase(DefaultSolverRegistry())
    start = np.array([0.0, 0.0])
    fk = ForwardKinematicsSolver().solve(planar_spec, start)
    target_pose = Pose(p=np.asarray(fk.ee_pose.p, dtype=float) + np.array([0.05, 0.0, 0.0]), R=fk.ee_pose.R)
    req = TrajectoryRequest(
        q_start=start,
        duration=0.4,
        dt=0.2,
        spec=planar_spec,
        q_goal=start,
        target_pose=target_pose,
        mode='cartesian_pose',
    )
    traj = PlanCartesianTrajectoryUseCase(ik_uc).execute(req)
    phase_timings = traj.metadata['phase_timings_ms']
    assert set(phase_timings) == {'sampling_ik', 'fk_projection', 'differentiation', 'total'}
    assert phase_timings['total'] >= phase_timings['sampling_ik']
    assert traj.metadata['trajectory_digest'] == traj.trajectory_digest
