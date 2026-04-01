from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import tomllib

from robot_sim.application.services.capability_service import CapabilityService
from robot_sim.application.services.module_status_service import ModuleStatusService
from robot_sim.application.services.runtime_feature_service import RuntimeFeaturePolicy
from robot_sim.infra.exception_policy import render_exception_catch_matrix_markdown, verify_exception_catch_matrix


QUALITY_GATE_LINES: tuple[str, ...] = (
    '- quick quality: `ruff check src tests` + targeted `mypy` + `pytest tests/unit tests/regression -q`',
    '- full validation: `pytest --cov=src/robot_sim --cov-report=term-missing -q` with `fail_under = 80`',
    '- gui smoke: `pytest tests/gui -q` on Ubuntu 22.04 with `PySide6>=6.5` installed',
    '- quality contracts: `python scripts/verify_quality_contracts.py`',
    '- contract regeneration: `python scripts/regenerate_quality_contracts.py` + `git diff --exit-code -- docs`',
)


@dataclass(frozen=True)
class QualityContractSnapshot:
    """Deterministic markdown/doc snapshot used by docs and regression checks."""

    quality_gates_markdown: str
    module_status_markdown: str
    capability_matrix_markdown: str
    exception_catch_matrix_markdown: str


class QualityContractService:
    """Render the doc snippets that define the project quality contract."""

    def __init__(
        self,
        *,
        runtime_feature_policy: RuntimeFeaturePolicy | None = None,
        capability_matrix_renderer: Callable[[], str] | None = None,
        module_status_renderer: Callable[[], str] | None = None,
        exception_catch_matrix_renderer: Callable[[], str] | None = None,
    ) -> None:
        self._runtime_feature_policy = runtime_feature_policy or RuntimeFeaturePolicy()
        self._capability_matrix_renderer = capability_matrix_renderer or CapabilityService(
            runtime_feature_policy=self._runtime_feature_policy,
        ).render_scene_markdown
        self._module_status_renderer = module_status_renderer or ModuleStatusService(
            runtime_feature_policy=self._runtime_feature_policy,
        ).render_markdown
        self._exception_catch_matrix_renderer = exception_catch_matrix_renderer or render_exception_catch_matrix_markdown

    def snapshot(self) -> QualityContractSnapshot:
        """Return the current rendered documentation snapshot."""
        return QualityContractSnapshot(
            quality_gates_markdown=self.render_quality_gates_markdown(),
            module_status_markdown=self._module_status_renderer(),
            capability_matrix_markdown=self._capability_matrix_renderer(),
            exception_catch_matrix_markdown=self._exception_catch_matrix_renderer(),
        )

    def render_quality_gates_markdown(self) -> str:
        """Render the quality-gates markdown document."""
        lines = ['# Quality Gates', '']
        lines.extend(QUALITY_GATE_LINES)
        lines.append('')
        return '\n'.join(lines)


def _expected_docs(root: Path, snapshot: QualityContractSnapshot) -> dict[Path, str]:
    docs_dir = root / 'docs'
    return {
        docs_dir / 'quality_gates.md': snapshot.quality_gates_markdown,
        docs_dir / 'module_status.md': snapshot.module_status_markdown,
        docs_dir / 'capability_matrix.md': snapshot.capability_matrix_markdown,
        docs_dir / 'exception_catch_matrix.md': snapshot.exception_catch_matrix_markdown,
    }


def write_quality_contract_files(project_root: str | Path) -> None:
    """Regenerate checked-in contract docs from runtime truth sources."""
    root = Path(project_root)
    snapshot = QualityContractService().snapshot()
    for path, content in _expected_docs(root, snapshot).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')


def verify_quality_contract_files(project_root: str | Path) -> list[str]:
    """Verify generated contract documents against checked-in copies."""
    root = Path(project_root)
    snapshot = QualityContractService().snapshot()
    errors: list[str] = []

    for path, expected in _expected_docs(root, snapshot).items():
        if not path.exists():
            errors.append(f'missing contract doc: {path.relative_to(root)}')
            continue
        actual = path.read_text(encoding='utf-8')
        if actual.strip() != expected.strip():
            errors.append(f'contract doc out of date: {path.relative_to(root)}')

    errors.extend(verify_exception_catch_matrix(root))

    workflow_path = root / '.github' / 'workflows' / 'ci.yml'
    workflow = ''
    if workflow_path.exists():
        workflow = workflow_path.read_text(encoding='utf-8')
        required_markers = (
            'quick_quality:',
            'full_validation:',
            'gui_smoke:',
            'python scripts/verify_quality_contracts.py',
            'python scripts/regenerate_quality_contracts.py',
            'git diff --exit-code -- docs',
            'pytest tests/unit tests/regression -q',
            'pytest --cov=src/robot_sim --cov-report=term-missing -q',
            'pytest tests/gui -q',
        )
        for marker in required_markers:
            if marker not in workflow:
                errors.append(f'workflow missing marker: {marker}')
    else:
        errors.append('missing workflow: .github/workflows/ci.yml')

    readme_path = root / 'README.md'
    readme = ''
    if readme_path.exists():
        readme = readme_path.read_text(encoding='utf-8')
        readme_markers = (
            '当前测试基线：**以 CI / pytest 实际收集结果为准**',
            'quick quality',
            'full validation',
            'gui smoke',
            'quality contracts',
            'regenerate_quality_contracts.py',
            'research.yaml',
        )
        for marker in readme_markers:
            if marker not in readme:
                errors.append(f'README missing marker: {marker}')
    else:
        errors.append('missing README.md')

    pyproject_path = root / 'pyproject.toml'
    pyproject = {}
    if pyproject_path.exists():
        pyproject = tomllib.loads(pyproject_path.read_text(encoding='utf-8'))
    else:
        errors.append('missing pyproject.toml')

    if readme and pyproject:
        project = dict(pyproject.get('project', {}))
        optional_deps = dict(project.get('optional-dependencies', {}))
        gui_deps = tuple(optional_deps.get('gui', ()))
        env_markers = (
            ('Ubuntu 22.04', readme, workflow),
            ('Python 3.10', readme, str(project.get('requires-python', ''))),
            ('PySide6 >= 6.5', readme, ' '.join(gui_deps)),
            ('pyqtgraph >= 0.13', readme, ' '.join(gui_deps)),
            ('PyVista >= 0.43', readme, ' '.join(gui_deps)),
            ('pyvistaqt >= 0.11', readme, ' '.join(gui_deps)),
        )
        for label, left, _right in env_markers:
            if label not in left:
                errors.append(f'README missing environment marker: {label}')
        if 'ubuntu-22.04' not in workflow:
            errors.append('workflow missing environment marker: ubuntu-22.04')
        if 'python-version: "3.10"' not in workflow:
            errors.append('workflow missing environment marker: python-version 3.10')
        if str(project.get('requires-python', '')) != '>=3.10':
            errors.append('pyproject requires-python drifted from 3.10+ baseline')
        joined_gui = ' '.join(gui_deps)
        for marker in ('PySide6>=6.5', 'pyqtgraph>=0.13', 'pyvista>=0.43', 'pyvistaqt>=0.11'):
            if marker not in joined_gui:
                errors.append(f'pyproject missing gui dependency marker: {marker}')

    return errors
