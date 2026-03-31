from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.backend_base import BackendBase
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope
from spine_ultrasound_ui.services.sdk_environment_doctor_service import SdkEnvironmentDoctorService


@dataclass
class SdkRuntimeAssetSnapshot:
    controller_logs: list[dict[str, Any]] = field(default_factory=list)
    rl_projects: list[dict[str, Any]] = field(default_factory=list)
    rl_status: dict[str, Any] = field(default_factory=dict)
    path_library: list[dict[str, Any]] = field(default_factory=list)
    drag_status: dict[str, Any] = field(default_factory=dict)
    io_snapshot: dict[str, Any] = field(default_factory=dict)
    safety_profile: dict[str, Any] = field(default_factory=dict)
    motion_contract: dict[str, Any] = field(default_factory=dict)
    register_snapshot: dict[str, Any] = field(default_factory=dict)
    runtime_alignment: dict[str, Any] = field(default_factory=dict)
    xmate_model_summary: dict[str, Any] = field(default_factory=dict)
    runtime_config_snapshot: dict[str, Any] = field(default_factory=dict)
    environment_doctor: dict[str, Any] = field(default_factory=dict)
    identity_contract: dict[str, Any] = field(default_factory=dict)
    clinical_mainline_contract: dict[str, Any] = field(default_factory=dict)
    capability_contract: dict[str, Any] = field(default_factory=dict)
    model_authority_contract: dict[str, Any] = field(default_factory=dict)
    session_freeze: dict[str, Any] = field(default_factory=dict)
    recovery_contract: dict[str, Any] = field(default_factory=dict)
    release_contract: dict[str, Any] = field(default_factory=dict)
    deployment_contract: dict[str, Any] = field(default_factory=dict)
    fault_injection_contract: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "controller_logs": list(self.controller_logs),
            "rl_projects": list(self.rl_projects),
            "rl_status": dict(self.rl_status),
            "path_library": list(self.path_library),
            "drag_status": dict(self.drag_status),
            "io_snapshot": dict(self.io_snapshot),
            "safety_profile": dict(self.safety_profile),
            "motion_contract": dict(self.motion_contract),
            "register_snapshot": dict(self.register_snapshot),
            "runtime_alignment": dict(self.runtime_alignment),
            "xmate_model_summary": dict(self.xmate_model_summary),
            "runtime_config_snapshot": dict(self.runtime_config_snapshot),
            "environment_doctor": dict(self.environment_doctor),
            "identity_contract": dict(self.identity_contract),
            "clinical_mainline_contract": dict(self.clinical_mainline_contract),
            "capability_contract": dict(self.capability_contract),
            "model_authority_contract": dict(self.model_authority_contract),
            "session_freeze": dict(self.session_freeze),
            "recovery_contract": dict(self.recovery_contract),
            "release_contract": dict(self.release_contract),
            "deployment_contract": dict(self.deployment_contract),
            "fault_injection_contract": dict(self.fault_injection_contract),
            "errors": list(self.errors),
        }


class SdkRuntimeAssetService:
    """Best-effort operational asset aggregator.

    The UI uses this service to surface runtime-facing SDK capabilities such as
    controller logs, RL project inventory, path replay inventory, I/O state, and
    safety governance settings. Failures are captured as asset errors instead of
    crashing the mainline UI.
    """

    def __init__(self) -> None:
        self.snapshot = SdkRuntimeAssetSnapshot()
        self.doctor = SdkEnvironmentDoctorService()

    def refresh(self, backend: BackendBase, config: RuntimeConfig) -> dict[str, Any]:
        self.snapshot = SdkRuntimeAssetSnapshot()
        self.snapshot.controller_logs = list(self._query_list(backend, "query_controller_log", {"count": 12, "level": "INFO"}, "logs"))
        rl_payload = self._query_data(backend, "query_rl_projects", {}, default={})
        self.snapshot.rl_projects = list(rl_payload.get("projects", []))
        self.snapshot.rl_status = dict(rl_payload.get("status", {}))
        path_payload = self._query_data(backend, "query_path_lists", {}, default={})
        self.snapshot.path_library = list(path_payload.get("paths", []))
        self.snapshot.drag_status = dict(path_payload.get("drag", {}))
        self.snapshot.io_snapshot = dict(self._query_data(backend, "get_io_snapshot", {}, default={}))
        self.snapshot.safety_profile = dict(self._query_data(backend, "get_safety_config", {}, default={}))
        motion_contract = dict(self._query_data(backend, "get_motion_contract", {}, default={}))
        motion_contract.setdefault("rt_mode", config.rt_mode)
        motion_contract.setdefault("preferred_link", config.preferred_link)
        motion_contract.setdefault("network_tolerance_percent", config.rt_network_tolerance_percent)
        self.snapshot.motion_contract = motion_contract
        self.snapshot.register_snapshot = dict(self._query_data(backend, "get_register_snapshot", {}, default={}))
        self.snapshot.runtime_alignment = dict(self._query_data(backend, "get_runtime_alignment", {}, default={}))
        self.snapshot.xmate_model_summary = dict(self._query_data(backend, "get_xmate_model_summary", {}, default={}))
        self.snapshot.runtime_config_snapshot = dict(self._query_data(backend, "get_sdk_runtime_config", {}, default={}))
        self.snapshot.environment_doctor = dict(self.doctor.inspect(config))
        self.snapshot.identity_contract = dict(self._query_data(backend, "get_identity_contract", {}, default={}))
        self.snapshot.clinical_mainline_contract = dict(self._query_data(backend, "get_clinical_mainline_contract", {}, default={}))
        self.snapshot.capability_contract = dict(self._query_data(backend, "get_capability_contract", {}, default={}))
        self.snapshot.model_authority_contract = dict(self._query_data(backend, "get_model_authority_contract", {}, default={}))
        self.snapshot.session_freeze = dict(self._query_data(backend, "get_session_freeze", {}, default={}))
        self.snapshot.recovery_contract = dict(self._query_data(backend, "get_recovery_contract", {}, default={}))
        self.snapshot.release_contract = dict(self._query_data(backend, "get_release_contract", {}, default={}))
        self.snapshot.deployment_contract = dict(self._query_data(backend, "get_deployment_contract", {}, default={}))
        self.snapshot.fault_injection_contract = dict(self._query_data(backend, "get_fault_injection_contract", {}, default={}))
        return self.snapshot.to_dict()

    def _query_list(self, backend: BackendBase, command: str, payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
        data = self._query_data(backend, command, payload, default={})
        values = data.get(key, [])
        return values if isinstance(values, list) else []

    def _query_data(self, backend: BackendBase, command: str, payload: dict[str, Any], *, default: dict[str, Any]) -> dict[str, Any]:
        try:
            reply = backend.send_command(command, payload)
        except Exception as exc:
            self.snapshot.errors.append(f"{command}: {exc}")
            return dict(default)
        if not isinstance(reply, ReplyEnvelope):
            self.snapshot.errors.append(f"{command}: invalid reply envelope")
            return dict(default)
        if not reply.ok:
            self.snapshot.errors.append(f"{command}: {reply.message}")
            return dict(default)
        return dict(reply.data or {})
