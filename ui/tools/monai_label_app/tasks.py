from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.training.specs.lamina_center_training_spec import LaminaCenterTrainingSpec
from spine_ultrasound_ui.training.specs.uca_training_spec import UCATrainingSpec
from spine_ultrasound_ui.training.trainers.lamina_keypoint_trainer import LaminaKeypointTrainer
from spine_ultrasound_ui.training.trainers.uca_slice_rank_trainer import UCASliceRankTrainer
from spine_ultrasound_ui.utils import ensure_dir, now_text

from .config import MonaiLabelAppConfig


@dataclass(slots=True)
class TaskResult:
    payload: dict[str, Any]


class BaseMonaiLabelTask:
    """Shared helpers for repository-owned offline annotation tasks."""

    task_name: str = ""

    def __init__(self, config: MonaiLabelAppConfig) -> None:
        self.config = config

    def case_dir(self, case_id: str) -> Path:
        patient_id, session_id = self._split_case_id(case_id)
        return self.config.raw_cases_dir / patient_id / session_id

    def ensure_split_contains_case(self, case_id: str) -> None:
        split_payload = {"train": [], "val": [], "test": []}
        if self.config.split_file.exists():
            split_payload.update(self._read_json(self.config.split_file))
        split_name = self.config.split_name if self.config.split_name in split_payload else "train"
        bucket = [str(item) for item in split_payload.get(split_name, [])]
        if case_id not in bucket:
            bucket.append(case_id)
            split_payload[split_name] = sorted(set(bucket))
            ensure_dir(self.config.split_file.parent)
            self.config.split_file.write_text(json.dumps(split_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _split_case_id(case_id: str) -> tuple[str, str]:
        normalized = str(case_id).replace("\\", "/").replace("__", "/")
        parts = [part for part in normalized.split("/") if part]
        if len(parts) < 2:
            raise ValueError(f"invalid case_id: {case_id}")
        return parts[-2], parts[-1]

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        ensure_dir(path.parent)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


class LaminaCenterTask(BaseMonaiLabelTask):
    task_name = "lamina_center"

    def infer(self, case_id: str) -> TaskResult:
        patient_id, session_id = self._split_case_id(case_id)
        annotation_path = self.config.annotations_dir / "lamina_centers" / f"{patient_id}__{session_id}.json"
        if annotation_path.exists():
            return TaskResult(
                {
                    "task_name": self.task_name,
                    "case_id": case_id,
                    "source": "existing_annotation",
                    "lamina_centers": self._read_json(annotation_path),
                }
            )
        candidates = self._read_json(self.case_dir(case_id) / "lamina_candidates.json")
        points = []
        for index, candidate in enumerate(candidates.get("candidates", []), start=1):
            if not isinstance(candidate, dict):
                continue
            vertebra_id = str(candidate.get("vertebra_instance_id", candidate.get("vertebra_id", f"v{index}")) or f"v{index}")
            point_id = str(candidate.get("point_id", candidate.get("candidate_id", f"p{index}")) or f"p{index}")
            points.append(
                {
                    "point_id": point_id,
                    "vertebra_instance_id": vertebra_id,
                    "side": str(candidate.get("side", "") or ""),
                    "x_mm": float(candidate.get("x_mm", 0.0) or 0.0),
                    "y_mm": float(candidate.get("y_mm", 0.0) or 0.0),
                    "z_mm": float(candidate.get("z_mm", 0.0) or 0.0),
                    "visibility": str(candidate.get("visibility", "clear") or "clear"),
                    "confidence": float(candidate.get("confidence", 0.0) or 0.0),
                }
            )
        return TaskResult(
            {
                "task_name": self.task_name,
                "case_id": case_id,
                "source": "reconstruction_candidates",
                "lamina_centers": {
                    "generated_at": now_text(),
                    "points": points,
                },
            }
        )

    def save_annotation(self, case_id: str, payload: dict[str, Any]) -> TaskResult:
        patient_id, session_id = self._split_case_id(case_id)
        lamina_centers = dict(payload.get("lamina_centers", payload))
        annotation_path = self.config.annotations_dir / "lamina_centers" / f"{patient_id}__{session_id}.json"
        self._write_json(annotation_path, lamina_centers)
        self._write_json(
            self.config.annotations_dir / "vertebra_pairs" / f"{patient_id}__{session_id}.json",
            {"pairs": self._build_vertebra_pairs(lamina_centers)},
        )
        self.ensure_split_contains_case(case_id)
        return TaskResult(
            {
                "task_name": self.task_name,
                "case_id": case_id,
                "saved": True,
                "lamina_centers_path": str(annotation_path),
            }
        )

    def train_request(self, output_dir: Path, *, backend: str = "monai") -> TaskResult:
        spec = LaminaCenterTrainingSpec(
            dataset_root=self.config.dataset_root,
            split_file=self.config.split_file,
            output_dir=Path(output_dir),
            trainer_backend=backend,
            split_name=self.config.split_name,
        )
        result = LaminaKeypointTrainer().train(spec)
        return TaskResult(result)

    @staticmethod
    def _build_vertebra_pairs(lamina_centers: dict[str, Any]) -> list[dict[str, Any]]:
        seen: dict[str, set[str]] = {}
        for point in lamina_centers.get("points", []):
            if not isinstance(point, dict):
                continue
            vertebra_id = str(point.get("vertebra_instance_id", "unknown") or "unknown")
            side = str(point.get("side", "") or "")
            seen.setdefault(vertebra_id, set()).add(side)
        pairs = []
        for vertebra_id in sorted(seen):
            if {"left", "right"} <= seen[vertebra_id]:
                pairs.append({"vertebra_instance_id": vertebra_id})
        return pairs


class UCAAuxiliaryTask(BaseMonaiLabelTask):
    task_name = "uca_auxiliary"

    def infer(self, case_id: str) -> TaskResult:
        patient_id, session_id = self._split_case_id(case_id)
        label_path = self.config.annotations_dir / "uca_labels" / f"{patient_id}__{session_id}.json"
        ranking_path = self.config.annotations_dir / "slice_ranking" / f"{patient_id}__{session_id}.json"
        if label_path.exists():
            return TaskResult(
                {
                    "task_name": self.task_name,
                    "case_id": case_id,
                    "source": "existing_annotation",
                    "uca_labels": self._read_json(label_path),
                    "slice_ranking": self._read_json(ranking_path),
                }
            )
        ranking = self._read_json(self.case_dir(case_id) / "ranked_slice_candidates.json")
        measurement = self._read_json(self.case_dir(case_id) / "uca_measurement.json")
        best_slice = dict(ranking.get("best_slice", {}))
        inferred = {
            "best_slice_index": int(best_slice.get("slice_index", 0) or 0),
            "best_slice_score": float(best_slice.get("score", 0.0) or 0.0),
            "uca_angle_deg": float(measurement.get("angle_deg", measurement.get("uca_angle_deg", 0.0)) or 0.0),
            "requires_manual_review": bool(measurement.get("requires_manual_review", False)),
        }
        return TaskResult(
            {
                "task_name": self.task_name,
                "case_id": case_id,
                "source": "ranked_slice_candidates",
                "uca_labels": inferred,
                "slice_ranking": ranking,
            }
        )

    def save_annotation(self, case_id: str, payload: dict[str, Any]) -> TaskResult:
        patient_id, session_id = self._split_case_id(case_id)
        label_path = self.config.annotations_dir / "uca_labels" / f"{patient_id}__{session_id}.json"
        ranking_path = self.config.annotations_dir / "slice_ranking" / f"{patient_id}__{session_id}.json"
        uca_labels = dict(payload.get("uca_labels", payload))
        slice_ranking = dict(payload.get("slice_ranking", {}))
        self._write_json(label_path, uca_labels)
        if slice_ranking:
            self._write_json(ranking_path, slice_ranking)
        self.ensure_split_contains_case(case_id)
        return TaskResult(
            {
                "task_name": self.task_name,
                "case_id": case_id,
                "saved": True,
                "uca_label_path": str(label_path),
                "slice_ranking_path": str(ranking_path) if slice_ranking else "",
            }
        )

    def train_request(self, output_dir: Path, *, backend: str = "monai") -> TaskResult:
        spec = UCATrainingSpec(
            dataset_root=self.config.dataset_root,
            split_file=self.config.split_file,
            output_dir=Path(output_dir),
            trainer_backend=backend,
            split_name=self.config.split_name,
        )
        result = UCASliceRankTrainer().train(spec)
        return TaskResult(result)


def build_task_registry(config: MonaiLabelAppConfig) -> dict[str, BaseMonaiLabelTask]:
    tasks: dict[str, BaseMonaiLabelTask] = {}
    for task_name in config.task_names:
        if task_name == "lamina_center":
            tasks[task_name] = LaminaCenterTask(config)
        elif task_name == "uca_auxiliary":
            tasks[task_name] = UCAAuxiliaryTask(config)
    return tasks
