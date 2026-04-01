from __future__ import annotations
try:
    from PySide6.QtWidgets import QWidget
except Exception:  # pragma: no cover
    QWidget = object  # type: ignore


class ExportPanel(QWidget):  # pragma: no cover - GUI shell
    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QFormLayout, QPushButton
        layout = QFormLayout(self)
        self.export_bundle_btn = QPushButton('导出轨迹包')
        self.export_benchmark_btn = QPushButton('导出 Benchmark')
        self.export_session_btn = QPushButton('导出会话')
        self.export_package_btn = QPushButton('导出完整 ZIP 包')
        layout.addRow(self.export_bundle_btn)
        layout.addRow(self.export_benchmark_btn)
        layout.addRow(self.export_session_btn)
        layout.addRow(self.export_package_btn)
