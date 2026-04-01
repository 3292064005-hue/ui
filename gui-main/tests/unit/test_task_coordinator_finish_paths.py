from types import SimpleNamespace

import numpy as np

from robot_sim.presentation.coordinators.benchmark_task_coordinator import BenchmarkTaskCoordinator
from robot_sim.presentation.coordinators.ik_task_coordinator import IKTaskCoordinator
from robot_sim.presentation.coordinators.trajectory_task_coordinator import TrajectoryTaskCoordinator


class DummySummary:
    def __init__(self):
        self.text = ''

    def setText(self, text):
        self.text = text


class DummyStatusPanel:
    def __init__(self):
        self.summary = DummySummary()
        self.metrics = {}
        self.messages = []

    def set_metrics(self, **kwargs):
        self.metrics.update(kwargs)

    def append(self, message):
        self.messages.append(message)


class DummyPlotsManager:
    def __init__(self):
        self.actions = []

    def clear(self, name):
        self.actions.append(('clear', name))

    def set_curve(self, panel, name, x, y):
        self.actions.append(('curve', panel, name, len(x), len(y)))


class DummyWindow:
    def __init__(self):
        self._pending_ik_request = object()
        self.status_panel = DummyStatusPanel()
        self.project_busy_state_calls = []
        self.threader = object()
        self.metrics_service = SimpleNamespace(
            summarize_ik=lambda result: {
                'iterations': 2, 'final_pos_err': 1e-4, 'final_ori_err': 2e-4, 'final_cond': 3.0,
                'final_manipulability': 0.2, 'final_dq_norm': 0.1, 'effective_mode': 'dls',
                'final_damping': 0.1, 'stop_reason': 'converged', 'elapsed_ms': 5.0,
            },
            summarize_trajectory=lambda traj: {'mode': 'joint_space', 'num_samples': 2, 'duration': 1.0, 'feasible': True, 'path_length': 1.0, 'jerk_proxy': 0.0},
            summarize_benchmark=lambda report: {'num_cases': report.num_cases, 'success_rate': report.success_rate, 'p95_elapsed_ms': 1.0, 'mean_restarts_used': 0.0},
        )
        self.scene_controller = SimpleNamespace(
            update_fk_projection=lambda fk, target=None: setattr(self, 'fk_updated', True),
            set_trajectory_from_fk_samples=lambda points: setattr(self, 'traj_points', np.asarray(points)),
        )
        self.solver_facade = SimpleNamespace(apply_ik_result=lambda req, result: None)
        self.trajectory_facade = SimpleNamespace(apply_trajectory=lambda traj: None)
        self.runtime_facade = SimpleNamespace(
            state=SimpleNamespace(trajectory=None),
            state_store=SimpleNamespace(patch=lambda **kwargs: setattr(self, 'patched', kwargs)),
        )
        self.benchmark_facade = SimpleNamespace()
        self.controller = SimpleNamespace(
            state=SimpleNamespace(fk_result=SimpleNamespace(), target_pose=None),
            apply_ik_result=lambda req, result: None,
            apply_trajectory=lambda traj: None,
            state_store=SimpleNamespace(patch=lambda **kwargs: setattr(self, 'patched', kwargs)),
        )
        self.plots_manager = DummyPlotsManager()
        self.playback_panel = SimpleNamespace(set_total_frames=lambda total: setattr(self, 'total_frames', total), set_frame=lambda idx, total: setattr(self, 'frame', (idx, total)))
        self.diagnostics = {}
        self._playback_status_text = lambda: 'idle'
        self._update_diagnostics_from_trajectory = lambda metrics: self.diagnostics.update(metrics)
        self._update_diagnostics_from_benchmark = lambda summary: self.diagnostics.update(summary)
        self.on_seek_frame = lambda idx: setattr(self, 'seek_idx', idx)
        self._playback_frame = None
        self.benchmark_panel = SimpleNamespace(set_report=lambda report: setattr(self, 'bench_report', report))
        self.project_busy_state = lambda busy, reason='': self.project_busy_state_calls.append((busy, reason))
        self.project_ik_result = self._project_ik_result
        self.project_trajectory_result = self._project_trajectory_result
        self.project_benchmark_result = self._project_benchmark_result
        self._projected = []
        self._project_exception = lambda exc, title='错误': self._projected.append((title, str(exc)))

    def _project_ik_result(self, result, summary):
        self.scene_controller.update_fk_projection(self.controller.state.fk_result, self.controller.state.target_pose)
        self.status_panel.summary.setText(
            f"IK {'收敛' if result.success else '失败'} | iters={summary['iterations']} | pos={summary['final_pos_err']:.3e}"
        )
        self.status_panel.set_metrics(
            iterations=summary['iterations'],
            pos_err=f"{summary['final_pos_err']:.4e}",
            ori_err=f"{summary['final_ori_err']:.4e}",
            cond=f"{summary['final_cond']:.4e}",
            manip=f"{summary['final_manipulability']:.4e}",
            dq_norm=f"{summary['final_dq_norm']:.4e}",
            mode=summary['effective_mode'] or '-',
            damping=f"{summary['final_damping']:.3e}",
            stop_reason=summary['stop_reason'] or '-',
            elapsed=f"{summary['elapsed_ms']:.1f}",
            playback=self._playback_status_text(),
        )
        self.status_panel.append(result.message)

    def _project_trajectory_result(self, traj, metrics, ee_points):
        self.playback_panel.set_total_frames(traj.t.shape[0])
        self.playback_panel.set_frame(0, traj.t.shape[0])
        if ee_points is not None and np.asarray(ee_points).size:
            self.scene_controller.set_trajectory_from_fk_samples(np.asarray(ee_points))
        self.status_panel.append(f'轨迹已生成：{traj.q.shape[0]} 个采样点')
        self.status_panel.summary.setText(
            f"轨迹完成 | mode={metrics['mode']} | samples={metrics['num_samples']} | duration={metrics['duration']:.2f}s"
        )
        self.status_panel.set_metrics(playback=self._playback_status_text())
        self._update_diagnostics_from_trajectory(metrics)
        self._playback_frame = 0 if bool(getattr(traj, 'is_playback_ready', False)) else None

    def _project_benchmark_result(self, report, summary):
        self.benchmark_panel.set_report({'num_cases': report.num_cases, 'success_rate': report.success_rate, 'cases': list(report.cases)})
        self._update_diagnostics_from_benchmark(summary)
        self.status_panel.summary.setText(
            f"Benchmark 完成 | cases={summary['num_cases']} | success={summary['success_rate']:.1%}"
        )
        self.status_panel.append('Benchmark 运行完成')


def test_task_coordinator_finish_handlers_update_window_state():
    window = DummyWindow()
    ik_result = SimpleNamespace(success=True, q_sol=np.array([0.1, 0.2]), message='ok', logs=[SimpleNamespace(attempt_idx=0, iter_idx=0, pos_err_norm=1e-3, ori_err_norm=2e-3, cond_number=10.0, manipulability=0.1, dq_norm=0.2)])
    IKTaskCoordinator(window).handle_finished(ik_result)
    traj = SimpleNamespace(
        t=np.array([0.0, 1.0]),
        q=np.array([[0.0, 0.0], [1.0, 1.0]]),
        qd=np.zeros((2,2)),
        qdd=np.zeros((2,2)),
        ee_positions=np.array([[0,0,0],[1,0,0]]),
        is_playback_ready=True,
    )
    TrajectoryTaskCoordinator(window).handle_finished(traj)
    report = SimpleNamespace(num_cases=2, success_rate=1.0, cases=[{'name': 'a'}])
    BenchmarkTaskCoordinator(window).handle_finished(report)
    assert window.status_panel.messages == ['ok', '轨迹已生成：2 个采样点', 'Benchmark 运行完成']
    assert window.total_frames == 2
    assert window.frame == (0, 2)
    assert window._playback_frame == 0
    assert window.bench_report['num_cases'] == 2
