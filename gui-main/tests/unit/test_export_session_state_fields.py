from __future__ import annotations

import json

from robot_sim.application.services.export_service import ExportService
from robot_sim.domain.enums import AppExecutionState
from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.session_state import SessionState


def test_export_service_persists_task_and_state_fields(tmp_path):
    service = ExportService(tmp_path)
    state = SessionState(
        playback=PlaybackState(frame_idx=2, total_frames=10, speed_multiplier=1.5, loop_enabled=True),
        app_state=AppExecutionState.PLAYING,
        active_task_id='task-123',
        active_task_kind='playback',
        scene_revision=5,
        warnings=('warn-a',),
        last_warning='warn-a',
    )
    path = service.save_session('session.json', state)
    payload = json.loads(path.read_text(encoding='utf-8'))

    assert payload['app_state'] == 'playing'
    assert payload['active_task_id'] == 'task-123'
    assert payload['scene_revision'] == 5
    assert payload['warnings'] == ['warn-a']
    assert payload['manifest']['producer_version']
