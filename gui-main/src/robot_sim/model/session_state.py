from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from robot_sim.domain.enums import AppExecutionState
from robot_sim.domain.types import FloatArray
from robot_sim.model.benchmark_report import BenchmarkReport
from robot_sim.model.fk_result import FKResult
from robot_sim.model.ik_result import IKResult
from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.pose import Pose
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.task_snapshot import TaskSnapshot
from robot_sim.model.trajectory import JointTrajectory

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.core.collision.scene import PlanningScene


@dataclass
class SessionState:
    """Mutable top-level GUI session state."""

    robot_spec: Optional[RobotSpec] = None
    q_current: Optional[FloatArray] = None
    target_pose: Optional[Pose] = None
    fk_result: Optional[FKResult] = None
    ik_result: Optional[IKResult] = None
    trajectory: Optional[JointTrajectory] = None
    playback: PlaybackState = field(default_factory=PlaybackState)
    benchmark_report: Optional[BenchmarkReport] = None
    planning_scene: PlanningScene | object | None = None
    is_busy: bool = False
    busy_reason: str = ""
    last_error: str = ""
    last_warning: str = ""
    app_state: AppExecutionState = AppExecutionState.IDLE
    active_task_id: str = ""
    active_task_kind: str = ""
    scene_revision: int = 0
    warnings: tuple[str, ...] = ()
    active_task_snapshot: TaskSnapshot | None = None
    active_warning_codes: tuple[str, ...] = ()
    capability_matrix: dict[str, object] | None = None
    module_statuses: dict[str, str] = field(default_factory=dict)
    last_error_payload: dict[str, object] = field(default_factory=dict)
    scene_summary: dict[str, object] = field(default_factory=dict)
    last_error_code: str = ''
    last_error_title: str = ''
    last_error_severity: str = ''
    last_error_hint: str = ''
    task_state: str = ''
    task_stop_reason: str = ''
    task_correlation_id: str = ''
    last_terminal_task_snapshot: TaskSnapshot | None = None
