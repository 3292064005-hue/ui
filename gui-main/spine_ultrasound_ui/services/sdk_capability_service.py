from __future__ import annotations

from ipaddress import IPv4Address
from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.xmate_profile import XMateProfile, load_xmate_profile


class SdkCapabilityService:
    """Build an SDK-aligned capability and preflight view for the desktop.

    This service encodes the xCore SDK C++ manual as an application-facing
    contract: what modules exist, which control paths are clinical mainline,
    and which configuration mismatches should block or warn the operator.
    """

    def __init__(self, profile: XMateProfile | None = None) -> None:
        self.profile = profile or load_xmate_profile()

    def build(self, config: RuntimeConfig, robot_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        robot = dict(robot_snapshot or {})
        modules = self._module_matrix(config)
        checks = self._preflight_checks(config, robot)
        blockers = [item for item in checks if item["severity"] == "blocker" and not item["ok"]]
        warnings = [item for item in checks if item["severity"] == "warning" and not item["ok"]]
        enabled_modules = sum(1 for item in modules if item["enabled"])
        summary_state = "aligned"
        if blockers:
            summary_state = "blocked"
        elif warnings:
            summary_state = "warning"
        return {
            "summary_state": summary_state,
            "summary_label": self._summary_label(summary_state),
            "sdk_family": "ROKAE xCore SDK (C++)",
            "controller_version": self.profile.controller_version,
            "robot_model": self.profile.robot_model,
            "sdk_robot_class": config.sdk_robot_class,
            "remote_ip": config.remote_ip,
            "local_ip": config.local_ip,
            "preferred_link": config.preferred_link,
            "rt_loop_hz": self.profile.rt_loop_hz,
            "scan_rt_mode": config.rt_mode,
            "feature_coverage": {
                "enabled_modules": enabled_modules,
                "total_modules": len(modules),
                "coverage_percent": int(round((enabled_modules / len(modules)) * 100)) if modules else 0,
            },
            "checks": checks,
            "blockers": blockers,
            "warnings": warnings,
            "modules": modules,
            "command_bindings": self._command_bindings(config),
            "mainline_sequence": [
                "connectToRobot(remoteIP, localIP)",
                "setPowerState(on)",
                "setOperateMode(auto)",
                "setMotionControlMode(NRT)",
                "MoveAbsJ / MoveJ / MoveL 接近",
                "setMotionControlMode(RT)",
                "startReceiveRobotState(1ms, fields)",
                "setCartesianImpedance / setLoad / setEndEffectorFrame",
                "startMove(cartesianImpedance)",
                "setControlLoop() + startLoop()",
            ],
            "realtime_notes": [
                "实时主线由 C++ 以 1 kHz 执行，UI 不进入 RT 回调。",
                "在回调中读状态时，应将状态发送周期与控制周期都保持在 1 ms。",
                "网络监测窗口内若收不到足够指令，控制器会报网络不稳定并停止运动。",
            ],
            "clinical_policy": {
                "mainline_scan_mode": self.profile.rt_mode,
                "direct_torque_allowed": self.profile.direct_torque_in_clinical_mainline,
                "single_control_source_required": self.profile.requires_single_control_source,
                "collision_detection_required": True,
                "soft_limit_required": True,
                "singularity_avoidance_recommended": True,
            },
            "safety_contract": {
                "collision_detection_enabled": config.collision_detection_enabled,
                "collision_sensitivity": config.collision_sensitivity,
                "collision_behavior": config.collision_behavior,
                "collision_fallback_mm": config.collision_fallback_mm,
                "soft_limit_enabled": config.soft_limit_enabled,
                "joint_soft_limit_margin_deg": config.joint_soft_limit_margin_deg,
                "singularity_avoidance_enabled": config.singularity_avoidance_enabled,
            },
        }

    def _module_matrix(self, config: RuntimeConfig) -> list[dict[str, Any]]:
        scan_mode_ok = config.rt_mode == self.profile.rt_mode
        direct_torque_selected = config.rt_mode == "directTorque"
        return [
            {
                "module": "rokae::Robot",
                "enabled": True,
                "status": "ready",
                "purpose": "连接、上电、模式切换、姿态/关节/日志/工具工件查询",
                "core_methods": [
                    "connectToRobot",
                    "setPowerState",
                    "setOperateMode",
                    "robotInfo",
                    "jointPos",
                    "posture",
                    "queryControllerLog",
                    "setToolset",
                ],
            },
            {
                "module": "rokae::RtMotionControl",
                "enabled": scan_mode_ok and not direct_torque_selected,
                "status": "ready" if scan_mode_ok and not direct_torque_selected else "policy_blocked",
                "purpose": "1 kHz 实时阻抗/位置控制主线",
                "core_methods": [
                    "startReceiveRobotState",
                    "setControlLoop",
                    "startLoop",
                    "startMove",
                    "setCartesianImpedance",
                    "setNetworkTolerance",
                ],
            },
            {
                "module": "rokae::Planner",
                "enabled": True,
                "status": "ready",
                "purpose": "S 曲线/点位跟随的上位机路径规划",
                "core_methods": ["JointMotionGenerator", "CartMotionGenerator", "FollowPosition"],
            },
            {
                "module": "rokae::xMateModel",
                "enabled": True,
                "status": "ready",
                "purpose": "正逆解、雅可比、动力学前向计算",
                "core_methods": ["robot.model()", "getCartPose", "getJointPos", "jacobian", "getTorque"],
            },
            {
                "module": "通信 I/O",
                "enabled": True,
                "status": "ready",
                "purpose": "DI/DO/AI/AO、寄存器、xPanel 供电配置",
                "core_methods": ["getDI", "setDO", "getAI", "setAO", "readRegister", "writeRegister"],
            },
            {
                "module": "RL 工程",
                "enabled": True,
                "status": "ready",
                "purpose": "projectInfo / loadProject / runProject / pauseProject",
                "core_methods": ["projectInfo", "loadProject", "runProject", "pauseProject"],
            },
            {
                "module": "协作功能",
                "enabled": True,
                "status": "ready",
                "purpose": "拖动示教、路径录制/回放、奇异规避",
                "core_methods": ["enableDrag", "startRecordPath", "replayPath", "queryPathLists", "setAvoidSingularity"],
            },
        ]

    def _preflight_checks(self, config: RuntimeConfig, robot_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []
        checks.append(self._check(
            name="机器人类匹配",
            ok=config.sdk_robot_class == self.profile.sdk_robot_class and int(config.axis_count) == int(self.profile.axis_count),
            severity="blocker",
            detail_ok=f"当前为 {config.sdk_robot_class}/{config.axis_count} 轴，符合 {self.profile.robot_model} 主线。",
            detail_bad=f"当前配置为 {config.sdk_robot_class}/{config.axis_count} 轴，主线期望 {self.profile.sdk_robot_class}/{self.profile.axis_count} 轴。",
        ))
        checks.append(self._check(
            name="实时扫描模式",
            ok=config.rt_mode == self.profile.rt_mode,
            severity="blocker",
            detail_ok=f"临床主线扫描模式为 {config.rt_mode}。",
            detail_bad=f"当前 rt_mode={config.rt_mode}，主线要求 {self.profile.rt_mode}。",
        ))
        checks.append(self._check(
            name="直接力矩控制",
            ok=config.rt_mode != "directTorque" and not self.profile.direct_torque_in_clinical_mainline,
            severity="blocker",
            detail_ok="临床主线未启用 directTorque。",
            detail_bad="临床主线禁止 directTorque，应保留给研究模式。",
        ))
        checks.append(self._check(
            name="远端/本机 IP",
            ok=bool(config.remote_ip and config.local_ip),
            severity="blocker",
            detail_ok=f"remote={config.remote_ip}, local={config.local_ip}",
            detail_bad="connectToRobot(remoteIP, localIP) 所需 IP 未配置完整。",
        ))
        checks.append(self._check(
            name="直连网段一致性",
            ok=self._same_subnet(config.remote_ip, config.local_ip),
            severity="warning",
            detail_ok="远端/本机 IP 位于同一 /24 网段。",
            detail_bad=f"remote={config.remote_ip}, local={config.local_ip} 看起来不在同一 /24 网段。",
        ))
        checks.append(self._check(
            name="连接方式",
            ok=config.preferred_link == self.profile.preferred_link,
            severity="blocker",
            detail_ok=f"当前使用 {config.preferred_link}，符合实时控制推荐链路。",
            detail_bad=f"当前 preferred_link={config.preferred_link}，实时主线推荐 {self.profile.preferred_link}。",
        ))
        checks.append(self._check(
            name="单控制源",
            ok=bool(config.requires_single_control_source),
            severity="blocker",
            detail_ok="当前配置要求单控制源。",
            detail_bad="当前未锁定单控制源，容易与 RobotAssist/其他客户端发生控制冲突。",
        ))
        checks.append(self._check(
            name="工具/TCP/载荷",
            ok=bool(config.tool_name and config.tcp_name and float(config.load_kg) > 0.0),
            severity="blocker",
            detail_ok=f"tool={config.tool_name}, tcp={config.tcp_name}, load={config.load_kg:.2f}kg",
            detail_bad="工具名、TCP 名或载荷质量未配置完整。",
        ))
        checks.append(self._check(
            name="网络容忍阈值",
            ok=10 <= int(config.rt_network_tolerance_percent) <= 20,
            severity="warning",
            detail_ok=f"rt_network_tolerance_percent={config.rt_network_tolerance_percent}，落在手册建议 10~20 范围。",
            detail_bad=f"rt_network_tolerance_percent={config.rt_network_tolerance_percent}，手册对不稳定排查建议 10~20。",
        ))
        checks.append(self._check(
            name="碰撞检测",
            ok=bool(config.collision_detection_enabled),
            severity="blocker",
            detail_ok=f"碰撞检测已开启，灵敏度={config.collision_sensitivity}，回退={config.collision_fallback_mm:.1f} mm。",
            detail_bad="当前未开启碰撞检测，正式主线不应继续。",
        ))
        checks.append(self._check(
            name="软限位",
            ok=bool(config.soft_limit_enabled),
            severity="blocker",
            detail_ok=f"软限位已开启，裕量={config.joint_soft_limit_margin_deg:.1f}°。",
            detail_bad="当前未开启软限位，正式主线不应继续。",
        ))
        checks.append(self._check(
            name="奇异规避",
            ok=bool(config.singularity_avoidance_enabled),
            severity="warning",
            detail_ok="奇异规避已开启。",
            detail_bad="当前未开启奇异规避，笛卡尔扫描主线存在姿态奇异风险。",
        ))
        checks.append(self._check(
            name="RL 主工程命名",
            ok=bool(config.rl_project_name and config.rl_task_name),
            severity="warning",
            detail_ok=f"RL project={config.rl_project_name}, task={config.rl_task_name}",
            detail_bad="未填写 RL 工程/任务名，RL 面板只能做只读展示。",
        ))
        checks.append(self._check(
            name="机器人已进入自动模式",
            ok=str(robot_snapshot.get("operate_mode", "")).lower() in {"automatic", "auto"} or not robot_snapshot,
            severity="warning",
            detail_ok="当前 operate_mode 已是自动。",
            detail_bad=f"当前 operate_mode={robot_snapshot.get('operate_mode', '-') }，正式主线应在自动模式下运行。",
        ))
        return checks

    def _command_bindings(self, config: RuntimeConfig) -> list[dict[str, str]]:
        return [
            {"ui_action": "连接机器人", "sdk_binding": f"{config.sdk_robot_class}.connectToRobot({config.remote_ip}, {config.local_ip})", "plane": "base"},
            {"ui_action": "系统上电", "sdk_binding": "setPowerState(on)", "plane": "base"},
            {"ui_action": "自动模式", "sdk_binding": "setOperateMode(auto)", "plane": "base"},
            {"ui_action": "预接近", "sdk_binding": "setMotionControlMode(NRT) + MoveAbsJ/MoveJ/MoveL", "plane": "nrt"},
            {"ui_action": "实时接触", "sdk_binding": "setMotionControlMode(RT) + setCartesianImpedance + startMove(cartesianImpedance)", "plane": "rt"},
            {"ui_action": "实时扫查", "sdk_binding": "setControlLoop + startReceiveRobotState + startLoop", "plane": "rt"},
            {"ui_action": "安全退让", "sdk_binding": "stopMove / MoveL retract / emergency_stop", "plane": "safety"},
            {"ui_action": "控制器日志", "sdk_binding": "queryControllerLog(count, level)", "plane": "observability"},
            {"ui_action": "RL 工程", "sdk_binding": "projectInfo / loadProject / runProject / pauseProject", "plane": "rl"},
            {"ui_action": "路径回放 / 拖动", "sdk_binding": "queryPathLists / replayPath / enableDrag", "plane": "collaboration"},
            {"ui_action": "通信 I/O", "sdk_binding": "getDI/DO/AI/AO + readRegister/writeRegister", "plane": "io"},
            {"ui_action": "路径规划", "sdk_binding": "rokae::Planner (JointMotionGenerator / CartMotionGenerator)", "plane": "planning"},
            {"ui_action": "运动学动力学", "sdk_binding": "robot.model() + xMateModel", "plane": "model"},
        ]

    @staticmethod
    def _same_subnet(remote_ip: str, local_ip: str) -> bool:
        try:
            remote = int(IPv4Address(remote_ip))
            local = int(IPv4Address(local_ip))
        except Exception:
            return False
        mask = 0xFFFFFF00
        return (remote & mask) == (local & mask)

    @staticmethod
    def _check(*, name: str, ok: bool, severity: str, detail_ok: str, detail_bad: str) -> dict[str, Any]:
        return {
            "name": name,
            "ok": bool(ok),
            "severity": severity,
            "detail": detail_ok if ok else detail_bad,
        }

    @staticmethod
    def _summary_label(state: str) -> str:
        mapping = {
            "aligned": "SDK 主线对齐",
            "warning": "SDK 主线可运行但有风险",
            "blocked": "SDK 主线未对齐",
        }
        return mapping.get(state, "SDK 状态未知")
