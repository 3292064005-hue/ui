from __future__ import annotations
import numpy as np
from robot_sim.core.math.transforms import rot_x, rot_y, rot_z
from robot_sim.core.math.so3 import log_so3, exp_so3

try:
    from PySide6.QtWidgets import QWidget
except Exception:  # pragma: no cover
    QWidget = object  # type: ignore


class TargetPosePanel(QWidget):  # pragma: no cover - GUI shell
    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QFormLayout, QDoubleSpinBox, QComboBox, QPushButton, QHBoxLayout, QVBoxLayout

        root = QVBoxLayout(self)
        self.orientation_mode = QComboBox()
        self.orientation_mode.addItems(["rvec", "euler_zyx"])
        root.addWidget(self.orientation_mode)

        form = QFormLayout()
        root.addLayout(form)
        self.pos_boxes = []
        for name in ("x", "y", "z", "o1", "o2", "o3"):
            box = QDoubleSpinBox()
            box.setRange(-999.0, 999.0)
            box.setDecimals(6)
            box.setSingleStep(0.05)
            self.pos_boxes.append(box)
            form.addRow(name, box)

        actions = QHBoxLayout()
        self.fill_current_btn = QPushButton("用当前位姿填充")
        self.reset_btn = QPushButton("清零")
        actions.addWidget(self.fill_current_btn)
        actions.addWidget(self.reset_btn)
        root.addLayout(actions)
        self.reset_btn.clicked.connect(self.reset_values)

    def reset_values(self):
        for box in self.pos_boxes:
            box.setValue(0.0)

    def values6(self):
        return np.array([box.value() for box in self.pos_boxes], dtype=float)

    def set_from_pose(self, pose) -> None:
        self.pos_boxes[0].setValue(float(pose.p[0]))
        self.pos_boxes[1].setValue(float(pose.p[1]))
        self.pos_boxes[2].setValue(float(pose.p[2]))
        if self.orientation_mode.currentText() == "euler_zyx":
            yaw = float(np.arctan2(pose.R[1, 0], pose.R[0, 0]))
            pitch = float(np.arctan2(-pose.R[2, 0], np.sqrt(pose.R[2, 1] ** 2 + pose.R[2, 2] ** 2)))
            roll = float(np.arctan2(pose.R[2, 1], pose.R[2, 2]))
            ori = [yaw, pitch, roll]
        else:
            ori = log_so3(pose.R)
        for i in range(3):
            self.pos_boxes[3 + i].setValue(float(ori[i]))

    def rotation_matrix(self) -> np.ndarray:
        values = self.values6()[3:]
        if self.orientation_mode.currentText() == "euler_zyx":
            yaw, pitch, roll = values
            return rot_z(float(yaw)) @ rot_y(float(pitch)) @ rot_x(float(roll))
        return exp_so3(values)
