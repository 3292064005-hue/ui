from __future__ import annotations

from pathlib import Path


def test_readme_lists_v7_quality_gates_and_experimental_modules(project_root: Path):
    readme = (project_root / "README.md").read_text(encoding="utf-8")
    assert "## V7 质量门禁" in readme
    assert "## Experimental 模块" in readme
    for marker in [
        "presentation.widgets.collision_panel",
        "presentation.widgets.export_panel",
        "presentation.widgets.scene_options_panel",
        "render.picking",
        "render.plot_sync",
    ]:
        assert marker in readme
