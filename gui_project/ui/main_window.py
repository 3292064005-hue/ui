from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QPushButton, QTextBrowser,
                               QLineEdit, QLabel)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高频网络轮询终端 (架构级)")
        self.resize(800, 600)

        # 初始化中心部件与主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 顶部控制面板布局
        control_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("输入目标 URL...")

        self.btn_start = QPushButton("启动任务")
        self.btn_stop = QPushButton("停止任务")
        self.btn_stop.setEnabled(False)  # 默认禁用

        # 组装控制面板
        control_layout.addWidget(QLabel("Target URL:"))
        control_layout.addWidget(self.url_input)
        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.btn_stop)

        # 底部日志面板 (使用 QTextBrowser，比纯 Text 渲染效率高且支持富文本)
        self.log_browser = QTextBrowser()
        self.log_browser.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas;")

        # 组装主界面
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.log_browser)