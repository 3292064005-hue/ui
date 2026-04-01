from __future__ import annotations

from robot_sim.core.ik._iterative_solver import IterativeIKSolverBase
from robot_sim.core.math.linalg import levenberg_marquardt_inverse, weighted_levenberg_marquardt_inverse
from robot_sim.domain.types import FloatArray


class LevenbergMarquardtIKSolver(IterativeIKSolverBase):
    def _inverse(
        self,
        J: FloatArray,
        config,
        *,
        damping_lambda: float,
        joint_weights: FloatArray | None = None,
    ) -> FloatArray:
        if joint_weights is not None:
            return weighted_levenberg_marquardt_inverse(J, damping_lambda, joint_weights)
        return levenberg_marquardt_inverse(J, damping_lambda)
