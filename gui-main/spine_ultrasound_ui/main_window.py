from __future__ import annotations

from html import escape

from PySide6.QtCore import Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from spine_ultrasound_ui.models import ExperimentRecord
from spine_ultrasound_ui.pages import (
    AssessmentPage,
    ExperimentPage,
    OverviewPage,
    PreparePage,
    ReconstructionPage,
    ReplayPage,
    RobotMonitorPage,
    ScanPage,
    SettingsPage,
    VisionPage,
)
from spine_ultrasound_ui.styles import MAIN_STYLESHEET
from spine_ultrasound_ui.widgets import AlarmBanner, ConfigForm, ExperimentTableModel, LogConsole, StatusCard


class MainWindow(QMainWindow):
    def __init__(self, backend):
        super().__init__()
        self.backend = backend
        self.setWindowTitle("脊柱侧弯自动检测研究平台")
        self.resize(1720, 1020)
        self.exp_model = ExperimentTableModel([])
        self.config_form = ConfigForm(self.backend.config)
        if hasattr(self.backend, "update_config"):
            self.config_form.config_applied.connect(self.backend.update_config)
        self._build_ui()
        self._connect_backend()
        self.setStyleSheet(MAIN_STYLESHEET)

    def _build_ui(self):
        self._build_toolbar()
        self._build_statusbar()
        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        self.hero_card = self._build_header_banner()
        self.alarm_banner = AlarmBanner()
        main_layout.addWidget(self.hero_card)
        main_layout.addWidget(self.alarm_banner)

        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)
        main_layout.addWidget(splitter, 1)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_center_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([360, 1020, 340])

        self.log_box = LogConsole()
        self.log_box.setMinimumHeight(170)
        main_layout.addWidget(self.log_box)

    def _build_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        actions = [
            ("新建实验", self.backend.create_experiment),
            ("保存结果", self.backend.save_results),
            ("导出摘要", self.backend.export_summary),
            ("安全退让", self.backend.safe_retreat),
        ]
        for text, fn in actions:
            act = QAction(text, self)
            act.triggered.connect(fn)
            toolbar.addAction(act)
        toolbar.addSeparator()
        estop = QAction("急停", self)
        estop.triggered.connect(self._confirm_estop)
        toolbar.addAction(estop)

    def _build_statusbar(self):
        status = QStatusBar()
        status.setSizeGripEnabled(False)
        self.setStatusBar(status)
        self.system_state_label = QLabel("状态 · BOOT")
        self.system_state_label.setObjectName("StatusPill")
        self.system_state_label.setProperty("state", "warn")
        self.exp_id_label = QLabel("实验 · -")
        self.exp_id_label.setObjectName("StatusPill")
        self.exp_id_label.setProperty("state", "ok")
        status.addPermanentWidget(self.system_state_label)
        status.addPermanentWidget(self.exp_id_label)

    def _build_header_banner(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("HeroCard")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)

        left = QVBoxLayout()
        left.setSpacing(4)
        title = QLabel("脊柱侧弯自动检测研究平台")
        title.setObjectName("PageTitle")
        subtitle = QLabel("面向机器人辅助扫查、超声重建与 Cobb 角量化评估的临床研究工作站")
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        left.addWidget(title)
        left.addWidget(subtitle)
        layout.addLayout(left, 3)

        pills = QHBoxLayout()
        pills.setSpacing(10)
        self.header_state_pill = QLabel("系统 · BOOT")
        self.header_mode_pill = QLabel("模式 · -")
        self.header_exp_pill = QLabel("实验 · -")
        for pill in [self.header_state_pill, self.header_mode_pill, self.header_exp_pill]:
            pill.setObjectName("HeaderPill")
            pill.setProperty("state", "warn")
            pills.addWidget(pill)
        layout.addLayout(pills, 2)
        return frame

    def _build_left_panel(self) -> QWidget:
        panel = QScrollArea()
        panel.setWidgetResizable(True)
        panel.setMinimumWidth(330)
        panel.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        panel.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        system_box = QGroupBox("机器人与系统")
        system_layout = QGridLayout(system_box)
        self.btn_connect = self._make_button("连接机器人", self.backend.connect_robot, kind="primary")
        self.btn_disconnect = self._make_button("断开机器人", self.backend.disconnect_robot)
        self.btn_power_on = self._make_button("上电", self.backend.power_on, kind="success")
        self.btn_power_off = self._make_button("下电", self.backend.power_off)
        self.btn_auto = self._make_button("自动模式", self.backend.set_auto_mode, kind="primary")
        self.btn_manual = self._make_button("手动模式", self.backend.set_manual_mode)
        system_buttons = [
            self.btn_connect,
            self.btn_disconnect,
            self.btn_power_on,
            self.btn_power_off,
            self.btn_auto,
            self.btn_manual,
        ]
        self._fill_grid(system_layout, system_buttons, columns=2)

        workflow_box = QGroupBox("实验与扫查")
        workflow_layout = QGridLayout(workflow_box)
        self.btn_new_exp = self._make_button("新建实验", self.backend.create_experiment, kind="primary")
        self.btn_localize = self._make_button("开始视觉定位", self.backend.run_localization)
        self.btn_path = self._make_button("生成扫查路径", self.backend.generate_path)
        self.btn_scan_start = self._make_button("开始扫查", self.backend.start_scan, kind="success")
        self.btn_scan_pause = self._make_button("暂停扫查", self.backend.pause_scan, kind="warning")
        self.btn_scan_resume = self._make_button("恢复扫查", self.backend.resume_scan, kind="primary")
        self.btn_scan_stop = self._make_button("停止扫查", self.backend.stop_scan)
        self.btn_home = self._make_button("回初始位", self.backend.go_home)
        self.btn_retreat = self._make_button("安全退让", self.backend.safe_retreat, kind="warning")
        workflow_buttons = [
            self.btn_new_exp,
            self.btn_localize,
            self.btn_path,
            self.btn_scan_start,
            self.btn_scan_pause,
            self.btn_scan_resume,
            self.btn_scan_stop,
            self.btn_home,
            self.btn_retreat,
        ]
        self._fill_grid(workflow_layout, workflow_buttons, columns=2, last_span=True)

        algo_box = QGroupBox("算法与导出")
        algo_layout = QGridLayout(algo_box)
        self.btn_pre = self._make_button("图像预处理", self.backend.run_preprocess)
        self.btn_recon = self._make_button("开始重建", self.backend.run_reconstruction, kind="primary")
        self.btn_assess = self._make_button("计算 Cobb 角", self.backend.run_assessment, kind="success")
        self.btn_save = self._make_button("保存结果", self.backend.save_results)
        self.btn_export = self._make_button("导出摘要", self.backend.export_summary, kind="primary")
        algo_buttons = [self.btn_pre, self.btn_recon, self.btn_assess, self.btn_save, self.btn_export]
        self._fill_grid(algo_layout, algo_buttons, columns=2, last_span=True)

        safety_box = QGroupBox("安全控制")
        safety_layout = QVBoxLayout(safety_box)
        self.btn_estop = self._make_button("急停", self._confirm_estop, kind="danger")
        safety_hint = QLabel("急停将立即中止当前流程，应仅在需要快速切断动作时使用。")
        safety_hint.setObjectName("MutedLabel")
        safety_hint.setWordWrap(True)
        safety_layout.addWidget(self.btn_estop)
        safety_layout.addWidget(safety_hint)

        for box in [system_box, workflow_box, algo_box, safety_box]:
            layout.addWidget(box)
        layout.addStretch(1)
        return panel

    def _build_center_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.overview_page = OverviewPage()
        self.experiment_page = ExperimentPage(self.config_form, self.exp_model)
        self.prepare_page = PreparePage()
        self.scan_page = ScanPage()
        self.robot_monitor_page = RobotMonitorPage()
        self.vision_page = VisionPage()
        self.reconstruction_page = ReconstructionPage()
        self.assessment_page = AssessmentPage()
        self.replay_page = ReplayPage()
        self.settings_page = SettingsPage()
        pages = [
            ("系统总览", self.overview_page),
            ("实验配置", self.experiment_page),
            ("系统准备", self.prepare_page),
            ("自动扫查", self.scan_page),
            ("机器人监控", self.robot_monitor_page),
            ("视觉与路径", self.vision_page),
            ("图像与重建", self.reconstruction_page),
            ("量化评估", self.assessment_page),
            ("实验回放", self.replay_page),
            ("系统设置", self.settings_page),
        ]
        for title, page in pages:
            self.tabs.addTab(page, title)
        layout.addWidget(self.tabs)
        return container

    def _build_right_panel(self) -> QWidget:
        panel = QScrollArea()
        panel.setWidgetResizable(True)
        panel.setMinimumWidth(320)
        panel.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        panel.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header = QGroupBox("运行摘要")
        header_layout = QVBoxLayout(header)
        head_title = QLabel("实时关键指标")
        head_title.setObjectName("SectionTitle")
        head_hint = QLabel("右侧卡片用于快速查看状态、压力、位姿、图像质量与结果摘要。")
        head_hint.setObjectName("SectionHint")
        head_hint.setWordWrap(True)
        header_layout.addWidget(head_title)
        header_layout.addWidget(head_hint)
        layout.addWidget(header)

        self.card_state = StatusCard("系统状态", tone="accent")
        self.card_exp = StatusCard("实验编号")
        self.card_pressure = StatusCard("接触与压力", tone="success")
        self.card_pose = StatusCard("TCP 位姿")
        self.card_quality = StatusCard("图像质量", tone="warning")
        self.card_result = StatusCard("结果摘要")
        for card in [self.card_state, self.card_exp, self.card_pressure, self.card_pose, self.card_quality, self.card_result]:
            layout.addWidget(card)
        layout.addStretch(1)
        return panel

    def _connect_backend(self):
        self.backend.status_updated.connect(self._on_status)
        self.backend.log_generated.connect(self._append_log)
        if hasattr(self.backend, "camera_pixmap_ready"):
            self.backend.camera_pixmap_ready.connect(self._update_camera_pixmap)
        if hasattr(self.backend, "ultrasound_pixmap_ready"):
            self.backend.ultrasound_pixmap_ready.connect(self._update_ultrasound_pixmap)
        if hasattr(self.backend, "reconstruction_pixmap_ready"):
            self.backend.reconstruction_pixmap_ready.connect(self._update_reconstruction_pixmap)
        self.backend.experiments_updated.connect(self._on_experiments)
        self.backend.system_state_changed.connect(self._on_system_state)
        if hasattr(self.backend, "alarm_raised"):
            self.backend.alarm_raised.connect(self._on_alarm)

    def _make_button(self, text: str, callback, kind: str = "secondary") -> QPushButton:
        button = QPushButton(text)
        button.setProperty("kind", kind)
        button.clicked.connect(callback)
        return button

    def _fill_grid(self, grid: QGridLayout, buttons: list[QPushButton], columns: int = 2, last_span: bool = False):
        row = 0
        col = 0
        for idx, button in enumerate(buttons):
            is_last = idx == len(buttons) - 1
            if last_span and is_last and col != 0:
                grid.addWidget(button, row, 0, 1, columns)
                row += 1
                col = 0
                continue
            if last_span and is_last and len(buttons) % columns == 1:
                grid.addWidget(button, row, 0, 1, columns)
                row += 1
                col = 0
                continue
            grid.addWidget(button, row, col)
            col += 1
            if col >= columns:
                row += 1
                col = 0

    def _apply_permissions(self, payload: dict):
        perms = payload.get("permissions", {})
        mapping = {
            self.btn_connect: "connect_robot",
            self.btn_disconnect: "disconnect_robot",
            self.btn_power_on: "power_on",
            self.btn_power_off: "power_off",
            self.btn_auto: "set_auto_mode",
            self.btn_manual: "set_manual_mode",
            self.btn_new_exp: "create_experiment",
            self.btn_localize: "run_localization",
            self.btn_path: "generate_path",
            self.btn_scan_start: "start_scan",
            self.btn_scan_pause: "pause_scan",
            self.btn_scan_resume: "resume_scan",
            self.btn_scan_stop: "stop_scan",
            self.btn_home: "go_home",
            self.btn_retreat: "safe_retreat",
            self.btn_pre: "run_preprocess",
            self.btn_recon: "run_reconstruction",
            self.btn_assess: "run_assessment",
            self.btn_export: "export_summary",
        }
        for btn, key in mapping.items():
            btn.setEnabled(perms.get(key, True))

    def _set_badge_state(self, widget: QLabel, text: str, state: str):
        widget.setText(text)
        widget.setProperty("state", state)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def _device_state(self, connected: bool, health: str) -> str:
        health_upper = str(health or "").upper()
        if not connected:
            return "danger"
        if health_upper in {"WARN", "WARNING", "DEGRADED"}:
            return "warn"
        return "ok"

    def _system_state_kind(self, state: str) -> str:
        state_upper = str(state or "").upper()
        if any(token in state_upper for token in ["FAULT", "ESTOP", "ALARM", "ERROR"]):
            return "danger"
        if any(token in state_upper for token in ["PAUSED", "SEEKING", "RETREAT", "BOOT", "DISCONNECTED"]):
            return "warn"
        return "ok"

    @Slot(dict)
    def _on_status(self, payload: dict):
        devices = payload["devices"]
        metrics = payload["metrics"]
        current_exp = payload["current_experiment"]
        robot = payload.get("robot", {})
        safety = payload.get("safety", {})
        recording = payload.get("recording", {})
        config = payload.get("config", {})
        workflow = payload.get("workflow", {})
        system_state = payload["state"]

        self._apply_permissions(payload)
        for name, (lab, det) in self.overview_page.device_labels.items():
            status = devices[name]
            state_kind = self._device_state(status.get("connected", False), status.get("health", ""))
            self._set_badge_state(lab, status["health"], state_kind)
            det.setText(status["detail"])

        self.overview_page.timeline.set_current(system_state)
        self.scan_page.lbl_segment.setText(str(metrics["segment_id"]))
        self.scan_page.lbl_path_idx.setText(str(metrics["path_index"]))
        self.scan_page.lbl_frame_id.setText(str(metrics["frame_id"]))
        self.scan_page.progress.setValue(int(metrics["scan_progress"]))
        self.scan_page.lbl_pressure_current.setText(f"{metrics['pressure_current']:.2f} N")
        self.scan_page.lbl_pressure_target.setText(f"{metrics['pressure_target']:.2f} N")
        self.scan_page.lbl_contact_mode.setText(metrics["contact_mode"])
        self.scan_page.lbl_contact_conf.setText(f"{metrics['contact_confidence']:.2f}")
        pose = metrics["tcp_pose"]
        pose_text = f"x={pose['x']:.1f}, y={pose['y']:.1f}, z={pose['z']:.1f}, rx={pose['rx']:.1f}, ry={pose['ry']:.1f}, rz={pose['rz']:.1f}"
        self.scan_page.lbl_pose.setText(pose_text)
        self.robot_monitor_page.lbl_joint_pos.setText(str(metrics["joint_pos"]))
        self.robot_monitor_page.lbl_joint_vel.setText(str(metrics["joint_vel"]))
        self.robot_monitor_page.lbl_joint_torque.setText(str(metrics["joint_torque"]))
        self.robot_monitor_page.lbl_tcp.setText(pose_text)
        self.robot_monitor_page.lbl_cart_force.setText(str(metrics["cart_force"]))
        self.robot_monitor_page.lbl_operate_mode.setText(robot.get("operate_mode", "-"))
        self.robot_monitor_page.lbl_power_state.setText("ON" if robot.get("powered", False) else "OFF")
        self.assessment_page.lbl_cobb.setText(f"{metrics['cobb_angle']:.1f}°")
        self.assessment_page.lbl_feature_conf.setText(f"{metrics['feature_confidence']:.2f}")
        self.assessment_page.lbl_quality_score.setText(f"{metrics.get('quality_score', metrics['image_quality']):.2f}")
        self.assessment_page.lbl_assessment_state.setText(system_state)

        state_kind = self._system_state_kind(system_state)
        exp_id = current_exp["exp_id"] if current_exp else "-"
        operate_mode = robot.get("operate_mode", "-")
        self._set_badge_state(self.system_state_label, f"状态 · {system_state}", state_kind)
        self._set_badge_state(self.exp_id_label, f"实验 · {exp_id}", "ok")
        self._set_badge_state(self.header_state_pill, f"系统 · {system_state}", state_kind)
        self._set_badge_state(self.header_mode_pill, f"模式 · {operate_mode}", "ok" if operate_mode not in {"-", "manual"} else "warn")
        self._set_badge_state(self.header_exp_pill, f"实验 · {exp_id}", "ok" if current_exp else "warn")

        self.card_state.update_text(system_state, f"Operate mode: {operate_mode}")
        self.card_state.set_tone("danger" if state_kind == "danger" else "accent")
        self.card_exp.update_text(exp_id, current_exp.get("session_id", "-") if current_exp else "尚未创建实验")
        self.card_pressure.update_text(
            f"{metrics['pressure_current']:.2f} / {metrics['pressure_target']:.2f} N",
            f"{metrics['contact_mode']} / {metrics.get('recommended_action', '-')}",
        )
        self.card_pressure.set_tone("success" if metrics["contact_mode"] == "CONTACT_STABLE" else "warning")
        self.card_pose.update_text(
            f"x={pose['x']:.1f}, y={pose['y']:.1f}, z={pose['z']:.1f}",
            f"rx={pose['rx']:.1f}, ry={pose['ry']:.1f}, rz={pose['rz']:.1f}",
        )
        self.card_quality.update_text(
            f"图像 {metrics['image_quality']:.2f}",
            f"质量分 {metrics.get('quality_score', 0.0):.2f}",
        )
        self.card_quality.set_tone("warning" if metrics.get("quality_score", 0.0) < 0.75 else "success")
        self.card_result.update_text(
            f"扫描进度 {metrics['scan_progress']:.0f}%",
            f"段 {metrics['segment_id']} / 录制 {'ON' if recording.get('recording', False) else 'OFF'}",
        )

        summary_lines = [
            ("当前系统状态", system_state),
            ("当前实验", exp_id),
            ("当前会话", current_exp.get("session_id", "-") if current_exp else "-"),
            ("当前压力", f"{metrics['pressure_current']:.2f} N / 目标 {metrics['pressure_target']:.2f} N"),
            ("接触状态", f"{metrics['contact_mode']} / 动作建议 {metrics.get('recommended_action', '-') }"),
            ("图像质量", f"{metrics['image_quality']:.2f} / 综合 {metrics.get('quality_score', 0.0):.2f}"),
            ("当前 Cobb角", f"{metrics['cobb_angle']:.1f}°"),
            (
                "定位策略",
                f"{workflow.get('localization', {}).get('implementation', '-')} / {workflow.get('localization', {}).get('state', '-')}",
            ),
            (
                "路径策略",
                f"{workflow.get('scan_plan', {}).get('implementation', '-')} / {workflow.get('scan_plan', {}).get('state', '-')}",
            ),
            (
                "安全判定",
                f"{'YES' if safety.get('safe_to_scan', False) else 'NO'} / 联锁 {', '.join(safety.get('active_interlocks', [])) or '-'}",
            ),
        ]
        summary_html = "".join(
            f"<p><span style='color:#8FA2BF;'>{escape(key)}</span><br>"
            f"<span style='color:#F8FAFC; font-weight:700;'>{escape(value)}</span></p>"
            for key, value in summary_lines
        )
        self.overview_page.overview_text.setHtml(summary_html)

        self.prepare_page.lbl_toolset.setText(str(config.get("tool_name", "-")))
        self.prepare_page.lbl_load.setText(f"{config.get('load_kg', '-') } kg")
        self.prepare_page.lbl_sdk.setText("ROKAE xCore SDK (integrated)")
        self.prepare_page.lbl_power.setText("ON" if robot.get("powered", False) else "OFF")
        self.prepare_page.lbl_mode.setText(operate_mode)
        self.prepare_page.lbl_camera.setText(f"{devices['camera']['health']} / fresh={devices['camera'].get('fresh', False)}")
        self.prepare_page.lbl_ultrasound.setText(f"{devices['ultrasound']['health']} / fresh={devices['ultrasound'].get('fresh', False)}")
        self.prepare_page.lbl_pressure.setText(f"{devices['pressure']['health']} / fresh={devices['pressure'].get('fresh', False)}")

        if safety.get("safe_to_scan", False) and state_kind != "danger":
            self.alarm_banner.set_normal("系统正常 · 安全联锁通过，可继续执行流程")

    @Slot(list)
    def _on_experiments(self, records: list[ExperimentRecord]):
        self.exp_model.set_records(records)

    @Slot(str)
    def _on_system_state(self, state: str):
        self.statusBar().showMessage(f"系统状态切换：{state}", 3000)

    @Slot(str)
    def _on_alarm(self, message: str):
        self.alarm_banner.set_alarm("ALARM", message)
        self._append_log("ALARM", message)

    @Slot(str, str)
    def _append_log(self, level: str, message: str):
        self.log_box.append_colored(level, message)
        self.robot_monitor_page.log_view.append(message)

    def _update_camera_pixmap(self, pix):
        self.scan_page.camera_pane.set_pixmap(pix)
        self.vision_page.camera_pane.set_pixmap(pix)
        self.reconstruction_page.raw_pane.set_pixmap(pix)

    def _update_ultrasound_pixmap(self, pix):
        self.scan_page.ultrasound_pane.set_pixmap(pix)
        self.reconstruction_page.pre_pane.set_pixmap(pix)
        self.reconstruction_page.feature_pane.set_pixmap(pix)

    def _update_reconstruction_pixmap(self, pix):
        self.reconstruction_page.reconstruction_pane.set_pixmap(pix)

    def _confirm_estop(self):
        ret = QMessageBox.warning(
            self,
            "急停确认",
            "确认执行急停？该操作将立即停止当前流程。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret == QMessageBox.Yes:
            self.alarm_banner.set_alarm("ALARM", "急停触发，所有运动应立即中止。")
            if hasattr(self.backend, "emergency_stop"):
                self.backend.emergency_stop()
            else:
                self.backend.safe_retreat()
