import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.services.mock_backend import MockBackend


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _call(controller: AppController, name: str, *args, **kwargs) -> None:
    getattr(controller, name)(*args, **kwargs)
    app = QApplication.instance()
    if app is not None:
        for _ in range(12):
            app.processEvents()


def _build_assessed_session(tmp_path: Path) -> Path:
    _app()
    backend = MockBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    _call(controller, "connect_robot")
    _call(controller, "power_on")
    _call(controller, "set_auto_mode")
    _call(controller, "create_experiment")
    _call(controller, "run_localization")
    _call(controller, "approve_localization_review", operator_id="fixture_acceptance")
    _call(controller, "generate_path")
    _call(controller, "start_procedure")
    _call(controller, "safe_retreat")
    _call(controller, "save_results")
    _call(controller, "export_summary")
    _call(controller, "run_preprocess")
    _call(controller, "run_reconstruction")
    _call(controller, "run_assessment")
    assert controller.session_service.current_session_dir is not None
    return controller.session_service.current_session_dir


def test_report_stage_emits_cobb_artifacts(tmp_path: Path) -> None:
    session_dir = _build_assessed_session(tmp_path)
    measurement_path = session_dir / "derived" / "assessment" / "cobb_measurement.json"
    summary_path = session_dir / "derived" / "assessment" / "assessment_summary.json"
    report_path = session_dir / "export" / "session_report.json"
    uca_path = session_dir / "derived" / "assessment" / "uca_measurement.json"
    agreement_path = session_dir / "derived" / "assessment" / "assessment_agreement.json"

    assert measurement_path.exists()
    assert summary_path.exists()
    assert report_path.exists()
    assert uca_path.exists()
    assert agreement_path.exists()

    measurement = json.loads(measurement_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    uca = json.loads(uca_path.read_text(encoding="utf-8"))
    agreement = json.loads(agreement_path.read_text(encoding="utf-8"))

    assert "angle_deg" in measurement
    assert "confidence" in measurement
    assert "requires_manual_review" in measurement
    assert "measurement_source" in measurement
    assert "angle_deg" in uca
    assert "agreement_status" in agreement
    assert report["assessment_summary"]["cobb_angle_deg"] == summary["cobb_angle_deg"]
    assert report["delivery_summary"]["claim_boundary"]["live_hil_closed"] is False
    assert report["delivery_summary"]["claim_boundary"]["clinical_ready"] is False
