from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from robot_sim.core.ik.dls import DLSIKSolver
from robot_sim.core.kinematics.dh import dh_transform
from robot_sim.core.kinematics.fk_solver import ForwardKinematicsSolver
from robot_sim.core.math.so3 import rotation_error
from robot_sim.domain.enums import JointType
from robot_sim.model.ik_result import IKIterationLog, IKResult
from robot_sim.model.pose import Pose
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.solver_config import IKConfig


@dataclass(frozen=True)
class _AnalyticCandidate:
    q: np.ndarray
    pos_err: float
    ori_err: float
    branch: dict[str, object]

    @property
    def score(self) -> float:
        return float(self.pos_err + self.ori_err)


class Analytic6RSphericalWristIKSolver:
    """Closed-form IK for a restricted 6R spherical-wrist DH family.

    The supported family matches the bundled PUMA-like demo arm:
      - 6 revolute joints
      - standard DH chain
      - rows 4/5/6 form a spherical wrist (a4=a5=a6=0, d5=0, alpha=[+pi/2,-pi/2,0])
      - rows 1/2/3 match a shoulder-elbow serial arm with a2, a3 and d4 offsets

    When these prerequisites are not met, the solver fails explicitly instead of silently
    returning an arbitrary numerical result.
    """

    plugin_id = 'analytic_6r'

    def __init__(self) -> None:
        self._fk = ForwardKinematicsSolver()
        self._fallback = DLSIKSolver()

    def solve(self, spec: RobotSpec, target: Pose, q0, config: IKConfig, *, cancel_flag=None, progress_cb=None, attempt_idx: int = 0) -> IKResult:
        if bool(config.position_only):
            delegated = self._fallback.solve(spec, target, np.asarray(q0, dtype=float), config, cancel_flag=cancel_flag, progress_cb=progress_cb, attempt_idx=attempt_idx)
            diagnostics = dict(delegated.diagnostics)
            diagnostics.setdefault('analytic_delegate', 'dls_position_only')
            diagnostics.setdefault('analytic_solver_id', self.plugin_id)
            return IKResult(
                success=delegated.success,
                q_sol=delegated.q_sol,
                logs=delegated.logs,
                message=delegated.message,
                final_pos_err=delegated.final_pos_err,
                final_ori_err=delegated.final_ori_err,
                final_cond=delegated.final_cond,
                final_manipulability=delegated.final_manipulability,
                final_dq_norm=delegated.final_dq_norm,
                elapsed_ms=delegated.elapsed_ms,
                effective_mode=delegated.effective_mode,
                stop_reason=delegated.stop_reason,
                best_q=delegated.best_q,
                restarts_used=delegated.restarts_used,
                diagnostics=diagnostics,
            )

        structure_error = self._validate_structure(spec)
        if structure_error is not None:
            return IKResult(
                False,
                np.asarray(q0, dtype=float).copy(),
                tuple(),
                structure_error,
                stop_reason='analytic_structure_unsupported',
                best_q=np.asarray(q0, dtype=float).copy(),
                diagnostics={'attempt_idx': attempt_idx, 'analytic_solver_id': self.plugin_id},
            )

        candidates = self._enumerate_candidates(spec, target)
        if not candidates:
            return IKResult(
                False,
                np.asarray(q0, dtype=float).copy(),
                tuple(),
                'analytic 6R solver found no admissible branch',
                stop_reason='analytic_no_branch',
                best_q=np.asarray(q0, dtype=float).copy(),
                diagnostics={'attempt_idx': attempt_idx, 'analytic_solver_id': self.plugin_id},
            )

        q0_arr = np.asarray(q0, dtype=float)
        best = min(candidates, key=lambda item: (item.score, float(np.linalg.norm(item.q - q0_arr))))
        success = best.pos_err <= float(config.pos_tol) and best.ori_err <= float(config.ori_tol)
        log = IKIterationLog(
            iter_idx=0,
            pos_err_norm=best.pos_err,
            ori_err_norm=best.ori_err,
            cond_number=0.0,
            manipulability=0.0,
            dq_norm=float(np.linalg.norm(best.q - q0_arr)),
            elapsed_ms=0.0,
            effective_mode=self.plugin_id,
            attempt_idx=attempt_idx,
            damping_lambda=0.0,
            score=best.score,
            step_clipped=False,
        )
        message = 'analytic branch resolved' if success else 'analytic branch selected but tolerances not met'
        stop_reason = 'converged' if success else 'analytic_residual'
        return IKResult(
            success=success,
            q_sol=best.q.copy(),
            logs=(log,),
            message=message,
            final_pos_err=best.pos_err,
            final_ori_err=best.ori_err,
            final_cond=0.0,
            final_manipulability=0.0,
            final_dq_norm=log.dq_norm,
            elapsed_ms=0.0,
            effective_mode=self.plugin_id,
            stop_reason=stop_reason,
            best_q=best.q.copy(),
            diagnostics={
                'attempt_idx': attempt_idx,
                'analytic_solver_id': self.plugin_id,
                'analytic_family': 'spherical_wrist_6r',
                'candidate_count': len(candidates),
                'selected_branch': dict(best.branch),
            },
        )

    def _validate_structure(self, spec: RobotSpec) -> str | None:
        if spec.dof != 6:
            return 'analytic 6R solver requires a 6-DOF robot'
        rows = spec.dh_rows
        if any(row.joint_type is not JointType.REVOLUTE for row in rows):
            return 'analytic 6R solver requires all joints to be revolute'
        checks = [
            (rows[0].a, 0.0, 'row1.a'),
            (rows[1].d, 0.0, 'row2.d'),
            (rows[2].d, 0.0, 'row3.d'),
            (rows[3].a, 0.0, 'row4.a'),
            (rows[4].a, 0.0, 'row5.a'),
            (rows[4].d, 0.0, 'row5.d'),
            (rows[5].a, 0.0, 'row6.a'),
            (rows[0].alpha, math.pi / 2.0, 'row1.alpha'),
            (rows[1].alpha, 0.0, 'row2.alpha'),
            (rows[2].alpha, -math.pi / 2.0, 'row3.alpha'),
            (rows[3].alpha, math.pi / 2.0, 'row4.alpha'),
            (rows[4].alpha, -math.pi / 2.0, 'row5.alpha'),
            (rows[5].alpha, 0.0, 'row6.alpha'),
        ]
        for actual, expected, label in checks:
            if not math.isclose(float(actual), float(expected), abs_tol=1.0e-5):
                return f'analytic 6R solver unsupported DH structure: {label}'
        return None

    def _enumerate_candidates(self, spec: RobotSpec, target: Pose) -> list[_AnalyticCandidate]:
        rows = spec.dh_rows
        T_target = np.linalg.inv(np.asarray(spec.base_T, dtype=float)) @ self._pose_to_matrix(target) @ np.linalg.inv(np.asarray(spec.tool_T, dtype=float))
        R06 = T_target[:3, :3]
        p06 = T_target[:3, 3]

        d1 = float(rows[0].d)
        a2 = float(rows[1].a)
        a3 = float(rows[2].a)
        d4 = float(rows[3].d)
        d6 = float(rows[5].d)
        phi = math.atan2(d4, a3)
        elbow_link = math.hypot(a3, d4)

        wrist_center = p06 - d6 * R06[:, 2]
        x, y, z = wrist_center
        q1_base = math.atan2(float(y), float(x))
        radial = float(math.hypot(float(x), float(y)))
        z_rel = float(z - d1)
        candidates: list[_AnalyticCandidate] = []
        mins = np.array([row.q_min for row in rows], dtype=float)
        maxs = np.array([row.q_max for row in rows], dtype=float)

        for shoulder_branch, (q1_eff, radial_signed) in enumerate(((q1_base, radial), (self._wrap(q1_base + math.pi), -radial))):
            cos_elbow = (radial_signed * radial_signed + z_rel * z_rel - a2 * a2 - elbow_link * elbow_link) / (2.0 * a2 * elbow_link)
            if cos_elbow < -1.0 - 1.0e-7 or cos_elbow > 1.0 + 1.0e-7:
                continue
            cos_elbow = float(np.clip(cos_elbow, -1.0, 1.0))
            sin_elbow_abs = math.sqrt(max(0.0, 1.0 - cos_elbow * cos_elbow))
            for elbow_branch, sin_elbow in enumerate((sin_elbow_abs, -sin_elbow_abs)):
                theta = math.atan2(sin_elbow, cos_elbow)
                q2_eff = math.atan2(z_rel, radial_signed) - math.atan2(elbow_link * math.sin(theta), a2 + elbow_link * math.cos(theta))
                q3_eff = theta - phi
                q123 = np.array([
                    self._wrap(q1_eff - rows[0].theta_offset),
                    self._wrap(q2_eff - rows[1].theta_offset),
                    self._wrap(q3_eff - rows[2].theta_offset),
                ], dtype=float)
                T03 = np.eye(4, dtype=float)
                for idx in range(3):
                    T03 = T03 @ dh_transform(rows[idx], float(q123[idx]))
                R36 = T03[:3, :3].T @ R06
                wrist_candidates = self._solve_wrist_branches(R36)
                for wrist_branch, q456_eff in wrist_candidates:
                    q_eff = np.array([q1_eff, q2_eff, q3_eff, *q456_eff], dtype=float)
                    q = np.array([self._wrap(q_eff[idx] - rows[idx].theta_offset) for idx in range(6)], dtype=float)
                    if np.any(q < mins - 1.0e-6) or np.any(q > maxs + 1.0e-6):
                        continue
                    fk = self._fk.solve(spec, q)
                    pos_err = float(np.linalg.norm(np.asarray(target.p, dtype=float) - fk.ee_pose.p))
                    ori_err = float(np.linalg.norm(rotation_error(target.R, fk.ee_pose.R)))
                    candidates.append(
                        _AnalyticCandidate(
                            q=q,
                            pos_err=pos_err,
                            ori_err=ori_err,
                            branch={
                                'shoulder_branch': shoulder_branch,
                                'elbow_branch': elbow_branch,
                                'wrist_branch': wrist_branch,
                            },
                        )
                    )
        return candidates

    def _solve_wrist_branches(self, R36: np.ndarray) -> list[tuple[int, tuple[float, float, float]]]:
        sin_q5 = math.sqrt(max(0.0, float(R36[0, 2] ** 2 + R36[1, 2] ** 2)))
        if sin_q5 > 1.0e-8:
            q5 = math.atan2(sin_q5, float(R36[2, 2]))
            q4 = math.atan2(float(-R36[1, 2]), float(-R36[0, 2]))
            q6 = math.atan2(float(-R36[2, 1]), float(R36[2, 0]))
            return [
                (0, (q4, q5, q6)),
                (1, (self._wrap(q4 + math.pi), -q5, self._wrap(q6 + math.pi))),
            ]
        q5 = 0.0 if float(R36[2, 2]) >= 0.0 else math.pi
        q46 = math.atan2(float(R36[1, 0]), float(R36[0, 0]))
        return [(0, (q46, q5, 0.0))]

    def _pose_to_matrix(self, pose: Pose) -> np.ndarray:
        T = np.eye(4, dtype=float)
        T[:3, :3] = np.asarray(pose.R, dtype=float)
        T[:3, 3] = np.asarray(pose.p, dtype=float)
        return T

    def _wrap(self, angle: float) -> float:
        return float((angle + math.pi) % (2.0 * math.pi) - math.pi)
