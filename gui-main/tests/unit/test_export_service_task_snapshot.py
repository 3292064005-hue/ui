from __future__ import annotations

import json
from datetime import datetime, timezone

from robot_sim.domain.enums import AppExecutionState, TaskState
from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.session_state import SessionState
from robot_sim.model.task_snapshot import TaskSnapshot
from robot_sim.application.services.export_service import ExportService


def test_export_service_persists_task_snapshot_and_correlation_id(tmp_path):
    service = ExportService(tmp_path)
    snapshot = TaskSnapshot(
        task_id="task-1",
        task_kind="benchmark",
        task_state=TaskState.RUNNING,
        progress_stage="solve",
        progress_percent=42.0,
        message="running",
        correlation_id="corr-123",
        started_at=datetime.now(timezone.utc),
        finished_at=None,
        stop_reason="",
    )
    state = SessionState(
        playback=PlaybackState(),
        app_state=AppExecutionState.IDLE,
        active_task_id="task-1",
        active_task_kind="benchmark",
        active_task_snapshot=snapshot,
    )
    path = service.save_session("session.json", state)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["manifest"]["correlation_id"] == "corr-123"
    assert payload["active_task_snapshot"]["task_id"] == "task-1"
    assert payload["active_task_snapshot"]["correlation_id"] == "corr-123"
