from __future__ import annotations

from pathlib import Path

from robot_sim.presentation.coordinators._helpers import require_dependency, require_view, run_presented


class SceneCoordinator:
    """Own scene-toolbar orchestration for the main window."""

    def __init__(self, window, *, runtime=None) -> None:
        self.window = window
        self.runtime = require_dependency(
            runtime if runtime is not None else getattr(window, 'runtime_facade', None),
            'runtime_facade',
        )

    def fit(self) -> None:
        require_view(self.window, 'project_scene_fit')

    def clear_path(self) -> None:
        require_view(self.window, 'project_scene_path_cleared')

    def capture(self) -> None:
        """Capture the current scene into the configured runtime export directory.

        Raises:
            AttributeError: If the required runtime export root or view capture contract is missing.
        """
        def action() -> None:
            export_root = require_dependency(getattr(self.runtime, 'export_root', None), 'runtime_facade.export_root')
            path = Path(export_root) / 'scene_capture.png'
            result = require_view(self.window, 'capture_scene_screenshot', path)
            require_view(self.window, 'project_scene_capture', result)

        run_presented(self.window, action, title='截图失败')
