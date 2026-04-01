from __future__ import annotations

import logging
from pathlib import Path

from robot_sim.app.container import AppContainer, build_container
from robot_sim.app.runtime_paths import resolve_runtime_paths
from robot_sim.app.version_catalog import VersionCatalog, default_version_catalog
from robot_sim.infra.logging_setup import setup_logging

logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Return the compatibility project root used by legacy startup callers.

    Returns:
        Path: Preferred project root for repository-style execution.

    Raises:
        None: Pure path discovery.
    """
    return Path(__file__).resolve().parents[3]


def _log_startup_summary(container: AppContainer, versions: VersionCatalog) -> dict[str, object]:
    """Log and return a startup summary derived from the application container.

    Args:
        container: Fully built application dependency container.
        versions: Version catalog used to project export/session schema versions.

    Returns:
        dict[str, object]: Structured startup summary used for logs and tests.

    Raises:
        None: Failures are contained to defensive logging.
    """
    summary: dict[str, object] = {
        'app_version': versions.app_version,
        'schemas': {
            'export': versions.export_schema_version,
            'session': versions.session_schema_version,
            'benchmark': versions.benchmark_pack_version,
        },
        'capabilities': {},
        'runtime': {},
    }
    try:
        matrix = container.capability_matrix_service.build_matrix(
            solver_registry=container.solver_registry,
            planner_registry=container.planner_registry,
            importer_registry=container.importer_registry,
        ).as_dict()
        summary['capabilities'] = {
            'solvers': len(matrix.get('solvers', [])),
            'planners': len(matrix.get('planners', [])),
            'importers': len(matrix.get('importers', [])),
        }
        summary['runtime'] = {
            'project_root': str(container.project_root),
            'resource_root': str(container.runtime_paths.resource_root),
            'config_root': str(container.runtime_paths.config_root),
            'export_root': str(container.runtime_paths.export_root),
            'source_layout_available': bool(container.runtime_paths.source_layout_available),
        }
        logger.info('robot-sim startup summary=%s', summary)
    except Exception as exc:  # pragma: no cover - defensive logging path
        logger.warning('failed to log startup summary: %s', exc)
    return summary


def bootstrap() -> tuple[Path, AppContainer]:
    """Initialize logging and build the application container.

    Returns:
        tuple[Path, AppContainer]: Compatibility project root together with the fully built
            application container.

    Raises:
        Exception: Propagates logging/configuration/container construction failures.

    Boundary behavior:
        Runtime resource resolution is driven by ``resolve_runtime_paths()`` rather than by a
        repository-layout assumption. ``get_project_root()`` remains available for legacy callers,
        but bootstrap itself now prefers the explicit runtime-path bundle.
    """
    runtime_paths = resolve_runtime_paths()
    setup_logging(runtime_paths.logging_config_path)
    container = build_container(runtime_paths)
    startup_summary = _log_startup_summary(container, default_version_catalog())
    if hasattr(container, 'startup_summary'):
        setattr(container, 'startup_summary', startup_summary)
    return runtime_paths.project_root, container
