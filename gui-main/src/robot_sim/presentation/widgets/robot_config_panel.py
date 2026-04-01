from __future__ import annotations

from robot_sim.presentation.models.dh_table_model import DHTableModel

try:
    from PySide6.QtWidgets import (
        QWidget,
        QLabel,
        QDoubleSpinBox,
    )
except Exception:  # pragma: no cover
    QWidget = object  # type: ignore


class RobotConfigPanel(QWidget):  # pragma: no cover - GUI shell
    def __init__(self, robot_entries, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import (
            QVBoxLayout,
            QLabel,
            QPushButton,
            QComboBox,
            QHBoxLayout,
            QTableView,
            QGroupBox,
            QFormLayout,
        )

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("机器人配置"))

        selector_row = QHBoxLayout()
        self.robot_combo = QComboBox()
        self._set_robot_entries(robot_entries)
        self.load_button = QPushButton("加载")
        self.save_button = QPushButton("保存 YAML")
        selector_row.addWidget(self.robot_combo)
        selector_row.addWidget(self.load_button)
        selector_row.addWidget(self.save_button)
        layout.addLayout(selector_row)

        self.info_label = QLabel("尚未加载机器人")
        layout.addWidget(self.info_label)

        self.table_model = DHTableModel([])
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table_view)

        home_group = QGroupBox("Home q")
        self.home_form = QFormLayout(home_group)
        self.home_boxes: list[QDoubleSpinBox] = []
        self.home_row_labels: list[QLabel] = []
        layout.addWidget(home_group)

    def _set_robot_entries(self, robot_entries) -> None:
        self.robot_combo.clear()
        for entry in robot_entries:
            if hasattr(entry, "label") and hasattr(entry, "name"):
                label = str(entry.label)
                if getattr(entry, "dof", None) is not None:
                    label = f"{label} ({int(entry.dof)} DOF)"
                self.robot_combo.addItem(label, str(entry.name))
            else:
                value = str(entry)
                self.robot_combo.addItem(value, value)

    def selected_robot_name(self) -> str:
        data = self.robot_combo.currentData()
        return str(data if data is not None else self.robot_combo.currentText())

    def _ensure_home_boxes(self, dof: int) -> None:
        from PySide6.QtWidgets import QLabel, QDoubleSpinBox

        while len(self.home_boxes) < dof:
            idx = len(self.home_boxes)
            box = QDoubleSpinBox()
            box.setRange(-999.0, 999.0)
            box.setDecimals(6)
            label = QLabel(f"q{idx}")
            self.home_boxes.append(box)
            self.home_row_labels.append(label)
            self.home_form.addRow(label, box)

    def set_robot_spec(self, spec) -> None:
        desc = f" | {spec.description}" if getattr(spec, 'description', '') else ""
        self.info_label.setText(f"{spec.label} | DOF = {spec.dof}{desc}")
        self.table_model.set_rows(list(spec.dh_rows))
        self._ensure_home_boxes(spec.dof)
        for i, box in enumerate(self.home_boxes):
            visible = i < spec.dof
            box.setVisible(visible)
            self.home_row_labels[i].setVisible(visible)
            if visible:
                box.setValue(float(spec.home_q[i]))

    def edited_home_q(self):
        rows = self.table_model.to_rows()
        return [self.home_boxes[i].value() for i in range(len(rows))]

    def edited_rows(self):
        return list(self.table_model.to_rows())
