import sys
import yaml
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from core.worker import NetworkWorker

class AppController:
    def __init__(self):
        # 1. 尝试加载配置文件
        self.config = self.load_config()

        # 2. 初始化 GUI 引擎与主窗口
        self.app = QApplication(sys.argv)
        self.app.setStyle("Fusion")  # 强制 Fusion 风格，跨平台表现最佳
        self.window = MainWindow()

        # 将配置中的默认 URL 填入 UI
        default_url = self.config.get('network', {}).get('target_url', '')
        self.window.url_input.setText(default_url)

        self.worker = None

        # 3. 绑定 UI 事件到控制器逻辑
        self.window.btn_start.clicked.connect(self.start_worker)
        self.window.btn_stop.clicked.connect(self.stop_worker)

    def load_config(self):
        try:
            with open("data/config.yaml", "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print("[SYSTEM] 警告: 未找到 config.yaml，将使用默认配置。")
            return {"network": {"target_url": "https://api.github.com/zen", "timeout": 3, "interval": 1}, "ui": {"max_log_lines": 500}}

    def start_worker(self):
        """处理启动逻辑"""
        # 从 UI 获取最新 URL 覆盖配置
        self.config['network']['target_url'] = self.window.url_input.text()

        # 实例化并启动后台线程
        self.worker = NetworkWorker(self.config)

        # 信号绑定：核心解耦点
        self.worker.log_signal.connect(self.update_log)
        self.worker.status_signal.connect(self.update_ui_state)

        self.worker.start()

    def stop_worker(self):
        """处理停止逻辑"""
        if self.worker and self.worker.isRunning():
            self.update_log("[SYSTEM] 发送停止指令，等待当前循环结束...")
            self.worker.stop()

    def update_log(self, message):
        """接收线程日志并渲染到 UI"""
        self.window.log_browser.append(message)

        # 核心：防 OOM (内存溢出) 截断逻辑
        max_lines = self.config.get('ui', {}).get('max_log_lines', 500)
        doc = self.window.log_browser.document()
        if doc.blockCount() > max_lines:
            cursor = self.window.log_browser.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

    def update_ui_state(self, is_running):
        """根据线程真实状态，动态锁定/解锁 UI 控件"""
        self.window.btn_start.setEnabled(not is_running)
        self.window.btn_stop.setEnabled(is_running)
        self.window.url_input.setEnabled(not is_running)

    def run(self):
        """启动应用"""
        self.window.show()
        # 核心：防止关闭窗口时，后台请求仍在进行导致僵尸进程
        self.app.aboutToQuit.connect(self.stop_worker)
        sys.exit(self.app.exec())

if __name__ == "__main__":
    controller = AppController()
    controller.run()