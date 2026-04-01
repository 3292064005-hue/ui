from __future__ import annotations

from robot_sim.domain.capabilities import CapabilityDescriptor, CapabilityMatrix
from robot_sim.domain.collision_backends import default_collision_backend_registry
from robot_sim.domain.enums import ModuleStatus
from robot_sim.domain.runtime_contracts import render_capability_matrix_markdown


class CapabilityService:
    """Build the runtime capability matrix exposed to the presentation layer."""

    def __init__(self, runtime_feature_policy=None) -> None:
        self._runtime_feature_policy = runtime_feature_policy
        self._collision_registry = default_collision_backend_registry()

    def _scene_features(self) -> tuple[CapabilityDescriptor, ...]:
        experimental_enabled = bool(getattr(self._runtime_feature_policy, 'experimental_backends_enabled', False))
        planning_scene_descriptor = CapabilityDescriptor(
            'planning_scene',
            'Planning scene',
            owner_module='collision.scene',
            status=ModuleStatus.STABLE,
            metadata={
                'supported_backends': list(self._collision_registry.supported_backend_ids(experimental_enabled=experimental_enabled)),
                'fallback_backend': self._collision_registry.default_backend,
                'experimental_backends': [
                    descriptor.backend_id for descriptor in self._collision_registry.descriptors() if descriptor.is_experimental
                ],
            },
        )
        return (planning_scene_descriptor, *self._collision_registry.scene_capabilities(experimental_enabled=experimental_enabled))

    def build_matrix(self, *, solver_registry, planner_registry, importer_registry) -> CapabilityMatrix:
        """Build a capability matrix from active registries.

        Args:
            solver_registry: Solver registry.
            planner_registry: Planner registry.
            importer_registry: Importer registry.

        Returns:
            CapabilityMatrix: Structured runtime capability matrix.

        Raises:
            Exception: Propagates registry descriptor failures.
        """
        solvers = tuple(
            CapabilityDescriptor(
                key=desc.solver_id,
                label=desc.solver_id,
                owner_module='solver_registry',
                status=ModuleStatus.STABLE,
                metadata={'aliases': list(desc.aliases), **dict(desc.metadata)},
            )
            for desc in solver_registry.descriptors()
        )
        planners = tuple(
            CapabilityDescriptor(
                key=desc.planner_id,
                label=desc.planner_id,
                owner_module='planner_registry',
                status=ModuleStatus.STABLE,
                metadata={'aliases': list(desc.aliases), **dict(desc.metadata)},
            )
            for desc in planner_registry.descriptors()
        )
        importers = tuple(
            CapabilityDescriptor(
                key=desc.importer_id,
                label=desc.importer_id,
                owner_module='importer_registry',
                status=ModuleStatus.STABLE,
                metadata={'aliases': list(desc.aliases), **dict(desc.metadata)},
            )
            for desc in importer_registry.descriptors()
        )
        return CapabilityMatrix(
            solvers=solvers,
            planners=planners,
            importers=importers,
            render_features=(CapabilityDescriptor('scene_toolbar', 'Scene toolbar', owner_module='render', status=ModuleStatus.STABLE),),
            export_features=(CapabilityDescriptor('package_export', 'Package export', owner_module='export', status=ModuleStatus.STABLE),),
            scene_features=self._scene_features(),
        )

    def render_scene_markdown(self) -> str:
        """Render the scene-capability subset as deterministic markdown.

        Returns:
            str: Markdown bullet list describing scene capabilities and statuses.

        Raises:
            None: Rendering is a pure formatting operation.
        """
        return render_capability_matrix_markdown(self._scene_features())
