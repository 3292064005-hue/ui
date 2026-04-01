from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np

from robot_sim.domain.enums import TaskState
from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.session_state import SessionState
from robot_sim.model.task_snapshot import TaskSnapshot
from robot_sim.presentation.main_window_actions import MainWindowActionMixin
from robot_sim.presentation.main_window_tasks import MainWindowTaskMixin
from robot_sim.presentation.main_window_ui import MainWindowUIMixin
from robot_sim.presentation.state_store import StateStore


class DummySignal:
    def __init__(self):
        self.connected = []

    def connect(self, callback):
        self.connected.append(callback)


class ValueWidget:
    def __init__(self, value=None, checked=False, text=''):
        self._value = value
        self._checked = checked
        self._text = text
        self.clicked = DummySignal()
        self.valueChanged = DummySignal()
        self.toggled = DummySignal()

    def value(self):
        return self._value

    def isChecked(self):
        return self._checked

    def currentText(self):
        return self._text


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


class DummyDiagnosticsPanel:
    def __init__(self):
        self.values = None

    def set_values(self, **kwargs):
        self.values = kwargs


class DummyBenchmarkPanel:
    def __init__(self):
        self.summary = DummySummary()
        self.log = SimpleNamespace(clear=lambda: None)
        self.run_btn = ValueWidget()
        self.export_btn = ValueWidget()
        self.running = None
        self.report = None

    def set_running(self, running):
        self.running = running

    def set_report(self, report):
        self.report = report


class DummySolverPanel:
    def __init__(self):
        self.mode_combo = ValueWidget(text='dls')
        self.max_iters = ValueWidget(value=50)
        self.step_scale = ValueWidget(value=0.5)
        self.damping = ValueWidget(value=0.1)
        self.enable_nullspace = ValueWidget(checked=True)
        self.position_only = ValueWidget(checked=False)
        self.pos_tol = ValueWidget(value=1e-3)
        self.ori_tol = ValueWidget(value=1e-3)
        self.max_step_norm = ValueWidget(value=0.2)
        self.auto_fallback = ValueWidget(checked=True)
        self.reachability_precheck = ValueWidget(checked=True)
        self.retry_count = ValueWidget(value=2)
        self.joint_limit_weight = ValueWidget(value=0.2)
        self.manipulability_weight = ValueWidget(value=0.1)
        self.orientation_weight = ValueWidget(value=1.0)
        self.adaptive_damping = ValueWidget(checked=True)
        self.weighted_ls = ValueWidget(checked=False)
        self.run_fk_btn = ValueWidget()
        self.run_ik_btn = ValueWidget()
        self.cancel_btn = ValueWidget()
        self.plan_btn = ValueWidget()
        self.traj_duration = ValueWidget(value=3.0)
        self.traj_dt = ValueWidget(value=0.1)
        self.traj_mode = ValueWidget(text='joint_space')
        self.running = None

    def set_running(self, running):
        self.running = running

    def apply_defaults(self, *_args, **_kwargs):
        return None

    def apply_trajectory_defaults(self, *_args, **_kwargs):
        return None


class DummyPlaybackPanel:
    def __init__(self):
        self.play_btn = ValueWidget()
        self.pause_btn = ValueWidget()
        self.stop_btn = ValueWidget()
        self.step_btn = ValueWidget()
        self.slider = ValueWidget(value=0)
        self.speed = ValueWidget(value=1.0)
        self.loop = ValueWidget(checked=False)
        self.export_btn = ValueWidget()
        self.session_btn = ValueWidget()
        self.package_btn = ValueWidget()
        self.running = None
        self.frame = None
        self.total = None

    def set_running(self, running):
        self.running = running

    def set_total_frames(self, total):
        self.total = total

    def set_frame(self, frame, total):
        self.frame = (frame, total)


class DummyRobotPanel:
    def __init__(self):
        self.load_button = ValueWidget()
        self.save_button = ValueWidget()
        self.spec = None

    def selected_robot_name(self):
        return 'planar_2dof'

    def edited_home_q(self):
        return [0.1, 0.2]

    def edited_rows(self):
        return []

    def set_robot_spec(self, spec):
        self.spec = spec


class DummyTargetPanel:
    def __init__(self):
        self.fill_current_btn = ValueWidget()
        self.orientation_mode = ValueWidget(text='rvec')
        self.pose = None

    def values6(self):
        return [1, 2, 3, 0, 0, 0]

    def set_from_pose(self, pose):
        self.pose = pose


class DummySceneToolbar:
    def __init__(self):
        self.fit_requested = DummySignal()
        self.clear_path_requested = DummySignal()
        self.screenshot_requested = DummySignal()
        self.target_axes_toggled = DummySignal()
        self.trajectory_toggled = DummySignal()


class DummySceneWidget:
    def __init__(self):
        self.fit_called = False
        self.trajectory_cleared = False
        self.target_axes_visible = None
        self.trajectory_visible = None

    def fit_camera(self):
        self.fit_called = True

    def clear_trajectory(self):
        self.trajectory_cleared = True

    def set_target_axes_visible(self, visible):
        self.target_axes_visible = visible

    def set_trajectory_visible(self, visible):
        self.trajectory_visible = visible

    def capture_screenshot(self, _path):
        return 'capture.png'


class DummySceneController:
    def __init__(self):
        self.reset_called = False
        self.fk_updates = []
        self.playback_updates = []
        self.trajectory_points = None
        self.cleared = False

    def reset_path(self):
        self.reset_called = True

    def update_fk_projection(self, *args, **kwargs):
        self.fk_updates.append((args, kwargs))

    def update_playback_projection(self, *args, **kwargs):
        self.playback_updates.append((args, kwargs))

    def set_trajectory_from_fk_samples(self, points):
        self.trajectory_points = np.asarray(points)

    def clear_transient_visuals(self):
        self.cleared = True


class DummyPlotsManager:
    def __init__(self):
        self.actions = []

    def clear(self, name):
        self.actions.append(('clear', name))

    def set_curve(self, panel, name, x, y):
        self.actions.append(('curve', panel, name, len(x), len(y)))

    def set_cursor(self, panel, value):
        self.actions.append(('cursor', panel, value))


class DummyThreader:
    def __init__(self):
        self.cancelled = False
        self.stopped = False
        self.started = None
        self.task_state_changed = DummySignal()

    def cancel(self):
        self.cancelled = True

    def stop(self, wait=False):
        self.stopped = True
        self.wait = wait

    def start(self, **kwargs):
        self.started = kwargs
        return SimpleNamespace(task_id='task-1', task_kind=kwargs.get('task_kind', 'unknown'))


class DummyPlaybackService:
    def build_state(self, *_args, **_kwargs):
        return PlaybackState(is_playing=False, frame_idx=0, total_frames=2, speed_multiplier=1.0, loop_enabled=False)


class DummyMetricsService:
    def summarize_ik(self, _result):
        return {
            'iterations': 3,
            'final_pos_err': 1e-4,
            'final_ori_err': 2e-4,
            'final_cond': 10.0,
            'final_manipulability': 0.2,
            'final_dq_norm': 0.05,
            'effective_mode': 'dls',
            'final_damping': 0.1,
            'stop_reason': 'converged',
            'elapsed_ms': 5.0,
        }

    def summarize_trajectory(self, _traj):
        return {'mode': 'joint_space', 'num_samples': 2, 'duration': 1.0, 'feasible': True, 'path_length': 1.0, 'jerk_proxy': 0.0}

    def summarize_benchmark(self, report):
        return {'num_cases': report.num_cases, 'success_rate': report.success_rate, 'p95_elapsed_ms': 1.0, 'mean_restarts_used': 0.0}


@dataclass
class DummyErrorPresentation:
    title: str = 'Err'
    user_message: str = 'boom'
    log_payload: dict[str, object] = None


class DummyTaskErrorMapper:
    def map_exception(self, _exc):
        return DummyErrorPresentation(log_payload={})


class DummyController:
    def __init__(self):
        self.state_store = StateStore(SessionState())
        self.state_store.patch(playback=PlaybackState(is_playing=False, frame_idx=0, total_frames=0, speed_multiplier=1.0, loop_enabled=False))
        self.state_store.patch(robot_spec=SimpleNamespace(label='Planar'), q_current=np.array([0.0, 0.0]))
        self.metrics_service = DummyMetricsService()
        self.playback_service = DummyPlaybackService()
        self.task_error_mapper = DummyTaskErrorMapper()
        self.project_root = '.'
        self.app_config = {'window': {'title': 't', 'width': 100, 'height': 100, 'splitter_sizes': [1, 1, 1], 'vertical_splitter_sizes': [1, 1]}}
        self.ik_uc = object()
        self.traj_uc = object()
        self.benchmark_uc = object()
        self.fk_calls = []
        self.playback_options = []

    @property
    def state(self):
        return self.state_store.state

    def robot_entries(self):
        return ['planar_2dof']

    def solver_defaults(self):
        return {}

    def trajectory_defaults(self):
        return {}

    def load_robot(self, _name):
        pose = SimpleNamespace(p=np.array([1.0, 2.0, 3.0]))
        fk = SimpleNamespace(ee_pose=pose, joint_positions=np.zeros((2, 3)))
        self.state_store.patch(robot_spec=SimpleNamespace(label='Planar'), fk_result=fk)
        return fk

    def save_current_robot(self, **_kwargs):
        return 'robot.yaml'

    def run_fk(self, q=None):
        self.fk_calls.append(q)
        pose = SimpleNamespace(p=np.array([1.0, 2.0, 3.0]))
        fk = SimpleNamespace(ee_pose=pose, joint_positions=np.zeros((2, 3)))
        self.state_store.patch(fk_result=fk)
        return fk

    def build_ik_request(self, values, **kwargs):
        return SimpleNamespace(target=values, config=SimpleNamespace(mode=SimpleNamespace(value='dls')), q0=np.array([0.0, 0.0]))

    def apply_ik_result(self, _req, result):
        self.state_store.patch(ik_result=result, fk_result=self.run_fk(q=result.q_sol))

    def build_trajectory_request(self, **kwargs):
        return SimpleNamespace(**kwargs)

    def apply_trajectory(self, traj):
        self.state_store.patch(trajectory=traj, playback=PlaybackState(is_playing=False, frame_idx=0, total_frames=traj.t.shape[0], speed_multiplier=1.0, loop_enabled=False))

    def sample_ee_positions(self, _q):
        return np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])

    def build_benchmark_config(self, **kwargs):
        return kwargs

    def set_playback_options(self, **kwargs):
        self.playback_options.append(kwargs)
        pb = self.state.playback
        speed = kwargs.get('speed_multiplier', pb.speed_multiplier)
        loop = kwargs.get('loop_enabled', pb.loop_enabled)
        self.state_store.patch(playback=PlaybackState(is_playing=pb.is_playing, frame_idx=pb.frame_idx, total_frames=pb.total_frames, speed_multiplier=speed, loop_enabled=loop))

    def next_playback_frame(self):
        return SimpleNamespace(frame_idx=1, t=0.5, q=np.array([0.2, 0.1]), qd=np.array([0.0, 0.0]), qdd=np.array([0.0, 0.0]), joint_positions=np.zeros((2, 3)), ee_position=np.array([1, 0, 0]))

    def set_playback_frame(self, idx):
        return SimpleNamespace(frame_idx=idx, t=0.5, q=np.array([0.2, 0.1]), qd=np.array([0.0, 0.0]), qdd=np.array([0.0, 0.0]), joint_positions=np.zeros((2, 3)), ee_position=np.array([1, 0, 0]))

    def export_trajectory(self):
        return 'trajectory.csv'

    def export_trajectory_metrics(self, _name, _metrics):
        return 'trajectory_metrics.json'

    def export_session(self):
        return 'session.json'

    def export_package(self):
        return 'package.zip'

    def export_benchmark(self):
        return 'benchmark.json'

    def export_benchmark_cases_csv(self):
        return 'benchmark.csv'


class DummyWindow(MainWindowTaskMixin, MainWindowActionMixin, MainWindowUIMixin):
    def __init__(self):
        self.controller = DummyController()
        self.metrics_service = self.controller.metrics_service
        self.runtime_facade = self.controller
        self.robot_facade = SimpleNamespace(
            robot_entries=self.controller.robot_entries,
            load_robot=self.controller.load_robot,
            save_current_robot=self.controller.save_current_robot,
        )
        self.solver_facade = SimpleNamespace(
            ik_use_case=self.controller.ik_uc,
            build_ik_request=self.controller.build_ik_request,
            apply_ik_result=self.controller.apply_ik_result,
            solver_defaults=self.controller.solver_defaults,
        )
        self.trajectory_facade = SimpleNamespace(
            trajectory_use_case=self.controller.traj_uc,
            build_trajectory_request=self.controller.build_trajectory_request,
            apply_trajectory=self.controller.apply_trajectory,
            trajectory_defaults=self.controller.trajectory_defaults,
        )
        self.playback_facade = SimpleNamespace(state=self.controller.state, set_playback_options=self.controller.set_playback_options, next_playback_frame=self.controller.next_playback_frame, set_playback_frame=self.controller.set_playback_frame, ensure_playback_ready=lambda strict=True: None)
        self.benchmark_facade = SimpleNamespace(benchmark_use_case=self.controller.benchmark_uc, build_benchmark_config=self.controller.build_benchmark_config)
        self.export_facade = SimpleNamespace(export_trajectory=self.controller.export_trajectory, export_trajectory_metrics=self.controller.export_trajectory_metrics, export_session=self.controller.export_session, export_package=self.controller.export_package, export_benchmark=self.controller.export_benchmark, export_benchmark_cases_csv=self.controller.export_benchmark_cases_csv)
        self.threader = DummyThreader()
        self.playback_threader = DummyThreader()
        self.window_cfg = self.controller.app_config['window']
        self.robot_panel = DummyRobotPanel()
        self.target_panel = DummyTargetPanel()
        self.solver_panel = DummySolverPanel()
        self.playback_panel = DummyPlaybackPanel()
        self.scene_toolbar = DummySceneToolbar()
        self.scene_widget = DummySceneWidget()
        self.scene_controller = DummySceneController()
        self.status_panel = DummyStatusPanel()
        self.diagnostics_panel = DummyDiagnosticsPanel()
        self.benchmark_panel = DummyBenchmarkPanel()
        self.plots_manager = DummyPlotsManager()
        self.ik_task_coordinator = SimpleNamespace(run=lambda: setattr(self, 'ik_run_called', True))
        self.trajectory_task_coordinator = SimpleNamespace(run=lambda: setattr(self, 'traj_run_called', True))
        self.benchmark_task_coordinator = SimpleNamespace(run=lambda: setattr(self, 'bench_run_called', True))
        self.playback_task_coordinator = SimpleNamespace(play=lambda: setattr(self, 'play_called', True), pause=lambda: setattr(self, 'pause_called', True), stop=lambda: setattr(self, 'stop_called', True))
        self.export_task_coordinator = SimpleNamespace(export_trajectory=lambda: setattr(self, 'export_traj_called', True), export_session=lambda: setattr(self, 'export_session_called', True), export_package=lambda: setattr(self, 'export_package_called', True), export_benchmark=lambda: setattr(self, 'export_bench_called', True))
        self.scene_coordinator = SimpleNamespace(fit=lambda: setattr(self, 'fit_called', True), clear_path=lambda: setattr(self, 'clear_called', True), capture=lambda: setattr(self, 'capture_called', True))
        self.status_coordinator = SimpleNamespace(apply_task_snapshot=lambda snap: self.controller.state_store.patch_task(snap))
        self._pending_ik_request = None
        self._pending_traj_request = None

    def setCentralWidget(self, widget):
        self.central = widget

    def _playback_worker_factory(self, traj):
        return SimpleNamespace(traj=traj)


def test_ui_mixin_helper_methods_and_signal_wiring(monkeypatch):
    from robot_sim.presentation import main_window_ui as ui_mod

    class DummyPanel:
        def __init__(self, *args, **kwargs):
            self.load_button = ValueWidget()
            self.save_button = ValueWidget()
            self.fill_current_btn = ValueWidget()
            self.orientation_mode = ValueWidget(text='rvec')
            self.run_fk_btn = ValueWidget()
            self.run_ik_btn = ValueWidget()
            self.cancel_btn = ValueWidget()
            self.plan_btn = ValueWidget()
            self.play_btn = ValueWidget()
            self.pause_btn = ValueWidget()
            self.stop_btn = ValueWidget()
            self.step_btn = ValueWidget()
            self.slider = ValueWidget()
            self.speed = ValueWidget(value=1.0)
            self.loop = ValueWidget()
            self.export_btn = ValueWidget()
            self.session_btn = ValueWidget()
            self.package_btn = ValueWidget()
            self.fit_requested = DummySignal()
            self.clear_path_requested = DummySignal()
            self.screenshot_requested = DummySignal()
            self.target_axes_toggled = DummySignal()
            self.trajectory_toggled = DummySignal()
            self.run_btn = ValueWidget()
            self.summary = DummySummary()
            self.log = SimpleNamespace(clear=lambda: None)

        def apply_defaults(self, *_a, **_k):
            return None

        def apply_trajectory_defaults(self, *_a, **_k):
            return None

        def set_running(self, *_a, **_k):
            return None

        def values6(self):
            return [1, 2, 3, 0, 0, 0]

        def edited_home_q(self):
            return [0.1, 0.2]

        def edited_rows(self):
            return []

        def selected_robot_name(self):
            return 'planar_2dof'

        def set_robot_spec(self, *_a, **_k):
            return None

        def set_from_pose(self, *_a, **_k):
            return None

        def set_total_frames(self, *_a, **_k):
            return None

        def set_frame(self, *_a, **_k):
            return None

    monkeypatch.setattr(ui_mod, 'RobotConfigPanel', DummyPanel)
    monkeypatch.setattr(ui_mod, 'TargetPosePanel', DummyPanel)
    monkeypatch.setattr(ui_mod, 'SolverPanel', DummyPanel)
    monkeypatch.setattr(ui_mod, 'PlaybackPanel', DummyPanel)
    monkeypatch.setattr(ui_mod, 'BenchmarkPanel', DummyPanel)
    monkeypatch.setattr(ui_mod, 'DiagnosticsPanel', DummyPanel)
    monkeypatch.setattr(ui_mod, 'StatusPanel', DummyPanel)
    monkeypatch.setattr(ui_mod, 'SceneToolbar', DummyPanel)
    monkeypatch.setattr(ui_mod, 'Scene3DWidget', DummySceneWidget)
    monkeypatch.setattr(ui_mod, 'SceneController', lambda widget: DummySceneController())
    monkeypatch.setattr(ui_mod, 'PlotsPanel', DummyPanel)
    monkeypatch.setattr(ui_mod, 'PlotsManager', lambda *_args, **_kwargs: DummyPlotsManager())

    window = DummyWindow()
    window._build_ui()
    window._wire_signals()
    window._wire_task_signals()
    assert hasattr(window, 'central')
    assert window.threader.task_state_changed.connected
    assert window.robot_panel.load_button.clicked.connected


def test_ui_mixin_status_helpers_cover_busy_and_metrics():
    window = DummyWindow()
    assert window._playback_status_text() == '无轨迹'
    window.controller.state_store.patch(playback=PlaybackState(is_playing=True, frame_idx=0, total_frames=2, speed_multiplier=2.0, loop_enabled=False))
    assert '播放中' in window._playback_status_text()
    kwargs = window._build_solver_kwargs()
    assert kwargs['mode'] == 'dls'
    window._set_busy(True, 'ik')
    assert window.controller.state.is_busy is True
    window._set_playback_running(True)
    assert window.playback_panel.running is True
    window._update_diagnostics_from_trajectory({'mode': 'joint', 'feasible': True, 'feasibility_reasons': '', 'path_length': 1.2, 'jerk_proxy': 0.0})
    window._update_diagnostics_from_benchmark({'success_rate': 1.0, 'p95_elapsed_ms': 3.0, 'mean_restarts_used': 0.0})
    window._sync_status_after_snapshot()
    assert window.diagnostics_panel.values is not None


def test_action_mixin_robot_and_export_paths():
    window = DummyWindow()
    window._load_robot_impl('planar_2dof')
    window._save_robot_impl()
    window.on_fill_current_pose()
    window.on_run_fk()
    window._fit_scene_impl()
    window._clear_scene_path_impl()
    window._capture_scene_impl()
    window._export_trajectory_impl()
    window._export_session_impl()
    window._export_package_impl()
    window._export_benchmark_impl()
    assert window.scene_controller.reset_called is True
    assert window.scene_widget.fit_called is True
    assert window.scene_controller.cleared is True
    assert window.status_panel.messages


def test_task_mixin_covers_ik_trajectory_benchmark_and_worker_terminal_paths():
    window = DummyWindow()
    window.on_run_ik()
    assert window.ik_run_called is True
    window._run_ik_impl()
    assert window.threader.started['task_kind'] == 'ik'
    window.on_cancel_ik()
    assert window.threader.cancelled is True
    log = SimpleNamespace(attempt_idx=0, iter_idx=0, pos_err_norm=1e-3, ori_err_norm=2e-3, cond_number=10.0, manipulability=0.1, dq_norm=0.2, effective_mode='dls', damping_lambda=0.1, elapsed_ms=1.0)
    window.on_ik_progress(log)
    result = SimpleNamespace(success=True, q_sol=np.array([0.3, 0.4]), message='ok', logs=[log])
    window.on_ik_finished(result)
    window.on_plan()
    assert window.traj_run_called is True
    window._run_traj_impl()
    assert window.threader.started['task_kind'] == 'trajectory'
    traj = SimpleNamespace(t=np.array([0.0, 1.0]), q=np.array([[0.0, 0.0], [1.0, 1.0]]), qd=np.zeros((2,2)), qdd=np.zeros((2,2)), ee_positions=np.array([[0,0,0],[1,0,0]]))
    window.on_trajectory_finished(traj)
    window.on_run_benchmark()
    assert window.bench_run_called is True
    report = SimpleNamespace(num_cases=2, success_rate=1.0, cases=[{'name': 'a', 'success': True, 'stop_reason': 'ok', 'final_pos_err': 0.0, 'final_ori_err': 0.0}])
    window.on_benchmark_finished(report)
    snap = TaskSnapshot(task_id='x', task_kind='ik', task_state=TaskState.RUNNING)
    window._on_task_state_changed(snap)
    window.on_worker_failed('boom')
    window.on_worker_cancelled()
    assert window.controller.state.active_task_snapshot is snap


def test_action_and_playback_mixins_cover_playback_paths():
    window = DummyWindow()
    traj = SimpleNamespace(t=np.array([0.0, 1.0]), q=np.array([[0.0, 0.0], [1.0, 1.0]]), qd=np.zeros((2,2)), qdd=np.zeros((2,2)))
    window.controller.state_store.patch(trajectory=traj, playback=PlaybackState(is_playing=False, frame_idx=0, total_frames=2, speed_multiplier=1.0, loop_enabled=False))
    window.on_play()
    assert window.play_called is True
    window._play_impl()
    assert window.playback_threader.started['task_kind'] == 'playback'
    window.on_pause()
    assert window.pause_called is True
    window._pause_impl()
    assert window.playback_threader.cancelled is True
    window.on_stop_playback()
    assert window.stop_called is True
    window._stop_playback_impl()
    assert window.playback_threader.stopped is True
    window.on_step()
    window.on_seek_frame(1)
    window.on_playback_speed_changed(1.5)
    window.on_playback_loop_changed(True)
    frame = SimpleNamespace(frame_idx=1, t=0.5, q=np.array([0.2, 0.1]), qd=np.array([0.0, 0.0]), qdd=np.array([0.0, 0.0]), joint_positions=np.zeros((2, 3)), ee_position=np.array([1, 0, 0]))
    window.on_playback_progress(frame)
    window.on_playback_finished(PlaybackState(is_playing=True, frame_idx=1, total_frames=2, speed_multiplier=1.0, loop_enabled=False))
    window.on_playback_cancelled()
    window.on_playback_failed('oops')
    assert window.playback_panel.frame is not None
    assert window.controller.playback_options
