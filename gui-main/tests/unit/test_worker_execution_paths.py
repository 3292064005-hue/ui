from __future__ import annotations

import numpy as np

from robot_sim.application.dto import FKRequest, IKRequest, TrajectoryRequest
from robot_sim.application.services.playback_service import PlaybackService
from robot_sim.application.workers.benchmark_worker import BenchmarkWorker
from robot_sim.application.workers.export_worker import ExportWorker
from robot_sim.application.workers.fk_worker import FKWorker
from robot_sim.application.workers.ik_worker import IKWorker
from robot_sim.application.workers.playback_worker import PlaybackWorker
from robot_sim.application.workers.screenshot_worker import ScreenshotWorker
from robot_sim.application.workers.trajectory_worker import TrajectoryWorker
from robot_sim.model.pose import Pose
from robot_sim.model.solver_config import IKConfig
from robot_sim.model.trajectory import JointTrajectory


def _trajectory() -> JointTrajectory:
    t = np.array([0.0, 0.1, 0.2], dtype=float)
    q = np.array([[0.0, 0.0], [0.2, 0.1], [0.4, 0.2]], dtype=float)
    qd = np.zeros_like(q)
    qdd = np.zeros_like(q)
    ee = np.array([[0.0, 0.0, 0.0], [0.1, 0.0, 0.0], [0.2, 0.0, 0.0]], dtype=float)
    return JointTrajectory(t=t, q=q, qd=qd, qdd=qdd, ee_positions=ee)


class _FKUseCase:
    def execute(self, request):
        return {'q': request.q.tolist()}


class _IKUseCase:
    def execute(self, request, cancel_flag=None, progress_cb=None):
        if progress_cb is not None:
            progress_cb({'iter': 1})
        return type('Result', (), {'message': 'ok'})()


class _TrajectoryUseCase:
    def __init__(self, result):
        self.result = result

    def execute(self, request):
        return self.result


class _BenchmarkUseCase:
    def execute(self, spec, config, cases=None):
        return {'spec': spec, 'config': config, 'cases': cases}


class _FailingUseCase:
    def execute(self, *args, **kwargs):
        raise RuntimeError('boom')


def test_fk_worker_uses_structured_emit(planar_spec):
    worker = FKWorker(FKRequest(planar_spec, np.zeros(2, dtype=float)), _FKUseCase())
    finished = []
    worker.finished.connect(finished.append)
    worker.run()
    assert worker.state == 'succeeded'
    assert finished[0] == {'q': [0.0, 0.0]}


def test_ik_worker_emits_progress_and_finishes(planar_spec):
    target = Pose(p=np.array([1.0, 0.0, 0.0]), R=np.eye(3))
    worker = IKWorker(IKRequest(planar_spec, target, np.zeros(2, dtype=float), IKConfig()), _IKUseCase())
    progress = []
    worker.progress.connect(progress.append)
    worker.run()
    assert worker.state == 'succeeded'
    assert progress and progress[0] == {'iter': 1}


def test_trajectory_worker_finishes_with_trajectory(planar_spec):
    traj = _trajectory()
    request = TrajectoryRequest(q_start=np.zeros(2), q_goal=np.ones(2), duration=1.0, dt=0.1, spec=planar_spec)
    worker = TrajectoryWorker(request, _TrajectoryUseCase(traj))
    finished = []
    worker.finished.connect(finished.append)
    worker.run()
    assert worker.state == 'succeeded'
    assert finished[0] is traj


def test_benchmark_worker_happy_path(planar_spec):
    worker = BenchmarkWorker(planar_spec, {'runs': 1}, _BenchmarkUseCase())
    finished = []
    worker.finished.connect(finished.append)
    worker.run()
    assert worker.state == 'succeeded'
    assert finished[0]['config'] == {'runs': 1}


def test_playback_worker_emits_frames_until_completion():
    traj = _trajectory()
    service = PlaybackService()
    state = service.build_state(traj, frame_idx=0)
    worker = PlaybackWorker(traj, state, service, frame_interval_ms=1)
    frames = []
    finished = []
    worker.progress.connect(frames.append)
    worker.finished.connect(finished.append)
    worker.run()
    assert worker.state == 'succeeded'
    assert [frame.frame_idx for frame in frames] == [0, 1, 2]
    assert finished[0].frame_idx == 2


def test_export_and_screenshot_workers_finish():
    export_worker = ExportWorker(lambda: 'archive.zip')
    screenshot_worker = ScreenshotWorker(lambda: 'shot.png')
    export_finished = []
    screenshot_finished = []
    export_worker.finished.connect(export_finished.append)
    screenshot_worker.finished.connect(screenshot_finished.append)
    export_worker.run()
    screenshot_worker.run()
    assert export_worker.state == 'succeeded'
    assert screenshot_worker.state == 'succeeded'
    assert export_finished == ['archive.zip']
    assert screenshot_finished == ['shot.png']


def test_workers_surface_failures(planar_spec):
    fk_worker = FKWorker(FKRequest(planar_spec, np.zeros(2, dtype=float)), _FailingUseCase())
    trajectory_worker = TrajectoryWorker(
        TrajectoryRequest(q_start=np.zeros(2), q_goal=np.ones(2), duration=1.0, dt=0.1, spec=planar_spec),
        _FailingUseCase(),
    )
    benchmark_worker = BenchmarkWorker(planar_spec, {}, _FailingUseCase())
    for worker in (fk_worker, trajectory_worker, benchmark_worker):
        messages = []
        worker.failed.connect(messages.append)
        worker.run()
        assert worker.state == 'failed'
        assert messages == ['boom']
