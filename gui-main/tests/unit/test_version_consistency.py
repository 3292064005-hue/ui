from __future__ import annotations

from robot_sim.app.version import APP_VERSION, current_app_version


def test_app_version_matches_canonical_source():
    assert APP_VERSION == current_app_version()
