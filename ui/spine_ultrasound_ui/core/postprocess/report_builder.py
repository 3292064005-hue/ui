from __future__ import annotations

from pathlib import Path
from typing import Any

from spine_ultrasound_ui.utils import now_text


def _unique_strings(values: list[Any]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


def _model_readiness(runtime_models: dict[str, Any]) -> dict[str, dict[str, Any]]:
    states: dict[str, dict[str, Any]] = {}
    for name, raw_model in runtime_models.items():
        model = dict(raw_model or {})
        runtime_kind = str(model.get("runtime_kind", ""))
        release_state = str(model.get("release_state", ""))
        blocked = runtime_kind == "blocked" or release_state == "blocked"
        states[str(name)] = {
            "state": "blocked" if blocked else "ready",
            "package_name": str(model.get("package_name", "")),
            "package_hash": str(model.get("package_hash", "")),
            "release_state": release_state,
            "runtime_kind": runtime_kind,
            "benchmark_gate": dict(model.get("benchmark_gate", {})) if isinstance(model.get("benchmark_gate"), dict) else {},
            "strict_runtime_required": bool(model.get("strict_runtime_required", False)),
        }
    return states


def _build_delivery_summary(
    *,
    manifest: dict[str, Any],
    sync_index: dict[str, Any],
    reconstruction_summary: dict[str, Any],
    assessment_summary: dict[str, Any],
    cobb_measurement: dict[str, Any],
    uca_measurement: dict[str, Any],
    assessment_agreement: dict[str, Any],
) -> dict[str, Any]:
    localization_readiness = dict(manifest.get("localization_readiness", {}))
    review_approval = dict(localization_readiness.get("review_approval", {}))
    sync_summary = dict(sync_index.get("summary", {}))
    runtime_models = dict(reconstruction_summary.get("runtime_models", {}))
    hard_blockers = _unique_strings(
        list(reconstruction_summary.get("hard_blockers", []))
        + list(assessment_summary.get("hard_blockers", []))
        + list(cobb_measurement.get("hard_blockers", []))
        + list(uca_measurement.get("hard_blockers", []))
    )
    manual_review_reasons = _unique_strings(
        list(reconstruction_summary.get("manual_review_reasons", []))
        + list(reconstruction_summary.get("soft_review_reasons", []))
        + list(assessment_summary.get("manual_review_reasons", []))
        + list(assessment_summary.get("soft_review_reasons", []))
        + list(cobb_measurement.get("manual_review_reasons", []))
        + list(uca_measurement.get("manual_review_reasons", []))
        + list(assessment_agreement.get("manual_review_reasons", []))
        + list(localization_readiness.get("warnings", []))
    )
    return {
        "evidence_tier": "fixture_research",
        "prototype_scope": "offline_research_prototype",
        "non_clinical_statement": "Fixture/mock evidence only; no live/HIL or clinical readiness claim is made.",
        "claim_boundary": {
            "live_hil_closed": False,
            "clinical_ready": False,
            "clinical_claim": "none",
            "authoritative_scope": "repository_fixture_replay",
        },
        "manual_review": {
            "required": bool(localization_readiness.get("review_required", False)),
            "approved": bool(review_approval.get("approved", False)),
            "operator_id": str(review_approval.get("operator_id", "")),
            "reason": str(review_approval.get("reason", "")),
        },
        "sync": {
            "frame_count": int(sync_summary.get("frame_count", 0) or 0),
            "reconstructable_count": int(sync_summary.get("reconstructable_count", 0) or 0),
            "pose_valid_count": int(sync_summary.get("pose_valid_count", 0) or 0),
            "usable_ratio": float(sync_summary.get("usable_ratio", 0.0) or 0.0),
        },
        "reconstruction": {
            "status": str(reconstruction_summary.get("reconstruction_status", "")),
            "selected_row_count": int(reconstruction_summary.get("selected_row_count", 0) or 0),
            "point_count": int(reconstruction_summary.get("point_count", 0) or 0),
            "confidence": float(reconstruction_summary.get("confidence", 0.0) or 0.0),
            "closure_verdict": str(reconstruction_summary.get("closure_verdict", "")),
        },
        "assessment": {
            "cobb_angle_deg": float(cobb_measurement.get("angle_deg", assessment_summary.get("cobb_angle_deg", 0.0)) or 0.0),
            "cobb_confidence": float(cobb_measurement.get("confidence", assessment_summary.get("confidence", 0.0)) or 0.0),
            "cobb_measurement_source": str(cobb_measurement.get("measurement_source", "")),
            "uca_angle_deg": float(uca_measurement.get("angle_deg", assessment_summary.get("uca_angle_deg", 0.0)) or 0.0),
            "agreement_status": str(assessment_agreement.get("agreement_status", "")),
        },
        "models": _model_readiness(runtime_models),
        "hard_blockers": hard_blockers,
        "manual_review_reasons": manual_review_reasons,
    }


def build_session_report(service, session_dir: Path) -> Path:
    manifest = service.exp_manager.load_manifest(session_dir)
    summary = service._read_json(session_dir / "export" / "summary.json")
    quality_timeline = service._read_json(session_dir / "derived/quality/quality_timeline.json")
    replay_index = service._read_json(session_dir / "replay/replay_index.json")
    alarms = service._read_json(session_dir / "derived/alarms/alarm_timeline.json")
    sync_index = service._read_json(session_dir / "derived/sync/frame_sync_index.json")
    pressure_timeline = service._read_json(session_dir / "derived/pressure/pressure_sensor_timeline.json")
    ultrasound_metrics = service._read_json(session_dir / "derived/ultrasound/ultrasound_frame_metrics.json")
    pressure_analysis = service._read_json(session_dir / "export/pressure_analysis.json")
    ultrasound_analysis = service._read_json(session_dir / "export/ultrasound_analysis.json")
    reconstruction_summary = service._read_json(session_dir / "derived" / "reconstruction" / "reconstruction_summary.json")
    assessment_summary = service._read_json(session_dir / "derived" / "assessment" / "assessment_summary.json")
    cobb_resolution = service.authoritative_artifact_reader.read_cobb_measurement(session_dir)
    cobb_measurement = dict(cobb_resolution.get("effective_payload", {}))
    uca_measurement = service._read_json(session_dir / "derived" / "assessment" / "uca_measurement.json")
    assessment_agreement = service._read_json(session_dir / "derived" / "assessment" / "assessment_agreement.json")
    journal_entries = service._read_jsonl(session_dir / "raw" / "ui" / "command_journal.jsonl")
    annotations = service._read_jsonl(session_dir / "raw" / "ui" / "annotations.jsonl")
    delivery_summary = _build_delivery_summary(
        manifest=manifest,
        sync_index=sync_index,
        reconstruction_summary=reconstruction_summary,
        assessment_summary=assessment_summary,
        cobb_measurement=cobb_measurement,
        uca_measurement=uca_measurement,
        assessment_agreement=assessment_agreement,
    )
    payload = {
        "generated_at": now_text(),
        "experiment_id": manifest["experiment_id"],
        "session_id": manifest["session_id"],
        "session_overview": {"core_state": summary.get("core_state", "UNKNOWN"), "software_version": manifest.get("software_version", ""), "build_id": manifest.get("build_id", ""), "force_sensor_provider": manifest.get("force_sensor_provider", ""), "robot_model": manifest.get("robot_profile", {}).get("robot_model", ""), "sdk_robot_class": manifest.get("robot_profile", {}).get("sdk_robot_class", ""), "axis_count": manifest.get("robot_profile", {}).get("axis_count", 0)},
        "workflow_trace": {**summary.get("workflow", {}), "patient_registration": manifest.get("patient_registration", {}), "scan_protocol": manifest.get("scan_protocol", {})},
        "safety_summary": {**summary.get("safety", {}), "alarms": alarms.get("summary", {}), "safety_thresholds": manifest.get("safety_thresholds", {}), "contact_force_policy": manifest.get("robot_profile", {}).get("clinical_scan_contract", {}).get("contact_force_policy", {})},
        "recording": summary.get("recording", {}),
        "quality_summary": {**quality_timeline.get("summary", {}), "annotation_count": len(annotations), "usable_sync_ratio": sync_index.get("summary", {}).get("usable_ratio", 0.0)},
        "ultrasound_summary": {**ultrasound_metrics.get("summary", {}), "analysis": ultrasound_analysis.get("summary", {})},
        "pressure_summary": {**pressure_timeline.get("summary", {}), "analysis": pressure_analysis.get("summary", {})},
        "operator_actions": {"command_count": len(journal_entries), "latest_command": journal_entries[-1].get("data", {}).get("command", "") if journal_entries else "", "annotation_count": len(annotations)},
        "closure": {"runtime_profile": reconstruction_summary.get("runtime_profile", assessment_summary.get("runtime_profile", "weighted_runtime")), "profile_release_state": reconstruction_summary.get("profile_release_state", assessment_summary.get("profile_release_state", "research_validated")), "closure_mode": reconstruction_summary.get("closure_mode", assessment_summary.get("closure_mode", "runtime_optional")), "profile_config_path": reconstruction_summary.get("profile_config_path", assessment_summary.get("profile_config_path", "")), "profile_load_error": reconstruction_summary.get("profile_load_error", assessment_summary.get("profile_load_error", "")), "closure_verdict": assessment_summary.get("closure_verdict", reconstruction_summary.get("closure_verdict", "blocked")), "provenance_purity": assessment_summary.get("provenance_purity", reconstruction_summary.get("provenance_purity", "blocked")), "source_contamination_flags": assessment_summary.get("source_contamination_flags", reconstruction_summary.get("source_contamination_flags", [])), "hard_blockers": assessment_summary.get("hard_blockers", reconstruction_summary.get("hard_blockers", [])), "soft_review_reasons": assessment_summary.get("soft_review_reasons", reconstruction_summary.get("soft_review_reasons", []))},
        "reconstruction_summary": reconstruction_summary,
        "assessment_summary": assessment_summary,
        "delivery_summary": delivery_summary,
        "cobb_measurement": cobb_measurement,
        "uca_measurement": uca_measurement,
        "assessment_agreement": assessment_agreement,
        "devices": {**manifest.get("device_health_snapshot", {}), "device_readiness": manifest.get("device_readiness", {}), "robot_profile": manifest.get("robot_profile", {})},
        "outputs": manifest.get("artifact_registry", {}),
        "replay": {"camera_frames": replay_index.get("streams", {}).get("camera", {}).get("frame_count", 0), "ultrasound_frames": replay_index.get("streams", {}).get("ultrasound", {}).get("frame_count", 0), "synced_frames": sync_index.get("summary", {}).get("frame_count", 0), "timeline_points": len(replay_index.get("timeline", [])), "pressure_samples": pressure_timeline.get("summary", {}).get("sample_count", 0), "ultrasound_metric_frames": ultrasound_metrics.get("summary", {}).get("frame_count", 0)},
        "algorithm_versions": {plugin.stage: plugin.plugin_version for plugin in service.plugins.all_plugins()},
        "open_issues": [],
    }
    return service.exp_manager.save_json_artifact(session_dir, "export/session_report.json", payload)


def build_session_compare(service, session_dir: Path) -> Path:
    payload = service.analytics.compare_session(session_dir)
    return service.exp_manager.save_json_artifact(session_dir, "export/session_compare.json", payload)


def build_session_trends(service, session_dir: Path) -> Path:
    payload = service.analytics.trend_summary(session_dir)
    return service.exp_manager.save_json_artifact(session_dir, "export/session_trends.json", payload)


def build_diagnostics_pack(service, session_dir: Path) -> Path:
    payload = service.diagnostics_service.build(session_dir)
    return service.exp_manager.save_json_artifact(session_dir, "export/diagnostics_pack.json", payload)


def build_qa_pack(service, session_dir: Path) -> Path:
    payload = service.qa_pack_service.build(session_dir)
    return service.exp_manager.save_json_artifact(session_dir, "export/qa_pack.json", payload)
