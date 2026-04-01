from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class PlannerDescriptor:
    """Metadata describing a registered trajectory planner."""

    planner_id: str
    aliases: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)
    source: str = 'runtime'
    replaced_from: str = ''
    capability_flags: tuple[str, ...] = ()


class TrajectoryPlannerRegistry:
    """Registry of available trajectory planner implementations."""

    def __init__(self) -> None:
        self._planners: dict[str, object] = {}
        self._aliases: dict[str, str] = {}
        self._metadata: dict[str, PlannerDescriptor] = {}

    def register(
        self,
        planner_id: str,
        planner: object,
        *,
        metadata: dict[str, object] | None = None,
        aliases: tuple[str, ...] = (),
        replace: bool = False,
        source: str = 'runtime',
    ) -> None:
        canonical_id = str(planner_id)
        alias_tuple = tuple(str(alias) for alias in aliases if str(alias) != canonical_id)
        replaced_from = ''
        if canonical_id in self._planners and not replace:
            raise ValueError(f'duplicate trajectory planner id: {canonical_id}')
        for alias in alias_tuple:
            owner = self._aliases.get(alias)
            if owner is not None and owner != canonical_id and not replace:
                raise ValueError(f'duplicate trajectory planner alias: {alias}')
        if replace and canonical_id in self._metadata:
            replaced_from = self._metadata[canonical_id].planner_id
            for alias in self._metadata[canonical_id].aliases:
                self._aliases.pop(alias, None)
        merged_metadata = dict(metadata or {})
        capability_flags = tuple(sorted(str(key) for key, value in merged_metadata.items() if isinstance(value, bool) and value))
        self._planners[canonical_id] = planner
        self._metadata[canonical_id] = PlannerDescriptor(
            planner_id=canonical_id,
            aliases=alias_tuple,
            metadata=merged_metadata,
            source=str(source),
            replaced_from=replaced_from,
            capability_flags=capability_flags,
        )
        for alias in alias_tuple:
            self._aliases[alias] = canonical_id

    def get(self, planner_id: str):
        key = str(planner_id)
        canonical = self._aliases.get(key, key)
        if canonical not in self._planners:
            raise KeyError(f'unknown trajectory planner: {planner_id}')
        return self._planners[canonical]

    def ids(self) -> list[str]:
        return sorted(self._planners)

    def items(self) -> Iterable[tuple[str, object]]:
        return self._planners.items()

    def descriptors(self) -> list[PlannerDescriptor]:
        return [self._metadata[key] for key in self.ids()]
