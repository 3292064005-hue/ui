from __future__ import annotations

from robot_sim.app.version_catalog import APP_NAME as _APP_NAME, current_version_catalog

_catalog = current_version_catalog()
APP_NAME = _APP_NAME
DEFAULT_APP_VERSION = _catalog.app_version
APP_VERSION = _catalog.app_version
EXPORT_SCHEMA_VERSION = _catalog.export_schema_version
SESSION_SCHEMA_VERSION = _catalog.session_schema_version
BENCHMARK_PACK_VERSION = _catalog.benchmark_pack_version
ROADMAP_VERSION = _catalog.roadmap_version
DOCS_RELEASE_LABEL = _catalog.docs_release_label


def current_app_version() -> str:
    return current_version_catalog().app_version
