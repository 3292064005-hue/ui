# Fixture Delivery Traceability Matrix

| Item | Status | Evidence tier | Artifacts |
| --- | --- | --- | --- |
| d435i_rgbd_guidance | delivered_fixture | fixture_research | derived/sync/source_frame_set.json<br>derived/guidance/body_surface.json<br>derived/guidance/guidance_targets.json |
| calibration_freeze | delivered_fixture | fixture_research | meta/calibration_bundle.json<br>meta/localization_freeze.json |
| path_planning | delivered_fixture | fixture_research | meta/scan_plan.json<br>derived/preview/scan_protocol.json |
| pressure_feedback | delivered_fixture | fixture_research | derived/pressure/pressure_sensor_timeline.json<br>export/pressure_analysis.json |
| continuous_ultrasound_capture | delivered_fixture | fixture_research | raw/ultrasound/index.jsonl<br>derived/ultrasound/ultrasound_frame_metrics.json<br>export/ultrasound_analysis.json |
| multimodal_sync | delivered_fixture | fixture_research | derived/sync/frame_sync_index.json<br>derived/reconstruction/reconstruction_input_index.json |
| anatomy_models | delivered_fixture | fixture_research | derived/reconstruction/bone_mask.npz<br>derived/reconstruction/frame_anatomy_points.json<br>derived/reconstruction/lamina_candidates.json |
| vpi_reconstruction | delivered_fixture | fixture_research | derived/reconstruction/coronal_vpi.npz<br>derived/reconstruction/vpi_preview.png<br>derived/reconstruction/reconstruction_summary.json |
| cobb_assessment | delivered_fixture | fixture_research | derived/assessment/cobb_measurement.json<br>derived/assessment/uca_measurement.json<br>derived/assessment/assessment_summary.json |
| ui_report_export | delivered_fixture | fixture_research | export/summary.txt<br>export/session_report.json |
| live_hil_boundary | open_live_hil_gap | not_claimed | docs/05_verification/CURRENT_KNOWN_GAPS.md |
