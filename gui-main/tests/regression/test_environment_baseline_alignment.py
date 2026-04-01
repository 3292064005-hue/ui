from __future__ import annotations

from pathlib import Path


def test_readme_and_ci_align_on_environment_baseline(project_root: Path):
    readme = (project_root / "README.md").read_text(encoding="utf-8")
    workflow = (project_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    pyproject = (project_root / "pyproject.toml").read_text(encoding="utf-8")

    assert "Ubuntu 22.04" in readme
    assert 'runs-on: ubuntu-22.04' in workflow
    assert 'python-version: "3.10"' in workflow
    assert 'requires-python = ">=3.10"' in pyproject
    assert '"PySide6>=6.5"' in pyproject
