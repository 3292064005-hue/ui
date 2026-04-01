from __future__ import annotations

from dataclasses import dataclass, field

from robot_sim.domain.enums import ModuleStatus


@dataclass(frozen=True)
class CapabilityDescriptor:
    key: str
    label: str
    enabled: bool = True
    status: ModuleStatus = ModuleStatus.STABLE
    owner_module: str = ''
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CapabilityMatrix:
    solvers: tuple[CapabilityDescriptor, ...] = ()
    planners: tuple[CapabilityDescriptor, ...] = ()
    importers: tuple[CapabilityDescriptor, ...] = ()
    render_features: tuple[CapabilityDescriptor, ...] = ()
    export_features: tuple[CapabilityDescriptor, ...] = ()
    scene_features: tuple[CapabilityDescriptor, ...] = ()

    def as_dict(self) -> dict[str, list[dict[str, object]]]:
        def _serialize(items: tuple[CapabilityDescriptor, ...]) -> list[dict[str, object]]:
            return [
                {
                    'key': item.key,
                    'label': item.label,
                    'enabled': item.enabled,
                    'status': item.status.value,
                    'owner_module': item.owner_module,
                    'metadata': dict(item.metadata),
                }
                for item in items
            ]

        return {
            'solvers': _serialize(self.solvers),
            'planners': _serialize(self.planners),
            'importers': _serialize(self.importers),
            'render_features': _serialize(self.render_features),
            'export_features': _serialize(self.export_features),
            'scene_features': _serialize(self.scene_features),
        }
