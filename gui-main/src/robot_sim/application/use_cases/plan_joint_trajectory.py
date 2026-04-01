from __future__ import annotations

import numpy as np

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver
from robot_sim.core.trajectory.quintic import QuinticTrajectoryPlanner
from robot_sim.model.trajectory import JointTrajectory
from robot_sim.model.trajectory_digest import ensure_trajectory_digest_metadata


class PlanJointTrajectoryUseCase:
    def __init__(self) -> None:
        self._planner = QuinticTrajectoryPlanner()
        self._fk = ForwardKinematicsSolver()

    def execute(self, req: TrajectoryRequest) -> JointTrajectory:
        if req.q_goal is None:
            raise ValueError('joint-space trajectory requires q_goal')
        traj = self._planner.plan(req.q_start, req.q_goal, req.duration, req.dt)
        if req.spec is None:
            return traj
        ee_positions = []
        ee_rotations = []
        joint_positions = []
        for q in traj.q:
            fk = self._fk.solve(req.spec, q)
            ee_positions.append(fk.ee_pose.p)
            ee_rotations.append(fk.ee_pose.R)
            joint_positions.append(fk.joint_positions)
        planned = JointTrajectory(
            t=traj.t,
            q=traj.q,
            qd=traj.qd,
            qdd=traj.qdd,
            ee_positions=np.asarray(ee_positions, dtype=float),
            ee_rotations=np.asarray(ee_rotations, dtype=float),
            joint_positions=np.asarray(joint_positions, dtype=float),
            metadata={'goal_source': 'joint_space', 'mode': req.mode.value, 'has_cached_fk': True, 'cached_fk_samples': int(traj.q.shape[0])},
        )
        ensure_trajectory_digest_metadata(planned)
        return planned
