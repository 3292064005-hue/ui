from __future__ import annotations

from dataclasses import dataclass
import os
from importlib.resources import files as resource_files
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    """Resolved runtime filesystem layout.

    Attributes:
        project_root: User-visible root retained for compatibility with existing startup code.
        resource_root: Root containing runtime configuration assets.
        config_root: Directory containing app/solver/plugins/profile configuration files.
        robot_root: Directory containing persisted robot YAML files.
        profiles_root: Directory containing profile overlays.
        logging_config_path: Logging configuration file consumed during bootstrap.
        plugin_manifest_path: Plugin manifest path.
        app_config_path: App/window configuration file.
        solver_config_path: Solver/trajectory configuration file.
        export_root: Writable directory used for screenshots, reports, and bundles.
        source_layout_available: Whether runtime assets were resolved from the repository layout.
    """

    project_root: Path
    resource_root: Path
    config_root: Path
    robot_root: Path
    profiles_root: Path
    logging_config_path: Path
    plugin_manifest_path: Path
    app_config_path: Path
    solver_config_path: Path
    export_root: Path
    source_layout_available: bool


_PACKAGE_CONFIG_ROOT = resource_files('robot_sim.resources').joinpath('configs')


def _package_config_root() -> Path:
    """Return the installed-package configuration root.

    Returns:
        Path: Filesystem path for packaged configuration resources.

    Raises:
        FileNotFoundError: If the packaged configuration directory is unavailable.
    """
    path = Path(str(_PACKAGE_CONFIG_ROOT))
    if not path.exists():
        raise FileNotFoundError(f'packaged runtime configs not found: {path}')
    return path


def _normalize_project_root(project_root: str | Path | None) -> Path:
    if project_root is None:
        return Path(__file__).resolve().parents[3]
    return Path(project_root)


def resolve_runtime_paths(project_root: str | Path | None = None) -> RuntimePaths:
    """Resolve runtime paths for both source-tree and installed-wheel execution.

    Args:
        project_root: Optional preferred project root. Existing source-tree callers pass the
            repository root here; installed-wheel callers may omit it.

    Returns:
        RuntimePaths: Normalized runtime path bundle.

    Raises:
        FileNotFoundError: If neither source-tree nor packaged runtime resources can be found.
    """
    root = _normalize_project_root(project_root)
    source_config_root = root / 'configs'
    source_layout_available = source_config_root.is_dir()
    if source_layout_available:
        resource_root = root
        config_root = source_config_root
    else:
        config_root = _package_config_root()
        resource_root = config_root.parent

    export_override = str(os.environ.get('ROBOT_SIM_EXPORT_DIR', '') or '').strip()
    if export_override:
        export_root = Path(export_override)
    elif source_layout_available:
        export_root = root / 'exports'
    else:
        export_root = Path.cwd() / 'exports'
    export_root.mkdir(parents=True, exist_ok=True)

    return RuntimePaths(
        project_root=root,
        resource_root=resource_root,
        config_root=config_root,
        robot_root=config_root / 'robots',
        profiles_root=config_root / 'profiles',
        logging_config_path=config_root / 'logging.yaml',
        plugin_manifest_path=config_root / 'plugins.yaml',
        app_config_path=config_root / 'app.yaml',
        solver_config_path=config_root / 'solver.yaml',
        export_root=export_root,
        source_layout_available=source_layout_available,
    )
