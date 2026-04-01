from __future__ import annotations

from collections.abc import Mapping

from robot_sim.domain.capabilities import CapabilityDescriptor
from robot_sim.domain.collision_backends import default_collision_backend_registry
from robot_sim.domain.enums import ModuleStatus


MODULE_STATUSES: dict[str, str] = {
    'presentation.widgets.collision_panel': ModuleStatus.EXPERIMENTAL.value,
    'presentation.widgets.export_panel': ModuleStatus.EXPERIMENTAL.value,
    'presentation.widgets.scene_options_panel': ModuleStatus.EXPERIMENTAL.value,
    'render.picking': ModuleStatus.EXPERIMENTAL.value,
    'render.plot_sync': ModuleStatus.EXPERIMENTAL.value,
    'application.importers.urdf_skeleton_importer': ModuleStatus.STABLE.value,
    'core.collision.capsule_backend': ModuleStatus.EXPERIMENTAL.value,
}

_collision_registry = default_collision_backend_registry()
SCENE_CAPABILITIES: tuple[CapabilityDescriptor, ...] = (
    CapabilityDescriptor(
        'planning_scene',
        'Planning scene',
        owner_module='collision.scene',
        status=ModuleStatus.STABLE,
        metadata={
            'supported_backends': list(_collision_registry.supported_backend_ids(experimental_enabled=False)),
            'fallback_backend': _collision_registry.default_backend,
            'experimental_backends': [
                descriptor.backend_id for descriptor in _collision_registry.descriptors() if descriptor.is_experimental
            ],
        },
    ),
    *_collision_registry.scene_capabilities(experimental_enabled=False),
)


def render_module_status_markdown(module_statuses: Mapping[str, object] | None = None) -> str:
    """Render deterministic module-status markdown from the shared runtime contract.

    Args:
        module_statuses: Optional mapping override. Values may be plain status strings
            or detail mappings containing ``status`` and ``enabled``.

    Returns:
        str: Deterministic markdown used by docs and regression checks.

    Raises:
        None: Rendering is a pure formatting operation.
    """
    normalized: dict[str, dict[str, object]] = {}
    source = dict(module_statuses or MODULE_STATUSES)
    for module_id, payload in source.items():
        if isinstance(payload, Mapping):
            status = str(payload.get('status', 'unknown'))
            enabled = bool(payload.get('enabled', True))
        else:
            status = str(payload)
            enabled = True
        normalized[str(module_id)] = {'status': status, 'enabled': enabled}

    grouped: dict[str, list[tuple[str, bool]]] = {}
    for module_id, detail in normalized.items():
        grouped.setdefault(str(detail['status']), []).append((module_id, bool(detail['enabled'])))

    lines = ['# Module Status', '']
    for status in sorted(grouped):
        lines.append(f'## {status}')
        for module_id, enabled in sorted(grouped[status], key=lambda item: item[0]):
            lines.append(f"- `{module_id}` ({'enabled' if enabled else 'disabled_by_profile'})")
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'



def render_capability_matrix_markdown(descriptors: tuple[CapabilityDescriptor, ...] | None = None) -> str:
    """Render deterministic scene-capability markdown from the shared runtime contract."""
    lines = ['# Capability Matrix', '', '## scene_features']
    for descriptor in descriptors or SCENE_CAPABILITIES:
        lines.append(f'- `{descriptor.key}` [{descriptor.status.value}]')
        lines.append(f'  - owner: `{descriptor.owner_module}`')
        if descriptor.metadata:
            for key in sorted(descriptor.metadata):
                lines.append(f'  - {key}: `{descriptor.metadata[key]}`')
    lines.append('')
    return '\n'.join(lines)
