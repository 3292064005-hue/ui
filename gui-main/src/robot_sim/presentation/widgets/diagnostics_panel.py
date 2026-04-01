from __future__ import annotations
try:
    from PySide6.QtWidgets import QWidget
except Exception:  # pragma: no cover
    QWidget = object  # type: ignore


class DiagnosticsPanel(QWidget):  # pragma: no cover - GUI shell
    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QVBoxLayout, QFormLayout, QLabel, QGroupBox
        layout = QVBoxLayout(self)
        group = QGroupBox('诊断 / 质量')
        form = QFormLayout(group)
        self.labels = {}
        for key, title in [
            ('traj_mode', '轨迹模式'),
            ('traj_feasible', '可行性'),
            ('traj_reasons', '不可行原因'),
            ('path_length', '末端路径长度'),
            ('jerk_proxy', 'Jerk 代理'),
            ('bench_success', 'Benchmark 成功率'),
            ('bench_p95', 'Benchmark P95 ms'),
            ('bench_restarts', '平均重试次数'),
        ]:
            label = QLabel('-')
            self.labels[key] = label
            form.addRow(title, label)
        layout.addWidget(group)

    def set_values(self, **kwargs) -> None:
        for key, value in kwargs.items():
            label = self.labels.get(key)
            if label is not None:
                label.setText(str(value))
