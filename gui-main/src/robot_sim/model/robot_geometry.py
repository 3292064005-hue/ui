from __future__ import annotations

from dataclasses import dataclass, field

from robot_sim.domain.types import FloatArray


@dataclass(frozen=True)
class GeometryPrimitive:
    kind: str
    params: dict[str, object] = field(default_factory=dict)
    local_transform: FloatArray | None = None


@dataclass(frozen=True)
class LinkGeometry:
    name: str
    radius: float = 0.03
    points_local: FloatArray | None = None
    visual_primitives: tuple[GeometryPrimitive, ...] = ()
    collision_primitives: tuple[GeometryPrimitive, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RobotGeometry:
    links: tuple[LinkGeometry, ...] = ()
    source: str = 'generated'
    fidelity: str = 'approximate'
    collision_backend_hint: str = 'aabb'
    metadata: dict[str, object] = field(default_factory=dict)

    @staticmethod
    def simple_capsules(num_links: int, radius: float = 0.03) -> 'RobotGeometry':
        def primitive(r: float) -> GeometryPrimitive:
            return GeometryPrimitive(kind='capsule', params={'radius': float(r)})

        return RobotGeometry(
            links=tuple(
                LinkGeometry(
                    name=f'link_{i}',
                    radius=radius,
                    collision_primitives=(primitive(radius),),
                    metadata={'generator': 'simple_capsules'},
                )
                for i in range(num_links)
            ),
            source='generated',
            fidelity='approximate',
            collision_backend_hint='capsule',
            metadata={'generator': 'simple_capsules'},
        )
