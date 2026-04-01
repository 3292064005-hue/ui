from __future__ import annotations

import numpy as np

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.trajectory_metadata import build_planner_metadata
from robot_sim.application.use_cases.plan_cartesian_trajectory import PlanCartesianTrajectoryUseCase
from robot_sim.application.use_cases.plan_joint_trajectory import PlanJointTrajectoryUseCase
from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver
from robot_sim.core.trajectory.joint_trapezoidal import TrapezoidalTrajectoryPlanner
from robot_sim.core.trajectory.waypoint_planner import WaypointTrajectoryPlanner
from robot_sim.model.trajectory import JointTrajectory


class JointQuinticTrajectoryPlugin:
    planner_id = 'joint_quintic'

    def __init__(self) -> None:
        self._uc = PlanJointTrajectoryUseCase()

    def plan(self, req: TrajectoryRequest) -> JointTrajectory:
        traj = self._uc.execute(req)
        metadata = build_planner_metadata(
            planner_id=self.planner_id,
            goal_source='joint_space',
            cache_status=traj.cache_status,
            mode=getattr(req.mode, 'value', req.mode),
            metadata=dict(traj.metadata),
            has_complete_fk=bool(traj.ee_positions is not None and traj.joint_positions is not None and traj.ee_rotations is not None),
            has_partial_fk=bool(traj.ee_positions is not None or traj.joint_positions is not None or traj.ee_rotations is not None),
        )
        return JointTrajectory(
            t=traj.t,
            q=traj.q,
            qd=traj.qd,
            qdd=traj.qdd,
            ee_positions=traj.ee_positions,
            joint_positions=traj.joint_positions,
            ee_rotations=traj.ee_rotations,
            metadata=metadata,
            feasibility=dict(traj.feasibility),
            quality=dict(traj.quality),
        )


class CartesianSampledTrajectoryPlugin:
    planner_id = 'cartesian_sampled'

    def __init__(self, ik_uc) -> None:
        self._uc = PlanCartesianTrajectoryUseCase(ik_uc)

    def plan(self, req: TrajectoryRequest) -> JointTrajectory:
        traj = self._uc.execute(req)
        metadata = build_planner_metadata(
            planner_id=self.planner_id,
            goal_source='cartesian_pose',
            cache_status=traj.cache_status,
            mode=getattr(req.mode, 'value', req.mode),
            metadata=dict(traj.metadata),
            correlation_id=str(traj.metadata.get('correlation_id', '') or ''),
            has_complete_fk=bool(traj.ee_positions is not None and traj.joint_positions is not None and traj.ee_rotations is not None),
            has_partial_fk=bool(traj.ee_positions is not None or traj.joint_positions is not None or traj.ee_rotations is not None),
        )
        return JointTrajectory(
            t=traj.t,
            q=traj.q,
            qd=traj.qd,
            qdd=traj.qdd,
            ee_positions=traj.ee_positions,
            joint_positions=traj.joint_positions,
            ee_rotations=traj.ee_rotations,
            metadata=metadata,
            feasibility=dict(traj.feasibility),
            quality=dict(traj.quality),
        )


class JointTrapezoidalTrajectoryPlugin:
    planner_id = 'joint_trapezoidal'

    def __init__(self) -> None:
        self._planner = TrapezoidalTrajectoryPlanner()
        self._fk = ForwardKinematicsSolver()

    def plan(self, req: TrajectoryRequest) -> JointTrajectory:
        if req.q_goal is None:
            raise ValueError('joint_trapezoidal planner requires q_goal')
        traj = self._planner.plan(req.q_start, req.q_goal, req.duration, req.dt)
        if req.spec is None:
            metadata = build_planner_metadata(
                planner_id=self.planner_id,
                goal_source='joint_space',
                cache_status='none',
                mode=getattr(req.mode, 'value', req.mode),
                metadata=dict(traj.metadata),
            )
            return JointTrajectory(
                t=traj.t,
                q=traj.q,
                qd=traj.qd,
                qdd=traj.qdd,
                ee_positions=traj.ee_positions,
                joint_positions=traj.joint_positions,
                ee_rotations=traj.ee_rotations,
                metadata=metadata,
                feasibility=dict(traj.feasibility),
                quality=dict(traj.quality),
            )
        ee_positions = []
        ee_rotations = []
        joint_positions = []
        for q in traj.q:
            fk = self._fk.solve(req.spec, np.asarray(q, dtype=float))
            ee_positions.append(fk.ee_pose.p)
            ee_rotations.append(fk.ee_pose.R)
            joint_positions.append(fk.joint_positions)
        metadata = build_planner_metadata(
            planner_id=self.planner_id,
            goal_source='joint_space',
            cache_status='ready',
            mode=getattr(req.mode, 'value', req.mode),
            metadata={
                'has_cached_fk': True,
                'cached_fk_samples': int(traj.q.shape[0]),
                'timing_strategy': 'trapezoidal',
            },
            has_complete_fk=True,
        )
        return JointTrajectory(
            t=np.asarray(traj.t, dtype=float),
            q=np.asarray(traj.q, dtype=float),
            qd=np.asarray(traj.qd, dtype=float),
            qdd=np.asarray(traj.qdd, dtype=float),
            ee_positions=np.asarray(ee_positions, dtype=float),
            joint_positions=np.asarray(joint_positions, dtype=float),
            ee_rotations=np.asarray(ee_rotations, dtype=float),
            metadata=metadata,
        )


class WaypointGraphTrajectoryPlugin:
    planner_id = 'waypoint_graph'

    def __init__(self, ik_uc) -> None:
        self._planner = WaypointTrajectoryPlanner(PlanJointTrajectoryUseCase(), PlanCartesianTrajectoryUseCase(ik_uc))

    def plan(self, req: TrajectoryRequest) -> JointTrajectory:
        spec = req.to_waypoint_planner_spec()
        traj = self._planner.plan(spec)
        metadata = build_planner_metadata(
            planner_id=self.planner_id,
            goal_source='waypoint_graph',
            cache_status=traj.cache_status,
            mode=getattr(req.mode, 'value', req.mode),
            metadata=dict(traj.metadata),
            correlation_id=str(traj.metadata.get('correlation_id', '') or ''),
            has_complete_fk=bool(traj.ee_positions is not None and traj.joint_positions is not None and traj.ee_rotations is not None),
            has_partial_fk=bool(traj.ee_positions is not None or traj.joint_positions is not None or traj.ee_rotations is not None),
        )
        return JointTrajectory(
            t=traj.t,
            q=traj.q,
            qd=traj.qd,
            qdd=traj.qdd,
            ee_positions=traj.ee_positions,
            joint_positions=traj.joint_positions,
            ee_rotations=traj.ee_rotations,
            metadata=metadata,
            feasibility=dict(traj.feasibility),
            quality=dict(traj.quality),
        )
