from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from robot_sim.infra.quality_contracts import write_quality_contract_files  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description='Regenerate checked-in contract docs from runtime truth sources.')
    parser.add_argument('--root', type=Path, default=PROJECT_ROOT, help='Repository root.')
    args = parser.parse_args()
    write_quality_contract_files(args.root)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
