from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class CollisionBackendProtocol(Protocol):
    backend_id: str

    def check_state_collision(self, *args, **kwargs) -> dict[str, object]: ...

    def check_path_collision(self, *args, **kwargs) -> dict[str, object]: ...

    def min_distance(self, *args, **kwargs) -> float: ...

    def contact_pairs(self, *args, **kwargs) -> tuple[tuple[str, str], ...]: ...
