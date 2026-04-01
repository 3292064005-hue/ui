from __future__ import annotations

from robot_sim.application.dto import TrajectoryRequest


class PlanWaypointTrajectoryUseCase:
    """Application use case that adapts DTOs for the waypoint planner."""

    def __init__(self, planner_registry) -> None:
        self._planner_registry = planner_registry

    def execute(self, req: TrajectoryRequest):
        """Execute the waypoint planner using a core-neutral planner spec.

        Args:
            req: Application trajectory request.

        Returns:
            Planned trajectory payload from the waypoint planner.

        Raises:
            ValueError: If the request cannot be converted into a waypoint planner spec.
        """
        planner = self._planner_registry.get('waypoint_graph')
        spec = req.to_waypoint_planner_spec() if hasattr(req, 'to_waypoint_planner_spec') else req
        return planner.plan(spec)
