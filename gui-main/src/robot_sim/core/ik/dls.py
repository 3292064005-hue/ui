from __future__ import annotations

from robot_sim.core.ik._iterative_solver import IterativeIKSolverBase
from robot_sim.core.math.linalg import damped_least_squares, weighted_damped_least_squares
from robot_sim.model.solver_config import IKConfig
from robot_sim.domain.types import FloatArray


class DLSIKSolver(IterativeIKSolverBase):
    def _inverse(
        self,
        J: FloatArray,
        config: IKConfig,
        *,
        damping_lambda: float,
        joint_weights: FloatArray | None = None,
    ) -> FloatArray:
        if joint_weights is not None:
            return weighted_damped_least_squares(J, damping_lambda, joint_weights)
        return damped_least_squares(J, damping_lambda)
