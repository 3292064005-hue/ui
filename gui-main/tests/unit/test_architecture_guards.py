from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / 'src' / 'robot_sim'


def test_core_waypoint_planner_does_not_import_application_layer():
    path = SRC_ROOT / 'core' / 'trajectory' / 'waypoint_planner.py'
    text = path.read_text(encoding='utf-8')
    assert 'robot_sim.application' not in text


def test_domain_layer_does_not_import_application_layer():
    for path in (SRC_ROOT / 'domain').rglob('*.py'):
        text = path.read_text(encoding='utf-8')
        assert 'robot_sim.application' not in text, f'domain import leak: {path.relative_to(PROJECT_ROOT)}'


def test_application_layer_does_not_import_app_layer():
    for path in (SRC_ROOT / 'application').rglob('*.py'):
        text = path.read_text(encoding='utf-8')
        assert 'robot_sim.app.' not in text, f'application import leak: {path.relative_to(PROJECT_ROOT)}'


def test_stable_main_window_ui_does_not_mount_experimental_widgets():
    path = SRC_ROOT / 'presentation' / 'main_window_ui.py'
    text = path.read_text(encoding='utf-8')
    for marker in ('collision_panel', 'export_panel', 'scene_options_panel'):
        assert marker not in text


def test_gui_boundary_catches_are_centralized_in_main_window_ui():
    allowed = {
        SRC_ROOT / 'presentation' / 'main_window_ui.py',
        SRC_ROOT / 'presentation' / 'coordinators' / '_helpers.py',
    }
    guarded_paths = [
        SRC_ROOT / 'presentation' / 'main_window_actions.py',
        SRC_ROOT / 'presentation' / 'main_window_tasks.py',
        *(path for path in (SRC_ROOT / 'presentation' / 'coordinators').glob('*.py') if path.name != '_helpers.py'),
    ]
    for path in guarded_paths:
        text = path.read_text(encoding='utf-8')
        assert 'except Exception' not in text, f'presentation boundary catch should be centralized: {path.relative_to(PROJECT_ROOT)}'
    for path in allowed:
        text = path.read_text(encoding='utf-8')
        assert 'except Exception' in text, f'missing centralized presentation error boundary: {path.relative_to(PROJECT_ROOT)}'


def test_coordinators_only_touch_view_boundary_methods_for_widget_projection():
    forbidden_markers = (
        '.status_panel',
        '.playback_panel',
        '.benchmark_panel',
        '.scene_controller',
        '.scene_widget',
        '.target_panel',
        '.robot_panel',
        '._set_busy',
        '._set_playback_running',
    )
    for path in (SRC_ROOT / 'presentation' / 'coordinators').glob('*.py'):
        if path.name in {'__init__.py', '_helpers.py'}:
            continue
        text = path.read_text(encoding='utf-8')
        for marker in forbidden_markers:
            assert marker not in text, f'coordinator should project through view boundary ({marker}): {path.relative_to(PROJECT_ROOT)}'
