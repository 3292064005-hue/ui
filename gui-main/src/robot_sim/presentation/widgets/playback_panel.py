from __future__ import annotations

try:
    from PySide6.QtWidgets import QWidget
except Exception:  # pragma: no cover
    QWidget = object  # type: ignore


class PlaybackPanel(QWidget):  # pragma: no cover - GUI shell
    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSlider, QLabel, QDoubleSpinBox, QCheckBox
        from PySide6.QtCore import Qt

        layout = QHBoxLayout(self)
        self.play_btn = QPushButton("播放")
        self.pause_btn = QPushButton("暂停")
        self.step_btn = QPushButton("单步")
        self.stop_btn = QPushButton("停止")
        self.export_btn = QPushButton("导出轨迹")
        self.session_btn = QPushButton("导出会话")
        self.package_btn = QPushButton("导出整包")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.cursor_label = QLabel("0 / 0")
        self.speed = QDoubleSpinBox()
        self.speed.setRange(0.1, 10.0)
        self.speed.setSingleStep(0.1)
        self.speed.setValue(1.0)
        self.loop = QCheckBox("循环")
        for w in [
            self.play_btn,
            self.pause_btn,
            self.step_btn,
            self.stop_btn,
            QLabel("帧"),
            self.slider,
            self.cursor_label,
            QLabel("倍率"),
            self.speed,
            self.loop,
            self.export_btn,
            self.session_btn,
            self.package_btn,
        ]:
            layout.addWidget(w)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)

    def set_total_frames(self, total: int) -> None:
        total = max(int(total), 0)
        self.slider.setRange(0, max(total - 1, 0))
        self.cursor_label.setText(f"0 / {max(total - 1, 0)}")

    def set_frame(self, idx: int, total: int) -> None:
        self.slider.blockSignals(True)
        self.slider.setRange(0, max(int(total) - 1, 0))
        self.slider.setValue(max(0, min(int(idx), max(int(total) - 1, 0))))
        self.slider.blockSignals(False)
        self.cursor_label.setText(f"{int(idx)} / {max(int(total) - 1, 0)}")

    def set_running(self, running: bool) -> None:
        self.play_btn.setEnabled(not running)
        self.pause_btn.setEnabled(running)
        self.step_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
