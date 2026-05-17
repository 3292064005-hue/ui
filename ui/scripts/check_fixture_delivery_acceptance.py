#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_fixture_delivery_acceptance import DEFAULT_OUTPUT_ROOT, validate_delivery_output  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check fixture delivery acceptance artifacts.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    report, blockers = validate_delivery_output(args.output_root)
    if blockers:
        print(json.dumps({"ok": False, "blockers": blockers}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, "report_path": str(args.output_root / "delivery_readiness_report.json"), "session_dir": report.get("session_dir", "")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
