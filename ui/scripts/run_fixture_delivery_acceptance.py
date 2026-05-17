#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "artifacts" / "delivery" / "final_fixture_acceptance"

MODEL_CONFIGS = {
    "frame_anatomy_keypoint": "frame_anatomy_keypoint_runtime.yaml",
    "lamina_seg": "lamina_seg_runtime.yaml",
    "lamina_keypoint": "lamina_keypoint_runtime.yaml",
    "uca_rank": "uca_rank_runtime.yaml",
}

REQUIRED_SESSION_ARTIFACTS = {
    "session_report": "export/session_report.json",
    "cobb_measurement": "derived/assessment/cobb_measurement.json",
    "assessment_summary": "derived/assessment/assessment_summary.json",
    "reconstruction_summary": "derived/reconstruction/reconstruction_summary.json",
    "frame_sync_index": "derived/sync/frame_sync_index.json",
    "reconstruction_input_index": "derived/reconstruction/reconstruction_input_index.json",
    "model_reconstruction_evidence": "derived/reconstruction/reconstruction_evidence.json",
    "coronal_vpi": "derived/reconstruction/coronal_vpi.npz",
    "vpi_preview": "derived/reconstruction/vpi_preview.png",
    "source_frame_set": "derived/sync/source_frame_set.json",
    "calibration_bundle": "meta/calibration_bundle.json",
    "scan_protocol": "derived/preview/scan_protocol.json",
}

PROTOTYPE_CLAIM = {
    "evidence_tier": "fixture_research",
    "prototype_scope": "offline_research_prototype",
    "non_clinical_statement": "Fixture/mock evidence only; no live/HIL or clinical readiness claim is made.",
    "live_hil_closed": False,
    "clinical_ready": False,
    "clinical_claim": "none",
}


def _json_default(value: Any) -> str:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")
    return path


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _portable(path: Path | str, *, base: Path = ROOT) -> str:
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(candidate)


def _run_subprocess(args: list[str]) -> dict[str, Any]:
    proc = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False)
    payload: dict[str, Any] = {
        "command": " ".join(args),
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout.splitlines()[-20:],
        "stderr_tail": proc.stderr.splitlines()[-20:],
    }
    if proc.stdout.strip():
        last_line = proc.stdout.strip().splitlines()[-1]
        try:
            payload["json_result"] = json.loads(last_line)
        except json.JSONDecodeError:
            payload["json_result"] = {}
    return payload


def _create_rgbd_guidance_fixture(frames_dir: Path) -> Path:
    frames_dir.mkdir(parents=True, exist_ok=True)
    height, width = 120, 160
    intrinsics = {
        "frame_type": "rgbd",
        "mm_per_pixel_x": 0.5,
        "mm_per_pixel_y": 0.75,
        "resolution": {"width": width, "height": height},
    }
    for index, offset in enumerate([-6, 0, 5], start=1):
        pixels = np.zeros((height, width), dtype=np.float32)
        center = width // 2 + offset
        pixels[16:108, max(0, center - 8):min(width, center + 8)] = 0.95
        row_gradient = np.linspace(-1.5, 1.5, height, dtype=np.float32).reshape(height, 1)
        col_gradient = np.linspace(-0.8, 0.8, width, dtype=np.float32).reshape(1, width)
        depth = 205.0 + row_gradient + col_gradient + (index - 2) * 0.4
        np.savez(
            frames_dir / f"rgbd_guidance_{index:03d}.npz",
            color=pixels,
            depth_mm=depth.astype(np.float32),
            intrinsics_json=json.dumps(intrinsics),
        )
    return frames_dir


def _validate_runtime_models(config_dir: Path) -> tuple[dict[str, Any], list[str]]:
    sys.path.insert(0, str(ROOT))
    from spine_ultrasound_ui.training.runtime_adapters.common import resolve_model_package

    evidence: dict[str, Any] = {}
    blockers: list[str] = []
    for model_name, filename in MODEL_CONFIGS.items():
        config_path = config_dir / filename
        try:
            package = resolve_model_package(config_path)
        except Exception as exc:
            blockers.append(f"model_runtime_blocked:{model_name}:{exc}")
            continue
        meta = dict(package.get("meta", {}))
        evidence[model_name] = {
            "config_path": _portable(config_path),
            "package_dir": _portable(Path(package.get("package_dir", ""))),
            "package_name": str(meta.get("package_name", "")),
            "package_hash": str(meta.get("package_hash", "")),
            "release_state": str(meta.get("release_state", "")),
            "clinical_claim": str(meta.get("clinical_claim", "")),
            "trainer_backend": str(meta.get("trainer_backend", "")),
            "dataset_source": str(meta.get("dataset_source", "")),
            "dataset_hash": str(meta.get("dataset_hash", "")),
            "strict_runtime_required": bool(meta.get("strict_runtime_required", False)),
        }
    return evidence, blockers


def _run_fixture_training(output_root: Path) -> dict[str, Any]:
    training_root = output_root / "fixture_model_training"
    result = _run_subprocess([
        sys.executable,
        str(ROOT / "scripts" / "run_model_training_pipeline.py"),
        "--task",
        "all",
        "--backend",
        "numpy_baseline",
        "--output-root",
        str(training_root),
    ])
    summary_path = Path(result.get("json_result", {}).get("summary_path", ""))
    if summary_path.exists():
        result["training_summary"] = _read_json(summary_path)
        result["summary_path"] = str(summary_path)
    return result


def _drain_qt(app: Any, iterations: int = 16) -> None:
    for _ in range(iterations):
        app.processEvents()


def _run_controller_flow(output_root: Path, guidance_frames_dir: Path) -> tuple[Path | None, list[str], list[dict[str, Any]]]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    sys.path.insert(0, str(ROOT))
    from PySide6.QtWidgets import QApplication
    from spine_ultrasound_ui.core.app_controller import AppController
    from spine_ultrasound_ui.services.mock_backend import MockBackend
    from spine_ultrasound_ui.utils import generate_demo_pixmap, now_ns

    app = QApplication.instance() or QApplication([])
    workspace = output_root / "workspace"
    backend = MockBackend(workspace)
    controller = AppController(workspace, backend)
    logs: list[dict[str, Any]] = []
    blockers: list[str] = []
    controller.log_generated.connect(lambda level, message: logs.append({"level": str(level), "message": str(message)}))

    config = replace(
        controller.config,
        camera_guidance_input_mode="filesystem",
        camera_guidance_source_path=str(guidance_frames_dir),
        camera_guidance_file_glob="*.npz",
        camera_guidance_frame_count=3,
    )
    controller.update_config(config)
    _drain_qt(app)

    def step(name: str, *args: Any, **kwargs: Any) -> None:
        try:
            getattr(controller, name)(*args, **kwargs)
            _drain_qt(app)
        except Exception as exc:
            blockers.append(f"controller_step_failed:{name}:{exc}")

    for command in ("connect_robot", "power_on", "set_auto_mode", "create_experiment", "run_localization"):
        step(command)
    step("approve_localization_review", operator_id="fixture_acceptance", reason="fixture_delivery_review")
    for command in ("generate_path", "start_procedure"):
        step(command)

    for _ in range(6):
        if hasattr(backend, "runtime") and hasattr(backend.runtime, "tick") and hasattr(backend, "_emit_telemetry"):
            backend._emit_telemetry(backend.runtime.tick())
        _drain_qt(app)
        frame_ts_ns = now_ns()
        camera_pixmap = generate_demo_pixmap(160, 120, "camera", float(getattr(backend, "phase", 0.0)))
        ultrasound_pixmap = generate_demo_pixmap(160, 120, "ultrasound", float(getattr(backend, "phase", 0.0)))
        controller.session_service.record_camera_pixmap(
            camera_pixmap,
            source_ts_ns=frame_ts_ns,
            metadata={
                "frame_id": int(controller.telemetry.metrics.frame_id),
                "segment_id": int(controller.telemetry.metrics.segment_id),
                "scan_progress": float(controller.telemetry.metrics.scan_progress),
            },
        )
        controller.session_service.record_ultrasound_pixmap(
            ultrasound_pixmap,
            source_ts_ns=frame_ts_ns,
            metadata={
                "frame_id": int(controller.telemetry.metrics.frame_id),
                "segment_id": int(controller.telemetry.metrics.segment_id),
                "quality_score": float(controller.telemetry.metrics.quality_score),
                "pressure_current": float(controller.telemetry.metrics.pressure_current),
                "contact_mode": str(controller.telemetry.metrics.contact_mode),
            },
        )

    for command in ("safe_retreat", "save_results", "export_summary", "run_preprocess", "run_reconstruction", "run_assessment"):
        step(command)

    session_dir = controller.session_service.current_session_dir
    if session_dir is None:
        blockers.append("session_not_locked")
    try:
        controller.shutdown()
    except Exception:
        pass
    return session_dir, blockers, logs


def _traceability_matrix(session_dir: Path | None) -> list[dict[str, Any]]:
    def item(name: str, claim: str, artifacts: list[str], status: str = "delivered_fixture") -> dict[str, Any]:
        present = bool(session_dir) and all((session_dir / rel).exists() for rel in artifacts)
        return {
            "name": name,
            "project_book_claim": claim,
            "status": status if present else ("open_live_hil_gap" if status == "open_live_hil_gap" else "blocked"),
            "evidence_tier": "fixture_research" if status != "open_live_hil_gap" else "not_claimed",
            "artifacts": artifacts,
            "artifacts_present": present,
        }

    return [
        item("d435i_rgbd_guidance", "D435i back ROI, midline, surface normal and scan corridor", ["derived/sync/source_frame_set.json", "derived/guidance/body_surface.json", "derived/guidance/guidance_targets.json"]),
        item("calibration_freeze", "Robot base, camera, probe TCP and ultrasound image-frame calibration bundle", ["meta/calibration_bundle.json", "meta/localization_freeze.json"]),
        item("path_planning", "Standardized scan path with smoothing, overlap, speed and normal constraints", ["meta/scan_plan.json", "derived/preview/scan_protocol.json"]),
        item("pressure_feedback", "Pressure/contact timeline for force-position mixed control evidence", ["derived/pressure/pressure_sensor_timeline.json", "export/pressure_analysis.json"]),
        item("continuous_ultrasound_capture", "Continuous ultrasound frames and frame quality evidence", ["raw/ultrasound/index.jsonl", "derived/ultrasound/ultrasound_frame_metrics.json", "export/ultrasound_analysis.json"]),
        item("multimodal_sync", "Ultrasound, camera, pressure and robot pose synchronized rows", ["derived/sync/frame_sync_index.json", "derived/reconstruction/reconstruction_input_index.json"]),
        item("anatomy_models", "Bone mask, frame anatomy keypoints and lamina candidates from strict runtime model packages", ["derived/reconstruction/bone_mask.npz", "derived/reconstruction/frame_anatomy_points.json", "derived/reconstruction/lamina_candidates.json"]),
        item("vpi_reconstruction", "VPI volume, preview and reconstruction summary", ["derived/reconstruction/coronal_vpi.npz", "derived/reconstruction/vpi_preview.png", "derived/reconstruction/reconstruction_summary.json"]),
        item("cobb_assessment", "Offline Cobb/UCA assessment and manual-review reasons", ["derived/assessment/cobb_measurement.json", "derived/assessment/uca_measurement.json", "derived/assessment/assessment_summary.json"]),
        item("ui_report_export", "Operator-facing summary and exportable session report", ["export/summary.txt", "export/session_report.json"]),
        {
            "name": "live_hil_boundary",
            "project_book_claim": "Real hardware/HIL and clinical consistency evidence",
            "status": "open_live_hil_gap",
            "evidence_tier": "not_claimed",
            "artifacts": ["docs/05_verification/CURRENT_KNOWN_GAPS.md"],
            "artifacts_present": (ROOT / "docs/05_verification/CURRENT_KNOWN_GAPS.md").exists(),
        },
    ]


def _write_traceability_markdown(path: Path, matrix: list[dict[str, Any]]) -> Path:
    lines = [
        "# Fixture Delivery Traceability Matrix",
        "",
        "| Item | Status | Evidence tier | Artifacts |",
        "| --- | --- | --- | --- |",
    ]
    for row in matrix:
        artifacts = "<br>".join(str(item) for item in row.get("artifacts", []))
        lines.append(f"| {row['name']} | {row['status']} | {row['evidence_tier']} | {artifacts} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def validate_delivery_output(output_root: Path) -> tuple[dict[str, Any], list[str]]:
    report_path = output_root / "delivery_readiness_report.json"
    report = _read_json(report_path)
    blockers: list[str] = []
    session_dir = Path(report.get("session_dir", ""))
    if not report_path.exists():
        blockers.append("missing_delivery_readiness_report")
        return report, blockers
    if not session_dir.exists():
        blockers.append("missing_session_dir")
    for name, rel_path in REQUIRED_SESSION_ARTIFACTS.items():
        if not (session_dir / rel_path).exists():
            blockers.append(f"missing_required_artifact:{name}:{rel_path}")
    claim_boundary = dict(report.get("claim_boundary", {}))
    if claim_boundary.get("live_hil_closed") is not False:
        blockers.append("claim_boundary_live_hil_not_false")
    if claim_boundary.get("clinical_ready") is not False:
        blockers.append("claim_boundary_clinical_ready_not_false")
    return report, blockers


def build_delivery_report(output_root: Path, *, model_config_dir: Path) -> tuple[dict[str, Any], int]:
    output_root.mkdir(parents=True, exist_ok=True)
    report_path = output_root / "delivery_readiness_report.json"
    training_result = _run_fixture_training(output_root)
    model_evidence, model_blockers = _validate_runtime_models(model_config_dir)
    hard_blockers = list(model_blockers)

    if training_result.get("returncode", 1) != 0:
        hard_blockers.append("fixture_training_pipeline_failed")

    session_dir: Path | None = None
    controller_blockers: list[str] = []
    logs: list[dict[str, Any]] = []
    guidance_frames_dir = _create_rgbd_guidance_fixture(output_root / "fixtures" / "rgbd_guidance")
    if not hard_blockers:
        session_dir, controller_blockers, logs = _run_controller_flow(output_root, guidance_frames_dir)
        hard_blockers.extend(controller_blockers)

    required_artifacts = {
        name: {
            "relative_path": rel_path,
            "present": bool(session_dir) and (session_dir / rel_path).exists(),
        }
        for name, rel_path in REQUIRED_SESSION_ARTIFACTS.items()
    }
    for name, artifact in required_artifacts.items():
        if not artifact["present"]:
            hard_blockers.append(f"missing_required_artifact:{name}:{artifact['relative_path']}")

    session_report = _read_json(session_dir / "export/session_report.json") if session_dir else {}
    delivery_summary = dict(session_report.get("delivery_summary", {}))
    hard_blockers.extend(str(item) for item in delivery_summary.get("hard_blockers", []))
    hard_blockers = sorted(set(item for item in hard_blockers if item))
    matrix = _traceability_matrix(session_dir)
    matrix_path = _write_json(output_root / "delivery_traceability_matrix.json", {"items": matrix})
    matrix_md_path = _write_traceability_markdown(output_root / "delivery_traceability_matrix.md", matrix)

    payload = {
        "ok": not hard_blockers,
        "generated_at": session_report.get("generated_at", ""),
        "output_root": str(output_root),
        "session_dir": str(session_dir or ""),
        "session_report_path": str(session_dir / "export/session_report.json") if session_dir else "",
        "delivery_traceability_matrix": str(matrix_path),
        "delivery_traceability_matrix_markdown": str(matrix_md_path),
        "guidance_fixture_dir": str(guidance_frames_dir),
        "manual_review_approval": delivery_summary.get("manual_review", {}),
        "claim_boundary": {
            **PROTOTYPE_CLAIM,
            **dict(delivery_summary.get("claim_boundary", {})),
        },
        "model_bundle_evidence": model_evidence,
        "fixture_training": training_result,
        "required_artifacts": required_artifacts,
        "traceability": matrix,
        "hard_blockers": hard_blockers,
        "logs_tail": logs[-80:],
    }
    _write_json(report_path, payload)
    validation_report, validation_blockers = validate_delivery_output(output_root)
    if validation_blockers:
        payload["hard_blockers"] = sorted(set(payload["hard_blockers"] + validation_blockers))
        payload["ok"] = False
        _write_json(report_path, payload)
    return validation_report if validation_report else payload, 0 if payload["ok"] else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the fixture/mock delivery acceptance flow for the offline research prototype.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--model-config-dir", type=Path, default=ROOT / "configs" / "models")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report, code = build_delivery_report(args.output_root, model_config_dir=args.model_config_dir)
    print(json.dumps({"ok": code == 0, "report_path": str(args.output_root / "delivery_readiness_report.json"), "session_dir": report.get("session_dir", "")}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
