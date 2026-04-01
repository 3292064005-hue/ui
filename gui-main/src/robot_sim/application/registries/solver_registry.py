from __future__ import annotations

from robot_sim.core.ik.registry import SolverRegistry as CoreSolverRegistry


class SolverRegistry(CoreSolverRegistry):
    """Application-visible solver registry.

    The application layer owns runtime registration policy while the built-in
    registry factory remains responsible for populating default solver entries.
    """

    pass
