from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

import spine_ultrasound_ui.api_server as api_server


class _StubAdapter:
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def status(self) -> dict:
        return {"backend_mode": "mock", "execution_state": "AUTO_READY", "protocol_version": 1}

    def snapshot(self) -> list[dict]:
        return [{"topic": "core_state", "ts_ns": 1, "data": {"execution_state": "AUTO_READY"}}]

    def schema(self) -> dict:
        return {
            "api_version": "v1",
            "protocol_version": 1,
            "commands": {"start_scan": {"required_payload_fields": []}},
            "telemetry_topics": {"core_state": {"core_fields": ["execution_state"]}},
            "force_control": {"desired_contact_force_n": 10.0},
        }

    def command(self, command: str, payload: dict) -> dict:
        if command == "start_scan":
            return {
                "ok": True,
                "message": "start_scan accepted",
                "request_id": "req-1",
                "data": payload,
                "protocol_version": 1,
            }
        if command == "bad_payload":
            raise ValueError("payload rejected")
        raise RuntimeError("transport failure")

    def camera_frame(self) -> str:
        return "camera"

    def ultrasound_frame(self) -> str:
        return "ultrasound"


def _client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(api_server, "adapter", _StubAdapter())
    return TestClient(api_server.app)


def test_api_server_schema_contract(monkeypatch: pytest.MonkeyPatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/schema")
        assert response.status_code == 200
        body = response.json()
        assert body["api_version"] == "v1"
        assert body["protocol_version"] == 1


def test_api_server_commands_return_reply_shape(monkeypatch: pytest.MonkeyPatch):
    with _client(monkeypatch) as client:
        response = client.post("/api/v1/commands/start_scan", json={"mode": "auto"})
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["protocol_version"] == 1
        assert body["data"]["mode"] == "auto"


def test_api_server_invalid_payload_returns_400(monkeypatch: pytest.MonkeyPatch):
    with _client(monkeypatch) as client:
        response = client.post("/api/v1/commands/start_scan", json=["not", "an", "object"])
        assert response.status_code == 400


def test_api_server_transport_failure_returns_502(monkeypatch: pytest.MonkeyPatch):
    with _client(monkeypatch) as client:
        response = client.post("/api/v1/commands/anything_else", json={})
        assert response.status_code == 502


def test_api_server_websocket_telemetry_shape(monkeypatch: pytest.MonkeyPatch):
    with _client(monkeypatch) as client:
        with client.websocket_connect("/ws/telemetry") as websocket:
            message = websocket.receive_json()
            assert message["topic"] == "core_state"
            assert message["data"]["execution_state"] == "AUTO_READY"
