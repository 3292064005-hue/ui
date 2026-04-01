from __future__ import annotations

from robot_sim.app.container import build_container


def test_import_robot_use_case_records_skeleton_fidelity_warning(project_root, tmp_path):
    urdf = tmp_path / 'mini.urdf'
    urdf.write_text(
        '<robot name="mini"><joint name="j1" type="revolute"><origin xyz="0 0 1" rpy="0 0 0"/><limit lower="-1" upper="1"/></joint></robot>',
        encoding='utf-8',
    )
    container = build_container(project_root)
    spec = container.import_robot_uc.execute(urdf, importer_id='urdf')

    assert spec.metadata['importer_resolved'] == 'urdf_skeleton'
    assert any('urdf_skeleton fidelity' in item for item in spec.metadata.get('warnings', []))
