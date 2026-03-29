from PySide6.QtWidgets import QGroupBox, QLabel, QTextEdit, QVBoxLayout, QWidget


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        title = QLabel("系统设置")
        title.setObjectName("PageTitle")
        subtitle = QLabel("集中管理全局配置、设备参数、扫查策略与导出规则。")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        box = QGroupBox("设置面板规划")
        v = QVBoxLayout(box)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setText(
            "建议按以下分区继续扩展：\n"
            "1. 全局配置\n"
            "2. 设备配置\n"
            "3. 扫查配置\n"
            "4. 接触配置\n"
            "5. 质量配置\n"
            "6. 导出配置\n"
        )
        v.addWidget(text)
        layout.addWidget(box)
        layout.addStretch(1)
