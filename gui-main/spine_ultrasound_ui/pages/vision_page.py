from PySide6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget

from spine_ultrasound_ui.widgets import ImagePane


class VisionPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        title = QLabel("视觉与路径")
        title.setObjectName("PageTitle")
        subtitle = QLabel("显示体表定位、脊柱走向估计以及扫查路径预览结果。")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.camera_pane = ImagePane("背部定位视图", "建议叠加 ROI、中线、起止点和路径轨迹")
        layout.addWidget(self.camera_pane)
        note = QTextEdit()
        note.setReadOnly(True)
        note.setText(
            "视觉定位页用于显示：\n"
            "1. 背部区域识别结果\n"
            "2. 体表中线与脊柱走向估计\n"
            "3. 起止点与路径预览\n\n"
            "后续只需把视觉节点的叠加层绘制到该视图即可。"
        )
        layout.addWidget(note)
