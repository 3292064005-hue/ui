from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

import spine_ultrasound_ui.api_server as api_server
from spine_ultrasound_ui.services.backend_control_plane_service import BackendControlPlaneService
from spine_ultrasound_ui.services.backend_link_service import BackendLinkMetrics, BackendLinkService


class _StubAdapter:
    def __init__(self) -> None:
        self._runtime_config = {"pressure_target": 8.0}

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def status(self) -> dict:
        return {
            "backend_mode": "mock",
            "execution_state": "AUTO_READY",
            "protocol_version": 1,
            "session_id": "S1",
            "command_endpoint": "127.0.0.1:5656",
            "telemetry_endpoint": "127.0.0.1:5657",
        }

    def health(self) -> dict:
        return {
            "backend_mode": "mock",
            "adapter_running": True,
            "telemetry_stale": False,
            "latest_telemetry_age_ms": 12,
            "execution_state": "AUTO_READY",
        }

    def snapshot(self, topics=None) -> list[dict]:
        payload = [{"topic": "core_state", "ts_ns": 1, "data": {"execution_state": "AUTO_READY"}}]
        return payload if topics is None else [item for item in payload if item["topic"] in topics]

    def schema(self) -> dict:
        return {
            "api_version": "v1",
            "protocol_version": 1,
            "commands": {},
            "telemetry_topics": {},
            "force_control": {"desired_contact_force_n": 8.0, "stale_telemetry_ms": 250},
        }

    def runtime_config(self) -> dict:
        return {"runtime_config": dict(self._runtime_config)}

    def set_runtime_config(self, payload: dict) -> dict:
        self._runtime_config = dict(payload)
        return {"runtime_config": dict(self._runtime_config), "backend_mode": "mock"}

    def topic_catalog(self) -> dict:
        return {"topics": [{"name": "core_state"}, {"name": "robot_state"}, {"name": "safety_status"}, {"name": "scan_progress"}, {"name": "contact_state"}]}

    def recent_commands(self) -> dict:
        return {"recent_commands": [{"command": "connect_robot", "ok": True, "message": "connected"}]}

    def control_plane_status(self) -> dict:
        return {
            "status": self.status(),
            "health": self.health(),
            "schema": self.schema(),
            "runtime_config": self.runtime_config(),
            "topics": self.topic_catalog(),
            "recent_commands": self.recent_commands(),
        }

    def camera_frame(self) -> str:
        return "camera"

    def ultrasound_frame(self) -> str:
        return "ultrasound"


def _client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(api_server, "adapter", _StubAdapter())
    return TestClient(api_server.app)


def test_backend_link_service_reports_ready_state() -> None:
    service = BackendLinkService()
    metrics = BackendLinkMetrics(
        commands_sent=5,
        commands_failed=0,
        telemetry_connected=True,
        camera_connected=True,
        ultrasound_connected=True,
        rest_reachable=True,
        using_websocket_telemetry=True,
        using_websocket_media=True,
    )
    snapshot = service.build_snapshot(
        mode="api",
        http_base="127.0.0.1:8000",
        ws_base="ws://127.0.0.1:8000",
        status={"backend_mode": "mock"},
        health={"adapter_running": True, "telemetry_stale": False, "latest_telemetry_age_ms": 12},
        metrics=metrics,
    )
    assert snapshot["summary_state"] == "ready"
    assert snapshot["command_success_rate"] == 100
    assert snapshot["telemetry_connected"] is True


def test_backend_link_service_reports_blocked_state() -> None:
    service = BackendLinkService()
    snapshot = service.build_snapshot(
        mode="api",
        http_base="http://127.0.0.1:8000",
        ws_base="ws://127.0.0.1:8000",
        status={},
        health={"adapter_running": False, "telemetry_stale": True},
        metrics=BackendLinkMetrics(commands_sent=2, commands_failed=1, rest_reachable=False, telemetry_connected=False),
    )
    assert snapshot["summary_state"] == "blocked"
    blocker_names = {item["name"] for item in snapshot["blockers"]}
    assert "REST 网关不可达" in blocker_names
    assert "遥测通道未连通" in blocker_names


def test_api_server_runtime_config_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    with _client(monkeypatch) as client:
        post_resp = client.post("/api/v1/runtime-config", json={"pressure_target": 9.5, "rt_mode": "cartesianImpedance"})
        assert post_resp.status_code == 200
        get_resp = client.get("/api/v1/runtime-config")
        assert get_resp.status_code == 200
        assert get_resp.json()["runtime_config"]["pressure_target"] == 9.5


def test_api_server_backend_link_state(monkeypatch: pytest.MonkeyPatch) -> None:
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/backend/link-state")
        assert response.status_code == 200
        body = response.json()
        assert body["status"]["backend_mode"] == "mock"
        assert body["health"]["adapter_running"] is True
        assert body["topics"]["topics"][0]["name"] == "core_state"


def test_backend_control_plane_service_detects_config_drift() -> None:
    service = BackendControlPlaneService()
    from spine_ultrasound_ui.models import RuntimeConfig

    result = service.build(
        local_config=RuntimeConfig(pressure_target=8.0),
        runtime_config={"runtime_config": {"pressure_target": 9.5, "rt_mode": "cartesianImpedance"}},
        schema={"protocol_version": 1},
        status={"protocol_version": 1},
        health={"protocol_version": 1},
        topic_catalog={"topics": [{"name": "core_state"}, {"name": "robot_state"}, {"name": "safety_status"}, {"name": "scan_progress"}, {"name": "contact_state"}]},
        recent_commands=[{"command": "start_scan", "ok": True, "message": "started"}],
    )
    assert result["summary_state"] == "blocked"
    assert result["config_sync"]["summary_label"] == "配置漂移"


def test_api_server_control_plane_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/control-plane")
        assert response.status_code == 200
        body = response.json()
        assert body["runtime_config"]["runtime_config"]["pressure_target"] == 8.0
        assert body["recent_commands"]["recent_commands"][0]["command"] == "connect_robot"
        assert body["topics"]["topics"][0]["name"] == "core_state"


def test_backend_link_snapshot_includes_control_plane() -> None:
    service = BackendLinkService()
    metrics = BackendLinkMetrics(
        commands_sent=4,
        commands_failed=0,
        telemetry_connected=True,
        camera_connected=True,
        ultrasound_connected=True,
        rest_reachable=True,
        using_websocket_telemetry=True,
        using_websocket_media=True,
    )
    control_plane = BackendControlPlaneService().build(
        local_config=__import__("spine_ultrasound_ui.models", fromlist=["RuntimeConfig"]).RuntimeConfig(),
        runtime_config={"runtime_config": __import__("spine_ultrasound_ui.models", fromlist=["RuntimeConfig"]).RuntimeConfig().to_dict()},
        schema={"protocol_version": 1},
        status={"protocol_version": 1},
        health={"protocol_version": 1},
        topic_catalog={"topics": [{"name": "core_state"}, {"name": "robot_state"}, {"name": "safety_status"}, {"name": "scan_progress"}, {"name": "contact_state"}]},
        recent_commands=[{"command": "connect_robot", "ok": True, "message": "ok"}],
    )
    snapshot = service.build_snapshot(
        mode="api",
        http_base="http://127.0.0.1:8000",
        ws_base="ws://127.0.0.1:8000",
        status={"backend_mode": "mock", "protocol_version": 1},
        health={"adapter_running": True, "telemetry_stale": False, "latest_telemetry_age_ms": 12, "protocol_version": 1},
        metrics=metrics,
        control_plane=control_plane,
    )
    assert snapshot["control_plane"]["summary_label"] == "控制面一致"
    assert snapshot["summary_state"] == "ready"
