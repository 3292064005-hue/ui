# Revalidation Note for v0.6.0 Round 2 Delivery (historical, superseded by FINAL_REVIEW_AUDIT.md)

This package was revalidated after the prior round-2 delivery.

Verified facts:
- `pytest -q` passes: 99 passed, 1 skipped.
- `python scripts/run_tests.py` passes: 99 passed, 1 skipped.
- `analytic_6r` is registered and covered by tests.
- IK request adapters are wired into `RunIKUseCase` and covered by tests.
- Version metadata is aligned to `0.6.0` in README, pyproject, PKG-INFO, and app/version.

Corrected packaging issue:
- Removed `__pycache__` directories and `.pytest_cache` from the distributable zip.

Known validation boundary:
- The single skipped test is `tests/gui/test_main_window_smoke.py`, which is guarded by `pytest.importorskip('PySide6')`. In this environment the GUI dependency is unavailable, so GUI smoke construction is not claimed as executed here.
