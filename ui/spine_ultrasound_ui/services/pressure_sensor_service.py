from __future__ import annotations

import csv
import json
import math
import os
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlparse

from spine_ultrasound_ui.utils import now_ns


@dataclass(frozen=True)
class ForceSample:
    ts_ns: int
    wrench_n: list[float]
    status: str
    source: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class ForceSensorProvider(ABC):
    provider_id: str = "force_sensor_provider"

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    @abstractmethod
    def read_sample(self, *, contact_active: bool, desired_force_n: float) -> ForceSample:
        ...


class MockForceSensorProvider(ForceSensorProvider):
    provider_id = "mock_force_sensor"

    def __init__(self) -> None:
        self._phase = 0.0

    def read_sample(self, *, contact_active: bool, desired_force_n: float) -> ForceSample:
        self._phase += 0.13
        base_force = desired_force_n if contact_active else 0.0
        ripple = 0.25 * math.sin(self._phase) + 0.05 * math.cos(self._phase * 0.5)
        z_force = round(base_force + (ripple if contact_active else 0.0), 3)
        return ForceSample(
            ts_ns=now_ns(),
            wrench_n=[0.03, 0.02, z_force, 0.0, 0.0, 0.0],
            status="ok",
            source=self.provider_id,
        )


class UnavailableForceSensorProvider(ForceSensorProvider):
    provider_id = "unavailable_force_sensor"

    def read_sample(self, *, contact_active: bool, desired_force_n: float) -> ForceSample:
        del contact_active, desired_force_n
        return ForceSample(
            ts_ns=now_ns(),
            wrench_n=[0.0] * 6,
            status="unavailable",
            source=self.provider_id,
        )


class SerialForceSensorProvider(ForceSensorProvider):
    """Read real force/pressure samples from a serial or replay line source.

    The provider accepts newline-delimited JSON or CSV. JSON may contain
    ``wrench_n`` or a scalar ``pressure_current``/``force_n``/``z_force_n``.
    CSV may contain six wrench values, or one scalar z-force value.
    """

    provider_id = "serial_force_sensor"

    def __init__(
        self,
        *,
        url: str | None = None,
        baud: int | None = None,
        line_format: str | None = None,
        timeout_ms: int | None = None,
        z_index: int | None = None,
    ) -> None:
        self.url = str(url or os.getenv("SPINE_FORCE_SENSOR_SERIAL_URL", "") or os.getenv("SPINE_FORCE_SENSOR_REPLAY_FILE", ""))
        self.baud = int(baud or os.getenv("SPINE_FORCE_SENSOR_SERIAL_BAUD", "115200") or 115200)
        self.line_format = str(line_format or os.getenv("SPINE_FORCE_SENSOR_SERIAL_FORMAT", "auto") or "auto").lower()
        self.timeout_ms = int(timeout_ms or os.getenv("SPINE_FORCE_SENSOR_SERIAL_TIMEOUT_MS", "50") or 50)
        self.z_index = int(z_index if z_index is not None else os.getenv("SPINE_FORCE_SENSOR_SERIAL_Z_INDEX", "2"))
        self._handle = None
        self._serial = None
        self._last_sample: ForceSample | None = None

    @classmethod
    def from_provider_id(cls, provider_id: str) -> "SerialForceSensorProvider":
        suffix = provider_id[len(cls.provider_id):]
        if suffix.startswith(":"):
            suffix = suffix[1:]
        if not suffix:
            return cls()
        parsed = urlparse(suffix)
        query = parse_qs(parsed.query)
        if parsed.scheme in {"file", "serial"}:
            url = suffix.split("?", 1)[0]
        else:
            url = suffix.split("?", 1)[0]
        return cls(
            url=url,
            baud=int(query.get("baud", ["115200"])[0]),
            line_format=query.get("format", ["auto"])[0],
            timeout_ms=int(query.get("timeout_ms", ["50"])[0]),
            z_index=int(query.get("z_index", ["2"])[0]),
        )

    def start(self) -> None:
        if self._handle is not None or self._serial is not None:
            return
        if not self.url:
            return
        parsed = urlparse(self.url)
        path = self.url
        if parsed.scheme == "file":
            path = parsed.path
        if parsed.scheme in {"", "file"} and Path(path).exists():
            self._handle = Path(path).open("r", encoding="utf-8")
            return
        try:  # pragma: no cover - optional hardware dependency
            import serial  # type: ignore
        except Exception:
            return
        serial_path = parsed.path if parsed.scheme == "serial" else self.url
        self._serial = serial.Serial(serial_path, baudrate=self.baud, timeout=self.timeout_ms / 1000.0)

    def stop(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None
        if self._serial is not None:  # pragma: no cover - optional hardware dependency
            self._serial.close()
            self._serial = None

    def read_sample(self, *, contact_active: bool, desired_force_n: float) -> ForceSample:
        del contact_active
        if self._handle is None and self._serial is None:
            self.start()
        line = self._read_line()
        if not line:
            return self._last_sample or ForceSample(
                ts_ns=now_ns(),
                wrench_n=[0.0] * 6,
                status="unavailable",
                source=self.provider_id,
            )
        try:
            sample = self._parse_line(line, desired_force_n=desired_force_n)
        except (ValueError, TypeError, json.JSONDecodeError):
            sample = ForceSample(
                ts_ns=now_ns(),
                wrench_n=[0.0] * 6,
                status="parse_error",
                source=self.provider_id,
            )
        self._last_sample = sample
        return sample

    def _read_line(self) -> str:
        if self._handle is not None:
            line = self._handle.readline()
            if line == "":
                self._handle.seek(0)
                line = self._handle.readline()
            return line.strip()
        if self._serial is not None:  # pragma: no cover - optional hardware dependency
            raw = self._serial.readline()
            return raw.decode("utf-8", errors="replace").strip()
        return ""

    def _parse_line(self, line: str, *, desired_force_n: float) -> ForceSample:
        fmt = self.line_format
        if fmt == "auto":
            fmt = "json" if line.lstrip().startswith("{") else "csv"
        if fmt == "json":
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError("force sample JSON must be an object")
            wrench = payload.get("wrench_n")
            if isinstance(wrench, list):
                wrench_n = [float(value) for value in wrench[:6]]
            else:
                z_force = float(payload.get("pressure_current", payload.get("force_n", payload.get("z_force_n", desired_force_n))) or 0.0)
                wrench_n = [0.0, 0.0, z_force, 0.0, 0.0, 0.0]
            while len(wrench_n) < 6:
                wrench_n.append(0.0)
            return ForceSample(
                ts_ns=int(payload.get("ts_ns", now_ns()) or now_ns()),
                wrench_n=wrench_n[:6],
                status=str(payload.get("status", "ok") or "ok"),
                source=str(payload.get("source", self.provider_id) or self.provider_id),
            )
        values = next(csv.reader([line]))
        numeric = [float(value.strip()) for value in values if value.strip()]
        if len(numeric) >= 6:
            wrench_n = numeric[:6]
        elif numeric:
            z = numeric[min(max(self.z_index, 0), len(numeric) - 1)] if len(numeric) > self.z_index else numeric[-1]
            wrench_n = [0.0, 0.0, z, 0.0, 0.0, 0.0]
        else:
            raise ValueError("empty CSV force sample")
        return ForceSample(ts_ns=now_ns(), wrench_n=wrench_n, status="ok", source=self.provider_id)


_PROVIDER_FACTORIES: dict[str, Callable[[], ForceSensorProvider]] = {
    MockForceSensorProvider.provider_id: MockForceSensorProvider,
    UnavailableForceSensorProvider.provider_id: UnavailableForceSensorProvider,
    SerialForceSensorProvider.provider_id: SerialForceSensorProvider,
}


def register_force_sensor_provider_factory(provider_id: str, factory: Callable[[], ForceSensorProvider]) -> None:
    provider_id = str(provider_id).strip()
    if not provider_id:
        raise ValueError("provider_id must not be empty")
    _PROVIDER_FACTORIES[provider_id] = factory


def available_force_sensor_providers() -> list[str]:
    return sorted(_PROVIDER_FACTORIES)


def create_force_sensor_provider(provider_id: str) -> ForceSensorProvider:
    if str(provider_id).startswith(SerialForceSensorProvider.provider_id):
        return SerialForceSensorProvider.from_provider_id(str(provider_id))
    factory = _PROVIDER_FACTORIES.get(provider_id, UnavailableForceSensorProvider)
    provider = factory()
    if not isinstance(provider, ForceSensorProvider):
        raise TypeError(f"factory for {provider_id!r} returned {type(provider).__name__}, expected ForceSensorProvider")
    return provider
