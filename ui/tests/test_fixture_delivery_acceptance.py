import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run_acceptance(output_root: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_fixture_delivery_acceptance.py"),
            "--output-root",
            str(output_root),
            *extra_args,
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )


def test_fixture_delivery_acceptance_generates_report(tmp_path: Path) -> None:
    output_root = tmp_path / "delivery"
    proc = _run_acceptance(output_root)
    assert proc.returncode == 0, proc.stderr + proc.stdout

    report_path = output_root / "delivery_readiness_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    session_report = json.loads(Path(report["session_report_path"]).read_text(encoding="utf-8"))

    assert report["ok"] is True
    assert report["hard_blockers"] == []
    assert report["manual_review_approval"]["approved"] is True
    assert report["claim_boundary"]["live_hil_closed"] is False
    assert report["claim_boundary"]["clinical_ready"] is False
    assert report["claim_boundary"]["clinical_claim"] == "none"
    assert session_report["delivery_summary"]["sync"]["reconstructable_count"] > 0
    assert session_report["delivery_summary"]["hard_blockers"] == []
    assert any(item["name"] == "live_hil_boundary" and item["status"] == "open_live_hil_gap" for item in report["traceability"])


def test_fixture_delivery_acceptance_fails_closed_on_bad_model_config(tmp_path: Path) -> None:
    config_dir = tmp_path / "bad_model_configs"
    config_dir.mkdir()
    for name, package in {
        "frame_anatomy_keypoint_runtime.yaml": ROOT / "models" / "frame_anatomy_keypoint",
        "lamina_keypoint_runtime.yaml": ROOT / "models" / "lamina_keypoint",
        "uca_rank_runtime.yaml": ROOT / "models" / "uca_rank",
    }.items():
        (config_dir / name).write_text(f"package_dir: {package}\nbackend: baseline\nstrict_runtime_required: true\n", encoding="utf-8")
    (config_dir / "lamina_seg_runtime.yaml").write_text("package_dir: ./missing_lamina_seg\nbackend: baseline\nstrict_runtime_required: true\n", encoding="utf-8")

    output_root = tmp_path / "blocked_delivery"
    proc = _run_acceptance(output_root, "--model-config-dir", str(config_dir))
    assert proc.returncode != 0

    report = json.loads((output_root / "delivery_readiness_report.json").read_text(encoding="utf-8"))
    assert report["ok"] is False
    assert any("model_runtime_blocked:lamina_seg" in blocker for blocker in report["hard_blockers"])
    assert report["claim_boundary"]["live_hil_closed"] is False
    assert report["claim_boundary"]["clinical_ready"] is False
