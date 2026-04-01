from __future__ import annotations

from dataclasses import dataclass, field

from robot_sim.domain.capabilities import CapabilityDescriptor
from robot_sim.domain.enums import ModuleStatus


@dataclass(frozen=True)
class CollisionBackendDescriptor:
    """Canonical descriptor for a collision backend declaration.

    Attributes:
        backend_id: Stable backend identifier used in configs and manifests.
        display_name: User-facing label.
        status: Stability status exposed to diagnostics.
        is_available: Whether the backend is currently importable/usable.
        is_experimental: Whether the backend is experimental.
        fallback_backend: Backend to fall back to when the requested backend is unavailable.
        required_dependencies: Optional dependency names required by the backend.
        metadata: Additional structured capability metadata.
    """

    backend_id: str
    display_name: str
    status: ModuleStatus
    is_available: bool = True
    is_experimental: bool = False
    fallback_backend: str = 'aabb'
    required_dependencies: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)

    def availability(self, *, experimental_enabled: bool) -> str:
        """Return the runtime availability label for diagnostics rendering.

        Args:
            experimental_enabled: Whether experimental backends may be advertised as enabled.

        Returns:
            str: ``enabled``, ``unavailable`` or ``disabled_by_profile``.

        Raises:
            None: Pure status projection.
        """
        if self.is_experimental:
            return 'enabled' if experimental_enabled else 'disabled_by_profile'
        return 'enabled' if self.is_available else 'unavailable'

    def to_capability_descriptor(self, *, experimental_enabled: bool) -> CapabilityDescriptor:
        """Project the backend descriptor into a scene-capability descriptor."""
        metadata = {
            'backend_id': self.backend_id,
            'fallback_backend': self.fallback_backend,
            'availability': self.availability(experimental_enabled=experimental_enabled),
            'required_dependencies': list(self.required_dependencies),
            **dict(self.metadata),
        }
        return CapabilityDescriptor(
            key=f'collision_backend_{self.backend_id}',
            label=self.display_name,
            owner_module='collision.scene',
            status=self.status,
            metadata=metadata,
        )


class CollisionBackendRegistry:
    """Single source of truth for collision-backend capability declarations."""

    def __init__(self, descriptors: tuple[CollisionBackendDescriptor, ...]) -> None:
        """Store immutable backend declarations.

        Args:
            descriptors: Backend descriptors in declaration order.

        Returns:
            None: Initializes registry state only.

        Raises:
            ValueError: If no descriptors are supplied or fallback references are invalid.
        """
        if not descriptors:
            raise ValueError('CollisionBackendRegistry requires at least one descriptor')
        self._descriptors = tuple(descriptors)
        self._by_id = {descriptor.backend_id: descriptor for descriptor in descriptors}
        for descriptor in descriptors:
            if descriptor.fallback_backend not in self._by_id:
                raise ValueError(f'unknown fallback backend: {descriptor.fallback_backend}')

    @property
    def default_backend(self) -> str:
        """Return the default fallback backend identifier."""
        return self._descriptors[0].backend_id

    def descriptors(self) -> tuple[CollisionBackendDescriptor, ...]:
        """Return all registered backend descriptors."""
        return self._descriptors

    def supported_backend_ids(self, *, experimental_enabled: bool = False) -> tuple[str, ...]:
        """Return backend identifiers considered selectable under the supplied runtime mode."""
        supported: list[str] = []
        for descriptor in self._descriptors:
            availability = descriptor.availability(experimental_enabled=experimental_enabled)
            if availability in {'enabled', 'disabled_by_profile'}:
                supported.append(descriptor.backend_id)
        return tuple(supported)

    def normalize_backend(
        self,
        backend_id: str,
        *,
        experimental_enabled: bool = False,
        metadata: dict[str, object] | None = None,
    ) -> tuple[str, dict[str, object]]:
        """Normalize a requested backend against the canonical descriptor table.

        Args:
            backend_id: Requested backend identifier.
            experimental_enabled: Whether experimental backends may be treated as enabled.
            metadata: Optional metadata payload to enrich with normalization results.

        Returns:
            tuple[str, dict[str, object]]: Resolved backend identifier and augmented metadata.

        Raises:
            None: Unsupported backends are normalized to the descriptor fallback.
        """
        payload = dict(metadata or {})
        requested = str(backend_id or self.default_backend).strip().lower() or self.default_backend
        descriptor = self._by_id.get(requested)
        if descriptor is None:
            resolved_descriptor = self._by_id[self.default_backend]
            payload['collision_backend_warning'] = (
                f'backend {requested!r} is unavailable; falling back to {resolved_descriptor.backend_id!r}'
            )
        else:
            if descriptor.is_experimental and not experimental_enabled:
                resolved_descriptor = self._by_id[descriptor.fallback_backend]
                payload['collision_backend_warning'] = (
                    f'backend {requested!r} is disabled by active profile; '
                    f'falling back to {resolved_descriptor.backend_id!r}'
                )
            elif not descriptor.is_available:
                resolved_descriptor = self._by_id[descriptor.fallback_backend]
                payload['collision_backend_warning'] = (
                    f'backend {requested!r} is unavailable; falling back to {resolved_descriptor.backend_id!r}'
                )
            else:
                resolved_descriptor = descriptor
        payload['requested_collision_backend'] = requested
        payload['resolved_collision_backend'] = resolved_descriptor.backend_id
        payload['collision_backend_available'] = bool(resolved_descriptor.backend_id == requested)
        return resolved_descriptor.backend_id, payload

    def scene_capabilities(self, *, experimental_enabled: bool = False) -> tuple[CapabilityDescriptor, ...]:
        """Render canonical scene capability descriptors from the backend table."""
        return tuple(
            descriptor.to_capability_descriptor(experimental_enabled=experimental_enabled)
            for descriptor in self._descriptors
        )


_DEFAULT_REGISTRY = CollisionBackendRegistry(
    descriptors=(
        CollisionBackendDescriptor(
            backend_id='aabb',
            display_name='AABB collision backend',
            status=ModuleStatus.STABLE,
            is_available=True,
            is_experimental=False,
            fallback_backend='aabb',
            metadata={'family': 'broad_phase', 'supported_collision_levels': ['aabb']},
        ),
        CollisionBackendDescriptor(
            backend_id='capsule',
            display_name='Capsule collision backend',
            status=ModuleStatus.EXPERIMENTAL,
            is_available=False,
            is_experimental=True,
            fallback_backend='aabb',
            required_dependencies=('capsule_backend',),
            metadata={'family': 'narrow_phase', 'supported_collision_levels': ['capsule']},
        ),
    )
)


def default_collision_backend_registry() -> CollisionBackendRegistry:
    """Return the process-wide canonical collision backend registry."""
    return _DEFAULT_REGISTRY
