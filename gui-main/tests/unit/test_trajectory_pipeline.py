from __future__ import annotations

import numpy as np

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.pipelines.trajectory_pipeline import TrajectoryExecutionPipeline
from robot_sim.core.trajectory.registry import TrajectoryPlannerRegistry
from robot_sim.model.dh_row import DHRow
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.trajectory import JointTrajectory


class DummyPlanner:
    def plan(self, req):
        return JointTrajectory(
            t=np.array([0.0, 1.0]),
            q=np.array([[0.0], [1.0]]),
            qd=np.array([[0.0], [0.0]]),
            qdd=np.array([[0.0], [0.0]]),
            metadata={'retimed': True},
        )


class DummyValidate:
    def execute(self, *args, **kwargs):
        return type(
            'Diag',
            (),
            {
                'max_velocity': 0.0,
                'max_acceleration': 0.0,
                'jerk_proxy': 0.0,
                'path_length': 1.0,
                'goal_position_error': 0.0,
                'goal_orientation_error': 0.0,
                'start_to_end_position_delta': 1.0,
                'start_to_end_orientation_delta': 0.0,
                'feasible': True,
                'reasons': (),
                'metadata': {},
            },
        )()


def test_trajectory_execution_pipeline_runs_planner_retime_and_validation():
    registry = TrajectoryPlannerRegistry()
    registry.register('joint_quintic', DummyPlanner())
    spec = RobotSpec(name='one', dh_rows=(DHRow(0, 0, 0, 0, 0, -1, 1),), home_q=np.array([0.0]), base_T=np.eye(4), tool_T=np.eye(4))
    req = TrajectoryRequest(q_start=np.array([0.0]), q_goal=np.array([1.0]), duration=1.0, dt=1.0, spec=spec)
    result = TrajectoryExecutionPipeline(registry, DummyValidate()).execute(req)
    assert result.planner_id == 'joint_quintic'
    assert result.retimed.q.shape == (2, 1)
    assert result.diagnostics.feasible is True
