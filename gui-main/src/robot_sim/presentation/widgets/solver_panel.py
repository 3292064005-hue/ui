from __future__ import annotations

try:
    from PySide6.QtWidgets import QWidget
except Exception:  # pragma: no cover
    QWidget = object


class SolverPanel(QWidget):  # pragma: no cover - GUI shell
    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QPushButton, QSpinBox

        layout = QFormLayout(self)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["pinv", "dls", "lm", "analytic_6r"])

        self.max_iters = QSpinBox()
        self.max_iters.setRange(1, 5000)
        self.max_iters.setValue(150)

        self.step_scale = QDoubleSpinBox()
        self.step_scale.setRange(0.01, 2.0)
        self.step_scale.setValue(0.5)

        self.damping = QDoubleSpinBox()
        self.damping.setRange(0.0, 10.0)
        self.damping.setValue(0.05)

        self.pos_tol = QDoubleSpinBox()
        self.pos_tol.setDecimals(6)
        self.pos_tol.setRange(1e-6, 1.0)
        self.pos_tol.setValue(1e-4)

        self.ori_tol = QDoubleSpinBox()
        self.ori_tol.setDecimals(6)
        self.ori_tol.setRange(1e-6, 10.0)
        self.ori_tol.setValue(1e-4)

        self.max_step_norm = QDoubleSpinBox()
        self.max_step_norm.setRange(1e-4, 10.0)
        self.max_step_norm.setValue(0.35)

        self.joint_limit_weight = QDoubleSpinBox()
        self.joint_limit_weight.setRange(0.0, 10.0)
        self.joint_limit_weight.setValue(0.03)

        self.manipulability_weight = QDoubleSpinBox()
        self.manipulability_weight.setRange(0.0, 10.0)
        self.manipulability_weight.setValue(0.0)

        self.orientation_weight = QDoubleSpinBox()
        self.orientation_weight.setRange(0.0, 10.0)
        self.orientation_weight.setValue(1.0)

        self.enable_nullspace = QCheckBox()
        self.enable_nullspace.setChecked(True)

        self.position_only = QCheckBox()
        self.position_only.setChecked(False)

        self.auto_fallback = QCheckBox()
        self.auto_fallback.setChecked(True)

        self.reachability_precheck = QCheckBox()
        self.reachability_precheck.setChecked(True)

        self.adaptive_damping = QCheckBox()
        self.adaptive_damping.setChecked(True)

        self.weighted_ls = QCheckBox()
        self.weighted_ls.setChecked(True)

        self.retry_count = QSpinBox()
        self.retry_count.setRange(0, 10)
        self.retry_count.setValue(1)

        self.traj_mode = QComboBox()
        self.traj_mode.addItems(["joint_space", "cartesian_pose"])

        self.traj_duration = QDoubleSpinBox()
        self.traj_duration.setRange(0.1, 120.0)
        self.traj_duration.setValue(3.0)

        self.traj_dt = QDoubleSpinBox()
        self.traj_dt.setDecimals(4)
        self.traj_dt.setRange(0.001, 1.0)
        self.traj_dt.setValue(0.02)

        self.run_fk_btn = QPushButton("执行 FK")
        self.run_ik_btn = QPushButton("执行 IK")
        self.cancel_btn = QPushButton("停止求解")
        self.plan_btn = QPushButton("生成轨迹")
        self.cancel_btn.setEnabled(False)

        layout.addRow("IK 模式", self.mode_combo)
        layout.addRow("最大迭代", self.max_iters)
        layout.addRow("步长", self.step_scale)
        layout.addRow("阻尼 λ", self.damping)
        layout.addRow("位置容差", self.pos_tol)
        layout.addRow("姿态容差", self.ori_tol)
        layout.addRow("步长限幅", self.max_step_norm)
        layout.addRow("关节限位权重", self.joint_limit_weight)
        layout.addRow("可操作度权重", self.manipulability_weight)
        layout.addRow("姿态误差权重", self.orientation_weight)
        layout.addRow("零空间优化", self.enable_nullspace)
        layout.addRow("仅位置 IK", self.position_only)
        layout.addRow("奇异自动切 DLS", self.auto_fallback)
        layout.addRow("工作空间预检查", self.reachability_precheck)
        layout.addRow("自适应阻尼", self.adaptive_damping)
        layout.addRow("加权最小二乘", self.weighted_ls)
        layout.addRow("失败重试次数", self.retry_count)
        layout.addRow("轨迹模式", self.traj_mode)
        layout.addRow("轨迹时长 s", self.traj_duration)
        layout.addRow("采样 dt", self.traj_dt)
        layout.addRow(self.run_fk_btn)
        layout.addRow(self.run_ik_btn)
        layout.addRow(self.cancel_btn)
        layout.addRow(self.plan_btn)

    def apply_defaults(self, config: dict | None) -> None:
        if not config:
            return
        mode = str(config.get("mode", self.mode_combo.currentText()))
        idx = self.mode_combo.findText(mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        self.max_iters.setValue(int(config.get("max_iters", self.max_iters.value())))
        self.step_scale.setValue(float(config.get("step_scale", self.step_scale.value())))
        self.damping.setValue(float(config.get("damping_lambda", config.get("damping", self.damping.value()))))
        self.pos_tol.setValue(float(config.get("pos_tol", self.pos_tol.value())))
        self.ori_tol.setValue(float(config.get("ori_tol", self.ori_tol.value())))
        self.max_step_norm.setValue(float(config.get("max_step_norm", self.max_step_norm.value())))
        self.joint_limit_weight.setValue(float(config.get("joint_limit_weight", self.joint_limit_weight.value())))
        self.manipulability_weight.setValue(float(config.get("manipulability_weight", self.manipulability_weight.value())))
        self.orientation_weight.setValue(float(config.get("orientation_weight", self.orientation_weight.value())))
        self.enable_nullspace.setChecked(bool(config.get("enable_nullspace", self.enable_nullspace.isChecked())))
        self.position_only.setChecked(bool(config.get("position_only", self.position_only.isChecked())))
        self.auto_fallback.setChecked(bool(config.get("fallback_to_dls_when_singular", self.auto_fallback.isChecked())))
        self.reachability_precheck.setChecked(bool(config.get("reachability_precheck", self.reachability_precheck.isChecked())))
        self.adaptive_damping.setChecked(bool(config.get("adaptive_damping", self.adaptive_damping.isChecked())))
        self.weighted_ls.setChecked(bool(config.get("use_weighted_least_squares", self.weighted_ls.isChecked())))
        self.retry_count.setValue(int(config.get("retry_count", self.retry_count.value())))

    def apply_trajectory_defaults(self, config: dict | None) -> None:
        if not config:
            return
        self.traj_duration.setValue(float(config.get("duration", self.traj_duration.value())))
        self.traj_dt.setValue(float(config.get("dt", self.traj_dt.value())))
        mode = str(config.get("mode", self.traj_mode.currentText()))
        idx = self.traj_mode.findText(mode)
        if idx >= 0:
            self.traj_mode.setCurrentIndex(idx)

    def set_running(self, running: bool) -> None:
        self.cancel_btn.setEnabled(running)
        self.run_ik_btn.setEnabled(not running)
        self.plan_btn.setEnabled(not running)
        self.run_fk_btn.setEnabled(not running)
