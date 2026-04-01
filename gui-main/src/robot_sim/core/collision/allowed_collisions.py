from __future__ import annotations

from dataclasses import dataclass, field


def _norm_pair(a: str, b: str) -> tuple[str, str]:
    x, y = str(a), str(b)
    return (x, y) if x <= y else (y, x)


@dataclass(frozen=True)
class AllowedCollisionMatrix:
    allowed_pairs: frozenset[tuple[str, str]] = field(default_factory=frozenset)

    def allows(self, a: str, b: str) -> bool:
        return _norm_pair(a, b) in self.allowed_pairs

    def allow(self, a: str, b: str) -> 'AllowedCollisionMatrix':
        pairs = set(self.allowed_pairs)
        pairs.add(_norm_pair(a, b))
        return AllowedCollisionMatrix(frozenset(pairs))

    def forbid(self, a: str, b: str) -> 'AllowedCollisionMatrix':
        pairs = set(self.allowed_pairs)
        pairs.discard(_norm_pair(a, b))
        return AllowedCollisionMatrix(frozenset(pairs))

    @staticmethod
    def from_pairs(pairs: list[tuple[str, str]] | tuple[tuple[str, str], ...]) -> 'AllowedCollisionMatrix':
        return AllowedCollisionMatrix(frozenset(_norm_pair(a, b) for a, b in pairs))
