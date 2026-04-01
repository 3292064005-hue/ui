from __future__ import annotations


class CapsuleCollisionBackend:
    """Placeholder capsule backend kept for interface compatibility only."""

    backend_id = 'capsule'
    availability = 'unavailable'
    fallback_backend = 'aabb'

    def _unsupported_payload(self) -> dict[str, object]:
        return {
            'backend_id': self.backend_id,
            'availability': self.availability,
            'fallback_backend': self.fallback_backend,
            'warning': 'capsule collision backend is not available in V7.1 and must fall back to aabb',
        }

    def check_state_collision(self, *args, **kwargs) -> dict[str, object]:
        payload = self._unsupported_payload()
        payload.update({'supported': False, 'self_collision': False, 'environment_collision': False})
        return payload

    def check_path_collision(self, *args, **kwargs) -> dict[str, object]:
        payload = self._unsupported_payload()
        payload.update({'supported': False, 'path_collision': False})
        return payload

    def min_distance(self, *args, **kwargs) -> float:
        return 0.0

    def contact_pairs(self, *args, **kwargs) -> tuple[tuple[str, str], ...]:
        return ()
