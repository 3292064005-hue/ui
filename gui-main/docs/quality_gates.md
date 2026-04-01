# Quality Gates

- quick quality: `ruff check src tests` + targeted `mypy` + `pytest tests/unit tests/regression -q`
- full validation: `pytest --cov=src/robot_sim --cov-report=term-missing -q` with `fail_under = 80`
- gui smoke: `pytest tests/gui -q` on Ubuntu 22.04 with `PySide6>=6.5` installed
- quality contracts: `python scripts/verify_quality_contracts.py`
- contract regeneration: `python scripts/regenerate_quality_contracts.py` + `git diff --exit-code -- docs`
