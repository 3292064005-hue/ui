from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.core.plan_service import PlanService
from spine_ultrasound_ui.core.postprocess_service import PostprocessService
from spine_ultrasound_ui.core.session_recorders import JsonlRecorder
from spine_ultrasound_ui.models import ExperimentRecord, RuntimeConfig
from spine_ultrasound_ui.services.pressure_sensor_service import create_force_sensor_provider


def _device_roster() -> dict:
    return {
        "robot": {"online": True, "fresh": True, "fact_source": "offline_fixture"},
        "camera": {"online": True, "fresh": True, "fact_source": "offline_fixture"},
        "ultrasound": {"online": True, "fresh": True, "fact_source": "offline_fixture"},
        "pressure": {"online": True, "fresh": True, "fact_source": "offline_fixture"},
    }


def _write_rgbd_fixture(path: Path) -> None:
    rgb = np.zeros((72, 96, 3), dtype=np.uint8)
    rgb[10:64, 42:54, :] = 230
    depth = np.full((72, 96), 205.0, dtype=np.float32)
    depth += np.linspace(-6.0, 6.0, 72, dtype=np.float32)[:, None]
    np.savez(path, rgb=rgb, depth_mm=depth, mm_per_pixel_x=0.5, mm_per_pixel_y=0.75)


def _write_ultrasound_frame(path: Path, *, offset: int) -> None:
    image = np.zeros((48, 64), dtype=np.uint8)
    for x in range(64):
        y = int(18 + 0.18 * x + offset)
        if 1 <= y < 47:
            image[y - 1:y + 2, x] = 235
    Image.fromarray(image, mode="L").save(path)


def _seed_multimodal_evidence(session_dir: Path, *, force_replay: Path) -> None:
    session_id = session_dir.name
    ts0 = 1_800_000_000_000_000_000
    camera_index = JsonlRecorder(session_dir / "raw" / "camera" / "index.jsonl", session_id)
    ultrasound_index = JsonlRecorder(session_dir / "raw" / "ultrasound" / "index.jsonl", session_id)
    quality_index = JsonlRecorder(session_dir / "raw" / "ui" / "quality_feedback.jsonl", session_id)
    pressure_index = JsonlRecorder(session_dir / "raw" / "pressure" / "samples.jsonl", session_id)
    robot_index = JsonlRecorder(session_dir / "raw" / "core" / "robot_state.jsonl", session_id)
    contact_index = JsonlRecorder(session_dir / "raw" / "core" / "contact_state.jsonl", session_id)
    progress_index = JsonlRecorder(session_dir / "raw" / "core" / "scan_progress.jsonl", session_id)
    provider = create_force_sensor_provider(f"serial_force_sensor:{force_replay}?format=json")
    try:
        for idx in range(6):
            ts_ns = ts0 + idx * 20_000_000
            camera_path = session_dir / "raw" / "camera" / "frames" / f"camera_{idx + 1:06d}.png"
            ultrasound_path = session_dir / "raw" / "ultrasound" / "frames" / f"us_{idx + 1:06d}.png"
            Image.fromarray(np.full((48, 64), 80 + idx, dtype=np.uint8), mode="L").save(camera_path)
            _write_ultrasound_frame(ultrasound_path, offset=idx % 3)
            sample = provider.read_sample(contact_active=True, desired_force_n=8.0)
            pressure_current = float(sample.wrench_n[2])
            camera_index.append(
                {
                    "frame_id": f"camera-{idx + 1}",
                    "frame_path": str(camera_path),
                    "provider_mode": "filesystem",
                    "frame_type": "rgbd",
                },
                source_ts_ns=ts_ns,
            )
            ultrasound_index.append(
                {
                    "frame_id": idx + 1,
                    "frame_path": str(ultrasound_path),
                    "segment_id": 1 + (idx % 3),
                    "quality_score": 0.91,
                    "pixel_spacing_mm": [0.5, 0.5],
                    "lateral_span_mm": 32.0,
                },
                source_ts_ns=ts_ns,
            )
            quality_index.append({"quality_score": 0.91, "coverage_score": 0.88}, source_ts_ns=ts_ns)
            pressure_index.append(
                {
                    "pressure_current": pressure_current,
                    "desired_force_n": 8.0,
                    "pressure_error": round(pressure_current - 8.0, 3),
                    "contact_confidence": 0.9,
                    "force_status": sample.status,
                    "force_source": sample.source,
                    "wrench_n": sample.wrench_n,
                },
                source_ts_ns=ts_ns,
            )
            contact_index.append(
                {
                    "mode": "STABLE_CONTACT",
                    "confidence": 0.9,
                    "pressure_current": pressure_current,
                    "recommended_action": "SCAN",
                    "contact_stable": True,
                },
                source_ts_ns=ts_ns,
            )
            progress_index.append(
                {
                    "execution_state": "SCANNING",
                    "active_segment": 1 + (idx % 3),
                    "path_index": idx,
                    "progress_pct": 10.0 + idx * 15.0,
                    "frame_id": idx + 1,
                },
                source_ts_ns=ts_ns,
            )
            robot_index.append(
                {
                    "powered": True,
                    "operate_mode": "automatic",
                    "joint_pos": [0.05 * idx, 0.1, -0.1, 0.2, 0.0, 0.3],
                    "joint_torque": [0.0, 0.0, 0.1, 0.0, 0.0, 0.0],
                    "tcp_pose": {"x": 110.0 + idx * 8.0, "y": -2.0 + idx * 0.2, "z": 205.0, "rx": 180.0, "ry": 0.0, "rz": 90.0},
                },
                source_ts_ns=ts_ns,
            )
    finally:
        provider.stop()


def test_offline_rgbd_pressure_ultrasound_loop_reconstructs_and_assesses(tmp_path: Path) -> None:
    rgbd_source = tmp_path / "rgbd_frame.npz"
    force_replay = tmp_path / "force.jsonl"
    _write_rgbd_fixture(rgbd_source)
    force_replay.write_text(
        "\n".join(json.dumps({"ts_ns": 1_800_000_000_000_000_000 + idx, "pressure_current": 8.0 + 0.05 * idx}) for idx in range(6)) + "\n",
        encoding="utf-8",
    )
    config = RuntimeConfig(
        camera_guidance_input_mode="filesystem",
        camera_guidance_source_path=str(rgbd_source),
        camera_guidance_frame_count=1,
        force_sensor_provider=f"serial_force_sensor:{force_replay}?format=json",
        segment_length_mm=24.0,
        sample_step_mm=8.0,
        scan_speed_mm_s=8.0,
    )
    exp_manager = ExperimentManager(tmp_path / "workspace")
    exp = exp_manager.create(config.to_dict(), note="offline multimodal closed-loop fixture")
    experiment = ExperimentRecord(
        exp_id=exp["exp_id"],
        created_at=exp["metadata"]["created_at"],
        state="AUTO_READY",
        cobb_angle=0.0,
        pressure_target=config.pressure_target,
        save_dir=exp["save_dir"],
    )
    plan_service = PlanService()
    localization = plan_service.run_localization(experiment, config, device_roster=_device_roster())
    preview_plan, _ = plan_service.build_preview_plan(experiment, localization, config)
    execution_plan = plan_service.build_execution_plan(preview_plan, config=config)
    lock = exp_manager.lock_session(
        exp["exp_id"],
        config.to_dict(),
        _device_roster(),
        config.software_version,
        config.build_id,
        execution_plan,
        registration_version=localization.registration_version,
        patient_registration=localization.patient_registration,
        patient_registration_hash=localization.registration_hash(),
        localization_readiness=localization.localization_readiness,
        localization_readiness_hash=str(localization.localization_readiness.get("readiness_hash", "")),
        calibration_bundle=localization.calibration_bundle,
        calibration_bundle_hash=str(localization.calibration_bundle.get("bundle_hash", "")),
        manual_adjustment=localization.manual_adjustment,
        manual_adjustment_hash=str(localization.manual_adjustment.get("hash", "")),
        source_frame_set=localization.source_frame_set,
        source_frame_set_hash=str(localization.source_frame_set.get("source_frame_set_hash", "")),
        guidance_source_type="camera_only",
        force_sensor_provider=config.force_sensor_provider,
        safety_thresholds={"stale_telemetry_ms": 250},
        guidance_algorithm_registry=localization.guidance_algorithm_registry,
        guidance_processing_steps=localization.guidance_processing_steps,
    )
    session_dir = Path(lock["session_dir"])
    exp_manager.save_json_artifact(session_dir, "meta/patient_registration.json", localization.patient_registration)
    exp_manager.save_json_artifact(session_dir, "meta/calibration_bundle.json", localization.calibration_bundle)
    exp_manager.save_summary(session_dir, {"session_id": session_dir.name, "experiment_id": exp["exp_id"], "source": "offline_multimodal_fixture"})
    _seed_multimodal_evidence(session_dir, force_replay=force_replay)

    postprocess = PostprocessService(exp_manager)
    assert postprocess.reconstruct(session_dir).ready is True
    assert postprocess.assess(session_dir).ready is True

    frame_sync = json.loads((session_dir / "derived" / "sync" / "frame_sync_index.json").read_text(encoding="utf-8"))
    reconstruction_input = json.loads((session_dir / "derived" / "reconstruction" / "reconstruction_input_index.json").read_text(encoding="utf-8"))
    cobb = json.loads((session_dir / "derived" / "assessment" / "cobb_measurement.json").read_text(encoding="utf-8"))
    report = json.loads((session_dir / "export" / "session_report.json").read_text(encoding="utf-8"))

    assert localization.patient_registration["body_surface"]["depth_source"] == "depth_frame"
    assert frame_sync["summary"]["pressure_alignment_available"] is True
    assert frame_sync["summary"]["robot_alignment_available"] is True
    assert reconstruction_input["selection_mode"] == "authoritative_measured_rows"
    assert reconstruction_input["gates"]["reconstructable_frame_count"] > 0
    assert cobb["measurement_status"] in {"authoritative", "degraded"}
    assert report["delivery_summary"]["claim_boundary"]["live_hil_closed"] is False
    assert report["delivery_summary"]["claim_boundary"]["clinical_ready"] is False
