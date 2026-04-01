from __future__ import annotations

import numpy as np

from robot_sim.application.dto import FKRequest
from robot_sim.application.services.robot_registry import RobotRegistry
from robot_sim.application.use_cases.run_fk import RunFKUseCase
from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.domain.enums import AppExecutionState
from robot_sim.presentation.state_store import StateStore
from robot_sim.presentation.validators.input_validator import InputValidator


class RobotController:
    def __init__(self, state_store: StateStore, registry: RobotRegistry, fk_uc: RunFKUseCase) -> None:
        self._state_store = state_store
        self._registry = registry
        self._fk_uc = fk_uc

    def load_robot(self, name: str):
        spec = self._registry.load(name)
        fk = self._fk_uc.execute(FKRequest(spec, spec.home_q.copy()))
        self._state_store.patch(
            robot_spec=spec,
            q_current=spec.home_q.copy(),
            fk_result=fk,
            target_pose=None,
            ik_result=None,
            trajectory=None,
            benchmark_report=None,
            playback=PlaybackState(),
            last_error='',
            last_warning='',
            app_state=AppExecutionState.ROBOT_READY,
            scene_revision=self._state_store.state.scene_revision + 1,
        )
        return fk

    def build_robot_from_editor(self, existing_spec: RobotSpec | None, rows, home_q) -> RobotSpec:
        if existing_spec is None:
            raise RuntimeError('robot not loaded')
        home_q = np.asarray(home_q, dtype=float)
        home_q = InputValidator.validate_home_q(rows, home_q)
        return RobotSpec(
            name=existing_spec.name,
            dh_rows=tuple(rows),
            base_T=existing_spec.base_T,
            tool_T=existing_spec.tool_T,
            home_q=home_q,
            display_name=existing_spec.display_name,
            description=existing_spec.description,
            metadata=dict(existing_spec.metadata),
        )

    def save_current_robot(self, rows=None, home_q=None, name: str | None = None):
        spec = self._state_store.state.robot_spec
        if spec is None:
            raise RuntimeError('robot not loaded')
        if rows is not None or home_q is not None:
            rows_in = rows if rows is not None else spec.dh_rows
            home_q_in = home_q if home_q is not None else spec.home_q
            spec = self.build_robot_from_editor(rows=rows_in, home_q=home_q_in, existing_spec=spec)
            self._state_store.patch(robot_spec=spec)
        return self._registry.save(spec, name=name)

    def run_fk(self, q=None):
        spec = self._state_store.state.robot_spec
        q_current = self._state_store.state.q_current if q is None else np.asarray(q, dtype=float)
        if spec is None or q_current is None:
            raise RuntimeError('robot not loaded')
        q_current = InputValidator.validate_joint_vector(spec, q_current, clamp=False)
        self._state_store.patch(q_current=q_current.copy())
        fk = self._fk_uc.execute(FKRequest(spec, q_current))
        self._state_store.patch(fk_result=fk, scene_revision=self._state_store.state.scene_revision + 1)
        return fk

    def sample_ee_positions(self, q_samples) -> np.ndarray:
        spec = self._state_store.state.robot_spec
        if spec is None:
            raise RuntimeError('robot not loaded')
        pts = []
        for q in np.asarray(q_samples, dtype=float):
            fk = self._fk_uc.execute(FKRequest(spec, np.asarray(q, dtype=float)))
            pts.append(np.asarray(fk.ee_pose.p, dtype=float))
        return np.asarray(pts, dtype=float)
