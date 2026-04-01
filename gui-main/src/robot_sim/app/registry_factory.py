from __future__ import annotations

from robot_sim.application.importers.urdf_skeleton_importer import URDFRobotImporter
from robot_sim.application.importers.yaml_importer import YAMLRobotImporter
from robot_sim.application.registries.importer_registry import ImporterRegistry
from robot_sim.application.registries.planner_registry import PlannerRegistry, build_default_planner_registry
from robot_sim.application.registries.solver_registry import SolverRegistry
from robot_sim.core.ik.analytic_6r import Analytic6RSphericalWristIKSolver
from robot_sim.core.ik.dls import DLSIKSolver
from robot_sim.core.ik.lm import LevenbergMarquardtIKSolver
from robot_sim.core.ik.pseudo_inverse import PseudoInverseIKSolver
from robot_sim.domain.enums import SolverFamily


def build_solver_registry(*, plugin_loader=None) -> SolverRegistry:
    """Build the builtin solver registry.

    Returns:
        SolverRegistry: Registry populated with the builtin IK solver set.

    Raises:
        Exception: Propagates constructor or registration failures from solver components.
    """
    solver_registry = SolverRegistry()
    solver_registry.register(
        'pinv',
        PseudoInverseIKSolver(),
        metadata={
            'family': SolverFamily.ITERATIVE.value,
            'supports_weighted_least_squares': True,
            'supports_nullspace': True,
            'supports_adaptive_damping_fallback': True,
            'supports_joint_limits': True,
            'source': 'builtin',
        },
        source='builtin',
    )
    solver_registry.register(
        'dls',
        DLSIKSolver(),
        metadata={
            'family': SolverFamily.ITERATIVE.value,
            'supports_weighted_least_squares': True,
            'supports_nullspace': True,
            'supports_adaptive_damping': True,
            'supports_joint_limits': True,
            'source': 'builtin',
        },
        source='builtin',
    )
    solver_registry.register(
        'lm',
        LevenbergMarquardtIKSolver(),
        metadata={
            'family': SolverFamily.ITERATIVE.value,
            'supports_weighted_least_squares': True,
            'supports_nullspace': True,
            'supports_adaptive_damping': True,
            'supports_joint_limits': True,
            'algorithm': 'levenberg_marquardt',
            'source': 'builtin',
        },
        aliases=('levenberg_marquardt',),
        source='builtin',
    )
    solver_registry.register(
        'analytic_6r',
        Analytic6RSphericalWristIKSolver(),
        metadata={
            'family': SolverFamily.ANALYTIC.value,
            'supports_weighted_least_squares': False,
            'supports_nullspace': False,
            'supports_joint_limits': True,
            'supports_position_only_via_fallback': True,
            'requires_spherical_wrist': True,
            'supported_dof': 6,
            'algorithm': 'closed_form_spherical_wrist',
            'source': 'builtin',
        },
        aliases=('spherical_wrist_6r',),
        source='builtin',
    )
    if plugin_loader is not None:
        for registration in plugin_loader.registrations('solver'):
            solver_registry.register(
                registration.plugin_id,
                registration.instance,
                metadata=dict(registration.metadata),
                aliases=tuple(registration.aliases),
                replace=registration.replace,
                source=registration.source,
            )
    return solver_registry


def build_planner_registry(ik_uc, *, plugin_loader=None) -> PlannerRegistry:
    """Build the builtin planner registry.

    Args:
        ik_uc: IK use case injected into planners that require inverse kinematics.

    Returns:
        PlannerRegistry: Registry populated with builtin planner implementations.

    Raises:
        Exception: Propagates planner construction failures.
    """
    planner_registry = build_default_planner_registry(ik_uc)
    if plugin_loader is not None:
        for registration in plugin_loader.registrations('planner', ik_uc=ik_uc):
            planner_registry.register(
                registration.plugin_id,
                registration.instance,
                metadata=dict(registration.metadata),
                aliases=tuple(registration.aliases),
                replace=registration.replace,
                source=registration.source,
            )
    return planner_registry


def build_importer_registry(robot_registry, *, plugin_loader=None) -> ImporterRegistry:
    """Build the builtin importer registry.

    Args:
        robot_registry: Robot registry used by importers that persist imported models.

    Returns:
        ImporterRegistry: Registry populated with builtin importer implementations.

    Raises:
        Exception: Propagates importer construction or registration failures.
    """
    importer_registry = ImporterRegistry()
    importer_registry.register(
        'yaml',
        YAMLRobotImporter(robot_registry),
        metadata={'source_format': 'yaml', 'fidelity': 'native', 'family': 'config', 'source': 'builtin'},
        source='builtin',
    )
    importer_registry.register(
        'urdf_skeleton',
        URDFRobotImporter(),
        metadata={
            'source_format': 'urdf',
            'fidelity': 'approximate',
            'family': 'approximate_tree_import',
            'notes': 'Approximates a serial DH-like chain from URDF joint origins. Not a full URDF tree importer.',
            'source': 'builtin',
        },
        aliases=('urdf',),
        source='builtin',
    )
    if plugin_loader is not None:
        for registration in plugin_loader.registrations('importer', robot_registry=robot_registry):
            importer_registry.register(
                registration.plugin_id,
                registration.instance,
                metadata=dict(registration.metadata),
                aliases=tuple(registration.aliases),
                replace=registration.replace,
                source=registration.source,
            )
    return importer_registry
