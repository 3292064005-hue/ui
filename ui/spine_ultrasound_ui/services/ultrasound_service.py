from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np

from .sensor_base import SensorIngestionProcess, SensorProvider, SensorPoller

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CouplingAssessment:
    dark_ratio: float
    coupled: bool
    warning: str | None = None


@dataclass(frozen=True)
class UltrasoundCaptureConfig:
    device_idx: int = 1
    width: int = 800
    height: int = 600
    fps: int = 30

    @classmethod
    def from_runtime_config(cls, config) -> "UltrasoundCaptureConfig":
        return cls(
            device_idx=int(getattr(config, "ultrasound_capture_device_index", 1) or 1),
            width=int(getattr(config, "ultrasound_capture_width", 800) or 800),
            height=int(getattr(config, "ultrasound_capture_height", 600) or 600),
            fps=int(getattr(config, "ultrasound_capture_fps", 30) or 30),
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "device_idx": int(self.device_idx),
            "width": int(self.width),
            "height": int(self.height),
            "fps": int(self.fps),
        }


class UltrasoundCouplingMonitor:
    def __init__(self, *, dark_threshold: int = 15, decoupled_ratio: float = 0.85) -> None:
        self.dark_threshold = dark_threshold
        self.decoupled_ratio = decoupled_ratio

    def assess(self, frame_gray: np.ndarray) -> CouplingAssessment:
        total_pixels = max(int(frame_gray.size), 1)
        dark_pixels = int(np.sum(frame_gray < self.dark_threshold))
        dark_ratio = dark_pixels / total_pixels
        coupled = dark_ratio <= self.decoupled_ratio
        warning = None if coupled else f"Probe decoupling detected (dark ratio={dark_ratio:.1%})"
        return CouplingAssessment(dark_ratio=dark_ratio, coupled=coupled, warning=warning)


class UltrasoundIngestionProcess(SensorIngestionProcess):
    """Sub-process that acquires grayscale ultrasound frames from a V4L2 capture device."""

    def __init__(self, device_idx: int, width: int, height: int, fps: int, init_kwargs):
        super().__init__(**init_kwargs)
        self.device_idx = device_idx
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None
        self.coupling_monitor = UltrasoundCouplingMonitor()

    def setup_hardware(self) -> bool:
        logger.info("Connecting to ultrasound capture card %s", self.device_idx)
        self.cap = cv2.VideoCapture(self.device_idx)
        if not self.cap.isOpened():
            logger.error("Failed to open ultrasound device %s", self.device_idx)
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        return True

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray], int]:
        if self.cap is None:
            return False, None, 0

        ret, frame = self.cap.read()
        ts_ns = time.time_ns()
        if not ret or frame is None:
            return False, None, ts_ns

        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        assessment = self.coupling_monitor.assess(frame_gray)
        if assessment.warning:
            logger.warning("[CouplingMonitor] %s", assessment.warning)
        return True, frame_gray, ts_ns

    def teardown_hardware(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            logger.info("Ultrasound capture released.")


class UltrasoundService(SensorProvider):
    """Provides a zero-copy grayscale ultrasound stream to the UI/runtime."""

    def __init__(self, device_idx: int = 1, width: int = 800, height: int = 600, fps: int = 30, parent=None):
        shape = (height, width)
        dtype = np.uint8
        self.capture_config = UltrasoundCaptureConfig(device_idx=device_idx, width=width, height=height, fps=fps)
        self.device_idx = self.capture_config.device_idx
        self.img_width = self.capture_config.width
        self.img_height = self.capture_config.height
        self.fps = self.capture_config.fps
        super().__init__(name="ultrasound", shape=shape, dtype=dtype, process_class=UltrasoundIngestionProcess, parent=parent)

    @classmethod
    def from_runtime_config(cls, config, parent=None) -> "UltrasoundService":
        capture = UltrasoundCaptureConfig.from_runtime_config(config)
        return cls(device_idx=capture.device_idx, width=capture.width, height=capture.height, fps=capture.fps, parent=parent)

    def capture_status(self) -> dict[str, object]:
        return {
            "provider": "v4l2_opencv",
            "configured": self.capture_config.to_dict(),
            "running": bool(self._process is not None and self._process.is_alive()),
            "latest_ts_ns": int(self.latest_ts_ns.value),
            "shm_name": self.shm_name,
            "frame_shape": list(self.shape),
            "dtype": str(self.dtype),
        }

    def start(self):
        if self._process is not None and self._process.is_alive():
            return

        try:
            from multiprocessing import shared_memory as shm

            self._shm = shm.SharedMemory(create=True, size=self.bytes_size, name=self.shm_name)
        except Exception as exc:  # pragma: no cover - OS/shared memory failure path
            logger.error("Failed to allocate SHM for ultrasound: %s", exc)
            return

        self.run_flag.set()
        self.latest_ts_ns.value = 0
        init_kwargs = {
            "shm_name": self.shm_name,
            "shape": self.shape,
            "dtype": self.dtype,
            "run_flag": self.run_flag,
            "latest_ts_ns": self.latest_ts_ns,
        }
        self._process = self.process_class(
            device_idx=self.device_idx,
            width=self.img_width,
            height=self.img_height,
            fps=self.fps,
            init_kwargs=init_kwargs,
        )
        self._process.start()
        self._poller = SensorPoller(self.latest_ts_ns, self.run_flag)
        self._poller.new_frame_detected.connect(self._on_new_frame)
        self._poller.start()
        logger.info("UltrasoundService started (device=%s, size=%sx%s).", self.device_idx, self.img_width, self.img_height)
