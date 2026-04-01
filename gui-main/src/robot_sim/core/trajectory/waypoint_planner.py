from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver
from robot_sim.core.rotation.rotation_error import orientation_error
from robot_sim.model.planner_specs import WaypointPlannerSpec
from robot_sim.model.trajectory import JointTrajectory


@dataclass(frozen=True)
class _CartesianSegmentRequest:
    q_start: object
    q_goal: object | None
    duration: float
    dt: float
    spec: object
    mode: object
    target_pose: object
    ik_config: object | None = None
    max_velocity: float | None = None
    max_acceleration: float | None = None


class WaypointTrajectoryPlanner:
    """Planner that executes waypoint graphs as Cartesian trajectory segments."""

    planner_id = 'waypoint_graph'

    def __init__(self, joint_planner, cartesian_planner) -> None:
        self._joint_planner = joint_planner
        self._cartesian_planner = cartesian_planner
        self._fk = ForwardKinematicsSolver()

    def _estimate_segment_duration(
        self,
        *,
        dt: float,
        total_duration: float,
        start_pose,
        waypoint,
        num_waypoints: int,
    ) -> float:
        minimum = max(float(dt) * 4.0, 0.2)
        hinted = waypoint.duration_hint
        if hinted is not None:
            return max(float(hinted), minimum)

        base_from_total = float(total_duration) / max(num_waypoints, 1) if float(total_duration) > 0.0 else minimum
        linear_distance = float(np.linalg.norm(np.asarray(waypoint.pose.p, dtype=float) - np.asarray(start_pose.p, dtype=float)))
        angular_distance = float(np.linalg.norm(orientation_error(waypoint.pose.R, start_pose.R)))
        translational_term = linear_distance / 0.15 if linear_distance > 0.0 else 0.0
        rotational_term = angular_distance / 0.75 if angular_distance > 0.0 else 0.0
        return max(minimum, base_from_total, translational_term, rotational_term)

    def plan(self, spec: WaypointPlannerSpec) -> JointTrajectory:
        """Plan a waypoint trajectory using a core-neutral waypoint spec.

        Args:
            spec: Core-neutral waypoint planner specification.

        Returns:
            JointTrajectory: Planned waypoint trajectory.

        Raises:
            ValueError: If the waypoint graph is empty.
            RuntimeError: If no trajectory segments are produced.
        """
        if spec.waypoint_graph is None or not spec.waypoint_graph.waypoints:
            raise ValueError('waypoint_graph planner requires waypoint_graph')
        segments = []
        q_start = np.asarray(spec.q_start, dtype=float).copy()
        accumulated_t = 0.0
        current_fk = self._fk.solve(spec.spec, q_start)
        segment_durations: list[float] = []
        segment_sources: list[str] = []
        num_waypoints = len(spec.waypoint_graph.waypoints)
        for idx, waypoint in enumerate(spec.waypoint_graph.waypoints):
            seg_duration = self._estimate_segment_duration(
                dt=spec.dt,
                total_duration=spec.duration,
                start_pose=current_fk.ee_pose,
                waypoint=waypoint,
                num_waypoints=num_waypoints,
            )
            segment_durations.append(float(seg_duration))
            segment_sources.append('hint' if waypoint.duration_hint is not None else 'estimated')
            seg_req = _CartesianSegmentRequest(
                q_start=q_start,
                q_goal=None,
                duration=max(seg_duration, spec.dt * 2.0),
                dt=spec.dt,
                spec=spec.spec,
                mode=spec.mode,
                target_pose=waypoint.pose,
                ik_config=spec.ik_config,
                max_velocity=spec.max_velocity,
                max_acceleration=spec.max_acceleration,
            )
            seg = self._cartesian_planner.execute(seg_req)
            if idx > 0:
                seg = JointTrajectory(
                    t=seg.t[1:] + accumulated_t,
                    q=seg.q[1:],
                    qd=seg.qd[1:],
                    qdd=seg.qdd[1:],
                    ee_positions=None if seg.ee_positions is None else seg.ee_positions[1:],
                    joint_positions=None if seg.joint_positions is None else seg.joint_positions[1:],
                    ee_rotations=None if seg.ee_rotations is None else seg.ee_rotations[1:],
                    metadata=dict(seg.metadata),
                    feasibility=dict(seg.feasibility),
                    quality=dict(seg.quality),
                )
            accumulated_t = float(seg.t[-1]) if seg.t.size else accumulated_t
            q_start = np.asarray(seg.q[-1], dtype=float).copy()
            current_fk = self._fk.solve(spec.spec, q_start)
            segments.append(seg)
        if not segments:
            raise RuntimeError('waypoint planner produced no segments')
        t = np.concatenate([seg.t for seg in segments], axis=0)
        q = np.concatenate([seg.q for seg in segments], axis=0)
        qd = np.concatenate([seg.qd for seg in segments], axis=0)
        qdd = np.concatenate([seg.qdd for seg in segments], axis=0)
        ee = None
        jp = None
        rot = None
        if all(seg.ee_positions is not None for seg in segments):
            ee = np.concatenate([seg.ee_positions for seg in segments], axis=0)
        if all(seg.joint_positions is not None for seg in segments):
            jp = np.concatenate([seg.joint_positions for seg in segments], axis=0)
        if all(seg.ee_rotations is not None for seg in segments):
            rot = np.concatenate([seg.ee_rotations for seg in segments], axis=0)
        metadata = {
            'num_waypoints': len(spec.waypoint_graph.waypoints),
            'has_cached_fk': ee is not None,
            'segment_durations': segment_durations,
            'segment_duration_sources': segment_sources,
            'cache_status': 'ready' if ee is not None and jp is not None and rot is not None else 'partial' if any(item is not None for item in (ee, jp, rot)) else 'none',
            'goal_source': 'waypoint_graph',
            'mode': getattr(spec.mode, 'value', spec.mode),
        }
        return JointTrajectory(
            t=t,
            q=q,
            qd=qd,
            qdd=qdd,
            ee_positions=ee,
            joint_positions=jp,
            ee_rotations=rot,
            metadata=metadata,
        )
