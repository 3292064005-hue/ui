from __future__ import annotations
try:
    from PySide6.QtWidgets import QWidget
except Exception:  # pragma: no cover
    QWidget = object  # type: ignore


class StatusPanel(QWidget):  # pragma: no cover - GUI shell
    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QVBoxLayout, QLabel, QTextEdit, QFormLayout, QGroupBox

        layout = QVBoxLayout(self)
        self.summary = QLabel("状态：未运行")
        layout.addWidget(self.summary)

        metrics_group = QGroupBox("求解指标")
        metrics_layout = QFormLayout(metrics_group)
        self.metric_labels = {}
        for key, title in [
            ("iterations", "迭代次数"),
            ("pos_err", "位置误差"),
            ("ori_err", "姿态误差"),
            ("cond", "条件数"),
            ("manip", "可操作度"),
            ("dq_norm", "末步长度"),
            ("mode", "实际模式"),
            ("damping", "最终阻尼"),
            ("stop_reason", "停止原因"),
            ("elapsed", "耗时 ms"),
            ("playback", "播放状态"),
        ]:
            label = QLabel("-")
            self.metric_labels[key] = label
            metrics_layout.addRow(title, label)
        layout.addWidget(metrics_group)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

    def append(self, text: str):
        self.log.append(text)

    def set_metrics(self, **kwargs) -> None:
        for key, value in kwargs.items():
            label = self.metric_labels.get(key)
            if label is not None:
                label.setText(str(value))
