from __future__ import annotations

from robot_sim.application.planner_plugins import (
    CartesianSampledTrajectoryPlugin,
    JointQuinticTrajectoryPlugin,
    JointTrapezoidalTrajectoryPlugin,
    WaypointGraphTrajectoryPlugin,
)
from robot_sim.core.trajectory.registry import TrajectoryPlannerRegistry
from robot_sim.domain.enums import PlannerFamily


class PlannerRegistry(TrajectoryPlannerRegistry):
    """Application-visible trajectory planner registry."""

    pass


def build_default_planner_registry(ik_uc) -> PlannerRegistry:
    """Build the default planner registry used by the application container."""
    registry = PlannerRegistry()
    registry.register(
        'joint_quintic',
        JointQuinticTrajectoryPlugin(),
        metadata={
            'family': PlannerFamily.JOINT.value,
            'goal_space': 'joint',
            'timing_strategy': 'quintic',
            'source': 'builtin',
        },
        source='builtin',
    )
    registry.register(
        'joint_trapezoidal',
        JointTrapezoidalTrajectoryPlugin(),
        metadata={
            'family': PlannerFamily.JOINT.value,
            'goal_space': 'joint',
            'timing_strategy': 'trapezoidal',
            'source': 'builtin',
        },
        source='builtin',
    )
    registry.register(
        'cartesian_sampled',
        CartesianSampledTrajectoryPlugin(ik_uc),
        metadata={
            'family': PlannerFamily.CARTESIAN.value,
            'goal_space': 'cartesian',
            'requires_ik': True,
            'timing_strategy': 'quintic_samples',
            'source': 'builtin',
        },
        source='builtin',
    )
    registry.register(
        'waypoint_graph',
        WaypointGraphTrajectoryPlugin(ik_uc),
        metadata={
            'family': PlannerFamily.WAYPOINT_GRAPH.value,
            'goal_space': 'waypoint_graph',
            'requires_ik': True,
            'timing_strategy': 'segmentwise',
            'source': 'builtin',
        },
        source='builtin',
    )
    return registry
