from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .app import SpineUltrasoundMonaiLabelSkeleton
from .config import MonaiLabelAppConfig
from .tasks import BaseMonaiLabelTask, build_task_registry


@dataclass(slots=True)
class TaskRegistry:
    infer_tasks: dict[str, BaseMonaiLabelTask]


class SpineUltrasoundMonaiLabelServerApp(SpineUltrasoundMonaiLabelSkeleton):
    """Thin server-facing facade for offline annotation tasks."""

    def __init__(self, config: MonaiLabelAppConfig) -> None:
        super().__init__(config)
        self.registry = TaskRegistry(infer_tasks=build_task_registry(config))

    def build_server_descriptor(self) -> dict[str, Any]:
        return {
            "dataset_root": str(self.config.dataset_root),
            "studies_path": str(self.config.raw_cases_dir),
            "server_tasks": {
                "infer": sorted(self.registry.infer_tasks.keys()),
                "save_annotation": sorted(self.registry.infer_tasks.keys()),
                "train_request": sorted(self.registry.infer_tasks.keys()),
            },
            "manifest": self.build_manifest(),
        }
