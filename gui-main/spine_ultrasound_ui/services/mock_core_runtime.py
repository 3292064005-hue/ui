from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

from spine_ultrasound_ui.core.session_recorders import JsonlRecorder
from spine_ultrasound_ui.models import RuntimeConfig, ScanPlan, SystemState
from spine_ultrasound_ui.services.force_control_config import load_force_control_config
from spine_ultrasound_ui.services.clinical_config_service import ClinicalConfigService
from spine_ultrasound_ui.services.sdk_capability_service import SdkCapabilityService
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope, TelemetryEnvelope
from spine_ultrasound_ui.services.pressure_sensor_service import ForceSensorProvider, create_force_sensor_provider
from spine_ultrasound_ui.services.robot_identity_service import RobotIdentityService
from spine_ultrasound_ui.utils.sdk_unit_contract import build_sdk_boundary_contract
from spine_ultrasound_ui.services.xmate_model_service import XMateModelService
from spine_ultrasound_ui.services.mainline_task_tree_service import MainlineTaskTreeService
from spine_ultrasound_ui.utils import ensure_dir, now_ns
from spine_ultrasound_ui.utils.runtime_fingerprint import payload_hash


class MockCoreRuntime:
    def __init__(self) -> None:
        self.config = RuntimeConfig()
        self.force_control = load_force_control_config()
        self.execution_state = SystemState.DISCONNECTED
        self.controller_online = False
        self.powered = False
        self.operate_mode = "manual"
        self.fault_code = ""
        self.session_id = ""
        self.session_dir: Optional[Path] = None
        self.scan_plan: Optional[dict] = None
        self.phase = 0.0
        self.frame_id = 0
        self.path_index = 0
        self.progress_pct = 0.0
        self.active_segment = 0
        self.pressure_current = 0.0
        self.contact_mode = "NO_CONTACT"
        self.contact_confidence = 0.0
        self.contact_stable = False
        self.recommended_action = "IDLE"
        self.plan_hash = ""
        self.locked_runtime_config_hash = ""
        self.locked_sdk_boundary_hash = ""
        self.locked_executor_hash = ""
        self.recovery_reason = ""
        self.last_recovery_action = ""
        self.image_quality = 0.82
        self.feature_confidence = 0.76
        self.quality_score = 0.79
        self.last_event = "-"
        self.last_controller_log = "-"
        self.controller_logs: list[dict[str, Any]] = [
            {"level": "INFO", "message": "mock runtime booted", "source": "runtime"},
        ]
        self.rl_projects: list[dict[str, Any]] = [
            {"name": "spine_mainline", "tasks": ["scan", "prep", "retreat"]},
            {"name": "spine_research", "tasks": ["sweep", "contact_probe"]},
        ]
        self.rl_status = {"loaded_project": "", "loaded_task": "", "running": False, "rate": 1.0, "loop": False}
        self.path_library: list[dict[str, Any]] = [
            {"name": "spine_demo_path", "rate": 0.5, "points": 128},
            {"name": "thoracic_followup", "rate": 0.4, "points": 92},
        ]
        self.drag_state = {"enabled": False, "space": "cartesian", "type": "admittance"}
        self.io_state = {
            "di": {"board0_port0": False, "board0_port1": True},
            "do": {"board0_port0": False, "board0_port1": False},
            "ai": {"board0_port0": 0.12},
            "ao": {"board0_port0": 0.0},
            "registers": {"spine.session.segment": 0, "spine.session.frame": 0},
        }
        self.retreat_ticks_remaining = 0
        self.dropped_samples = 0
        self.last_flush_ns = 0
        self.recorders: dict[str, JsonlRecorder] = {}
        self.device_roster: Dict[str, Any] = {}
        self.tool_ready = False
        self.tcp_ready = False
        self.load_ready = False
        self.pressure_fresh = False
        self.robot_state_fresh = False
        self.rt_jitter_ok = True
        self.force_sensor_provider_name = "mock_force_sensor"
        self.force_sensor_provider: ForceSensorProvider = create_force_sensor_provider(self.force_sensor_provider_name)
        self.force_sensor_status = "ok"
        self.force_sensor_source = self.force_sensor_provider_name
        self.force_sensor_stale_ticks = 0
        self.force_sensor_timeout_alarm = False
        self.force_sensor_estop_alarm = False
        self.devices = {
            "robot": self._device(False, "offline", "xMate3 控制器未连接"),
            "camera": self._device(False, "offline", "摄像头未连接"),
            "pressure": self._device(False, "offline", "压力传感器未连接"),
            "ultrasound": self._device(False, "offline", "超声设备未连接"),
        }
        self.tcp_pose = {"x": 0.0, "y": 0.0, "z": 240.0, "rx": 180.0, "ry": 0.0, "rz": 90.0}
        self.joint_pos = [0.0] * 6
        self.joint_vel = [0.0] * 6
        self.joint_torque = [0.0] * 6
        self.cart_force = [0.0] * 6
        self.pending_alarms: list[dict[str, Any]] = []
        self.model_service = XMateModelService()
        self.mainline_task_tree = MainlineTaskTreeService()
        self.identity_service = RobotIdentityService()
        self.clinical_config_service = ClinicalConfigService()
        self.capability_service = SdkCapabilityService()
        self.last_final_verdict: dict[str, Any] = {}
        self.session_locked_ts_ns = 0
        self.locked_scan_plan_hash = ""
        self.injected_faults: set[str] = set()

    def update_runtime_config(self, config: RuntimeConfig) -> None:
        self.config = config
        self.force_sensor_provider_name = config.force_sensor_provider
        self.force_sensor_provider = create_force_sensor_provider(config.force_sensor_provider)
        self._append_controller_log("INFO", f"runtime config updated: rt_mode={config.rt_mode}, collision={config.collision_detection_enabled}, soft_limit={config.soft_limit_enabled}")

    def handle_command(self, command: str, payload: Optional[dict] = None) -> ReplyEnvelope:
        payload = payload or {}
        handler = getattr(self, f"_cmd_{command}", None)
        if handler is None:
            return ReplyEnvelope(ok=False, message=f"unsupported command: {command}")
        return handler(payload)

    def tick(self) -> list[TelemetryEnvelope]:
        self.phase += 0.15
        self.frame_id += 1
        self.image_quality = 0.78 + 0.12 * math.sin(self.phase * 0.7)
        self.feature_confidence = 0.74 + 0.10 * math.cos(self.phase * 0.45)
        self.quality_score = round((self.image_quality + self.feature_confidence) / 2.0, 3)
        self._update_robot_kinematics()
        if 'overpressure' in self.injected_faults and self.execution_state in {SystemState.CONTACT_STABLE, SystemState.SCANNING, SystemState.PAUSED_HOLD}:
            self.pressure_current = max(self.config.pressure_upper + 0.5, self.force_control['max_z_force_n'] + 0.5)
        if 'pressure_stale' in self.injected_faults:
            self.force_sensor_stale_ticks = max(self.force_sensor_stale_ticks, 1)
        if 'rt_jitter_high' in self.injected_faults:
            self.rt_jitter_ok = False
        self._update_contact_and_progress()
        ts_ns = now_ns()
        self._refresh_device_health(ts_ns)
        self._record_core_streams(ts_ns)
        return self.telemetry_snapshot(ts_ns=ts_ns)

    def telemetry_snapshot(self, ts_ns: Optional[int] = None) -> list[TelemetryEnvelope]:
        ts_ns = ts_ns or now_ns()
        messages = [
            TelemetryEnvelope(
                topic="core_state",
                ts_ns=ts_ns,
                data={
                    "execution_state": self.execution_state.value,
                    "armed": bool(self.session_id and self.scan_plan and self.execution_state not in {SystemState.FAULT, SystemState.ESTOP}),
                    "fault_code": self.fault_code,
                    "active_segment": self.active_segment,
                    "progress_pct": self.progress_pct,
                    "session_id": self.session_id,
                    "recovery_state": self._recovery_state(),
                    "plan_hash": self.plan_hash,
                    "contact_stable": self.contact_stable,
                },
            ),
            TelemetryEnvelope(
                topic="robot_state",
                ts_ns=ts_ns,
                data={
                    "powered": self.powered,
                    "operate_mode": self.operate_mode,
                    "joint_pos": self.joint_pos,
                    "joint_vel": self.joint_vel,
                    "joint_torque": self.joint_torque,
                    "cart_force": self.cart_force,
                    "tcp_pose": self.tcp_pose,
                    "last_event": self.last_event,
                    "last_controller_log": self.last_controller_log,
                    "rl_status": dict(self.rl_status),
                    "drag_state": dict(self.drag_state),
                },
            ),
            TelemetryEnvelope(
                topic="contact_state",
                ts_ns=ts_ns,
                data={
                    "mode": self.contact_mode,
                    "confidence": self.contact_confidence,
                    "pressure_current": self.pressure_current,
                    "recommended_action": self.recommended_action,
                    "contact_stable": self.contact_stable,
                },
            ),
            TelemetryEnvelope(
                topic="scan_progress",
                ts_ns=ts_ns,
                data={
                    "active_segment": self.active_segment,
                    "path_index": self.path_index,
                    "overall_progress": self.progress_pct,
                    "frame_id": self.frame_id,
                },
            ),
            TelemetryEnvelope(topic="device_health", ts_ns=ts_ns, data={"devices": self.devices}),
            TelemetryEnvelope(topic="safety_status", ts_ns=ts_ns, data=self._safety_status()),
            TelemetryEnvelope(
                topic="recording_status",
                ts_ns=ts_ns,
                data={
                    "session_id": self.session_id,
                    "recording": bool(self.recorders),
                    "dropped_samples": self.dropped_samples,
                    "last_flush_ns": self.last_flush_ns,
                },
            ),
            TelemetryEnvelope(
                topic="quality_feedback",
                ts_ns=ts_ns,
                data={
                    "image_quality": self.image_quality,
                    "feature_confidence": self.feature_confidence,
                    "quality_score": self.quality_score,
                    "need_resample": self.quality_score < self.config.image_quality_threshold,
                },
            ),
        ]
        for alarm in self.pending_alarms:
            messages.append(TelemetryEnvelope(topic="alarm_event", ts_ns=ts_ns, data=alarm))
        self.pending_alarms.clear()
        return messages


    def _runtime_alignment_payload(self) -> dict[str, Any]:
        return {
            "sdk_family": "ROKAE xCore SDK (C++)",
            "robot_model": self.config.robot_model,
            "sdk_robot_class": self.config.sdk_robot_class,
            "axis_count": self.config.axis_count,
            "remote_ip": self.config.remote_ip,
            "local_ip": self.config.local_ip,
            "preferred_link": self.config.preferred_link,
            "rt_mode": self.config.rt_mode,
            "single_control_source": self.config.requires_single_control_source,
            "source": "mock_runtime_contract",
            "sdk_available": False,
        }

    def _xmate_model_summary_payload(self) -> dict[str, Any]:
        profile = self.model_service.profile
        return {
            "robot_model": profile.robot_model,
            "sdk_robot_class": profile.sdk_robot_class,
            "axis_count": profile.axis_count,
            "dh_parameters": [item.to_dict() for item in profile.dh_parameters],
            "supported_rt_modes": list(profile.supported_rt_modes),
            "clinical_mainline_mode": profile.rt_mode,
            "approximate": True,
            "source": "python_profile_contract",
            "duplication_policy": "desktop_advisory_only__official_fk_ik_jacobian_torque_stay_in_cpp_runtime",
        }

    def _identity_payload(self) -> dict[str, Any]:
        identity = self.identity_service.resolve(self.config.robot_model, self.config.sdk_robot_class, self.config.axis_count)
        return identity.to_dict()

    def _clinical_mainline_contract_payload(self) -> dict[str, Any]:
        identity = self.identity_service.resolve(self.config.robot_model, self.config.sdk_robot_class, self.config.axis_count)
        return {
            "robot_model": identity.robot_model,
            "clinical_mainline_mode": identity.rt_mode,
            "required_sequence": ["connect_robot", "power_on", "set_auto_mode", "lock_session", "load_scan_plan", "approach_prescan", "seek_contact", "start_scan", "safe_retreat"],
            "single_control_source_required": identity.requires_single_control_source,
            "preferred_link": identity.preferred_link,
            "rt_loop_hz": 1000,
            "cartesian_impedance_limits": list(identity.cartesian_impedance_limits),
            "desired_wrench_limits": list(identity.desired_wrench_limits),
        }

    def _runtime_profile_payload(self) -> dict[str, Any]:
        return {
            "robot_model": self.config.robot_model,
            "sdk_robot_class": self.config.sdk_robot_class,
            "axis_count": int(self.config.axis_count),
            "remote_ip": self.config.remote_ip,
            "local_ip": self.config.local_ip,
            "preferred_link": self.config.preferred_link,
            "rt_mode": self.config.rt_mode,
            "rt_network_tolerance_percent": int(self.config.rt_network_tolerance_percent),
            "joint_filter_hz": float(self.config.joint_filter_hz),
            "cart_filter_hz": float(self.config.cart_filter_hz),
            "torque_filter_hz": float(self.config.torque_filter_hz),
            "collision_detection_enabled": bool(self.config.collision_detection_enabled),
            "soft_limit_enabled": bool(self.config.soft_limit_enabled),
            "tool_name": self.config.tool_name,
            "tcp_name": self.config.tcp_name,
            "load_kg": float(self.config.load_kg),
            "cartesian_impedance": list(self.config.cartesian_impedance),
            "desired_wrench_n": list(self.config.desired_wrench_n),
        }

    def _executor_profile_payload(self) -> dict[str, Any]:
        executor = self._mainline_executor_contract_payload()
        return {
            "nrt_templates": [item.get("name", "") for item in executor.get("nrt_executor", {}).get("templates", [])],
            "rt_nominal_loop_hz": int(executor.get("rt_executor", {}).get("nominal_loop_hz", 1000) or 1000),
            "rt_monitors": {
                "reference_limiter": bool(executor.get("rt_executor", {}).get("reference_limiter_enabled", False)),
                "freshness_guard": bool(executor.get("rt_executor", {}).get("freshness_guard_enabled", False)),
                "jitter_monitor": bool(executor.get("rt_executor", {}).get("jitter_monitor_enabled", False)),
                "contact_band_monitor": bool(executor.get("rt_executor", {}).get("contact_band_monitor_enabled", False)),
            },
        }

    def _hardware_lifecycle_contract_payload(self) -> dict[str, Any]:
        lifecycle_state = 'boot'
        if self.controller_online:
            lifecycle_state = 'connected'
        if self.controller_online and self.powered:
            lifecycle_state = 'powered'
        if self.controller_online and self.powered and self.operate_mode == 'AUTO':
            lifecycle_state = 'auto_ready'
        if self.execution_state in {SystemState.CONTACT_SEEKING, SystemState.CONTACT_STABLE, SystemState.SCANNING, SystemState.PAUSED_HOLD}:
            lifecycle_state = 'rt_active'
        elif self.execution_state in {SystemState.PATH_VALIDATED, SystemState.APPROACHING, SystemState.RETREATING, SystemState.SCAN_COMPLETE}:
            lifecycle_state = 'nrt_ready'
        state_channel_ready = bool(self.controller_online)
        motion_channel_ready = bool(self.controller_online and self.powered)
        aux_channel_ready = bool(self.controller_online)
        live_takeover = bool(self.controller_online and self.powered and self.operate_mode == 'AUTO')
        return {
            'summary_state': 'warning' if not live_takeover else 'ready',
            'summary_label': 'hardware lifecycle ready' if live_takeover else 'hardware lifecycle contract only',
            'detail': 'Mock runtime exposes hardware-layer lifecycle and channel readiness without claiming live SDK control.',
            'runtime_source': 'mock_runtime_contract',
            'sdk_binding_mode': 'contract_only',
            'lifecycle_state': lifecycle_state,
            'controller_manager_model': 'hardware_layer__read_update_write',
            'transport_ready': bool(self.controller_online),
            'motion_channel_ready': motion_channel_ready,
            'state_channel_ready': state_channel_ready,
            'aux_channel_ready': aux_channel_ready,
            'live_takeover_ready': live_takeover,
            'single_control_source_required': bool(self.config.requires_single_control_source),
        }

    def _rt_kernel_contract_payload(self) -> dict[str, Any]:
        executor = self._mainline_executor_contract_payload()
        rt_executor = dict(executor.get('rt_executor', {}))
        jitter_budget_ms = round(max(0.25, 1000.0 / float(rt_executor.get('nominal_loop_hz', 1000) or 1000) * 0.2), 3)
        freshness_budget_ms = int(self.config.pressure_stale_ms)
        return {
            'summary_state': 'warning' if not self.controller_online else 'ready',
            'summary_label': 'rt kernel wrapped by official sdk lifecycle' if self.controller_online else 'rt kernel contract only',
            'detail': 'RT kernel follows read/update/write staging and keeps limiter/guard semantics outside the official controller.',
            'runtime_source': 'mock_runtime_contract',
            'nominal_loop_hz': int(rt_executor.get('nominal_loop_hz', 1000) or 1000),
            'read_update_write': ['read_state', 'update_phase_policy', 'write_command'],
            'phase': str(rt_executor.get('phase', 'idle')),
            'monitors': {
                'reference_limiter': bool(rt_executor.get('reference_limiter_enabled', False)),
                'freshness_guard': bool(rt_executor.get('freshness_guard_enabled', False)),
                'jitter_monitor': bool(rt_executor.get('jitter_monitor_enabled', False)),
                'contact_band_monitor': bool(rt_executor.get('contact_band_monitor_enabled', False)),
            },
            'jitter_budget_ms': jitter_budget_ms,
            'freshness_budget_ms': freshness_budget_ms,
            'reference_limits': {
                'max_cart_step_mm': 2.5,
                'max_force_delta_n': 1.0,
            },
            'degraded_without_sdk': True,
        }

    def _session_drift_contract_payload(self) -> dict[str, Any]:
        runtime_profile_hash = payload_hash(self._runtime_profile_payload())
        sdk_boundary = build_sdk_boundary_contract(fc_frame_matrix=self.config.fc_frame_matrix, tcp_frame_matrix=self.config.tcp_frame_matrix, load_com_mm=self.config.load_com_mm)
        sdk_boundary_hash = str(sdk_boundary.get('contract_hash', '')) or payload_hash(sdk_boundary)
        executor_hash = payload_hash(self._executor_profile_payload())
        drifts: list[dict[str, Any]] = []
        if self.session_id:
            if self.locked_runtime_config_hash and self.locked_runtime_config_hash != runtime_profile_hash:
                drifts.append({'name': 'runtime_profile_hash', 'detail': 'runtime config drifted after session lock'})
            if self.locked_sdk_boundary_hash and self.locked_sdk_boundary_hash != sdk_boundary_hash:
                drifts.append({'name': 'sdk_boundary_hash', 'detail': 'sdk boundary/unit contract drifted after session lock'})
            if self.locked_executor_hash and self.locked_executor_hash != executor_hash:
                drifts.append({'name': 'executor_profile_hash', 'detail': 'executor profile drifted after session lock'})
            if self.locked_scan_plan_hash and self.plan_hash and self.locked_scan_plan_hash != self.plan_hash:
                drifts.append({'name': 'plan_hash', 'detail': 'locked plan hash does not match active plan hash'})
        summary_state = 'ready' if not drifts else 'blocked'
        return {
            'summary_state': summary_state,
            'summary_label': 'hard freeze consistent' if summary_state == 'ready' else 'hard freeze drift detected',
            'detail': 'Session hard freeze watches runtime profile, SDK boundary contract, executor profile, and plan hash.',
            'session_locked': bool(self.session_id),
            'locked_runtime_config_hash': self.locked_runtime_config_hash,
            'active_runtime_config_hash': runtime_profile_hash,
            'locked_sdk_boundary_hash': self.locked_sdk_boundary_hash,
            'active_sdk_boundary_hash': sdk_boundary_hash,
            'locked_executor_hash': self.locked_executor_hash,
            'active_executor_hash': executor_hash,
            'locked_scan_plan_hash': self.locked_scan_plan_hash,
            'active_plan_hash': self.plan_hash,
            'drifts': drifts,
        }

    def _session_freeze_payload(self) -> dict[str, Any]:
        runtime_profile_hash = payload_hash(self._runtime_profile_payload())
        sdk_boundary = build_sdk_boundary_contract(fc_frame_matrix=self.config.fc_frame_matrix, tcp_frame_matrix=self.config.tcp_frame_matrix, load_com_mm=self.config.load_com_mm)
        executor_hash = payload_hash(self._executor_profile_payload())
        return {
            "session_locked": bool(self.session_id),
            "session_id": self.session_id,
            "session_dir": str(self.session_dir) if self.session_dir else "",
            "locked_at_ns": int(self.session_locked_ts_ns),
            "plan_hash": self.plan_hash,
            "active_segment": int(self.active_segment),
            "tool_name": self.config.tool_name,
            "tcp_name": self.config.tcp_name,
            "load_kg": self.config.load_kg,
            "rt_mode": self.config.rt_mode,
            "cartesian_impedance": list(self.config.cartesian_impedance),
            "desired_wrench_n": list(self.config.desired_wrench_n),
            "freeze_version": "hard_freeze_v2",
            "runtime_profile_hash": runtime_profile_hash,
            "sdk_boundary_hash": str(sdk_boundary.get('contract_hash', '')),
            "executor_profile_hash": executor_hash,
        }

    def _control_governance_contract_payload(self) -> dict[str, Any]:
        session_locked = bool(self.session_id)
        drift_contract = self._session_drift_contract_payload()
        runtime_binding_valid = session_locked and not drift_contract.get('drifts')
        return {
            "single_control_source_required": bool(self.config.requires_single_control_source),
            "control_authority_expected_source": "cpp_robot_core",
            "write_surface": "core_runtime_only",
            "current_execution_state": self.execution_state.value,
            "controller_online": bool(self.controller_online),
            "powered": bool(self.powered),
            "automatic_mode": self.operate_mode == "AUTO",
            "session_binding_valid": runtime_binding_valid,
            "runtime_config_bound": session_locked,
            "session_id": self.session_id,
            "active_plan_hash": self.plan_hash,
            "locked_scan_plan_hash": self.locked_scan_plan_hash,
            "tool_ready": bool(self.tool_ready),
            "tcp_ready": bool(self.tcp_ready),
            "load_ready": bool(self.load_ready),
            "rt_ready": bool(self.controller_online and self.powered and self.operate_mode == "AUTO" and self.config.rt_mode == "cartesianImpedance"),
            "nrt_ready": bool(self.controller_online and self.powered),
            "lifecycle_state": self._hardware_lifecycle_contract_payload().get('lifecycle_state', 'boot'),
            "detail": "single control source contract requires session freeze + AUTO + powered + contract-aligned rt mode + no hard-freeze drift",
        }

    def _controller_evidence_payload(self) -> dict[str, Any]:
        rt_kernel = self._rt_kernel_contract_payload()
        return {
            "runtime_source": "mock_runtime_contract",
            "last_event": self.last_event,
            "last_controller_log": self.last_controller_log,
            "controller_log_tail": list(self.controller_logs[-6:]),
            "rl_status": dict(self.rl_status),
            "drag_state": dict(self.drag_state),
            "registers": {"segment": int(self.active_segment), "frame": int(self.frame_id)},
            "pending_alarm_count": len(self.pending_alarms),
            "fault_code": self.fault_code,
            "last_nrt_profile": 'safe_retreat' if self.execution_state == SystemState.RETREATING else ('approach_prescan' if self.execution_state == SystemState.APPROACHING else ''),
            "last_rt_phase": str(rt_kernel.get('phase', 'idle')),
            "reason_chain": [
                item for item in [
                    self.last_event or '',
                    self.recovery_reason or '',
                    self.last_recovery_action or '',
                    self.fault_code or '',
                ] if item
            ],
        }



    def _dual_state_machine_contract_payload(self) -> dict[str, Any]:
        runtime_state = self.execution_state.value
        clinical_task_state = {
            'BOOT': 'boot',
            'DISCONNECTED': 'boot',
            'CONNECTED': 'startup',
            'POWERED': 'startup',
            'AUTO_READY': 'startup',
            'SESSION_LOCKED': 'session_locked',
            'PATH_VALIDATED': 'plan_validated',
            'APPROACHING': 'approaching',
            'CONTACT_SEEKING': 'seek_contact',
            'CONTACT_STABLE': 'contact_stable',
            'SCANNING': 'scan_follow',
            'PAUSED_HOLD': 'paused_hold',
            'RETREATING': 'controlled_retract',
            'SCAN_COMPLETE': 'completed',
            'FAULT': 'fault',
            'ESTOP': 'estop',
        }.get(runtime_state, 'boot')
        aligned = True
        detail = '执行状态机与临床任务状态机已通过映射规则对齐。'
        if runtime_state == 'SCANNING' and clinical_task_state != 'scan_follow':
            aligned = False
            detail = 'SCANNING 必须映射到 scan_follow。'
        execution_permissions = {
            'allow_nrt': runtime_state in {'AUTO_READY', 'SESSION_LOCKED', 'PATH_VALIDATED', 'SCAN_COMPLETE'},
            'allow_rt_seek': runtime_state in {'PATH_VALIDATED', 'APPROACHING', 'CONTACT_SEEKING'},
            'allow_rt_scan': runtime_state in {'CONTACT_STABLE', 'SCANNING', 'PAUSED_HOLD'},
            'allow_retract': runtime_state not in {'BOOT', 'DISCONNECTED', 'ESTOP'},
        }
        return {
            'summary_state': 'ready' if aligned else 'blocked',
            'summary_label': '双层状态机已对齐' if aligned else '双层状态机冲突',
            'detail': detail,
            'runtime_state': runtime_state,
            'clinical_task_state': clinical_task_state,
            'execution_and_clinical_aligned': aligned,
            'execution_permissions': execution_permissions,
        }
    
    def _mainline_executor_contract_payload(self) -> dict[str, Any]:
        runtime_state = self.execution_state.value
        rt_phase = {
            'APPROACHING': 'idle',
            'CONTACT_SEEKING': 'seek_contact',
            'CONTACT_STABLE': 'contact_hold',
            'SCANNING': 'scan_follow',
            'PAUSED_HOLD': 'pause_hold',
            'RETREATING': 'controlled_retract',
        }.get(runtime_state, 'idle')
        nrt_templates = [
            {'name': 'go_home', 'sdk_delegate': 'MoveAbsJ', 'blocking': True, 'preconditions': ['connected', 'powered']},
            {'name': 'approach_prescan', 'sdk_delegate': 'MoveL', 'blocking': True, 'preconditions': ['session_locked', 'plan_validated', 'auto_mode']},
            {'name': 'approach_entry', 'sdk_delegate': 'MoveL', 'blocking': True, 'preconditions': ['session_locked', 'plan_validated', 'auto_mode']},
            {'name': 'safe_retreat', 'sdk_delegate': 'MoveL', 'blocking': True, 'preconditions': ['connected', 'powered']},
        ]
        rt_executor = {
            'summary_state': 'warning' if not self.controller_online else 'ready',
            'detail': 'RT executor wraps official cartesianImpedance mainline and keeps limiter/guard semantics in the runtime shell.',
            'phase': rt_phase,
            'phase_group': 'scan' if rt_phase in {'contact_hold', 'scan_follow', 'pause_hold'} else ('recovery' if rt_phase == 'controlled_retract' else ('contact' if rt_phase == 'seek_contact' else 'idle')),
            'nominal_loop_hz': 1000,
            'reference_limiter_enabled': True,
            'freshness_guard_enabled': True,
            'jitter_monitor_enabled': True,
            'contact_band_monitor_enabled': True,
            'delegation_policy': 'official_sdk_rt_loop_only',
        }
        nrt_executor = {
            'summary_state': 'warning' if not self.controller_online else 'ready',
            'detail': 'NRT executor only submits templated MoveAbsJ/MoveL intents and delegates planning to the official SDK.',
            'templates': nrt_templates,
            'last_blocking_template': 'approach_prescan' if runtime_state == 'APPROACHING' else ('safe_retreat' if runtime_state == 'RETREATING' else ''),
            'delegation_policy': 'official_sdk_nrt_only',
        }
        task_tree_aligned = not (runtime_state == 'SCANNING' and rt_phase != 'scan_follow')
        return {
            'summary_state': 'ready' if task_tree_aligned else 'blocked',
            'summary_label': '主线执行器已对齐' if task_tree_aligned else '主线执行器未对齐',
            'detail': 'NRT/RT executor 合同描述的是意图、阶段与监测器，不替代官方控制器。',
            'task_tree_aligned': task_tree_aligned,
            'nrt_executor': nrt_executor,
            'rt_executor': rt_executor,
        }
    
    def _mainline_task_tree_payload(self) -> dict[str, Any]:
        return dict(self.mainline_task_tree.build(
            config=self.config,
            sdk_runtime={
                'control_governance_contract': self._control_governance_contract_payload(),
                'clinical_mainline_contract': self._clinical_mainline_contract_payload(),
                'release_contract': self._release_contract_payload(),
                'mainline_executor_contract': self._mainline_executor_contract_payload(),
                'dual_state_machine_contract': self._dual_state_machine_contract_payload(),
                'environment_doctor': {'summary_state': 'warning', 'summary_label': 'mock environment', 'detail': 'mock runtime; live SDK not attached'},
                'hardware_lifecycle_contract': self._hardware_lifecycle_contract_payload(),
                'rt_kernel_contract': self._rt_kernel_contract_payload(),
                'session_freeze': self._session_freeze_payload(),
                'session_drift_contract': self._session_drift_contract_payload(),
            },
            backend_link={},
            model_report={'final_verdict': dict(self.last_final_verdict.get('final_verdict', {}))},
            session_governance={'summary_state': 'ready' if self.session_id else 'warning'},
        ))


    def _capability_contract_payload(self) -> dict[str, Any]:
        robot_snapshot = {"operate_mode": self.operate_mode, "powered": self.powered}
        return dict(self.capability_service.build(self.config, robot_snapshot))

    def _model_authority_contract_payload(self) -> dict[str, Any]:
        identity = self.identity_service.resolve(self.config.robot_model, self.config.sdk_robot_class, self.config.axis_count)
        return {
            "authoritative_kernel": "cpp_robot_core",
            "runtime_source": "mock_runtime_contract",
            "robot_model": identity.robot_model,
            "sdk_robot_class": identity.sdk_robot_class,
            "planner_supported": bool(identity.supports_planner),
            "xmate_model_supported": bool(identity.supports_xmate_model),
            "authoritative_precheck": False,
            "approximate_advisory_allowed": True,
            "planner_primitives": ["JointMotionGenerator", "CartMotionGenerator", "FollowPosition"],
            "model_methods": ["robot.model()", "getCartPose", "getJointPos", "jacobian", "getTorque"],
            "warnings": [
                {"name": "model_authority", "detail": "mock runtime does not execute vendored C++ xMateModel / Planner"}
            ],
        }

    def _recovery_contract_payload(self) -> dict[str, Any]:
        return {
            "collision_behavior": self.config.collision_behavior,
            "pause_resume_enabled": True,
            "safe_retreat_enabled": True,
            "resume_force_band_n": self.force_control["resume_force_band_n"],
            "warning_z_force_n": self.force_control["warning_z_force_n"],
            "max_z_force_n": self.force_control["max_z_force_n"],
            "sensor_timeout_ms": self.force_control["sensor_timeout_ms"],
            "stale_telemetry_ms": self.force_control["stale_telemetry_ms"],
            "emergency_retract_mm": self.force_control["emergency_retract_mm"],
        }

    def _sdk_runtime_config_payload(self) -> dict[str, Any]:
        return {
            "robot_model": self.config.robot_model,
            "sdk_robot_class": self.config.sdk_robot_class,
            "remote_ip": self.config.remote_ip,
            "local_ip": self.config.local_ip,
            "axis_count": self.config.axis_count,
            "rt_network_tolerance_percent": self.config.rt_network_tolerance_percent,
            "joint_filter_hz": self.config.joint_filter_hz,
            "cart_filter_hz": self.config.cart_filter_hz,
            "torque_filter_hz": self.config.torque_filter_hz,
            "cartesian_impedance": list(self.config.cartesian_impedance),
            "desired_wrench_n": list(self.config.desired_wrench_n),
            "fc_frame_type": self.config.fc_frame_type,
            "fc_frame_matrix": list(self.config.fc_frame_matrix),
            "tcp_frame_matrix": list(self.config.tcp_frame_matrix),
            "load_com_mm": list(self.config.load_com_mm),
            "load_inertia": list(self.config.load_inertia),
            "sdk_boundary_units": build_sdk_boundary_contract(fc_frame_matrix=self.config.fc_frame_matrix, tcp_frame_matrix=self.config.tcp_frame_matrix, load_com_mm=self.config.load_com_mm),
        }


    def _release_contract_payload(self) -> dict[str, Any]:
        safety = self._safety_status()
        drift_contract = self._session_drift_contract_payload()
        hardware = self._hardware_lifecycle_contract_payload()
        freeze_consistent = bool(self.session_id) and bool(self.session_dir) and self.tool_ready and self.tcp_ready and self.load_ready and not drift_contract.get('drifts')
        final_verdict = dict(self.last_final_verdict.get("final_verdict", {}))
        blockers = list(self.last_final_verdict.get("blockers", []))
        warnings = list(self.last_final_verdict.get("warnings", []))
        if drift_contract.get('drifts'):
            blockers.append({'name': 'hard_freeze_drift', 'detail': 'session hard freeze drift detected'})
        if hardware.get('summary_state') in {'warning', 'degraded'}:
            warnings.append({'name': 'hardware_lifecycle_not_live', 'detail': str(hardware.get('detail', 'hardware lifecycle not live'))})
        release_allowed = bool(final_verdict.get("accepted")) and freeze_consistent and not safety.get("active_interlocks")
        return {
            "summary_state": 'ready' if release_allowed else ('blocked' if blockers or safety.get('active_interlocks') else 'warning'),
            "session_locked": bool(self.session_id),
            "session_freeze_consistent": freeze_consistent,
            "locked_scan_plan_hash": self.locked_scan_plan_hash,
            "active_plan_hash": self.plan_hash,
            "runtime_source": "mock_runtime_contract",
            "compile_ready": bool(final_verdict.get("accepted")) and freeze_consistent,
            "ready_for_approach": bool(final_verdict.get("accepted")) and freeze_consistent and self.execution_state == SystemState.PATH_VALIDATED,
            "ready_for_scan": bool(final_verdict.get("accepted")) and freeze_consistent and self.execution_state == SystemState.CONTACT_STABLE,
            "release_recommendation": "allow" if release_allowed else "block",
            "active_interlocks": list(safety.get("active_interlocks", [])),
            "final_verdict": final_verdict,
            "blockers": blockers,
            "warnings": warnings,
            "active_injections": sorted(self.injected_faults),
            'hardware_lifecycle': {'summary_state': hardware.get('summary_state', 'unknown'), 'lifecycle_state': hardware.get('lifecycle_state', 'boot')},
            'hard_freeze': {'summary_state': drift_contract.get('summary_state', 'unknown'), 'drift_count': len(drift_contract.get('drifts', []))},
        }


    def _deployment_contract_payload(self) -> dict[str, Any]:
        identity = self.identity_service.resolve(self.config.robot_model, self.config.sdk_robot_class, self.config.axis_count)
        return {
            "runtime_source": "mock_runtime_contract",
            "vendored_sdk_required": True,
            "vendored_sdk_detected": False,
            "xmate_model_detected": False,
            "preferred_link": identity.preferred_link,
            "single_control_source_required": identity.requires_single_control_source,
            "required_host_dependencies": ["cmake", "g++/clang++", "protobuf headers", "protoc", "openssl headers"],
            "required_runtime_materials": ["configs/tls/runtime/*", "vendored librokae include/lib/external"],
            "bringup_sequence": ["doctor_runtime.py", "generate_dev_tls_cert.sh", "start_real.sh", "run.py --backend core"],
            "systemd_units": ["spine-cpp-core.service", "spine-python-api.service", "spine-web-kiosk.service", "spine-ultrasound.target"],
            "summary_label": "mock deployment contract",
        }

    def _fault_injection_contract_payload(self) -> dict[str, Any]:
        catalog = [
            {"name": "pressure_stale", "effect": "forces stale telemetry watchdog and estop path", "phase_scope": ["CONTACT_SEEKING", "SCANNING", "PAUSED_HOLD"], "recoverable": False},
            {"name": "rt_jitter_high", "effect": "marks RT jitter interlock active", "phase_scope": ["CONTACT_SEEKING", "SCANNING", "PAUSED_HOLD"], "recoverable": True},
            {"name": "overpressure", "effect": "forces pressure above upper bound and pause/retreat logic", "phase_scope": ["CONTACT_STABLE", "SCANNING"], "recoverable": True},
            {"name": "collision_event", "effect": "injects recoverable collision alarm and retreat", "phase_scope": ["APPROACHING", "CONTACT_SEEKING", "SCANNING"], "recoverable": True},
            {"name": "plan_hash_mismatch", "effect": "breaks locked plan hash consistency", "phase_scope": ["SESSION_LOCKED", "PATH_VALIDATED"], "recoverable": True},
            {"name": "estop_latch", "effect": "forces ESTOP latched state", "phase_scope": ["*"], "recoverable": False},
        ]
        return {
            "runtime_source": "mock_runtime_contract",
            "enabled": True,
            "simulation_only": True,
            "active_injections": sorted(self.injected_faults),
            "catalog": catalog,
        }

    def _append_controller_log(self, level: str, message: str, source: str = "sdk") -> None:
        self.last_controller_log = f"{level}: {message}"
        self.controller_logs.insert(0, {"level": level, "message": message, "source": source})
        self.controller_logs = self.controller_logs[:40]

    def _cmd_query_controller_log(self, payload: dict) -> ReplyEnvelope:
        count = int(payload.get("count", 10) or 10)
        return ReplyEnvelope(ok=True, message="query_controller_log accepted", data={"logs": self.controller_logs[:max(1, count)]})

    def _cmd_query_rl_projects(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="query_rl_projects accepted", data={"projects": list(self.rl_projects), "status": dict(self.rl_status)})

    def _cmd_run_rl_project(self, payload: dict) -> ReplyEnvelope:
        project = str(payload.get("project", self.config.rl_project_name or "spine_mainline"))
        task = str(payload.get("task", self.config.rl_task_name or "scan"))
        candidates = {item["name"]: item for item in self.rl_projects}
        if project not in candidates:
            return ReplyEnvelope(ok=False, message=f"unknown RL project: {project}")
        if task not in list(candidates[project].get("tasks", [])):
            return ReplyEnvelope(ok=False, message=f"unknown RL task: {task}")
        self.rl_status.update({"loaded_project": project, "loaded_task": task, "running": True})
        self.execution_state = SystemState.AUTO_READY if self.execution_state in {SystemState.CONNECTED, SystemState.POWERED} else self.execution_state
        self._append_controller_log("INFO", f"RL project started: {project}/{task}")
        return ReplyEnvelope(ok=True, message="run_rl_project accepted", data={"status": dict(self.rl_status)})

    def _cmd_pause_rl_project(self, payload: dict) -> ReplyEnvelope:
        del payload
        self.rl_status["running"] = False
        self._append_controller_log("INFO", "RL project paused")
        return ReplyEnvelope(ok=True, message="pause_rl_project accepted", data={"status": dict(self.rl_status)})

    def _cmd_query_path_lists(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="query_path_lists accepted", data={"paths": list(self.path_library), "drag": dict(self.drag_state)})

    def _cmd_enable_drag(self, payload: dict) -> ReplyEnvelope:
        self.drag_state = {
            "enabled": True,
            "space": str(payload.get("space", "cartesian")),
            "type": str(payload.get("type", "admittance")),
        }
        self._append_controller_log("INFO", f"drag enabled: {self.drag_state['space']}/{self.drag_state['type']}")
        return ReplyEnvelope(ok=True, message="enable_drag accepted", data={"drag": dict(self.drag_state)})

    def _cmd_disable_drag(self, payload: dict) -> ReplyEnvelope:
        del payload
        self.drag_state["enabled"] = False
        self._append_controller_log("INFO", "drag disabled")
        return ReplyEnvelope(ok=True, message="disable_drag accepted", data={"drag": dict(self.drag_state)})

    def _cmd_replay_path(self, payload: dict) -> ReplyEnvelope:
        path_name = str(payload.get("name", "spine_demo_path"))
        match = next((item for item in self.path_library if item.get("name") == path_name), None)
        if match is None:
            return ReplyEnvelope(ok=False, message=f"unknown path: {path_name}")
        self._append_controller_log("INFO", f"path replay started: {path_name}")
        return ReplyEnvelope(ok=True, message="replay_path accepted", data={"path": dict(match)})

    def _cmd_get_io_snapshot(self, payload: dict) -> ReplyEnvelope:
        del payload
        snapshot = dict(self.io_state)
        snapshot["xpanel_vout_mode"] = self.config.xpanel_vout_mode
        return ReplyEnvelope(ok=True, message="get_io_snapshot accepted", data=snapshot)

    def _cmd_get_register_snapshot(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_register_snapshot accepted", data={"registers": dict(self.io_state.get("registers", {}))})

    def _cmd_get_safety_config(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(
            ok=True,
            message="get_safety_config accepted",
            data={
                "collision_detection_enabled": self.config.collision_detection_enabled,
                "collision_sensitivity": self.config.collision_sensitivity,
                "collision_behavior": self.config.collision_behavior,
                "collision_fallback_mm": self.config.collision_fallback_mm,
                "soft_limit_enabled": self.config.soft_limit_enabled,
                "joint_soft_limit_margin_deg": self.config.joint_soft_limit_margin_deg,
                "singularity_avoidance_enabled": self.config.singularity_avoidance_enabled,
            },
        )

    def _cmd_get_motion_contract(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(
            ok=True,
            message="get_motion_contract accepted",
            data={
                "rt_mode": self.config.rt_mode,
                "network_tolerance_percent": self.config.rt_network_tolerance_percent,
                "preferred_link": self.config.preferred_link,
                "filters": {
                    "joint_hz": self.config.joint_filter_hz,
                    "cart_hz": self.config.cart_filter_hz,
                    "torque_hz": self.config.torque_filter_hz,
                },
                "collision_behavior": self.config.collision_behavior,
                "collision_detection_enabled": self.config.collision_detection_enabled,
                "soft_limit_enabled": self.config.soft_limit_enabled,
                "sdk_boundary_units": build_sdk_boundary_contract(fc_frame_matrix=self.config.fc_frame_matrix, tcp_frame_matrix=self.config.tcp_frame_matrix, load_com_mm=self.config.load_com_mm),
            },
        )

    def _cmd_get_runtime_alignment(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_runtime_alignment accepted", data=self._runtime_alignment_payload())

    def _cmd_get_xmate_model_summary(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_xmate_model_summary accepted", data=self._xmate_model_summary_payload())

    def _cmd_get_sdk_runtime_config(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_sdk_runtime_config accepted", data=self._sdk_runtime_config_payload())


    def _cmd_get_identity_contract(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_identity_contract accepted", data=self._identity_payload())

    def _cmd_get_clinical_mainline_contract(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_clinical_mainline_contract accepted", data=self._clinical_mainline_contract_payload())

    def _cmd_get_session_freeze(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_session_freeze accepted", data=self._session_freeze_payload())

    def _cmd_get_session_drift_contract(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_session_drift_contract accepted", data=self._session_drift_contract_payload())

    def _cmd_get_hardware_lifecycle_contract(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_hardware_lifecycle_contract accepted", data=self._hardware_lifecycle_contract_payload())

    def _cmd_get_rt_kernel_contract(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_rt_kernel_contract accepted", data=self._rt_kernel_contract_payload())

    def _cmd_get_control_governance_contract(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_control_governance_contract accepted", data=self._control_governance_contract_payload())

    def _cmd_get_controller_evidence(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_controller_evidence accepted", data=self._controller_evidence_payload())

    def _cmd_get_dual_state_machine_contract(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_dual_state_machine_contract accepted", data=self._dual_state_machine_contract_payload())

    def _cmd_get_mainline_executor_contract(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_mainline_executor_contract accepted", data=self._mainline_executor_contract_payload())

    def _cmd_get_mainline_task_tree(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_mainline_task_tree accepted", data=self._mainline_task_tree_payload())

    def _cmd_get_recovery_contract(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_recovery_contract accepted", data=self._recovery_contract_payload())

    def _cmd_get_capability_contract(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_capability_contract accepted", data=self._capability_contract_payload())

    def _cmd_get_model_authority_contract(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_model_authority_contract accepted", data=self._model_authority_contract_payload())

    def _cmd_get_release_contract(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_release_contract accepted", data=self._release_contract_payload())

    def _cmd_get_deployment_contract(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_deployment_contract accepted", data=self._deployment_contract_payload())

    def _cmd_get_fault_injection_contract(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message="get_fault_injection_contract accepted", data=self._fault_injection_contract_payload())

    def _cmd_inject_fault(self, payload: dict) -> ReplyEnvelope:
        fault = str(payload.get("fault_name", "")).strip()
        if not fault:
            return ReplyEnvelope(ok=False, message="fault_name missing")
        self.injected_faults.add(fault)
        if fault == "pressure_stale":
            self.force_sensor_stale_ticks = max(self.force_sensor_stale_ticks, max(2, int(self.config.pressure_stale_ms / 100)))
            self.pressure_fresh = False
        elif fault == "rt_jitter_high":
            self.rt_jitter_ok = False
        elif fault == "overpressure":
            self.pressure_current = max(self.config.pressure_upper + 0.5, self.force_control["max_z_force_n"] + 0.5)
        elif fault == "collision_event":
            self.pending_alarms.append({
                "severity": "RECOVERABLE_FAULT", "source": "collision", "message": "模拟碰撞事件", "session_id": self.session_id,
                "segment_id": int(self.active_segment), "event_ts_ns": now_ns(), "workflow_step": "fault_injection", "request_id": "", "auto_action": "safe_retreat"
            })
            self.execution_state = SystemState.RETREATING
            self.retreat_ticks_remaining = max(self.retreat_ticks_remaining, 10)
        elif fault == "plan_hash_mismatch":
            self.plan_hash = f"mismatch:{self.plan_hash or 'empty'}"
        elif fault == "estop_latch":
            self.execution_state = SystemState.ESTOP
            self.fault_code = "ESTOP_INJECTED"
        else:
            self.injected_faults.discard(fault)
            return ReplyEnvelope(ok=False, message=f"unsupported fault injection: {fault}")
        self._append_controller_log("WARN", f"fault injected: {fault}", source="fault_injection")
        return ReplyEnvelope(ok=True, message="inject_fault accepted", data=self._fault_injection_contract_payload())

    def _cmd_clear_injected_faults(self, payload: dict) -> ReplyEnvelope:
        del payload
        self.injected_faults.clear()
        self.rt_jitter_ok = True
        self.force_sensor_stale_ticks = 0
        self.force_sensor_timeout_alarm = False
        self.force_sensor_estop_alarm = False
        if self.execution_state == SystemState.ESTOP and self.fault_code == "ESTOP_INJECTED":
            self.execution_state = SystemState.AUTO_READY if self.operate_mode == "automatic" and self.powered else (SystemState.POWERED if self.powered else SystemState.CONNECTED)
            self.fault_code = ""
        self._append_controller_log("INFO", "fault injections cleared", source="fault_injection")
        return ReplyEnvelope(ok=True, message="clear_injected_faults accepted", data=self._fault_injection_contract_payload())

    def _cmd_connect_robot(self, payload: dict) -> ReplyEnvelope:
        del payload
        if self.execution_state not in {SystemState.BOOT, SystemState.DISCONNECTED}:
            return ReplyEnvelope(ok=False, message="robot already connected")
        self.execution_state = SystemState.CONNECTED
        self.controller_online = True
        self.devices = {
            "robot": self._device(True, "online", "xMate3 robot_core 已连接"),
            "camera": self._device(True, "online", "摄像头在线"),
            "pressure": self._device(True, "online", f"压力传感器在线 ({self.force_sensor_provider_name})"),
            "ultrasound": self._device(True, "online", "超声设备在线"),
        }
        self.last_event = "robot_connected"
        self._append_controller_log("INFO", f"robot connected: remote={self.config.remote_ip} local={self.config.local_ip}")
        return ReplyEnvelope(ok=True, message="connect_robot accepted")

    def _cmd_disconnect_robot(self, payload: dict) -> ReplyEnvelope:
        del payload
        config = self.config
        self.__init__()
        self.config = config
        return ReplyEnvelope(ok=True, message="disconnect_robot accepted")

    def _cmd_power_on(self, payload: dict) -> ReplyEnvelope:
        del payload
        if self.execution_state == SystemState.DISCONNECTED:
            return ReplyEnvelope(ok=False, message="robot not connected")
        self.powered = True
        self.execution_state = SystemState.POWERED
        self.last_event = "power_on"
        self._append_controller_log("INFO", "power on")
        return ReplyEnvelope(ok=True, message="power_on accepted")

    def _cmd_power_off(self, payload: dict) -> ReplyEnvelope:
        del payload
        self.powered = False
        self.execution_state = SystemState.CONNECTED
        self.operate_mode = "manual"
        self.last_event = "power_off"
        return ReplyEnvelope(ok=True, message="power_off accepted")

    def _cmd_set_auto_mode(self, payload: dict) -> ReplyEnvelope:
        del payload
        if not self.powered:
            return ReplyEnvelope(ok=False, message="robot not powered")
        self.operate_mode = "automatic"
        self.execution_state = SystemState.AUTO_READY
        self._append_controller_log("INFO", "operate mode -> automatic")
        return ReplyEnvelope(ok=True, message="set_auto_mode accepted")

    def _cmd_set_manual_mode(self, payload: dict) -> ReplyEnvelope:
        del payload
        self.operate_mode = "manual"
        self.execution_state = SystemState.POWERED if self.powered else SystemState.CONNECTED
        return ReplyEnvelope(ok=True, message="set_manual_mode accepted")

    def _cmd_validate_setup(self, payload: dict) -> ReplyEnvelope:
        del payload
        safety = self._safety_status()
        ok = safety["safe_to_arm"]
        return ReplyEnvelope(ok=ok, message="setup validated" if ok else "setup invalid", data=safety)

    def _cmd_lock_session(self, payload: dict) -> ReplyEnvelope:
        if self.execution_state != SystemState.AUTO_READY:
            return ReplyEnvelope(ok=False, message="core not ready for session lock")
        self.session_id = str(payload.get("session_id", ""))
        if not self.session_id:
            return ReplyEnvelope(ok=False, message="session_id missing")
        self.locked_scan_plan_hash = str(payload.get("scan_plan_hash", ""))
        config_snapshot = dict(payload.get("config_snapshot", {}))
        if config_snapshot:
            self.config = RuntimeConfig.from_dict(config_snapshot)
        capability_report = self.capability_service.build(self.config, {"operate_mode": self.operate_mode, "powered": self.powered})
        blockers = list(capability_report.get("blockers", []))
        if blockers:
            self.session_id = ""
            self.locked_scan_plan_hash = ""
            return ReplyEnvelope(ok=False, message=str(blockers[0].get("detail", blockers[0].get("name", "configuration blocked"))))
        self.tool_ready = bool(self.config.tool_name)
        self.tcp_ready = bool(self.config.tcp_name)
        self.load_ready = self.config.load_kg > 0.0
        self.session_dir = ensure_dir(Path(str(payload.get("session_dir", "."))))
        self.device_roster = dict(payload.get("device_roster", {}))
        self.force_sensor_provider_name = str(payload.get("force_sensor_provider", self.config.force_sensor_provider))
        self.force_sensor_provider = create_force_sensor_provider(self.force_sensor_provider_name)
        self._open_recorders(self.session_dir, self.session_id)
        self.locked_runtime_config_hash = payload_hash(self._runtime_profile_payload())
        sdk_boundary = build_sdk_boundary_contract(fc_frame_matrix=self.config.fc_frame_matrix, tcp_frame_matrix=self.config.tcp_frame_matrix, load_com_mm=self.config.load_com_mm)
        self.locked_sdk_boundary_hash = str(sdk_boundary.get('contract_hash', ''))
        self.locked_executor_hash = payload_hash(self._executor_profile_payload())
        self.session_locked_ts_ns = now_ns()
        self.execution_state = SystemState.SESSION_LOCKED
        self._append_controller_log("INFO", f"session locked: {self.session_id}")
        self.recovery_reason = ""
        self.last_recovery_action = "session_locked"
        self.last_event = "session_locked"
        return ReplyEnvelope(ok=True, message="lock_session accepted", data={"session_id": self.session_id})

    def _cmd_load_scan_plan(self, payload: dict) -> ReplyEnvelope:
        if self.execution_state not in {SystemState.SESSION_LOCKED, SystemState.PATH_VALIDATED, SystemState.SCAN_COMPLETE}:
            return ReplyEnvelope(ok=False, message="session not locked")
        plan_payload = dict(payload.get("scan_plan", {}))
        validation_error = self._validate_scan_plan(plan_payload)
        if validation_error:
            return ReplyEnvelope(ok=False, message=validation_error)
        self.scan_plan = plan_payload
        self.plan_hash = self._plan_hash(plan_payload)
        if self.locked_scan_plan_hash and self.plan_hash and self.locked_scan_plan_hash != self.plan_hash:
            self.scan_plan = None
            self.plan_hash = ""
            return ReplyEnvelope(ok=False, message="locked scan_plan_hash does not match loaded plan")
        self.path_index = 0
        self.progress_pct = 0.0
        self.active_segment = 0
        self.execution_state = SystemState.PATH_VALIDATED
        self._append_controller_log("INFO", f"scan plan loaded: {plan_payload.get('plan_id', '-')}")
        self.contact_stable = False
        self.recovery_reason = ""
        self.last_recovery_action = "load_scan_plan"
        self.last_event = "scan_plan_loaded"
        return ReplyEnvelope(ok=True, message="load_scan_plan accepted", data={"plan_id": plan_payload.get("plan_id", "")})

    def _cmd_approach_prescan(self, payload: dict) -> ReplyEnvelope:
        del payload
        if self.execution_state != SystemState.PATH_VALIDATED:
            return ReplyEnvelope(ok=False, message="scan plan not ready")
        self.execution_state = SystemState.APPROACHING
        self.contact_stable = False
        self.recommended_action = "SEEK_CONTACT"
        return ReplyEnvelope(ok=True, message="approach_prescan accepted")

    def _cmd_seek_contact(self, payload: dict) -> ReplyEnvelope:
        del payload
        if self.execution_state not in {SystemState.APPROACHING, SystemState.PATH_VALIDATED}:
            return ReplyEnvelope(ok=False, message="cannot seek contact from current state")
        self.execution_state = SystemState.CONTACT_STABLE
        self.contact_mode = "STABLE_CONTACT"
        self.contact_confidence = 0.82
        self.contact_stable = True
        self.recommended_action = "START_SCAN"
        self.last_recovery_action = "contact_stable"
        return ReplyEnvelope(ok=True, message="seek_contact accepted")

    def _cmd_start_scan(self, payload: dict) -> ReplyEnvelope:
        del payload
        if self.execution_state not in {SystemState.CONTACT_STABLE, SystemState.PAUSED_HOLD}:
            return ReplyEnvelope(ok=False, message="cannot start scan before contact is stable")
        self.execution_state = SystemState.SCANNING
        self.contact_mode = "STABLE_CONTACT"
        self.contact_stable = True
        self.recovery_reason = ""
        self.last_recovery_action = "start_scan"
        self.recommended_action = "SCAN"
        self.last_event = "scan_started"
        self._append_controller_log("INFO", "scan started")
        return ReplyEnvelope(ok=True, message="start_scan accepted")

    def _cmd_pause_scan(self, payload: dict) -> ReplyEnvelope:
        del payload
        if self.execution_state != SystemState.SCANNING:
            return ReplyEnvelope(ok=False, message="scan not active")
        self.execution_state = SystemState.PAUSED_HOLD
        self.contact_mode = "HOLDING_CONTACT"
        self.contact_stable = True
        self.recovery_reason = "operator_pause"
        self.last_recovery_action = "pause_hold"
        self.recommended_action = "RESUME_OR_RETREAT"
        return ReplyEnvelope(ok=True, message="pause_scan accepted")

    def _cmd_resume_scan(self, payload: dict) -> ReplyEnvelope:
        del payload
        if self.execution_state != SystemState.PAUSED_HOLD:
            return ReplyEnvelope(ok=False, message="scan not paused")
        self.execution_state = SystemState.SCANNING
        self.contact_mode = "STABLE_CONTACT"
        self.contact_stable = True
        self.recovery_reason = ""
        self.last_recovery_action = "resume_scan"
        self.recommended_action = "SCAN"
        return ReplyEnvelope(ok=True, message="resume_scan accepted")

    def _cmd_safe_retreat(self, payload: dict) -> ReplyEnvelope:
        del payload
        if self.execution_state in {SystemState.DISCONNECTED, SystemState.BOOT, SystemState.ESTOP}:
            return ReplyEnvelope(ok=False, message="cannot retreat from current state")
        self.execution_state = SystemState.RETREATING
        self.retreat_ticks_remaining = 6
        self.contact_mode = "NO_CONTACT"
        self.contact_stable = False
        self.recovery_reason = "requested_safe_retreat"
        self.last_recovery_action = "safe_retreat"
        self.recommended_action = "WAIT_RETREAT_COMPLETE"
        self.last_event = "safe_retreat"
        self._append_controller_log("WARN", "safe retreat requested")
        return ReplyEnvelope(ok=True, message="safe_retreat accepted")

    def _cmd_go_home(self, payload: dict) -> ReplyEnvelope:
        del payload
        self.tcp_pose = {"x": 0.0, "y": 0.0, "z": 240.0, "rx": 180.0, "ry": 0.0, "rz": 90.0}
        self.last_event = "go_home"
        self._append_controller_log("INFO", "go home")
        return ReplyEnvelope(ok=True, message="go_home accepted")

    def _cmd_clear_fault(self, payload: dict) -> ReplyEnvelope:
        del payload
        if self.execution_state != SystemState.FAULT:
            return ReplyEnvelope(ok=False, message="no fault to clear")
        self.fault_code = ""
        self.execution_state = SystemState.PATH_VALIDATED if self.scan_plan else SystemState.AUTO_READY
        return ReplyEnvelope(ok=True, message="clear_fault accepted")

    def _cmd_emergency_stop(self, payload: dict) -> ReplyEnvelope:
        del payload
        self.execution_state = SystemState.ESTOP
        self.fault_code = "ESTOP"
        self.last_event = "emergency_stop"
        self._queue_alarm("FATAL_FAULT", "safety", "急停触发", workflow_step="emergency_stop", auto_action="estop")
        self._append_controller_log("ERROR", "emergency stop")
        return ReplyEnvelope(ok=True, message="emergency_stop accepted")

    def _update_robot_kinematics(self) -> None:
        self.joint_pos = [round(math.sin(self.phase * 0.1 + i * 0.2), 4) for i in range(6)]
        self.joint_vel = [round(0.08 * math.cos(self.phase * 0.2 + i * 0.15), 4) for i in range(6)]
        self.joint_torque = [round(0.45 * math.sin(self.phase * 0.16 + i * 0.18), 4) for i in range(6)]
        z_base = 240.0
        if self.execution_state == SystemState.APPROACHING:
            z_base = 220.0
        elif self.execution_state in {SystemState.CONTACT_SEEKING, SystemState.CONTACT_STABLE, SystemState.SCANNING, SystemState.PAUSED_HOLD}:
            z_base = 205.0
        elif self.execution_state == SystemState.RETREATING:
            z_base = 230.0
        self.tcp_pose = {
            "x": round(118.0 + 8.0 * math.sin(self.phase * 0.2), 2),
            "y": round(15.0 + 5.0 * math.cos(self.phase * 0.25), 2),
            "z": round(z_base + 2.5 * math.sin(self.phase * 0.33), 2),
            "rx": 180.0,
            "ry": round(0.3 * math.sin(self.phase), 3),
            "rz": 90.0,
        }

    def _update_contact_and_progress(self) -> None:
        force_sample = self.force_sensor_provider.read_sample(
            contact_active=self.execution_state in {SystemState.CONTACT_SEEKING, SystemState.CONTACT_STABLE, SystemState.SCANNING, SystemState.PAUSED_HOLD},
            desired_force_n=float(self.force_control["desired_contact_force_n"]),
        )
        self.force_sensor_status = force_sample.status
        self.force_sensor_source = force_sample.source
        measured_pressure = abs(float(force_sample.wrench_n[2])) if force_sample.status == "ok" else 0.0
        if force_sample.status == "ok":
            self.force_sensor_stale_ticks = 0
        else:
            self.force_sensor_stale_ticks += 1
        if self.execution_state == SystemState.CONTACT_SEEKING:
            self.pressure_current = round(max(measured_pressure, 0.0), 3)
            self.contact_mode = "SEEKING_CONTACT"
            self.contact_confidence = 0.72
            self.contact_stable = False
            self.recommended_action = "WAIT_CONTACT_STABLE"
        elif self.execution_state == SystemState.CONTACT_STABLE:
            self.pressure_current = round(measured_pressure if measured_pressure > 0.0 else self.config.pressure_target, 3)
            self.contact_mode = "STABLE_CONTACT"
            self.contact_confidence = 0.84
            self.contact_stable = True
            self.recommended_action = "START_SCAN"
        elif self.execution_state == SystemState.SCANNING:
            total_points = max(sum(len(segment.get("waypoints", [])) for segment in self.scan_plan.get("segments", [])) if self.scan_plan else 0, 120)
            self.path_index += 1
            self.progress_pct = min(100.0, self.progress_pct + 100.0 / total_points)
            self.active_segment = self._segment_for_path_index()
            self.pressure_current = round(measured_pressure if measured_pressure > 0.0 else self.config.pressure_target + 0.08 * math.sin(self.phase) + random.uniform(-0.03, 0.03), 3)
            self.contact_mode = "STABLE_CONTACT"
            self.contact_confidence = 0.87
            self.contact_stable = True
            self.recommended_action = "SCAN"
            if self.pressure_current > self.config.pressure_upper:
                self.execution_state = SystemState.PAUSED_HOLD
                self.contact_mode = "OVERPRESSURE"
                self.contact_stable = False
                self.recovery_reason = "pressure_over_upper_limit"
                self.last_recovery_action = "pause_hold"
                self.recommended_action = "CONTROLLED_RETRACT"
                self._queue_alarm(
                    "RECOVERABLE_FAULT",
                    "contact",
                    "压力超上限，已进入保持状态",
                    workflow_step="scan_monitor",
                    auto_action="pause_hold",
                )
            if self.progress_pct >= 100.0:
                self.execution_state = SystemState.SCAN_COMPLETE
                self.contact_mode = "NO_CONTACT"
                self.contact_stable = False
                self.recovery_reason = ""
                self.last_recovery_action = "scan_complete"
                self.recommended_action = "POSTPROCESS"
                self.last_event = "scan_complete"
        elif self.execution_state == SystemState.PAUSED_HOLD:
            self.pressure_current = round(measured_pressure if measured_pressure > 0.0 else max(self.config.pressure_target - 0.03, 0.0), 3)
            self.contact_mode = "HOLDING_CONTACT"
            self.contact_confidence = 0.75
            self.contact_stable = True
            self.recommended_action = "RESUME_OR_RETREAT"
        elif self.execution_state == SystemState.RETREATING:
            self.pressure_current = 0.0
            self.contact_confidence = 0.0
            self.contact_mode = "NO_CONTACT"
            self.contact_stable = False
            self.recommended_action = "WAIT_RETREAT_COMPLETE"
            self.retreat_ticks_remaining -= 1
            if self.retreat_ticks_remaining <= 0:
                self.execution_state = SystemState.PATH_VALIDATED if self.scan_plan else SystemState.AUTO_READY
                self.recovery_reason = ""
                self.last_recovery_action = "retreat_complete"
                self.recommended_action = "IDLE"
        else:
            self.pressure_current = max(0.0, measured_pressure)
            self.contact_confidence = 0.0
            self.contact_mode = "NO_CONTACT"
            self.contact_stable = False
            self.recommended_action = "IDLE"
        self.cart_force = [0.02, 0.01, round(self.pressure_current, 3), 0.0, 0.0, 0.0]
        self.io_state["registers"]["spine.session.segment"] = int(self.active_segment)
        self.io_state["registers"]["spine.session.frame"] = int(self.frame_id)

    def _segment_for_path_index(self) -> int:
        if not self.scan_plan:
            return 0
        segments = self.scan_plan.get("segments", [])
        if not segments:
            return 0
        points_seen = 0
        for segment in segments:
            points_seen += max(len(segment.get("waypoints", [])), 1)
            if self.path_index <= points_seen:
                return int(segment.get("segment_id", 0))
        return int(segments[-1].get("segment_id", 0))

    def _recovery_state(self) -> str:
        if self.execution_state == SystemState.ESTOP:
            return "ESTOP_LATCHED"
        if self.execution_state == SystemState.FAULT:
            return "CONTROLLED_RETRACT"
        if self.execution_state == SystemState.PAUSED_HOLD:
            return "HOLDING"
        if self.execution_state in {SystemState.RETREATING, SystemState.SCAN_COMPLETE, SystemState.CONTACT_STABLE}:
            return "RETRY_READY" if self.execution_state != SystemState.CONTACT_STABLE else "IDLE"
        return "IDLE"

    def _safety_status(self) -> dict[str, Any]:
        interlocks = []
        if not self.controller_online or self.execution_state in {SystemState.BOOT, SystemState.DISCONNECTED}:
            interlocks.append("controller_offline")
        if not self.powered:
            interlocks.append("power_off")
        if self.operate_mode != "automatic":
            interlocks.append("not_in_automatic_mode")
        if not self.tool_ready:
            interlocks.append("tool_unvalidated")
        if not self.tcp_ready:
            interlocks.append("tcp_unvalidated")
        if not self.load_ready:
            interlocks.append("load_unvalidated")
        if not self.session_id:
            interlocks.append("session_unlocked")
        if not self.scan_plan:
            interlocks.append("scan_plan_missing")
        if not self.pressure_fresh:
            interlocks.append("pressure_stale")
        if not self.robot_state_fresh:
            interlocks.append("robot_state_stale")
        if self.pressure_current > self.config.pressure_upper:
            interlocks.append("pressure_over_upper_limit")
        if not self.rt_jitter_ok:
            interlocks.append("rt_jitter_high")
        if self.execution_state in {SystemState.FAULT, SystemState.ESTOP}:
            interlocks.append("fault_active")
        safe_to_arm = self.powered and self.operate_mode == "automatic" and self.execution_state not in {SystemState.DISCONNECTED, SystemState.ESTOP}
        safe_to_scan = safe_to_arm and not {
            "session_unlocked",
            "scan_plan_missing",
            "pressure_over_upper_limit",
            "fault_active",
            "pressure_stale",
            "robot_state_stale",
            "tool_unvalidated",
            "tcp_unvalidated",
            "load_unvalidated",
            "rt_jitter_high",
        } & set(interlocks)
        return {
            "safe_to_arm": safe_to_arm,
            "safe_to_scan": safe_to_scan,
            "active_interlocks": interlocks,
            "recovery_reason": self.recovery_reason,
            "last_recovery_action": self.last_recovery_action,
            "max_z_force_n": self.force_control["max_z_force_n"],
            "warning_z_force_n": self.force_control["warning_z_force_n"],
            "max_xy_force_n": self.force_control["max_xy_force_n"],
            "desired_contact_force_n": self.force_control["desired_contact_force_n"],
            "collision_detection_enabled": self.config.collision_detection_enabled,
            "soft_limit_enabled": self.config.soft_limit_enabled,
            "singularity_avoidance_enabled": self.config.singularity_avoidance_enabled,
        }

    def _refresh_device_health(self, ts_ns: int) -> None:
        self.pressure_fresh = False
        self.robot_state_fresh = False
        stale_telemetry_ms = int(self.force_control["stale_telemetry_ms"])
        timeout_ms = int(self.force_control["sensor_timeout_ms"])
        current_stale_ms = self.force_sensor_stale_ticks * 100
        for name, device in self.devices.items():
            device["fresh"] = device["connected"]
            device["last_ts_ns"] = ts_ns if device["connected"] else 0
            if device["connected"] and name == "pressure":
                self.pressure_fresh = self.force_sensor_status == "ok" and current_stale_ms < stale_telemetry_ms
                device["fresh"] = self.pressure_fresh
                device["health"] = "online" if self.pressure_fresh else "degraded"
                device["detail"] = (
                    f"{self.force_sensor_source} fresh"
                    if self.pressure_fresh
                    else f"{self.force_sensor_source} stale ({current_stale_ms} ms)"
                )
            if device["connected"] and name == "robot":
                self.robot_state_fresh = True
            if self.execution_state in {SystemState.FAULT, SystemState.ESTOP} and name == "robot":
                device["health"] = "fault"
                device["detail"] = "机器人控制器处于故障或急停状态"
        if current_stale_ms >= stale_telemetry_ms and not self.force_sensor_timeout_alarm:
            self._queue_alarm(
                "WARN",
                "sensor",
                "力传感器数据陈旧，已触发 stale telemetry 告警",
                workflow_step="telemetry_watchdog",
                auto_action="mark_stale",
            )
            self.force_sensor_timeout_alarm = True
        if current_stale_ms < stale_telemetry_ms:
            self.force_sensor_timeout_alarm = False
        if self.execution_state == SystemState.SCANNING and current_stale_ms >= timeout_ms and not self.force_sensor_estop_alarm:
            self.execution_state = SystemState.PAUSED_HOLD
            self.contact_mode = "SENSOR_STALE"
            self.contact_stable = False
            self.recovery_reason = "sensor_timeout"
            self.last_recovery_action = "pause_hold"
            self.recommended_action = "CONTROLLED_RETRACT"
            self._queue_alarm(
                "RECOVERABLE_FAULT",
                "sensor",
                "力传感器超时，已进入保持状态",
                workflow_step="scan_monitor",
                auto_action="pause_hold",
            )
            self.force_sensor_estop_alarm = True
        if self.execution_state in {SystemState.SCANNING, SystemState.PAUSED_HOLD} and current_stale_ms >= timeout_ms * 2 and self.fault_code != "SENSOR_TIMEOUT":
            self.execution_state = SystemState.ESTOP
            self.fault_code = "SENSOR_TIMEOUT"
            self.contact_stable = False
            self.recovery_reason = "sensor_timeout_escalated"
            self.last_recovery_action = "estop"
            self._queue_alarm(
                "FATAL_FAULT",
                "sensor",
                "力传感器连续超时，已升级为急停",
                workflow_step="scan_monitor",
                auto_action="estop",
            )
        if current_stale_ms < timeout_ms:
            self.force_sensor_estop_alarm = False

    def _record_core_streams(self, ts_ns: int) -> None:
        if not self.recorders:
            return
        robot_payload = {
            "powered": self.powered,
            "operate_mode": self.operate_mode,
            "joint_pos": self.joint_pos,
            "joint_vel": self.joint_vel,
            "joint_torque": self.joint_torque,
            "cart_force": self.cart_force,
            "tcp_pose": self.tcp_pose,
        }
        contact_payload = {
            "mode": self.contact_mode,
            "confidence": self.contact_confidence,
            "pressure_current": self.pressure_current,
            "recommended_action": self.recommended_action,
            "contact_stable": self.contact_stable,
        }
        progress_payload = {
            "execution_state": self.execution_state.value,
            "active_segment": self.active_segment,
            "path_index": self.path_index,
            "progress_pct": self.progress_pct,
            "frame_id": self.frame_id,
        }
        self.recorders["robot_state"].append(robot_payload, source_ts_ns=ts_ns)
        self.recorders["contact_state"].append(contact_payload, source_ts_ns=ts_ns)
        self.recorders["scan_progress"].append(progress_payload, source_ts_ns=ts_ns)
        self.last_flush_ns = now_ns()

    def _open_recorders(self, session_dir: Path, session_id: str) -> None:
        core_root = ensure_dir(session_dir / "raw" / "core")
        self.recorders = {
            "robot_state": JsonlRecorder(core_root / "robot_state.jsonl", session_id),
            "contact_state": JsonlRecorder(core_root / "contact_state.jsonl", session_id),
            "scan_progress": JsonlRecorder(core_root / "scan_progress.jsonl", session_id),
            "alarm_event": JsonlRecorder(core_root / "alarm_event.jsonl", session_id),
        }

    def _queue_alarm(
        self,
        severity: str,
        source: str,
        message: str,
        *,
        workflow_step: str = "",
        request_id: str = "",
        auto_action: str = "",
    ) -> None:
        ts_ns = now_ns()
        alarm = {
            "severity": severity,
            "source": source,
            "message": message,
            "session_id": self.session_id,
            "segment_id": self.active_segment,
            "event_ts_ns": ts_ns,
            "workflow_step": workflow_step,
            "request_id": request_id,
            "auto_action": auto_action,
        }
        self.pending_alarms.append(alarm)
        recorder = self.recorders.get("alarm_event")
        if recorder is not None:
            recorder.append(alarm, source_ts_ns=ts_ns)
        self._append_controller_log(severity, message, source)
        if severity == "FATAL_FAULT":
            self.fault_code = source.upper()
            self.recovery_reason = source
            self.last_recovery_action = auto_action or severity.lower()
            self.execution_state = SystemState.FAULT if self.execution_state != SystemState.ESTOP else SystemState.ESTOP

    @staticmethod
    def _plan_hash(plan_payload: dict[str, Any]) -> str:
        import hashlib
        import json
        canonical = dict(plan_payload)
        canonical.pop("plan_hash", None)
        canonical.pop("scan_plan_hash", None)
        return hashlib.sha256(json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    @staticmethod
    def _validate_scan_plan(plan_payload: dict[str, Any]) -> str:
        segments = list(plan_payload.get("segments") or [])
        if not segments:
            return "scan plan missing segments"
        if not isinstance(plan_payload.get("approach_pose"), dict) or not isinstance(plan_payload.get("retreat_pose"), dict):
            return "scan plan missing approach/retreat poses"
        previous_segment = 0
        for segment in segments:
            segment_id = int(segment.get("segment_id", 0) or 0)
            if segment_id <= 0:
                return "scan plan contains invalid segment id"
            if previous_segment and segment_id != previous_segment + 1:
                return "scan plan segment ids must be contiguous"
            previous_segment = segment_id
            waypoints = list(segment.get("waypoints") or [])
            if not waypoints:
                return f"segment {segment_id} has no waypoints"
        return ""


    @staticmethod
    def _device(connected: bool, health: str, detail: str) -> Dict[str, Any]:
        return {
            "connected": connected,
            "health": health,
            "detail": detail,
            "fresh": connected,
            "last_ts_ns": 0,
        }


    def compile_scan_plan_verdict(self, plan_payload: dict[str, Any] | None, config_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        config = RuntimeConfig.from_dict(dict(config_snapshot or self.config.to_dict()))
        plan = None
        plan_error = ""
        if plan_payload:
            try:
                plan = ScanPlan.from_dict(dict(plan_payload))
            except Exception:
                plan = None
                plan_error = "scan plan parse failed"
            if not plan_error:
                plan_error = self._validate_scan_plan(dict(plan_payload))
        advisory = self.model_service.build_report(plan, config)
        capability = self.capability_service.build(config, {"operate_mode": self.operate_mode, "powered": self.powered})
        baseline = self.clinical_config_service.build_report(config)
        blockers = list(advisory.get('blockers', [])) + list(capability.get('blockers', [])) + list(baseline.get('blockers', []))
        warnings = list(advisory.get('warnings', [])) + list(capability.get('warnings', [])) + list(baseline.get('warnings', []))
        if plan_error:
            blockers.append({"name": "scan_plan", "severity": "blocker", "detail": plan_error})
        if self.locked_scan_plan_hash and plan is not None and getattr(plan, 'plan_hash', '') and self.locked_scan_plan_hash != plan.plan_hash:
            blockers.append({"name": "session_freeze", "severity": "blocker", "detail": "plan_hash does not match locked session freeze"})
        summary_state = 'blocked' if blockers else ('warning' if warnings else 'ready')
        accepted = summary_state != 'blocked'
        evidence_id = f"mock-verdict:{plan.plan_id if plan is not None else 'none'}:{self.session_id or 'unlocked'}"
        detail = str(advisory.get('detail', '')) if accepted else str(blockers[0].get('detail', 'compile blocked'))
        verdict = {
            'summary_state': summary_state,
            'summary_label': {
                'ready': '模型前检通过',
                'warning': '模型前检告警',
                'blocked': '模型前检阻塞',
                'idle': '未生成路径',
            }.get(summary_state, '运行时前检'),
            'detail': detail,
            'warnings': warnings,
            'blockers': blockers,
            'authority_source': 'cpp_robot_core',
            'verdict_kind': 'final',
            'approximate': False,
            'model_contract': dict(advisory.get('model_contract', {})),
            'plan_metrics': dict(advisory.get('plan_metrics', {})),
            'execution_selection': dict(advisory.get('execution_selection', {})),
            'capability_contract': capability,
            'baseline_contract': baseline,
            'model_authority_contract': self._model_authority_contract_payload(),
            'advisory_python': advisory,
            'final_verdict': {
                'accepted': accepted,
                'reason': detail,
                'evidence_id': evidence_id,
                'expected_state_delta': {'next_state': 'lock_session' if accepted and not self.session_id else ('load_scan_plan' if accepted else 'replan_required')},
                'policy_state': summary_state,
                'source': 'cpp_robot_core',
                'advisory_only': False,
            },
        }
        self.last_final_verdict = verdict
        return verdict

    def _cmd_compile_scan_plan(self, payload: dict) -> ReplyEnvelope:
        verdict = self.compile_scan_plan_verdict(payload.get('scan_plan'), payload.get('config_snapshot'))
        return ReplyEnvelope(ok=bool(verdict.get('final_verdict', {}).get('accepted', False)), message=str(verdict.get('detail', 'compile_scan_plan evaluated')), data={'final_verdict': verdict})

    def _cmd_query_final_verdict(self, payload: dict) -> ReplyEnvelope:
        del payload
        return ReplyEnvelope(ok=True, message='final verdict snapshot', data={'final_verdict': dict(self.last_final_verdict)})
