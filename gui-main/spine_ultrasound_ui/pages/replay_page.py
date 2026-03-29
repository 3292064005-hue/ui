from PySide6.QtWidgets import QGroupBox, QLabel, QTextEdit, QVBoxLayout, QWidget


class ReplayPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        title = QLabel("实验回放")
        title.setObjectName("PageTitle")
        subtitle = QLabel("查看时间轴、关键告警点、低质量片段与回放备注。")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        box = QGroupBox("回放时间轴")
        v = QVBoxLayout(box)
        self.lbl_current = QLabel("未加载实验")
        self.lbl_current.setObjectName("FieldValue")
        self.timeline = QTextEdit()
        self.timeline.setReadOnly(True)
        self.timeline.setPlaceholderText("时间轴 / 告警点 / 低质量段将在这里显示。")
        v.addWidget(self.lbl_current)
        v.addWidget(self.timeline)
        layout.addWidget(box)
