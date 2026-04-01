from __future__ import annotations

from dataclasses import dataclass

from robot_sim.domain.enums import TrajectoryMode
from robot_sim.domain.types import FloatArray
from robot_sim.model.pose import Pose
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.solver_config import IKConfig
from robot_sim.model.waypoint_graph import WaypointGraph
from robot_sim.model.planner_specs import WaypointPlannerSpec


@dataclass(frozen=True)
class FKRequest:
    """Forward-kinematics request at the application boundary."""

    spec: RobotSpec
    q: FloatArray


@dataclass(frozen=True)
class IKRequest:
    """Inverse-kinematics request at the application boundary."""

    spec: RobotSpec
    target: Pose
    q0: FloatArray
    config: IKConfig



@dataclass(frozen=True)
class TrajectoryRequest:
    """Trajectory planning request at the application boundary."""

    q_start: FloatArray
    q_goal: FloatArray | None
    duration: float
    dt: float
    spec: RobotSpec | None = None
    mode: TrajectoryMode = TrajectoryMode.JOINT
    target_pose: Pose | None = None
    ik_config: IKConfig | None = None
    planner_id: str | None = None
    waypoint_graph: WaypointGraph | None = None
    max_velocity: float | None = None
    max_acceleration: float | None = None
    collision_obstacles: tuple[object, ...] = ()
    planning_scene: object | None = None

    def to_waypoint_planner_spec(self) -> WaypointPlannerSpec:
        """Build a core-neutral waypoint planner spec from the request.

        Returns:
            Immutable waypoint planner specification.

        Raises:
            ValueError: If the robot specification or waypoint graph is missing.
        """
        if self.spec is None:
            raise ValueError('waypoint planner requires robot spec')
        if self.waypoint_graph is None:
            raise ValueError('waypoint planner requires waypoint_graph')
        return WaypointPlannerSpec(
            q_start=self.q_start,
            duration=float(self.duration),
            dt=float(self.dt),
            spec=self.spec,
            mode=self.mode,
            waypoint_graph=self.waypoint_graph,
            ik_config=self.ik_config,
            max_velocity=self.max_velocity,
            max_acceleration=self.max_acceleration,
        )
