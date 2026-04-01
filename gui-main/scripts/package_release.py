from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _configure_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / 'src'
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))


_configure_path()

from robot_sim.infra.release_package import build_release_zip  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description='Build a clean release zip excluding caches and local artifacts.')
    parser.add_argument('--root', type=Path, default=REPO_ROOT, help='Repository root to package')
    parser.add_argument('--output', type=Path, required=True, help='Output zip path')
    parser.add_argument('--top-level-dir', type=str, default=None, help='Optional top-level directory inside zip')
    args = parser.parse_args()

    archive = build_release_zip(args.root, args.output, top_level_dir=args.top_level_dir)
    print(archive)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
