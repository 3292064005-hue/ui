from __future__ import annotations

from robot_sim.core.ik._iterative_solver import IterativeIKSolverBase
from robot_sim.core.math.linalg import pseudo_inverse_svd, weighted_damped_least_squares
from robot_sim.model.solver_config import IKConfig
from robot_sim.domain.types import FloatArray


class PseudoInverseIKSolver(IterativeIKSolverBase):
    def _inverse(
        self,
        J: FloatArray,
        config: IKConfig,
        *,
        damping_lambda: float,
        joint_weights: FloatArray | None = None,
    ) -> FloatArray:
        if joint_weights is not None:
            # Weighted pseudo-inverse is approximated with a small damping term for stability.
            return weighted_damped_least_squares(J, max(damping_lambda, config.min_damping_lambda), joint_weights)
        return pseudo_inverse_svd(J)
