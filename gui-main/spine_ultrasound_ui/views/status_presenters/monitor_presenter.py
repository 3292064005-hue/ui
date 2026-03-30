from __future__ import annotations

from .common import StatusViewContext, join_lines


class MonitorPresenter:
    def apply(self, ctx: StatusViewContext) -> None:
        window = ctx.window
        metrics = ctx.metrics
        pose = ctx.pose
        pose_text = f"x={pose['x']:.1f}, y={pose['y']:.1f}, z={pose['z']:.1f}, rx={pose['rx']:.1f}, ry={pose['ry']:.1f}, rz={pose['rz']:.1f}"
        window.robot_monitor_page.lbl_joint_pos.setText(str(metrics["joint_pos"]))
        window.robot_monitor_page.lbl_joint_vel.setText(str(metrics["joint_vel"]))
        window.robot_monitor_page.lbl_joint_torque.setText(str(metrics["joint_torque"]))
        window.robot_monitor_page.lbl_tcp.setText(pose_text)
        window.robot_monitor_page.lbl_cart_force.setText(str(metrics["cart_force"]))
        window.robot_monitor_page.lbl_operate_mode.setText(ctx.robot.get("operate_mode", "-"))
        window.robot_monitor_page.lbl_power_state.setText("ON" if ctx.robot.get("powered", False) else "OFF")
        window.robot_monitor_page.lbl_rl_state.setText(f"{ctx.rl_status.get('loaded_project', '-')}/{ctx.rl_status.get('loaded_task', '-')} / {'RUN' if ctx.rl_status.get('running') else 'IDLE'}")
        window.robot_monitor_page.lbl_drag.setText(f"{'ON' if ctx.drag_status.get('enabled') else 'OFF'} / {ctx.drag_status.get('space', '-')} / {ctx.drag_status.get('type', '-')}")

        controller_logs = list(ctx.sdk_runtime.get('controller_logs', []))
        if controller_logs:
            window.robot_monitor_page.log_view.setPlainText(join_lines([f"[{item.get('level', '-')}] {item.get('source', '-')}: {item.get('message', '-')}" for item in controller_logs], "暂无控制器日志。"))

        rl_projects = list(ctx.sdk_runtime.get('rl_projects', []))
        io_snapshot = dict(ctx.sdk_runtime.get('io_snapshot', {}))
        path_library = list(ctx.sdk_runtime.get('path_library', []))
        safety_profile = dict(ctx.sdk_runtime.get('safety_profile', {}))
        motion_contract = dict(ctx.sdk_runtime.get('motion_contract', {}))
        asset_lines = [
            f"RL 状态：{ctx.rl_status.get('loaded_project', '-')}/{ctx.rl_status.get('loaded_task', '-')} / {'RUN' if ctx.rl_status.get('running') else 'IDLE'}",
            f"拖动示教：{'ON' if ctx.drag_status.get('enabled') else 'OFF'} / {ctx.drag_status.get('space', '-')} / {ctx.drag_status.get('type', '-')}",
            "",
            "RL 工程:",
        ]
        asset_lines.extend([f"- {item.get('name')} :: tasks={', '.join(item.get('tasks', []))}" for item in rl_projects] or ["- 无"])
        asset_lines.extend(["", "路径库:"])
        asset_lines.extend([f"- {item.get('name')} :: rate={item.get('rate')} / points={item.get('points')}" for item in path_library] or ["- 无"])
        asset_lines.extend(["", f"I/O DI={io_snapshot.get('di', {})}", f"I/O DO={io_snapshot.get('do', {})}", f"寄存器={io_snapshot.get('registers', {})}", f"xPanel={io_snapshot.get('xpanel_vout_mode', '-')}", "", f"安全配置：collision={safety_profile.get('collision_detection_enabled', '-')}, soft_limit={safety_profile.get('soft_limit_enabled', '-')}, singularity={safety_profile.get('singularity_avoidance_enabled', '-')}", f"运动契约：rt={motion_contract.get('rt_mode', '-')}, tolerance={motion_contract.get('network_tolerance_percent', '-')}, link={motion_contract.get('preferred_link', '-')}" ])
        if ctx.sdk_runtime.get('errors'):
            asset_lines.extend(["", "资产刷新错误:"])
            asset_lines.extend([f"- {item}" for item in ctx.sdk_runtime.get('errors', [])])
        if ctx.backend_link:
            asset_lines.extend(["", f"前后端链路：{ctx.backend_link.get('summary_label', '-')}", f"链路说明：{ctx.backend_link.get('detail', '-')}", f"REST={'UP' if ctx.backend_link.get('rest_reachable') else 'DOWN'} / telemetry={'ON' if ctx.backend_link.get('telemetry_connected') else 'OFF'} / camera={'ON' if ctx.backend_link.get('camera_connected') else 'OFF'} / ultrasound={'ON' if ctx.backend_link.get('ultrasound_connected') else 'OFF'}", f"endpoint={ctx.backend_link.get('http_base', '-')} / ws={ctx.backend_link.get('ws_base', '-')}" ])
            if ctx.control_plane:
                asset_lines.extend([f"控制面：{ctx.control_plane.get('summary_label', '-')}", f"控制面说明：{ctx.control_plane.get('detail', '-')}", f"配置同步：{ctx.control_plane.get('config_sync', {}).get('detail', '-')}", f"协议状态：{ctx.control_plane.get('protocol_status', {}).get('detail', '-')}", f"topic 覆盖：{ctx.control_plane.get('topic_coverage', {}).get('coverage_percent', 0)}% / 缺失 {', '.join(ctx.control_plane.get('topic_coverage', {}).get('missing', [])) or '无'}" ])
            if ctx.bridge_observability:
                asset_lines.extend([f"桥接观测：{ctx.bridge_observability.get('summary_label', '-')}", f"桥接说明：{ctx.bridge_observability.get('detail', '-')}", f"遥测新鲜度：{ctx.bridge_observability.get('freshness', {}).get('summary_label', '-')} / worst_age={ctx.bridge_observability.get('freshness', {}).get('worst_age_ms', '-')}", f"命令确认：{ctx.bridge_observability.get('command_observability', {}).get('summary_label', '-')} / latest={ctx.bridge_observability.get('command_observability', {}).get('latest_checked_command', '-')}" ])
                recent_commands = ctx.control_plane.get('command_window', {}).get('recent_commands', [])
                if recent_commands:
                    asset_lines.extend(["最近命令窗口:"])
                    asset_lines.extend([f"- {item.get('command', '-')} :: {'OK' if item.get('ok') else 'FAIL'} :: {item.get('message', '-')}" for item in recent_commands[-5:]])
        if ctx.session_governance:
            asset_lines.extend(["", f"会话治理：{ctx.session_governance.get('summary_label', '-')}", f"治理说明：{ctx.session_governance.get('detail', '-')}", f"发布门禁：{'PASS' if ctx.session_governance.get('release_gate', {}).get('release_allowed') else 'BLOCK'}", f"artifact ready={ctx.session_governance.get('artifact_counts', {}).get('ready', 0)} / {ctx.session_governance.get('artifact_counts', {}).get('registered', 0)}" ])
        asset_text = join_lines(asset_lines, "暂无 SDK 资产。")
        window.robot_monitor_page.asset_view.setPlainText(asset_text)
        window.replay_page.asset_view.setPlainText(asset_text)
