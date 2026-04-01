from __future__ import annotations

from pathlib import Path

from robot_sim.infra.quality_contracts import verify_quality_contract_files


def test_ci_workflow_contains_quality_gates(project_root: Path):
    ci_text = (project_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for marker in [
        "quick_quality:",
        "full_validation:",
        "gui_smoke:",
        "ruff check src tests",
        "run: mypy",
        "python scripts/verify_quality_contracts.py",
        "pytest tests/unit tests/regression -q",
        "pytest --cov=src/robot_sim --cov-report=term-missing -q",
        "pytest tests/gui -q",
    ]:
        assert marker in ci_text


def test_precommit_and_gitignore_cover_local_quality_workflow(project_root: Path):
    precommit_text = (project_root / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    gitignore_text = (project_root / ".gitignore").read_text(encoding="utf-8")
    assert "ruff-check" in precommit_text
    assert "mypy" in precommit_text
    assert "pytest -q" in precommit_text
    assert ".pytest_cache/" in gitignore_text
    assert "__pycache__/" in gitignore_text


def test_checked_in_quality_contract_docs_are_current(project_root: Path):
    assert verify_quality_contract_files(project_root) == []
