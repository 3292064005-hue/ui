import time
import requests
from PySide6.QtCore import QThread, Signal

class NetworkWorker(QThread):
    # 定义标准输出信号
    log_signal = Signal(str)
    # 定义状态变化信号 (True=运行中, False=已停止)
    status_signal = Signal(bool)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self._is_running = False

    def run(self):
        self._is_running = True
        self.status_signal.emit(True)

        # 安全读取配置
        target_url = self.config.get('network', {}).get('target_url', 'http://localhost')
        timeout_val = self.config.get('network', {}).get('timeout', 5.0)
        interval_val = self.config.get('network', {}).get('interval', 1.0)

        while self._is_running:
            try:
                response = requests.get(target_url, timeout=timeout_val)
                self.log_signal.emit(f"[INFO] 成功 | 状态码: {response.status_code} | {target_url}")
            except requests.Timeout:
                self.log_signal.emit(f"[WARN] 超时 | 超过 {timeout_val}s 未响应")
            except Exception as e:
                self.log_signal.emit(f"[ERROR] 异常 | {str(e)}")

            # 微轮询休眠机制：将长 sleep 切分为 0.1s 的短轮询
            # 确保用户点击停止时，能立即打断休眠并退出循环
            elapsed = 0.0
            while elapsed < interval_val and self._is_running:
                time.sleep(0.1)
                elapsed += 0.1

        # 循环结束，发射停止信号
        self.status_signal.emit(False)

    def stop(self):
        """外部调用，改变标志位"""
        self._is_running = False