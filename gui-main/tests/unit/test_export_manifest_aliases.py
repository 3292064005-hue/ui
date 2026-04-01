from robot_sim.application.services.export_service import ExportService


def test_manifest_contains_migration_aliases(tmp_path):
    service = ExportService(tmp_path)
    manifest = service.build_manifest(robot_id='r')
    assert manifest['migration_aliases']['endpoint_position_error'] == 'goal_position_error'
    assert manifest['migration_aliases']['endpoint_orientation_error'] == 'goal_orientation_error'
