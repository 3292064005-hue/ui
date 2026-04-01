from __future__ import annotations

from robot_sim.application.services.export_service import ExportService
from robot_sim.application.services.package_service import PackageService


def test_export_and_package_services_share_manifest_builder_contract(tmp_path):
    export_service = ExportService(tmp_path)
    package_service = PackageService(tmp_path)

    export_manifest = export_service.build_manifest(robot_id='planar', files=['trajectory.csv'], correlation_id='corr-1')
    package_manifest = package_service.build_manifest(robot_id='planar', files=['trajectory.csv'], correlation_id='corr-1')

    assert export_manifest['app_name'] == package_manifest.app_name
    assert export_manifest['schema_version'] == package_manifest.schema_version
    assert export_manifest['migration_aliases'] == package_manifest.migration_aliases
    assert export_manifest['correlation_id'] == package_manifest.correlation_id == 'corr-1'
    assert export_manifest['files'] == list(package_manifest.files)
