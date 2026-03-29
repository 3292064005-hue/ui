from PySide6.QtWidgets import QFormLayout, QGridLayout, QGroupBox, QLabel, QVBoxLayout, QWidget


class PreparePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        title = QLabel("系统准备")
        title.setObjectName("PageTitle")
        subtitle = QLabel("用于开机自检、硬件连通性确认与当前运行模式检查。")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setSpacing(12)

        box_hw = QGroupBox("硬件与载荷")
        form_hw = QFormLayout(box_hw)
        self.lbl_toolset = QLabel("-")
        self.lbl_toolset.setObjectName("FieldValue")
        self.lbl_load = QLabel("-")
        self.lbl_load.setObjectName("FieldValue")
        self.lbl_sdk = QLabel("-")
        self.lbl_sdk.setObjectName("FieldValue")
        form_hw.addRow("Toolset", self.lbl_toolset)
        form_hw.addRow("Load", self.lbl_load)
        form_hw.addRow("SDK", self.lbl_sdk)
        grid.addWidget(box_hw, 0, 0)

        box_runtime = QGroupBox("运行状态")
        form_runtime = QFormLayout(box_runtime)
        self.lbl_power = QLabel("-")
        self.lbl_power.setObjectName("FieldValue")
        self.lbl_mode = QLabel("-")
        self.lbl_mode.setObjectName("FieldValue")
        form_runtime.addRow("Power", self.lbl_power)
        form_runtime.addRow("Operate mode", self.lbl_mode)
        grid.addWidget(box_runtime, 0, 1)

        box_io = QGroupBox("感知链路")
        form_io = QFormLayout(box_io)
        self.lbl_camera = QLabel("-")
        self.lbl_camera.setObjectName("FieldValue")
        self.lbl_ultrasound = QLabel("-")
        self.lbl_ultrasound.setObjectName("FieldValue")
        self.lbl_pressure = QLabel("-")
        self.lbl_pressure.setObjectName("FieldValue")
        form_io.addRow("Camera", self.lbl_camera)
        form_io.addRow("Ultrasound", self.lbl_ultrasound)
        form_io.addRow("Pressure", self.lbl_pressure)
        grid.addWidget(box_io, 1, 0, 1, 2)

        layout.addLayout(grid)

        note = QLabel("进入自动扫查前，请确认 Power=ON、Operate mode 正确，且 Camera / Ultrasound / Pressure 三路均 fresh。")
        note.setObjectName("MutedLabel")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
