from __future__ import annotations

from robot_sim.application.services.config_service import ConfigService


def test_config_service_loads_defaults_and_merges_overrides(tmp_path):
    (tmp_path / 'app.yaml').write_text(
        'window:\n  title: Custom Title\n  width: 1234\nplots:\n  max_points: 42\n',
        encoding='utf-8',
    )
    (tmp_path / 'solver.yaml').write_text(
        'ik:\n  mode: pinv\n  retry_count: 3\ntrajectory:\n  dt: 0.05\n',
        encoding='utf-8',
    )
    service = ConfigService(tmp_path)
    app_cfg = service.load_app_config()
    solver_cfg = service.load_solver_config()
    assert app_cfg['window']['title'] == 'Custom Title'
    assert app_cfg['window']['height'] == 980
    assert app_cfg['plots']['max_points'] == 42
    assert solver_cfg['ik']['mode'] == 'pinv'
    assert solver_cfg['ik']['retry_count'] == 3
    assert solver_cfg['ik']['reachability_precheck'] is True
    assert solver_cfg['trajectory']['duration'] == 3.0
    assert solver_cfg['trajectory']['dt'] == 0.05
