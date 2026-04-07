from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.services.datasets.annotation_manifest_builder import AnnotationManifestBuilder
from spine_ultrasound_ui.utils import ensure_dir, now_text

from .config import MonaiLabelAppConfig


class SpineUltrasoundMonaiLabelSkeleton:
    """Repository-owned offline MONAI Label skeleton metadata."""

    def __init__(self, config: MonaiLabelAppConfig) -> None:
        self.config = config
        self.annotation_manifest_builder = AnnotationManifestBuilder()

    def build_manifest(self) -> dict[str, Any]:
        case_manifest = self._safe_annotation_manifest()
        tasks = [
            {
                "name": "lamina_center",
                "kind": "keypoint_annotation",
                "description": "Annotate left/right lamina center points from exported reconstruction candidates.",
            },
            {
                "name": "uca_auxiliary",
                "kind": "slice_ranking",
                "description": "Annotate auxiliary UCA labels and ranked coronal-VPI slices.",
            },
        ]
        enabled = [task for task in tasks if task["name"] in self.config.task_names]
        return {
            "generated_at": now_text(),
            "dataset_root": str(self.config.dataset_root),
            "studies_path": str(self.config.raw_cases_dir),
            "tasks": enabled,
            "annotation_manifest": case_manifest,
        }

    def validate_dataset_layout(self) -> dict[str, Any]:
        return {
            "dataset_root_exists": self.config.dataset_root.exists(),
            "raw_cases_exists": self.config.raw_cases_dir.exists(),
            "annotations_exists": self.config.annotations_dir.exists(),
            "split_file_exists": self.config.split_file.exists(),
        }

    def write_manifest(self, output_path: Path) -> dict[str, Any]:
        output_path = Path(output_path)
        payload = self.build_manifest()
        ensure_dir(output_path.parent)
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return payload

    def _safe_annotation_manifest(self) -> dict[str, Any]:
        if not self.config.dataset_root.exists():
            return {
                "generated_at": now_text(),
                "dataset_root": str(self.config.dataset_root),
                "case_count": 0,
                "cases": [],
                "split": {"train": [], "val": [], "test": []},
            }
        try:
            return self.annotation_manifest_builder.build(self.config.dataset_root)
        except FileNotFoundError:
            return {
                "generated_at": now_text(),
                "dataset_root": str(self.config.dataset_root),
                "case_count": 0,
                "cases": [],
                "split": {"train": [], "val": [], "test": []},
            }
