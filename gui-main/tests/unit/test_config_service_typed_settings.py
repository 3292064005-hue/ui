from __future__ import annotations

from robot_sim.application.services.config_service import ConfigService


def test_config_service_typed_settings_roundtrip(tmp_path):
    profiles = tmp_path / 'profiles'
    profiles.mkdir(parents=True)
    (profiles / 'default.yaml').write_text(
        'window:\n  title: Demo\nplots:\n  max_points: 42\nik:\n  mode: dls\ntrajectory:\n  duration: 2.0\n  dt: 0.05\n',
        encoding='utf-8',
    )
    service = ConfigService(tmp_path)

    app_settings = service.load_app_settings()
    solver_settings = service.load_solver_settings()

    assert app_settings.window.title == 'Demo'
    assert app_settings.plots.max_points == 42
    assert solver_settings.trajectory.duration == 2.0
    assert solver_settings.as_dict()['ik']['mode'] == 'dls'
