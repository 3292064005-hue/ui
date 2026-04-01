from __future__ import annotations

from pathlib import Path
from typing import Any
import re
import numpy as np
import yaml

from robot_sim.model.dh_row import DHRow
from robot_sim.model.robot_catalog_entry import RobotCatalogEntry
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.domain.enums import JointType


class RobotRegistry:
    def __init__(self, robots_dir: str | Path) -> None:
        self.robots_dir = Path(robots_dir)
        self.robots_dir.mkdir(parents=True, exist_ok=True)

    def list_names(self) -> list[str]:
        return sorted(p.stem for p in self.robots_dir.glob("*.yaml"))

    def list_specs(self) -> list[RobotSpec]:
        return [self.load(name) for name in self.list_names()]

    def list_entries(self) -> list[RobotCatalogEntry]:
        entries = [
            RobotCatalogEntry(
                name=spec.name,
                label=spec.label,
                dof=spec.dof,
                description=spec.description,
                metadata=dict(spec.metadata),
            )
            for spec in self.list_specs()
        ]
        return sorted(entries, key=lambda item: (item.label.lower(), item.name.lower()))

    def _slugify(self, value: str) -> str:
        text = re.sub(r"[^a-zA-Z0-9_\-]+", "_", value.strip()).strip("_")
        return text or "robot"

    def _path(self, name: str) -> Path:
        return self.robots_dir / f"{name}.yaml"

    def load(self, name: str) -> RobotSpec:
        path = self._path(name)
        if not path.exists():
            raise FileNotFoundError(f"robot config not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        spec = self.from_dict(data)
        if spec.display_name is None:
            spec = RobotSpec(
                name=spec.name,
                dh_rows=spec.dh_rows,
                base_T=spec.base_T,
                tool_T=spec.tool_T,
                home_q=spec.home_q,
                display_name=str(data.get("name") or spec.name),
                description=spec.description,
                metadata=spec.metadata,
            )
        return spec

    def save(self, spec: RobotSpec, name: str | None = None) -> Path:
        stem = self._slugify(name or spec.name)
        path = self._path(stem)
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(self.to_dict(spec), f, sort_keys=False, allow_unicode=True)
        return path

    def from_dict(self, data: dict[str, Any]) -> RobotSpec:
        rows_data = data.get("dh_rows") or []
        if not rows_data:
            raise ValueError("dh_rows is required")
        rows = []
        for idx, r in enumerate(rows_data):
            q_min = float(r.get("q_min", -np.pi))
            q_max = float(r.get("q_max", np.pi))
            if q_min > q_max:
                raise ValueError(f"dh_rows[{idx}] has q_min > q_max")
            rows.append(
                DHRow(
                    a=float(r.get("a", 0.0)),
                    alpha=float(r.get("alpha", 0.0)),
                    d=float(r.get("d", 0.0)),
                    theta_offset=float(r.get("theta_offset", 0.0)),
                    joint_type=JointType(str(r.get("joint_type", JointType.REVOLUTE.value))),
                    q_min=q_min,
                    q_max=q_max,
                )
            )
        rows = tuple(rows)
        display_name = str(data.get("name") or "unnamed_robot")
        stored_name = str(data.get("id") or self._slugify(display_name))
        dof = len(rows)
        home_q = np.array(data.get("home_q", [0.0] * dof), dtype=float)
        if home_q.shape != (dof,):
            raise ValueError(f"home_q shape mismatch, expected {(dof,)}, got {home_q.shape}")
        base_T = np.array(data.get("base_T", np.eye(4).tolist()), dtype=float)
        tool_T = np.array(data.get("tool_T", np.eye(4).tolist()), dtype=float)
        if base_T.shape != (4, 4) or tool_T.shape != (4, 4):
            raise ValueError("base_T and tool_T must be 4x4")
        if not np.isfinite(home_q).all() or not np.isfinite(base_T).all() or not np.isfinite(tool_T).all():
            raise ValueError("robot configuration contains non-finite values")
        mins = np.array([r.q_min for r in rows], dtype=float)
        maxs = np.array([r.q_max for r in rows], dtype=float)
        if np.any(home_q < mins) or np.any(home_q > maxs):
            raise ValueError("home_q must lie within joint limits")
        metadata = dict(data.get("metadata") or {})
        description = str(data.get("description") or "")
        return RobotSpec(
            name=stored_name,
            dh_rows=rows,
            base_T=base_T,
            tool_T=tool_T,
            home_q=home_q,
            display_name=display_name,
            description=description,
            metadata=metadata,
        )

    def to_dict(self, spec: RobotSpec) -> dict[str, Any]:
        payload = {
            "id": spec.name,
            "name": spec.label,
            "description": spec.description,
            "metadata": dict(spec.metadata),
            "dh_rows": [
                {
                    "a": float(r.a),
                    "alpha": float(r.alpha),
                    "d": float(r.d),
                    "theta_offset": float(r.theta_offset),
                    "joint_type": r.joint_type.value,
                    "q_min": float(r.q_min),
                    "q_max": float(r.q_max),
                }
                for r in spec.dh_rows
            ],
            "base_T": np.asarray(spec.base_T, dtype=float).tolist(),
            "tool_T": np.asarray(spec.tool_T, dtype=float).tolist(),
            "home_q": np.asarray(spec.home_q, dtype=float).tolist(),
        }
        if not payload["description"]:
            payload.pop("description")
        if not payload["metadata"]:
            payload.pop("metadata")
        return payload
