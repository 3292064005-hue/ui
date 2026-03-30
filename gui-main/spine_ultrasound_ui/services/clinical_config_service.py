from __future__ import annotations

from ipaddress import ip_address
from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.xmate_profile import XMateProfile, load_xmate_profile


class ClinicalConfigService:
    """Validate and normalize the desktop runtime config against the xMate mainline.

    The service keeps configuration governance separate from SDK capability governance.
    SDK alignment answers whether the selected control path matches the official xCore
    mainline, while this service answers whether the application's own runtime numbers,
    matrices, bands, and scan parameters are internally coherent and close to the
    preferred clinical baseline.
    """

    def __init__(self, profile: XMateProfile | None = None) -> None:
        self.profile = profile or load_xmate_profile()

    def apply_mainline_defaults(self, config: RuntimeConfig) -> RuntimeConfig:
        payload = config.to_dict()
        pressure_policy = dict(self.profile.contact_force_policy)
        payload.update(
            robot_model=self.profile.robot_model,
            sdk_robot_class=self.profile.sdk_robot_class,
            axis_count=self.profile.axis_count,
            remote_ip=self.profile.remote_ip,
            local_ip=self.profile.local_ip,
            preferred_link=self.profile.preferred_link,
            requires_single_control_source=self.profile.requires_single_control_source,
            rt_mode=self.profile.rt_mode,
            tool_name=self.profile.tool_name,
            tcp_name=self.profile.tcp_name,
            load_kg=self.profile.load_mass_kg,
            load_com_mm=list(self.profile.load_com_mm),
            load_inertia=list(self.profile.load_inertia),
            rt_network_tolerance_percent=self.profile.rt_network_tolerance_percent,
            joint_filter_hz=self.profile.joint_filter_hz,
            cart_filter_hz=self.profile.cart_filter_hz,
            torque_filter_hz=self.profile.torque_filter_hz,
            collision_detection_enabled=self.profile.collision_detection_enabled,
            collision_sensitivity=self.profile.collision_sensitivity,
            collision_behavior=self.profile.collision_behavior,
            collision_fallback_mm=self.profile.collision_fallback_mm,
            soft_limit_enabled=self.profile.soft_limit_enabled,
            joint_soft_limit_margin_deg=self.profile.joint_soft_limit_margin_deg,
            singularity_avoidance_enabled=self.profile.singularity_avoidance_enabled,
            cartesian_impedance=list(self.profile.cartesian_impedance),
            desired_wrench_n=list(self.profile.desired_wrench_n),
            fc_frame_type=self.profile.fc_frame_type,
            fc_frame_matrix=list(self.profile.fc_frame_matrix),
            tcp_frame_matrix=list(self.profile.tcp_frame_matrix),
            strip_width_mm=self.profile.strip_width_mm,
            strip_overlap_mm=self.profile.strip_overlap_mm,
            pressure_target=float(pressure_policy.get("target_n", config.pressure_target)),
            pressure_upper=float(pressure_policy.get("warning_n", config.pressure_upper)),
            pressure_lower=max(1.0, float(pressure_policy.get("target_n", config.pressure_target)) - float(pressure_policy.get("settle_band_n", 1.0))),
            scan_speed_mm_s=float(self.profile.sweep_policy.get("scan_speed_mm_s", config.scan_speed_mm_s)),
            contact_seek_speed_mm_s=float(self.profile.sweep_policy.get("contact_seek_speed_mm_s", config.contact_seek_speed_mm_s)),
            retreat_speed_mm_s=float(self.profile.sweep_policy.get("retreat_speed_mm_s", config.retreat_speed_mm_s)),
            image_quality_threshold=float(self.profile.sweep_policy.get("rescan_quality_threshold", config.image_quality_threshold)),
        )
        return RuntimeConfig.from_dict(payload)

    def build_report(self, config: RuntimeConfig) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        checks.append(self._check(
            "压力工作带",
            config.pressure_lower < config.pressure_target < config.pressure_upper,
            "blocker",
            f"pressure_lower={config.pressure_lower:.2f} < target={config.pressure_target:.2f} < upper={config.pressure_upper:.2f}",
            "压力上下限与目标压力顺序错误，正式流程会导致接触控制策略失真。",
        ))
        checks.append(self._check(
            "条带宽度/重叠",
            config.strip_width_mm > 0 and 0 <= config.strip_overlap_mm < config.strip_width_mm,
            "blocker",
            f"strip_width={config.strip_width_mm:.1f} mm, overlap={config.strip_overlap_mm:.1f} mm",
            "strip_overlap 必须非负且小于 strip_width，否则路径密度与覆盖率计算会失真。",
        ))
        checks.append(self._check(
            "速度关系",
            config.contact_seek_speed_mm_s > 0 and config.scan_speed_mm_s > 0 and config.retreat_speed_mm_s > 0 and config.contact_seek_speed_mm_s <= config.scan_speed_mm_s <= config.retreat_speed_mm_s,
            "warning",
            f"seek={config.contact_seek_speed_mm_s:.1f}, scan={config.scan_speed_mm_s:.1f}, retreat={config.retreat_speed_mm_s:.1f} mm/s",
            "推荐满足 seek <= scan <= retreat，避免接触搜索过快或退让过慢。",
        ))
        checks.append(self._check(
            "遥测与超时",
            config.telemetry_rate_hz > 0 and config.network_stale_ms > 0 and config.pressure_stale_ms > 0,
            "blocker",
            f"telemetry_rate_hz={config.telemetry_rate_hz}, network_stale_ms={config.network_stale_ms}, pressure_stale_ms={config.pressure_stale_ms}",
            "telemetry_rate_hz / network_stale_ms / pressure_stale_ms 必须为正值。",
        ))
        checks.append(self._check(
            "IP 格式",
            self._valid_ip(config.remote_ip) and self._valid_ip(config.local_ip),
            "blocker",
            f"remote={config.remote_ip}, local={config.local_ip}",
            "remote_ip 或 local_ip 不是合法 IPv4 地址。",
        ))
        checks.append(self._check(
            "阻抗/期望力维度",
            len(config.cartesian_impedance) == 6 and len(config.desired_wrench_n) == 6,
            "blocker",
            "cartesian_impedance / desired_wrench_n 均为 6 维。",
            "cartesian_impedance 和 desired_wrench_n 都必须是 6 维向量。",
        ))
        checks.append(self._check(
            "坐标矩阵维度",
            len(config.fc_frame_matrix) == 16 and len(config.tcp_frame_matrix) == 16,
            "blocker",
            "fc_frame_matrix / tcp_frame_matrix 均为 4x4 展平矩阵。",
            "fc_frame_matrix 或 tcp_frame_matrix 不是 16 维齐次矩阵。",
        ))
        checks.append(self._check(
            "负载参数维度",
            len(config.load_com_mm) == 3 and len(config.load_inertia) == 6 and config.load_kg > 0,
            "blocker",
            f"load={config.load_kg:.2f} kg, com={config.load_com_mm}, inertia={config.load_inertia}",
            "负载质量必须大于 0，load_com_mm 必须 3 维，load_inertia 必须 6 维。",
        ))
        checks.append(self._check(
            "滤波与阈值",
            config.joint_filter_hz > 0 and config.cart_filter_hz > 0 and config.torque_filter_hz > 0 and config.rt_network_tolerance_percent > 0,
            "blocker",
            f"filters=({config.joint_filter_hz}, {config.cart_filter_hz}, {config.torque_filter_hz}), tolerance={config.rt_network_tolerance_percent}%",
            "滤波截止频率和 RT 网络容忍阈值必须为正值。",
        ))
        checks.append(self._check(
            "主线配置贴合度",
            config.rt_mode == self.profile.rt_mode and config.preferred_link == self.profile.preferred_link and config.sdk_robot_class == self.profile.sdk_robot_class,
            "warning",
            f"rt_mode={config.rt_mode}, link={config.preferred_link}, robot_class={config.sdk_robot_class}",
            "当前配置与 xMate 主线基线存在偏差，建议应用主线基线后再继续。",
        ))
        checks.append(self._check(
            "工具/TCP 命名",
            bool(config.tool_name.strip()) and bool(config.tcp_name.strip()),
            "blocker",
            f"tool={config.tool_name}, tcp={config.tcp_name}",
            "tool_name / tcp_name 不能为空。",
        ))
        blockers = [item for item in checks if item["severity"] == "blocker" and not item["ok"]]
        warnings = [item for item in checks if item["severity"] == "warning" and not item["ok"]]
        summary_state = "aligned"
        if blockers:
            summary_state = "blocked"
        elif warnings:
            summary_state = "warning"
        return {
            "summary_state": summary_state,
            "summary_label": {
                "aligned": "配置基线通过",
                "warning": "配置基线告警",
                "blocked": "配置基线阻塞",
            }.get(summary_state, "配置状态未知"),
            "checks": checks,
            "blockers": blockers,
            "warnings": warnings,
            "profile_robot_model": self.profile.robot_model,
            "profile_sdk_robot_class": self.profile.sdk_robot_class,
            "recommended_patch": self._recommended_patch(config),
            "baseline_summary": {
                "rt_mode": self.profile.rt_mode,
                "preferred_link": self.profile.preferred_link,
                "tool_name": self.profile.tool_name,
                "tcp_name": self.profile.tcp_name,
                "target_force_n": self.profile.contact_force_policy.get("target_n", 0.0),
                "warning_force_n": self.profile.contact_force_policy.get("warning_n", 0.0),
            },
        }

    def _recommended_patch(self, config: RuntimeConfig) -> list[dict[str, Any]]:
        patch: list[dict[str, Any]] = []
        expected = {
            "robot_model": self.profile.robot_model,
            "sdk_robot_class": self.profile.sdk_robot_class,
            "axis_count": self.profile.axis_count,
            "remote_ip": self.profile.remote_ip,
            "preferred_link": self.profile.preferred_link,
            "rt_mode": self.profile.rt_mode,
            "tool_name": self.profile.tool_name,
            "tcp_name": self.profile.tcp_name,
            "rt_network_tolerance_percent": self.profile.rt_network_tolerance_percent,
        }
        current = config.to_dict()
        for key, value in expected.items():
            if current.get(key) != value:
                patch.append({"field": key, "current": current.get(key), "expected": value})
        return patch

    @staticmethod
    def _check(name: str, ok: bool, severity: str, detail_ok: str, detail_bad: str) -> dict[str, Any]:
        return {"name": name, "ok": bool(ok), "severity": severity, "detail": detail_ok if ok else detail_bad}

    @staticmethod
    def _valid_ip(value: str) -> bool:
        try:
            ip_address(str(value))
        except ValueError:
            return False
        return True
