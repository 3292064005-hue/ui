from __future__ import annotations

from dataclasses import dataclass, field
import time

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.use_cases.validate_trajectory import ValidateTrajectoryUseCase
from robot_sim.core.trajectory.retiming import retime_trajectory
from robot_sim.model.trajectory import JointTrajectory


@dataclass(frozen=True)
class TrajectoryPipelineResult:
    """Structured result emitted by the trajectory execution pipeline.

    Attributes:
        planner_id: Planner identifier selected for execution.
        raw: Raw trajectory before retiming.
        retimed: Final retimed trajectory returned to callers.
        diagnostics: Validation diagnostics associated with the final trajectory.
        cache_status: Cache state projected onto the final trajectory metadata.
        scene_revision: Planning-scene revision used during validation.
        validation_stage: Name of the validation stage that produced diagnostics.
        phase_timings_ms: Per-stage timing measurements used by diagnostics and profiling.
    """

    planner_id: str
    raw: JointTrajectory
    retimed: JointTrajectory
    diagnostics: object
    cache_status: str = 'none'
    scene_revision: int = 0
    validation_stage: str = 'validate_trajectory'
    phase_timings_ms: dict[str, float] = field(default_factory=dict)


class TrajectoryExecutionPipeline:
    """Pipeline that resolves a planner, retimes the result, and validates it."""

    def __init__(self, planner_registry, validate_uc: ValidateTrajectoryUseCase | None = None) -> None:
        self._planner_registry = planner_registry
        self._validate_uc = validate_uc or ValidateTrajectoryUseCase()

    def resolve_planner_id(self, req: TrajectoryRequest) -> str:
        if req.waypoint_graph is not None:
            return str(req.planner_id or 'waypoint_graph')
        if req.planner_id:
            return str(req.planner_id)
        mode = getattr(req.mode, 'value', req.mode)
        return 'cartesian_sampled' if str(mode) == 'cartesian_pose' else 'joint_quintic'

    def execute(self, req: TrajectoryRequest) -> TrajectoryPipelineResult:
        started = time.perf_counter()
        planner_id = self.resolve_planner_id(req)
        planner = self._planner_registry.get(planner_id)

        planner_started = time.perf_counter()
        raw = planner.plan(req)
        planner_elapsed_ms = (time.perf_counter() - planner_started) * 1000.0

        retime_started = time.perf_counter()
        retimed = retime_trajectory(raw, max_velocity=req.max_velocity, max_acceleration=req.max_acceleration)
        retime_elapsed_ms = (time.perf_counter() - retime_started) * 1000.0

        validate_started = time.perf_counter()
        diagnostics = self._validate_uc.execute(
            retimed,
            collision_obstacles=req.collision_obstacles,
            target_pose=req.target_pose,
            spec=req.spec,
            q_goal=req.q_goal,
            planning_scene=req.planning_scene,
        )
        validate_elapsed_ms = (time.perf_counter() - validate_started) * 1000.0

        phase_timings_ms = {
            'planner': float(planner_elapsed_ms),
            'retime': float(retime_elapsed_ms),
            'validate': float(validate_elapsed_ms),
            'total': float((time.perf_counter() - started) * 1000.0),
        }
        collision_summary = dict(diagnostics.metadata.get('collision_summary', {}))
        timing_summary = dict(diagnostics.metadata.get('timing_summary', {}))
        collision_summary.setdefault('phase_timings_ms', dict(phase_timings_ms))
        timing_summary.setdefault('phase_timings_ms', dict(phase_timings_ms))
        diagnostics.metadata['collision_summary'] = collision_summary
        diagnostics.metadata['timing_summary'] = timing_summary
        cache_status = getattr(retimed, 'cache_status', 'none')
        scene_revision = int(collision_summary.get('scene_revision', 0))
        return TrajectoryPipelineResult(
            planner_id=planner_id,
            raw=raw,
            retimed=retimed,
            diagnostics=diagnostics,
            cache_status=cache_status,
            scene_revision=scene_revision,
            validation_stage='validate_trajectory',
            phase_timings_ms=phase_timings_ms,
        )
