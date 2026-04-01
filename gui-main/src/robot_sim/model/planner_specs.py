from __future__ import annotations

from dataclasses import dataclass

from robot_sim.domain.enums import TrajectoryMode
from robot_sim.domain.types import FloatArray
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.solver_config import IKConfig
from robot_sim.model.waypoint_graph import WaypointGraph


@dataclass(frozen=True)
class WaypointPlannerSpec:
    """Core-neutral waypoint planner input specification.

    Args:
        q_start: Initial joint configuration.
        duration: Requested total trajectory duration in seconds.
        dt: Sampling period in seconds.
        spec: Robot specification used for FK/IK queries.
        mode: Requested trajectory mode.
        waypoint_graph: Waypoint graph defining the Cartesian route.
        ik_config: Optional IK configuration used for Cartesian segment planning.
        max_velocity: Optional trajectory velocity limit.
        max_acceleration: Optional trajectory acceleration limit.

    Raises:
        None: Dataclass construction only stores normalized planner input.
    """

    q_start: FloatArray
    duration: float
    dt: float
    spec: RobotSpec
    mode: TrajectoryMode
    waypoint_graph: WaypointGraph
    ik_config: IKConfig | None = None
    max_velocity: float | None = None
    max_acceleration: float | None = None
