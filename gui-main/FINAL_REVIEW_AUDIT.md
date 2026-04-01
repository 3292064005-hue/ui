# Final Review Audit for v0.6.3

This package supersedes the previous v0.6.1 reviewed delivery.

## Verified in this audit

- `pytest -q` passes after remediation: `107 passed, 1 skipped`.
- `python scripts/run_tests.py` passes after remediation: `107 passed, 1 skipped`.
- `ruff check src tests` passes.
- `mypy` passes for the scoped typed boundary declared in `pyproject.toml`.
- `pytest --cov=src/robot_sim --cov-report=term-missing -q` passes with the configured coverage gate.
- GitHub Actions workflow enforces ruff, scoped mypy, and the coverage-gated pytest run.
- `.pre-commit-config.yaml` is present and wired for ruff, mypy, and pytest.
- Cache directories are excluded via `.gitignore` and removed from the distributable zip.
- Snapshot screenshots no longer depend on optional PyVista for basic off-screen export; a deterministic built-in PNG fallback is now present and regression-tested.

## Important boundary note

This package is materially stronger than the previous delivery, but it still does **not** mean every item in the long-range P0/P1/P2 roadmap is fully closed. In particular, GUI/render coverage and several thin presentation wrappers remain below the maturity of the math kernel and application services. That is a roadmap-completeness gap, not a hidden test failure.

## Why mypy remains scoped

The stable typed boundary in the current phase is the pure-math kernel, domain contracts, and trajectory model. GUI/render modules still rely on optional runtime dependencies and looser typing.

## Packaging hygiene

- Added `src/robot_sim/infra/release_package.py` and `scripts/package_release.py`.
- Clean release archives now explicitly exclude `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.coverage`, and `*.pyc`/`*.pyo`.
- This closes the recurring artifact-cleanliness regression seen in earlier zip deliveries.
