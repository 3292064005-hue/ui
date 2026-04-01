from pathlib import Path

from robot_sim.infra.exception_policy import render_exception_catch_matrix_markdown, verify_exception_catch_matrix


def test_exception_catch_matrix_matches_repo_contract(project_root: Path):
    errors = verify_exception_catch_matrix(project_root)
    assert errors == []
    markdown = render_exception_catch_matrix_markdown(project_root)
    assert '## runtime_boundaries' in markdown
    assert 'src/robot_sim/presentation/main_window_ui.py' in markdown
