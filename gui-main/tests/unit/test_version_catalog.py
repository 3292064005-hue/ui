from robot_sim.app.version import APP_VERSION, BENCHMARK_PACK_VERSION, EXPORT_SCHEMA_VERSION, SESSION_SCHEMA_VERSION
from robot_sim.app.version_catalog import current_version_catalog


def test_version_catalog_matches_export_and_session_contracts():
    catalog = current_version_catalog()
    assert catalog.app_version == APP_VERSION
    assert catalog.export_schema_version == EXPORT_SCHEMA_VERSION
    assert catalog.session_schema_version == SESSION_SCHEMA_VERSION
    assert catalog.benchmark_pack_version == BENCHMARK_PACK_VERSION
