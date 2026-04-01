from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from robot_sim.application.services.metrics_service import MetricsService
from robot_sim.application.use_cases.plan_waypoint_trajectory import PlanWaypointTrajectoryUseCase
from robot_sim.core.collision.broad_phase import AABB, aabb_from_points, broad_phase_intersections
from robot_sim.domain.enums import TaskState
from robot_sim.infra.logging_setup import setup_logging
from robot_sim.infra.profiler import timed
from robot_sim.infra.yaml_loader import load_yaml
from robot_sim.model.ik_result import IKIterationLog, IKResult
from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.session_state import SessionState
from robot_sim.model.state import SessionState as SessionStateAlias
from robot_sim.model.task_snapshot import TaskSnapshot


class _WaypointPlanner:
    def __init__(self):
        self.requests = []

    def plan(self, req):
        self.requests.append(req)
        return {'planned': True, 'req': req}


class _PlannerRegistry:
    def __init__(self):
        self.planner = _WaypointPlanner()

    def get(self, name: str):
        assert name == 'waypoint_graph'
        return self.planner


class _Scene:
    revision = 3
    obstacles = ('box-1', 'box-2')
    collision_backend = 'capsule'
    collision_level = type('Level', (), {'value': 'capsule'})()
    attached_objects = ('tool',)


def test_metrics_service_summarizes_ik_batch_task_and_scene():
    service = MetricsService()
    logs = (
        IKIterationLog(
            iter_idx=0,
            pos_err_norm=0.2,
            ori_err_norm=0.3,
            cond_number=12.0,
            manipulability=0.5,
            dq_norm=0.1,
            elapsed_ms=4.0,
            effective_mode='dls',
            damping_lambda=0.02,
        ),
    )
    result = IKResult(
        success=True,
        q_sol=np.array([0.1, 0.2]),
        logs=logs,
        message='ok',
        final_pos_err=float('nan'),
        final_ori_err=float('nan'),
        final_cond=float('nan'),
        final_manipulability=float('nan'),
        final_dq_norm=float('nan'),
        elapsed_ms=0.0,
        restarts_used=2,
        stop_reason='converged',
        diagnostics={'damping_lambda': 0.02},
    )
    summary = service.summarize_ik(result)
    assert summary['final_pos_err'] == 0.2
    assert summary['final_ori_err'] == 0.3
    assert summary['final_cond'] == 12.0
    assert summary['final_manipulability'] == 0.5
    assert summary['final_dq_norm'] == 0.1
    assert summary['elapsed_ms'] == 4.0
    assert summary['effective_mode'] == 'dls'
    assert summary['final_damping'] == 0.02

    batch = service.summarize_batch([result, result])
    assert batch['count'] == 2.0
    assert batch['success_rate'] == 1.0
    assert batch['mean_restarts_used'] == 2.0

    snapshot = TaskSnapshot(
        task_id='task-1',
        task_kind='ik',
        task_state=TaskState.RUNNING,
        progress_stage='iterating',
        progress_percent=40.0,
        message='running',
        correlation_id='corr-1',
    )
    task_summary = service.summarize_task(snapshot)
    assert task_summary['task_state'] == 'running'
    assert task_summary['progress_percent'] == 40.0
    assert service.summarize_task(None)['task_state'] == 'idle'

    scene_summary = service.summarize_scene(_Scene())
    assert scene_summary['revision'] == 3
    assert scene_summary['obstacle_count'] == 2
    assert scene_summary['attached_objects'] == 1
    assert service.summarize_scene(None)['collision_backend'] == 'none'


def test_logging_setup_yaml_loader_profiler_and_state_alias(tmp_path: Path, monkeypatch):
    calls: list[object] = []
    monkeypatch.setattr(logging, 'basicConfig', lambda **kwargs: calls.append(('basic', kwargs)))
    monkeypatch.setattr(logging.config, 'dictConfig', lambda cfg: calls.append(('dict', cfg)))

    setup_logging(None)
    assert calls[0][0] == 'basic'

    missing_path = tmp_path / 'missing.yaml'
    setup_logging(missing_path)
    assert calls[1][0] == 'basic'

    yaml_path = tmp_path / 'logging.yaml'
    yaml_path.write_text('version: 1\nhandlers: {}\nroot: {level: INFO, handlers: []}\n', encoding='utf-8')
    setup_logging(yaml_path)
    assert calls[2][0] == 'dict'
    assert load_yaml(yaml_path)['version'] == 1

    with timed() as payload:
        pass
    assert payload['elapsed_s'] >= 0.0

    assert SessionStateAlias is SessionState


def test_broad_phase_exports_and_waypoint_use_case():
    a = aabb_from_points(np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]], dtype=float))
    b = AABB(minimum=np.array([0.5, 0.5, 0.5]), maximum=np.array([1.5, 1.5, 1.5]))
    c = AABB(minimum=np.array([2.0, 2.0, 2.0]), maximum=np.array([3.0, 3.0, 3.0]))
    pairs = broad_phase_intersections((a, b, c))
    assert pairs == [(0, 1)]

    registry = _PlannerRegistry()
    req = object()
    result = PlanWaypointTrajectoryUseCase(registry).execute(req)
    assert result['planned'] is True
    assert registry.planner.requests == [req]


def test_playback_state_stop_and_pause():
    state = PlaybackState(is_playing=True, frame_idx=1, total_frames=3, speed_multiplier=2.0)
    assert state.pause().is_playing is False
    assert state.stop().is_playing is False
