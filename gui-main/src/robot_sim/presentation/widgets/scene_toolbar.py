from __future__ import annotations

try:
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import QWidget
except Exception:  # pragma: no cover
    class QWidget:  # type: ignore
        def __init__(self, *args, **kwargs): ...
    class _DummySignal:  # type: ignore
        def __init__(self, *args, **kwargs): ...
        def emit(self, *args, **kwargs): ...
        def connect(self, *args, **kwargs): ...
    Signal = _DummySignal  # type: ignore


class SceneToolbar(QWidget):  # pragma: no cover - GUI shell
    fit_requested = Signal()
    clear_path_requested = Signal()
    screenshot_requested = Signal()
    target_axes_toggled = Signal(bool)
    trajectory_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            from PySide6.QtWidgets import QHBoxLayout, QPushButton, QCheckBox
        except ImportError:
            return
        layout = QHBoxLayout(self)
        self.fit_btn = QPushButton('适配视角')
        self.clear_path_btn = QPushButton('清空轨迹')
        self.screenshot_btn = QPushButton('截图')
        self.target_axes_chk = QCheckBox('目标坐标轴')
        self.trajectory_chk = QCheckBox('轨迹')
        self.target_axes_chk.setChecked(True)
        self.trajectory_chk.setChecked(True)
        for widget in [self.fit_btn, self.clear_path_btn, self.screenshot_btn, self.target_axes_chk, self.trajectory_chk]:
            layout.addWidget(widget)
        layout.addStretch(1)
        self.fit_btn.clicked.connect(self.fit_requested.emit)
        self.clear_path_btn.clicked.connect(self.clear_path_requested.emit)
        self.screenshot_btn.clicked.connect(self.screenshot_requested.emit)
        self.target_axes_chk.toggled.connect(self.target_axes_toggled.emit)
        self.trajectory_chk.toggled.connect(self.trajectory_toggled.emit)
