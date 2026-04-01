from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import logging
from pathlib import Path

try:  # pragma: no cover - Python 3.11+
    import tomllib
except ImportError:  # pragma: no cover
    tomllib = None

from robot_sim.domain.errors import RobotSimError

logger = logging.getLogger(__name__)

APP_NAME = 'robot-sim-engine'
DEFAULT_APP_VERSION = '0.7.0'
DEFAULT_EXPORT_SCHEMA_VERSION = 'v7'
DEFAULT_SESSION_SCHEMA_VERSION = 'session-v7'
DEFAULT_BENCHMARK_PACK_VERSION = 'v7'
DEFAULT_ROADMAP_VERSION = 'V7'
DEFAULT_DOCS_RELEASE_LABEL = 'V7 工程硬化版'


class VersionCatalogLoadError(RobotSimError):
    """Raised when version metadata cannot be loaded from ``pyproject.toml``."""

    default_error_code = 'version_catalog_load_failed'
    default_remediation_hint = '检查 pyproject.toml 是否存在且 TOML 格式有效。'


@dataclass(frozen=True)
class VersionCatalogDiagnostic:
    """Structured diagnostic describing why version metadata fell back to defaults."""

    degraded_mode: bool = False
    message: str = ''
    root: str = ''
    error_code: str = ''


_LAST_DIAGNOSTIC = VersionCatalogDiagnostic()


def _set_last_diagnostic(diagnostic: VersionCatalogDiagnostic) -> None:
    global _LAST_DIAGNOSTIC
    _LAST_DIAGNOSTIC = diagnostic


def last_version_catalog_diagnostic() -> VersionCatalogDiagnostic:
    """Return the last version-catalog loading diagnostic."""
    return _LAST_DIAGNOSTIC


def _candidate_roots() -> list[Path]:
    here = Path(__file__).resolve()
    return [
        here.parents[3],
        here.parents[4] if len(here.parents) > 4 else here.parents[3],
    ]


def _load_version_from_root(root: Path) -> str | None:
    """Load the application version from a single candidate root.

    Args:
        root: Candidate repository root containing ``pyproject.toml``.

    Returns:
        str | None: Trimmed version string when present.

    Raises:
        VersionCatalogLoadError: If ``pyproject.toml`` exists but cannot be parsed.
    """
    path = root / 'pyproject.toml'
    if not path.exists() or tomllib is None:
        return None
    try:
        data = tomllib.loads(path.read_text(encoding='utf-8'))
    except (OSError, TypeError, AttributeError, tomllib.TOMLDecodeError) as exc:
        raise VersionCatalogLoadError(
            'failed to parse version metadata',
            metadata={'root': str(root), 'path': str(path)},
        ) from exc
    project = data.get('project') if isinstance(data, dict) else None
    version = project.get('version') if isinstance(project, dict) else None
    if isinstance(version, str) and version.strip():
        return version.strip()
    return None


@lru_cache(maxsize=1)
def _read_pyproject_version() -> str | None:
    if tomllib is None:
        _set_last_diagnostic(VersionCatalogDiagnostic(True, 'tomllib unavailable; using default version', '', 'tomllib_unavailable'))
        return None
    last_error: VersionCatalogLoadError | None = None
    for root in _candidate_roots():
        try:
            version = _load_version_from_root(root)
        except VersionCatalogLoadError as exc:
            last_error = exc
            logger.warning('version catalog degraded at %s: %s', root, exc)
            continue
        if version is not None:
            _set_last_diagnostic(VersionCatalogDiagnostic(False, '', str(root), ''))
            return version
    if last_error is not None:
        metadata = dict(last_error.metadata)
        _set_last_diagnostic(
            VersionCatalogDiagnostic(
                degraded_mode=True,
                message=last_error.message,
                root=str(metadata.get('root', '')),
                error_code=last_error.error_code,
            )
        )
    return None


@dataclass(frozen=True)
class VersionCatalog:
    app_name: str = APP_NAME
    app_version: str = DEFAULT_APP_VERSION
    export_schema_version: str = DEFAULT_EXPORT_SCHEMA_VERSION
    session_schema_version: str = DEFAULT_SESSION_SCHEMA_VERSION
    benchmark_pack_version: str = DEFAULT_BENCHMARK_PACK_VERSION
    roadmap_version: str = DEFAULT_ROADMAP_VERSION
    docs_release_label: str = DEFAULT_DOCS_RELEASE_LABEL

    def as_dict(self) -> dict[str, str]:
        return {
            'app_name': self.app_name,
            'app_version': self.app_version,
            'export_schema_version': self.export_schema_version,
            'session_schema_version': self.session_schema_version,
            'benchmark_pack_version': self.benchmark_pack_version,
            'roadmap_version': self.roadmap_version,
            'docs_release_label': self.docs_release_label,
        }


@lru_cache(maxsize=1)
def current_version_catalog() -> VersionCatalog:
    return VersionCatalog(app_version=_read_pyproject_version() or DEFAULT_APP_VERSION)


def default_version_catalog() -> VersionCatalog:
    return current_version_catalog()
