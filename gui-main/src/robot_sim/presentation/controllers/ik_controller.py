from __future__ import annotations

import numpy as np

from robot_sim.application.dto import FKRequest, IKRequest
from robot_sim.application.use_cases.run_fk import RunFKUseCase
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.core.math.so3 import exp_so3
from robot_sim.core.math.transforms import rot_x, rot_y, rot_z
from robot_sim.domain.enums import AppExecutionState, IKSolverMode
from robot_sim.model.pose import Pose
from robot_sim.model.solver_config import IKConfig
from robot_sim.presentation.state_store import StateStore
from robot_sim.presentation.validators.input_validator import InputValidator


class IKController:
    def _parse_mode(self, value):
        value = str(value)
        try:
            return IKSolverMode(value)
        except ValueError:
            return value

    def __init__(self, state_store: StateStore, solver_defaults: dict, fk_uc: RunFKUseCase, ik_uc: RunIKUseCase) -> None:
        self._state_store = state_store
        self._solver_defaults = dict(solver_defaults)
        self._fk_uc = fk_uc
        self._ik_uc = ik_uc

    def build_target_pose(self, values6, orientation_mode: str = 'rvec') -> Pose:
        values6 = InputValidator.validate_target_values(values6)
        p = np.asarray(values6[:3], dtype=float)
        if orientation_mode == 'euler_zyx':
            yaw, pitch, roll = values6[3:]
            R = rot_z(float(yaw)) @ rot_y(float(pitch)) @ rot_x(float(roll))
        else:
            R = exp_so3(np.asarray(values6[3:], dtype=float))
        return Pose(p=p, R=R)

    def build_ik_request(self, values6, **kwargs) -> IKRequest:
        spec = self._state_store.state.robot_spec
        q0 = self._state_store.state.q_current
        if spec is None or q0 is None:
            raise RuntimeError('robot not loaded')
        target = self.build_target_pose(values6, orientation_mode=str(kwargs.get('orientation_mode', 'rvec')))
        config = IKConfig(
            mode=self._parse_mode(kwargs.get('mode', 'dls')),
            max_iters=int(kwargs.get('max_iters', 150)),
            step_scale=float(kwargs.get('step_scale', 0.5)),
            damping_lambda=float(kwargs.get('damping', 0.05)),
            enable_nullspace=bool(kwargs.get('enable_nullspace', True)),
            position_only=bool(kwargs.get('position_only', False)),
            pos_tol=float(kwargs.get('pos_tol', 1e-4)),
            ori_tol=float(kwargs.get('ori_tol', 1e-4)),
            max_step_norm=float(kwargs.get('max_step_norm', 0.35)),
            fallback_to_dls_when_singular=bool(kwargs.get('auto_fallback', True)),
            reachability_precheck=bool(kwargs.get('reachability_precheck', True)),
            retry_count=max(int(kwargs.get('retry_count', 0)), 0),
            random_seed=int(self._solver_defaults.get('random_seed', 7)),
            joint_limit_weight=float(self._solver_defaults.get('joint_limit_weight', 0.03) if kwargs.get('joint_limit_weight') is None else kwargs['joint_limit_weight']),
            manipulability_weight=float(self._solver_defaults.get('manipulability_weight', 0.0) if kwargs.get('manipulability_weight') is None else kwargs['manipulability_weight']),
            orientation_weight=float(self._solver_defaults.get('orientation_weight', 1.0) if kwargs.get('orientation_weight') is None else kwargs['orientation_weight']),
            adaptive_damping=bool(self._solver_defaults.get('adaptive_damping', True) if kwargs.get('adaptive_damping') is None else kwargs['adaptive_damping']),
            min_damping_lambda=float(self._solver_defaults.get('min_damping_lambda', 1.0e-4)),
            max_damping_lambda=float(self._solver_defaults.get('max_damping_lambda', 1.5)),
            use_weighted_least_squares=bool(self._solver_defaults.get('use_weighted_least_squares', True) if kwargs.get('use_weighted_least_squares') is None else kwargs['use_weighted_least_squares']),
            clamp_seed_to_joint_limits=bool(self._solver_defaults.get('clamp_seed_to_joint_limits', True) if kwargs.get('clamp_seed_to_joint_limits') is None else kwargs['clamp_seed_to_joint_limits']),
            normalize_target_rotation=bool(self._solver_defaults.get('normalize_target_rotation', True) if kwargs.get('normalize_target_rotation') is None else kwargs['normalize_target_rotation']),
            allow_orientation_relaxation=bool(self._solver_defaults.get('allow_orientation_relaxation', False) if kwargs.get('allow_orientation_relaxation') is None else kwargs['allow_orientation_relaxation']),
            orientation_relaxation_pos_multiplier=float(self._solver_defaults.get('orientation_relaxation_pos_multiplier', 5.0) if kwargs.get('orientation_relaxation_pos_multiplier') is None else kwargs['orientation_relaxation_pos_multiplier']),
            orientation_relaxation_ori_multiplier=float(self._solver_defaults.get('orientation_relaxation_ori_multiplier', 25.0) if kwargs.get('orientation_relaxation_ori_multiplier') is None else kwargs['orientation_relaxation_ori_multiplier']),
        )
        return IKRequest(spec, target, q0.copy(), config)

    def apply_ik_result(self, req: IKRequest, result) -> None:
        q_current = result.q_sol.copy() if result.success else (result.best_q.copy() if result.best_q is not None else req.q0.copy())
        self._state_store.patch(
            target_pose=req.target,
            ik_result=result,
            q_current=q_current,
            last_error='' if result.success else result.message,
            last_warning='' if result.success else result.message,
            app_state=AppExecutionState.ROBOT_READY if result.success else AppExecutionState.ERROR,
        )
        self._state_store.patch(
            fk_result=self._fk_uc.execute(FKRequest(req.spec, self._state_store.state.q_current)),
            scene_revision=self._state_store.state.scene_revision + 1,
        )

    def run_ik(self, values6, **kwargs):
        req = self.build_ik_request(values6, **kwargs)
        result = self._ik_uc.execute(req)
        self.apply_ik_result(req, result)
        return result
