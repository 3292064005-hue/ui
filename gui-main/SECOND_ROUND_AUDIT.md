# SECOND ROUND AUDIT

## Historical note: delivered in v0.6.0

- Added `analytic_6r` spherical-wrist closed-form IK plugin and registered it in the canonical solver registry.
- Added IK request adapter pipeline with seed clamping, target rotation normalization, and orientation-relaxation retry.
- Extended schema/UI/config defaults to expose the new solver and adapter controls.
- Added CI workflow for `pytest -q`.
- Expanded regression and unit coverage.

## Validation

- `pytest -q` -> `99 passed, 1 skipped`
- `python scripts/run_tests.py` -> `99 passed, 1 skipped`
