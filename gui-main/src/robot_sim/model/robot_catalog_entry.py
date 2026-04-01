from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RobotCatalogEntry:
    name: str
    label: str
    dof: int
    description: str = ""
    metadata: dict[str, object] = field(default_factory=dict)
