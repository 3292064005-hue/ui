from __future__ import annotations

import asyncio
import base64
import os
import socket
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QGuiApplication

from spine_ultrasound_ui.services import ipc_messages_pb2
from spine_ultrasound_ui.services.ipc_protocol import TelemetryEnvelope
from spine_ultrasound_ui.services.mock_core_runtime import MockCoreRuntime
from spine_ultrasound_ui.services.protobuf_transport import (
    DEFAULT_TLS_SERVER_NAME,
    create_client_ssl_context,
    recv_length_prefixed_message,
)
from spine_ultrasound_ui.utils import generate_demo_pixmap, now_ns


def _ensure_qt_app() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if QGuiApplication.instance() is None:
        QGuiApplication([])


def _pixmap_to_base64(mode: str, phase: float) -> str:
    _ensure_qt_app()
    pixmap = generate_demo_pixmap(720, 360, mode, phase)
    if pixmap.isNull():
        return ""
    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QIODevice.WriteOnly)
    pixmap.save(buffer, "PNG")
    return base64.b64encode(bytes(byte_array)).decode("ascii")


class HeadlessAdapter:
    def __init__(self, mode: str, command_host: str, command_port: int, telemetry_host: str, telemetry_port: int):
        self.mode = mode
        self.command_host = command_host
        self.command_port = command_port
        self.telemetry_host = telemetry_host
        self.telemetry_port = telemetry_port
        self.runtime = MockCoreRuntime() if mode == "mock" else None
        self.ssl_context = create_client_ssl_context() if mode == "core" else None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self.latest_by_topic: dict[str, dict[str, Any]] = {}
        self.phase = 0.0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        target = self._mock_loop if self.mode == "mock" else self._core_loop
        self._thread = threading.Thread(target=target, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def status(self) -> dict[str, Any]:
        with self._lock:
            core = self.latest_by_topic.get("core_state", {})
            robot = self.latest_by_topic.get("robot_state", {})
            safety = self.latest_by_topic.get("safety_status", {})
        return {
            "backend_mode": self.mode,
            "command_endpoint": f"{self.command_host}:{self.command_port}",
            "telemetry_endpoint": f"{self.telemetry_host}:{self.telemetry_port}",
            "execution_state": core.get("execution_state", "BOOT"),
            "powered": robot.get("powered", False),
            "safe_to_scan": safety.get("safe_to_scan", False),
            "topics": sorted(self.latest_by_topic.keys()),
        }

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {"topic": topic, "ts_ns": data.get("_ts_ns", now_ns()), "data": {k: v for k, v in data.items() if k != "_ts_ns"}}
                for topic, data in self.latest_by_topic.items()
            ]

    def camera_frame(self) -> str:
        self.phase += 0.1
        return _pixmap_to_base64("camera", self.phase)

    def ultrasound_frame(self) -> str:
        self.phase += 0.1
        return _pixmap_to_base64("ultrasound", self.phase)

    def _store_message(self, env: TelemetryEnvelope) -> None:
        payload = dict(env.data)
        payload["_ts_ns"] = env.ts_ns or now_ns()
        with self._lock:
            self.latest_by_topic[env.topic] = payload

    def _mock_loop(self) -> None:
        assert self.runtime is not None
        while not self._stop.is_set():
            for env in self.runtime.tick():
                self._store_message(env)
            time.sleep(0.1)

    def _core_loop(self) -> None:
        while not self._stop.is_set():
            try:
                with socket.create_connection((self.telemetry_host, self.telemetry_port), timeout=1.0) as raw_sock:
                    raw_sock.settimeout(2.0)
                    assert self.ssl_context is not None
                    with self.ssl_context.wrap_socket(raw_sock, server_hostname=DEFAULT_TLS_SERVER_NAME) as tls_sock:
                        while not self._stop.is_set():
                            message_bytes = recv_length_prefixed_message(tls_sock)
                            proto = ipc_messages_pb2.TelemetryEnvelope()
                            proto.ParseFromString(message_bytes)
                            self._store_message(TelemetryEnvelope.from_protobuf(proto))
            except OSError:
                if not self._stop.is_set():
                    time.sleep(1.0)
            except Exception as exc:
                if self._stop.is_set():
                    break
                logger.warning(f"Headless telemetry loop exception: {exc}")
                time.sleep(1.0)


adapter = HeadlessAdapter(
    mode=os.getenv("SPINE_HEADLESS_BACKEND", os.getenv("SPINE_UI_BACKEND", "mock")),
    command_host=os.getenv("ROBOT_CORE_HOST", "127.0.0.1"),
    command_port=int(os.getenv("ROBOT_CORE_COMMAND_PORT", "5656")),
    telemetry_host=os.getenv("ROBOT_CORE_HOST", "127.0.0.1"),
    telemetry_port=int(os.getenv("ROBOT_CORE_TELEMETRY_PORT", "5657")),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing headless adapter...")
    adapter.start()
    yield
    logger.info("Tearing down headless adapter...")
    adapter.stop()


app = FastAPI(title="Spine Ultrasound Headless Adapter", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/status")
async def get_system_status():
    return adapter.status()


@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            for item in adapter.snapshot():
                await websocket.send_json(item)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        return


@app.websocket("/ws/camera")
async def websocket_camera_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_text(adapter.camera_frame())
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        return


@app.websocket("/ws/ultrasound")
async def websocket_ultrasound_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_text(adapter.ultrasound_frame())
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        return
