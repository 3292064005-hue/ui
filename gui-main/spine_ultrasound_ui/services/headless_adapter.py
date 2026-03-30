from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.backend_control_plane_service import BackendControlPlaneService
from spine_ultrasound_ui.services.command_state_policy import CommandStatePolicyService
from spine_ultrasound_ui.services.control_authority_service import ControlAuthorityService
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService
from spine_ultrasound_ui.services.event_bus import EventBus
from spine_ultrasound_ui.services.headless_adapter_surface import HeadlessAdapterSurface
from spine_ultrasound_ui.services.headless_command_service import HeadlessCommandService
from spine_ultrasound_ui.services.headless_control_plane_aggregator import HeadlessControlPlaneAggregator
from spine_ultrasound_ui.services.headless_runtime_introspection import HeadlessRuntimeIntrospection
from spine_ultrasound_ui.services.headless_session_context import HeadlessSessionContext
from spine_ultrasound_ui.services.headless_session_products_reader import HeadlessSessionProductsReader
from spine_ultrasound_ui.services.headless_telemetry_cache import HeadlessTelemetryCache
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope
from spine_ultrasound_ui.services.mock_core_runtime import MockCoreRuntime
from spine_ultrasound_ui.services.protobuf_transport import create_client_ssl_context
from spine_ultrasound_ui.services.role_matrix import RoleMatrix
from spine_ultrasound_ui.services.session_dir_watcher import SessionDirWatcher
from spine_ultrasound_ui.services.session_evidence_seal_service import SessionEvidenceSealService
from spine_ultrasound_ui.services.session_integrity_service import SessionIntegrityService
from spine_ultrasound_ui.services.session_intelligence_service import SessionIntelligenceService
from spine_ultrasound_ui.services.topic_registry import TopicRegistry


class HeadlessAdapter:
    def __init__(self, mode: str, command_host: str, command_port: int, telemetry_host: str, telemetry_port: int):
        self.mode = mode
        self.command_host = command_host
        self.command_port = command_port
        self.telemetry_host = telemetry_host
        self.telemetry_port = telemetry_port
        self.runtime = MockCoreRuntime() if mode == 'mock' else None
        self.ssl_context = create_client_ssl_context() if mode == 'core' else None
        self.read_only_mode = os.getenv('SPINE_READ_ONLY_MODE', '0').lower() in {'1', 'true', 'yes', 'on'}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self.phase = 0.0

        self.telemetry_cache = HeadlessTelemetryCache(self._lock)
        self.latest_by_topic = self.telemetry_cache.latest_by_topic
        self.role_matrix = RoleMatrix()
        self.event_bus = EventBus()
        self.topic_registry = TopicRegistry(self.role_matrix)
        self.command_policy_service = CommandStatePolicyService(self.role_matrix)
        self.session_watcher = SessionDirWatcher()
        self.integrity_service = SessionIntegrityService()
        self.backend_control_plane_service = BackendControlPlaneService()
        self.deployment_profile_service = DeploymentProfileService()
        self.control_plane_aggregator = HeadlessControlPlaneAggregator(self.backend_control_plane_service, self.deployment_profile_service)
        self.session_intelligence = SessionIntelligenceService()
        self.evidence_seal_service = SessionEvidenceSealService()
        self.control_authority = ControlAuthorityService(
            strict_mode=os.getenv('SPINE_STRICT_CONTROL_AUTHORITY', '0').lower() in {'1', 'true', 'yes', 'on'},
            auto_issue_implicit_lease=os.getenv('SPINE_IMPLICIT_CONTROL_LEASE', '1').lower() not in {'0', 'false', 'no', 'off'},
        )
        self.runtime_config_snapshot_data: dict[str, Any] = {}
        self.session_context = HeadlessSessionContext()
        self.runtime_introspection = HeadlessRuntimeIntrospection(self)
        self.command_service = HeadlessCommandService(
            mode=self.mode,
            runtime=self.runtime,
            ssl_context=self.ssl_context,
            command_host=self.command_host,
            command_port=self.command_port,
            control_authority=self.control_authority,
            current_session_id=lambda: self._current_session_id,
            prepare_session_tracking=self.session_context.prepare_session_tracking,
            clear_current_session=self.session_context.clear_current_session,
            remember_recent_command=self._remember_recent_command_hook,
            record_command_journal=self.session_context.record_command_journal,
            store_runtime_messages=self._store_messages,
            deployment_profile_snapshot=lambda: self.deployment_profile_service.build_snapshot(RuntimeConfig.from_dict(self.runtime_config_snapshot_data or {})),
        )
        self.session_products = HeadlessSessionProductsReader(
            telemetry_cache=self.telemetry_cache,
            resolve_session_dir=self._resolve_session_dir,
            current_session_id=lambda: self._current_session_id,
            manifest_reader=self._read_manifest_if_available,
            json_reader=self._read_json,
            json_if_exists_reader=self._read_json_if_exists,
            jsonl_reader=self._read_jsonl,
            status_reader=self.runtime_introspection.status,
            derive_recovery_state=self._derive_recovery_state,
            command_policy_catalog=self.command_policy_catalog,
            integrity_service=self.integrity_service,
            session_intelligence=self.session_intelligence,
            evidence_seal_service=self.evidence_seal_service,
        )
        self.surface = HeadlessAdapterSurface(self)

    @property
    def _current_session_dir(self) -> Path | None:
        return self.session_context.current_session_dir

    @property
    def _current_session_id(self) -> str:
        return self.session_context.current_session_id

    def __getattr__(self, name: str):
        runtime_introspection = self.__dict__.get('runtime_introspection')
        command_service = self.__dict__.get('command_service')
        surface = self.__dict__.get('surface')
        event_bus = self.__dict__.get('event_bus')
        session_products = self.__dict__.get('session_products')
        if name.startswith('current_') and session_products is not None:
            attr = getattr(session_products, name, None)
            if attr is not None:
                return attr
        delegation = {
            'status': getattr(runtime_introspection, 'status', None),
            'health': getattr(runtime_introspection, 'health', None),
            'schema': getattr(runtime_introspection, 'schema', None),
            'topic_catalog': getattr(runtime_introspection, 'topic_catalog', None),
            'role_catalog': getattr(runtime_introspection, 'role_catalog', None),
            'command_policy_catalog': getattr(runtime_introspection, 'command_policy_catalog', None),
            'control_authority_status': getattr(runtime_introspection, 'control_authority_status', None),
            'recent_commands': getattr(command_service, 'recent_commands', None),
            'command': getattr(command_service, 'command', None),
            'snapshot': getattr(surface, 'snapshot', None),
            'control_plane_status': getattr(surface, 'control_plane_status', None),
            'replay_events': getattr(surface, 'replay_events', None),
            'event_bus_stats': getattr(event_bus, 'stats', None),
            'event_dead_letters': getattr(event_bus, 'dead_letters', None),
            'event_delivery_audit': getattr(event_bus, 'delivery_audit', None),
            'subscribe': getattr(surface, 'subscribe', None),
            'unsubscribe': getattr(surface, 'unsubscribe', None),
            'iter_events': getattr(surface, 'iter_events', None),
            'camera_frame': getattr(surface, 'camera_frame', None),
            'ultrasound_frame': getattr(surface, 'ultrasound_frame', None),
        }
        if delegation.get(name) is not None:
            return delegation[name]
        raise AttributeError(f"{type(self).__name__!s} has no attribute {name!r}")

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        target = self.surface.mock_loop if self.mode == 'mock' else self.surface.core_loop
        self._thread = threading.Thread(target=target, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self.event_bus.close()

    def acquire_control_lease(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = dict(payload or {})
        profile = self.deployment_profile_service.build_snapshot(RuntimeConfig.from_dict(self.runtime_config_snapshot_data or {})).get('name', 'dev')
        return self.control_authority.acquire(
            actor_id=str(data.get('actor_id', '')),
            role=str(data.get('role', 'operator')),
            workspace=str(data.get('workspace', 'desktop')),
            session_id=str(data.get('session_id', self._current_session_id)),
            intent_reason=str(data.get('intent_reason', '')),
            deployment_profile=str(data.get('profile', profile)),
            ttl_s=int(data.get('ttl_s', self.control_authority.lease_ttl_s) or self.control_authority.lease_ttl_s),
            source=str(data.get('source', 'api')),
            preempt=bool(data.get('preempt', False)),
            preempt_reason=str(data.get('preempt_reason', '')),
        )

    def renew_control_lease(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = dict(payload or {})
        return self.control_authority.renew(
            lease_id=str(data.get('lease_id', '')),
            actor_id=str(data.get('actor_id', '')) or None,
            ttl_s=int(data.get('ttl_s', self.control_authority.lease_ttl_s) or self.control_authority.lease_ttl_s),
        )

    def release_control_lease(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = dict(payload or {})
        return self.control_authority.release(
            lease_id=str(data.get('lease_id', '')) or None,
            actor_id=str(data.get('actor_id', '')) or None,
            reason=str(data.get('reason', '')),
        )

    def set_runtime_config(self, config_payload: dict[str, Any]) -> dict[str, Any]:
        self.runtime_config_snapshot_data = dict(config_payload or {})
        if self.runtime is not None:
            self.runtime.update_runtime_config(RuntimeConfig.from_dict(self.runtime_config_snapshot_data))
            self._store_messages(self.runtime.telemetry_snapshot())
        return {'runtime_config': dict(self.runtime_config_snapshot_data), 'backend_mode': self.mode}

    def runtime_config(self) -> dict[str, Any]:
        return {'runtime_config': dict(self.runtime_config_snapshot_data), 'backend_mode': self.mode}

    def _remember_recent_command_hook(self, command: str, payload: dict[str, Any], reply: ReplyEnvelope) -> None:
        return None

    def _store_messages(self, messages) -> None:
        self.surface.store_messages(messages)

    def _resolve_session_dir(self) -> Path | None:
        return self.session_context.resolve_session_dir(self.runtime.session_dir if self.runtime is not None else None)

    def _read_json(self, path: Path) -> dict[str, Any]:
        return self.session_context.read_json(path)

    def _read_json_if_exists(self, path: Path) -> dict[str, Any]:
        return self.session_context.read_json_if_exists(path)

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        return self.session_context.read_jsonl(path)

    def _read_manifest_if_available(self, session_dir: Path | None = None) -> dict[str, Any]:
        return self.session_context.read_manifest_if_available(session_dir or self._resolve_session_dir())

    def _derive_recovery_state(self, core: dict[str, Any]) -> str:
        return self.session_context.derive_recovery_state(core)
