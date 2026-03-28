from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.models import CapabilityStatus, ImplementationState


class PostprocessService:
    def preprocess(self, session_dir: Path | None) -> CapabilityStatus:
        return self._status(session_dir, "图像预处理")

    def reconstruct(self, session_dir: Path | None) -> CapabilityStatus:
        return self._status(session_dir, "局部重建")

    def assess(self, session_dir: Path | None) -> CapabilityStatus:
        return self._status(session_dir, "Cobb 角评估")

    @staticmethod
    def _status(session_dir: Path | None, label: str) -> CapabilityStatus:
        if session_dir is None:
            return CapabilityStatus(
                ready=False,
                state="BLOCKED",
                implementation=ImplementationState.PLANNED.value,
                detail=f"{label}需要先完成一次有效会话。",
            )
        return CapabilityStatus(
            ready=True,
            state="AVAILABLE",
            implementation=ImplementationState.PLANNED.value,
            detail=f"{label}接口已保留，当前仍为 Planned。",
        )
