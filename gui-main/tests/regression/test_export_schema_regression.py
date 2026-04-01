from robot_sim.application.services.export_service import ExportService


def test_export_manifest_keeps_versions_and_aliases(tmp_path):
    manifest = ExportService(tmp_path).build_manifest(robot_id='r')
    assert manifest['schema_version']
    assert manifest['export_version']
    assert manifest['producer_version']
    assert manifest['migration_aliases']['endpoint_position_error'] == 'goal_position_error'
    assert manifest['migration_aliases']['endpoint_orientation_error'] == 'goal_orientation_error'
