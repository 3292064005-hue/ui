from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class PlaybackState:
    is_playing: bool = False
    frame_idx: int = 0
    total_frames: int = 0
    speed_multiplier: float = 1.0
    loop_enabled: bool = False

    def with_frame(self, frame_idx: int) -> "PlaybackState":
        return replace(self, frame_idx=max(0, min(int(frame_idx), max(self.total_frames - 1, 0))))

    def play(self) -> "PlaybackState":
        return replace(self, is_playing=True)

    def pause(self) -> "PlaybackState":
        return replace(self, is_playing=False)

    def stop(self) -> "PlaybackState":
        return replace(self, is_playing=False)
