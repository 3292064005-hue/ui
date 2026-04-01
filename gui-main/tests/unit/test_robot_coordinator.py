from types import SimpleNamespace

import numpy as np

from robot_sim.presentation.coordinators.robot_coordinator import RobotCoordinator


class DummyWindow:
    def __init__(self):
        pose = SimpleNamespace(p=np.array([1.0, 2.0, 3.0]))
        self._fk = SimpleNamespace(ee_pose=pose)
        self.controller = SimpleNamespace(
            state=SimpleNamespace(robot_spec=SimpleNamespace(label='Planar')),
            load_robot=lambda name: self._fk,
            save_current_robot=lambda **kwargs: 'robot.yaml',
        )
        self.robot_facade = SimpleNamespace(load_robot=lambda name: self._fk, save_current_robot=lambda **kwargs: 'robot.yaml')
        self.scene_controller = SimpleNamespace(reset_path=lambda: setattr(self, 'reset', True), update_fk_projection=lambda fk: setattr(self, 'updated_fk', fk))
        self.target_panel = SimpleNamespace(set_from_pose=lambda pose: setattr(self, 'pose', pose))
        self.playback_panel = SimpleNamespace(set_total_frames=lambda total: setattr(self, 'total', total))
        self.benchmark_panel = SimpleNamespace(summary=SimpleNamespace(setText=lambda text: setattr(self, 'bench_text', text)), log=SimpleNamespace(clear=lambda: setattr(self, 'log_cleared', True)))
        self.status_panel = SimpleNamespace(summary=SimpleNamespace(setText=lambda text: setattr(self, 'status_text', text)), metrics=None, set_metrics=lambda **kwargs: setattr(self, 'metrics', kwargs), messages=[], append=lambda message: self.status_panel.messages.append(message))
        self._playback_status_text = lambda: 'idle'
        self.read_selected_robot_name = lambda: 'planar_2dof'
        self.read_robot_editor_state = lambda: {'rows': [], 'home_q': [0.0, 0.0], 'name': 'planar_2dof'}
        self.project_robot_loaded = self._project_robot_loaded
        self.project_robot_saved = lambda path: self.status_panel.append(f'机器人配置已保存：{path}')
        self._projected = []
        self._project_exception = lambda exc, title='错误': self._projected.append((title, str(exc)))

    def _project_robot_loaded(self, fk):
        self.spec = self.controller.state.robot_spec
        self.scene_controller.reset_path()
        self.scene_controller.update_fk_projection(fk)
        self.target_panel.set_from_pose(fk.ee_pose)
        self.playback_panel.set_total_frames(0)
        self.benchmark_panel.summary.setText('尚未运行 benchmark')
        self.benchmark_panel.log.clear()
        self.status_panel.summary.setText(f'已加载机器人：{self.controller.state.robot_spec.label}')
        self.status_panel.set_metrics(playback=self._playback_status_text())
        self.status_panel.append('机器人加载完成')


def test_robot_coordinator_loads_and_saves_robot():
    window = DummyWindow()
    coord = RobotCoordinator(window)
    coord.load_robot()
    coord.save_current_robot()
    assert window.reset is True
    assert window.updated_fk is window._fk
    assert window.pose is window._fk.ee_pose
    assert window.total == 0
    assert window.status_panel.messages == ['机器人加载完成', '机器人配置已保存：robot.yaml']
