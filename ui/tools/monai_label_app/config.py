from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class MonaiLabelAppConfig:
    """Structured configuration for the repository-owned MONAI Label skeleton."""

    dataset_root: Path
    task_names: list[str] = field(default_factory=lambda: ["lamina_center", "uca_auxiliary"])
    split_name: str = "train"

    def __post_init__(self) -> None:
        self.dataset_root = Path(self.dataset_root)
        normalized: list[str] = []
        for task_name in self.task_names:
            name = str(task_name).strip()
            if name and name not in normalized:
                normalized.append(name)
        self.task_names = normalized or ["lamina_center", "uca_auxiliary"]

    @property
    def raw_cases_dir(self) -> Path:
        return self.dataset_root / "raw_cases"

    @property
    def annotations_dir(self) -> Path:
        return self.dataset_root / "annotations"

    @property
    def split_file(self) -> Path:
        return self.dataset_root / "splits" / "split_v1.json"
