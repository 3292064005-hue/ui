from __future__ import annotations

from dataclasses import asdict, dataclass, field
from robot_sim.domain.enums import IKSolverMode


@dataclass(frozen=True)
class IKConfig:
    mode: IKSolverMode = IKSolverMode.DLS
    max_iters: int = 150
    pos_tol: float = 1.0e-4
    ori_tol: float = 1.0e-4
    damping_lambda: float = 0.05
    step_scale: float = 0.5
    enable_nullspace: bool = True
    joint_limit_weight: float = 0.03
    manipulability_weight: float = 0.0
    position_only: bool = False
    orientation_weight: float = 1.0
    max_step_norm: float = 0.35
    singularity_cond_threshold: float = 250.0
    fallback_to_dls_when_singular: bool = True
    reachability_precheck: bool = True
    retry_count: int = 0
    random_seed: int = 7
    adaptive_damping: bool = True
    min_damping_lambda: float = 1.0e-4
    max_damping_lambda: float = 1.5
    use_weighted_least_squares: bool = True
    clamp_seed_to_joint_limits: bool = True
    normalize_target_rotation: bool = True
    allow_orientation_relaxation: bool = False
    orientation_relaxation_pos_multiplier: float = 5.0
    orientation_relaxation_ori_multiplier: float = 25.0

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload['mode'] = getattr(self.mode, 'value', str(self.mode))
        return payload


@dataclass(frozen=True)
class TrajectoryConfig:
    """Typed trajectory runtime configuration."""

    duration: float = 3.0
    dt: float = 0.02

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SolverSettings:
    """Typed container grouping solver and trajectory configuration."""

    ik: IKConfig = field(default_factory=IKConfig)
    trajectory: TrajectoryConfig = field(default_factory=TrajectoryConfig)

    def as_dict(self) -> dict[str, object]:
        return {
            'ik': self.ik.as_dict(),
            'trajectory': self.trajectory.as_dict(),
        }
