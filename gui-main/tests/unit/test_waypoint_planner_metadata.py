from __future__ import annotations

import numpy as np

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver
from robot_sim.core.trajectory.waypoint_planner import WaypointTrajectoryPlanner
from robot_sim.model.pose import Pose
from robot_sim.model.trajectory import JointTrajectory
from robot_sim.model.waypoint_graph import Waypoint, WaypointGraph


class _DummyCartesianPlanner:
    def __init__(self, spec):
        self._spec = spec
        self._fk = ForwardKinematicsSolver()
        self.calls = []

    def execute(self, req):
        self.calls.append(req)
        q0 = np.asarray(req.q_start, dtype=float)
        q1 = q0 + 0.05
        t = np.array([0.0, req.duration])
        q = np.vstack([q0, q1])
        qd = np.gradient(q, t, axis=0)
        qdd = np.gradient(qd, t, axis=0)
        ee_positions = []
        ee_rotations = []
        joint_positions = []
        for q_i in q:
            fk = self._fk.solve(self._spec, q_i)
            ee_positions.append(fk.ee_pose.p)
            ee_rotations.append(fk.ee_pose.R)
            joint_positions.append(fk.joint_positions)
        return JointTrajectory(
            t=t,
            q=q,
            qd=qd,
            qdd=qdd,
            ee_positions=np.asarray(ee_positions, dtype=float),
            ee_rotations=np.asarray(ee_rotations, dtype=float),
            joint_positions=np.asarray(joint_positions, dtype=float),
            metadata={'has_cached_fk': True},
        )


class _DummyJointPlanner:
    def execute(self, req):
        raise AssertionError('joint planner should not be used in this test')


def test_waypoint_planner_records_segment_durations(planar_spec):
    waypoint_graph = WaypointGraph(
        waypoints=(
            Waypoint(name='w0', pose=Pose(p=np.array([1.8, 0.0, 0.0]), R=np.eye(3))),
            Waypoint(name='w1', pose=Pose(p=np.array([1.7, 0.1, 0.0]), R=np.eye(3)), duration_hint=0.75),
        )
    )
    cart = _DummyCartesianPlanner(planar_spec)
    planner = WaypointTrajectoryPlanner(_DummyJointPlanner(), cart)
    req = TrajectoryRequest(
        q_start=planar_spec.home_q.copy(),
        q_goal=None,
        duration=2.0,
        dt=0.05,
        spec=planar_spec,
        waypoint_graph=waypoint_graph,
    )

    traj = planner.plan(req)

    assert len(traj.metadata['segment_durations']) == 2
    assert traj.metadata['segment_duration_sources'] == ['estimated', 'hint']
    assert abs(traj.metadata['segment_durations'][1] - 0.75) < 1.0e-12
    assert len(cart.calls) == 2
