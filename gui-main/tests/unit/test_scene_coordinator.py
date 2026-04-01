from types import SimpleNamespace

from robot_sim.presentation.coordinators.scene_coordinator import SceneCoordinator


class DummyWindow:
    def __init__(self):
        self.scene_widget = SimpleNamespace(
            fit_called=False,
            trajectory_cleared=False,
            fit_camera=self._fit,
            clear_trajectory=self._clear,
            capture_screenshot=lambda path: 'capture.png',
        )
        self.scene_controller = SimpleNamespace(cleared=False, clear_transient_visuals=self._clear_visuals)
        self.status_panel = SimpleNamespace(messages=[], append=lambda message: self.status_panel.messages.append(message))
        self.runtime_facade = SimpleNamespace(export_root='.')
        self.project_scene_fit = lambda: (self.scene_widget.fit_camera(), self.status_panel.append('3D 视图已适配到当前场景'))
        self.project_scene_path_cleared = lambda: (self.scene_controller.clear_transient_visuals(), self.scene_widget.clear_trajectory(), self.status_panel.append('末端轨迹显示已清空'))
        self.capture_scene_screenshot = lambda path: self.scene_widget.capture_screenshot(path)
        self.project_scene_capture = lambda result: self.status_panel.append(f'场景截图已导出：{result}')
        self._projected = []
        self._project_exception = lambda exc, title='错误': self._projected.append((title, str(exc)))

    def _fit(self):
        self.scene_widget.fit_called = True

    def _clear(self):
        self.scene_widget.trajectory_cleared = True

    def _clear_visuals(self):
        self.scene_controller.cleared = True


def test_scene_coordinator_handles_fit_clear_and_capture():
    window = DummyWindow()
    coord = SceneCoordinator(window)
    coord.fit()
    coord.clear_path()
    coord.capture()
    assert window.scene_widget.fit_called is True
    assert window.scene_widget.trajectory_cleared is True
    assert window.scene_controller.cleared is True
    assert window.status_panel.messages == [
        '3D 视图已适配到当前场景',
        '末端轨迹显示已清空',
        '场景截图已导出：capture.png',
    ]
