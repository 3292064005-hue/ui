from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from robot_sim.core.ik.analytic_6r import Analytic6RSphericalWristIKSolver
from robot_sim.core.ik.dls import DLSIKSolver
from robot_sim.core.ik.lm import LevenbergMarquardtIKSolver
from robot_sim.core.ik.pseudo_inverse import PseudoInverseIKSolver
from robot_sim.domain.enums import IKSolverMode


@dataclass(frozen=True)
class SolverDescriptor:
    """Metadata describing a registered IK solver."""

    solver_id: str
    aliases: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)
    source: str = 'runtime'
    replaced_from: str = ''
    capability_flags: tuple[str, ...] = ()


class SolverRegistry:
    """Registry of available IK solver implementations."""

    def __init__(self) -> None:
        self._solvers: dict[str, object] = {}
        self._aliases: dict[str, str] = {}
        self._metadata: dict[str, SolverDescriptor] = {}

    def register(
        self,
        solver_id: str,
        solver: object,
        *,
        metadata: dict[str, object] | None = None,
        aliases: tuple[str, ...] = (),
        replace: bool = False,
        source: str = 'runtime',
    ) -> None:
        """Register an IK solver implementation.

        Args:
            solver_id: Canonical solver identifier.
            solver: Solver implementation instance.
            metadata: Optional descriptor metadata.
            aliases: Optional alias identifiers.
            replace: Whether to replace an existing registration explicitly.
            source: Registration source identifier.

        Raises:
            ValueError: If a duplicate id or alias is registered without ``replace``.
        """
        canonical_id = str(solver_id)
        alias_tuple = tuple(str(alias) for alias in aliases if str(alias) != canonical_id)
        replaced_from = ''
        if canonical_id in self._solvers and not replace:
            raise ValueError(f'duplicate IK solver id: {canonical_id}')
        for alias in alias_tuple:
            owner = self._aliases.get(alias)
            if owner is not None and owner != canonical_id and not replace:
                raise ValueError(f'duplicate IK solver alias: {alias}')
        if replace and canonical_id in self._metadata:
            replaced_from = self._metadata[canonical_id].solver_id
            for alias in self._metadata[canonical_id].aliases:
                self._aliases.pop(alias, None)
        merged_metadata = dict(metadata or {})
        capability_flags = tuple(sorted(str(key) for key, value in merged_metadata.items() if isinstance(value, bool) and value))
        self._solvers[canonical_id] = solver
        self._metadata[canonical_id] = SolverDescriptor(
            solver_id=canonical_id,
            aliases=alias_tuple,
            metadata=merged_metadata,
            source=str(source),
            replaced_from=replaced_from,
            capability_flags=capability_flags,
        )
        for alias in alias_tuple:
            self._aliases[alias] = canonical_id

    def get(self, solver_id: str):
        key = str(solver_id)
        canonical = self._aliases.get(key, key)
        if canonical not in self._solvers:
            raise KeyError(f'unknown IK solver: {solver_id}')
        return self._solvers[canonical]

    def ids(self) -> list[str]:
        return sorted(self._solvers)

    def items(self) -> Iterable[tuple[str, object]]:
        return self._solvers.items()

    def descriptors(self) -> list[SolverDescriptor]:
        return [self._metadata[key] for key in self.ids()]


class DefaultSolverRegistry(SolverRegistry):
    """Built-in solver registry populated with the default solver set."""

    def __init__(self) -> None:
        super().__init__()
        self.register(
            IKSolverMode.PINV.value,
            PseudoInverseIKSolver(),
            metadata={
                'family': 'iterative',
                'supports_weighted_least_squares': True,
                'supports_nullspace': True,
                'supports_adaptive_damping_fallback': True,
            },
            source='builtin',
        )
        self.register(
            IKSolverMode.DLS.value,
            DLSIKSolver(),
            metadata={
                'family': 'iterative',
                'supports_weighted_least_squares': True,
                'supports_nullspace': True,
                'supports_adaptive_damping': True,
            },
            source='builtin',
        )
        self.register(
            IKSolverMode.LM.value,
            LevenbergMarquardtIKSolver(),
            metadata={
                'family': 'iterative',
                'supports_weighted_least_squares': True,
                'supports_nullspace': True,
                'supports_adaptive_damping': True,
                'algorithm': 'levenberg_marquardt',
            },
            aliases=('levenberg_marquardt',),
            source='builtin',
        )
        self.register(
            IKSolverMode.ANALYTIC_6R.value,
            Analytic6RSphericalWristIKSolver(),
            metadata={
                'family': 'analytic',
                'supports_weighted_least_squares': False,
                'supports_nullspace': False,
                'supports_position_only_via_fallback': True,
                'requires_spherical_wrist': True,
                'supported_dof': 6,
                'algorithm': 'closed_form_spherical_wrist',
            },
            aliases=('spherical_wrist_6r',),
            source='builtin',
        )
