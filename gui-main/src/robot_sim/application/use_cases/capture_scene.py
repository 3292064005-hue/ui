from __future__ import annotations


class CaptureSceneUseCase:
    def __init__(self, screenshot_service) -> None:
        self._screenshot_service = screenshot_service

    def execute(self, scene_widget, path):
        return self._screenshot_service.capture(scene_widget, path)
