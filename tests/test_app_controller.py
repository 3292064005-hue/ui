import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_app_controller_locks_session_only_when_scan_starts(tmp_path):
    _app()
    backend = MockBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    assert controller.session_service.current_experiment is not None
    assert controller.session_service.current_experiment.session_id == ""
    controller.run_localization()
    controller.generate_path()
    assert controller.workflow_artifacts.preview_plan_ready is True
    assert controller.workflow_artifacts.session_locked is False
    controller.start_scan()
    assert controller.workflow_artifacts.session_locked is True
    assert controller.session_service.current_experiment.session_id
    manifest_path = controller.session_service.current_session_dir / "meta" / "manifest.json"
    assert manifest_path.exists()


def test_app_controller_rolls_back_local_session_if_core_lock_fails(tmp_path):
    class LockFailBackend(MockBackend):
        def send_command(self, command, payload=None):
            if command == "lock_session":
                return ReplyEnvelope(ok=False, message="lock rejected", data={})
            return super().send_command(command, payload)

    _app()
    backend = LockFailBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.start_scan()
    assert controller.workflow_artifacts.session_locked is False
    assert controller.session_service.current_session_dir is None
    assert controller.session_service.current_experiment.session_id == ""
