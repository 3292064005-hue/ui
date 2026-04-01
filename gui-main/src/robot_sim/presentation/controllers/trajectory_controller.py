from __future__ import annotations

import numpy as np

from robot_sim.application.dto import TrajectoryRequest
from robot_sim.application.services.playback_service import PlaybackService
from robot_sim.application.use_cases.plan_trajectory import PlanTrajectoryUseCase
from robot_sim.domain.enums import AppExecutionState, TrajectoryMode
from robot_sim.presentation.state_store import StateStore
from robot_sim.presentation.validators.input_validator import InputValidator


class TrajectoryController:
    """Presentation controller for trajectory requests and application state."""

    def __init__(self, state_store: StateStore, planner_uc: PlanTrajectoryUseCase, playback_service: PlaybackService, ik_builder) -> None:
        self._state_store = state_store
        self._planner_uc = planner_uc
        self._playback_service = playback_service
        self._ik_builder = ik_builder

    def trajectory_goal_or_raise(self) -> np.ndarray:
        result = self._state_store.state.ik_result
        if result is None or not result.success:
            raise RuntimeError('请先得到一个成功的 IK 解，再生成轨迹')
        return np.asarray(result.q_sol, dtype=float).copy()

    def build_trajectory_request(self, q_goal=None, duration=3.0, dt=0.02, *, mode: str = 'joint_space', target_values6=None, orientation_mode: str = 'rvec', ik_kwargs: dict | None = None) -> TrajectoryRequest:
        if self._state_store.state.q_current is None or self._state_store.state.robot_spec is None:
            raise RuntimeError('robot not loaded')
        duration, dt = InputValidator.validate_duration_and_dt(duration, dt)
        traj_mode = TrajectoryMode(str(mode))
        common_kwargs = {
            'spec': self._state_store.state.robot_spec,
            'planning_scene': self._state_store.state.planning_scene,
        }
        if traj_mode is TrajectoryMode.CARTESIAN:
            if target_values6 is None:
                raise RuntimeError('笛卡尔轨迹需要目标位姿')
            ik_kwargs = dict(ik_kwargs or {})
            ik_req = self._ik_builder(target_values6, orientation_mode=orientation_mode, **ik_kwargs)
            return TrajectoryRequest(
                self._state_store.state.q_current.copy(),
                None,
                duration,
                dt,
                mode=traj_mode,
                target_pose=ik_req.target,
                ik_config=ik_req.config,
                **common_kwargs,
            )
        goal = self.trajectory_goal_or_raise() if q_goal is None else q_goal
        q_goal = InputValidator.validate_joint_vector(self._state_store.state.robot_spec, goal, clamp=True)
        return TrajectoryRequest(
            self._state_store.state.q_current.copy(),
            np.asarray(q_goal, dtype=float),
            duration,
            dt,
            mode=traj_mode,
            **common_kwargs,
        )

    def plan_trajectory(self, **kwargs):
        req = self.build_trajectory_request(**kwargs)
        result = self._planner_uc.execute(req)
        self.apply_trajectory(result)
        return result

    def apply_trajectory(self, traj) -> None:
        self._state_store.patch(
            trajectory=traj,
            playback=self._playback_service.build_state(traj, frame_idx=0, speed_multiplier=self._state_store.state.playback.speed_multiplier, loop_enabled=self._state_store.state.playback.loop_enabled),
            app_state=AppExecutionState.ROBOT_READY,
            scene_revision=max(int(self._state_store.state.scene_revision), int(getattr(traj, 'scene_revision', 0))),
            scene_summary={
                **dict(self._state_store.state.scene_summary),
                'scene_revision': int(getattr(traj, 'scene_revision', 0)),
                'trajectory_cache_status': str(getattr(traj, 'cache_status', 'none')),
            },
        )
