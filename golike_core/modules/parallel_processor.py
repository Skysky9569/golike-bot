"""
Module xử lý đa luồng cho hệ thống GoLike
"""

import threading
import time
from golike_core.modules.config_manager import ConfigManager
from golike_core.modules.job_processor import JobProcessor

class ParallelProcessor:
    """Module xử lý đa luồng"""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.active_threads = []
        self.is_running = False

    def start_parallel_processing(self, configs):
        """Bắt đầu xử lý song song với nhiều cấu hình"""
        threads = []

        for config in configs:
            thread = threading.Thread(target=self._process_account, args=(config,))
            threads.append(thread)
            thread.start()

        # Chờ tất cả các luồng hoàn thành
        for thread in threads:
            thread.join()

    def _process_account(self, config):
        """Xử lý một tài khoản cụ thể"""
        try:
            # Logic xử lý cho từng tài khoản
            account_id = config.get('account_id')
            print(f"Đang xử lý tài khoản: {account_id}")

            # Mô phỏng xử lý công việc
            time.sleep(2)
            print(f"Xử lý hoàn tất cho tài khoản: {account_id}")

        except Exception as e:
            print(f"Lỗi khi xử lý tài khoản: {e}")

    def stop_all_threads(self):
        """Dừng tất cả các luồng"""
        self.is_running = False
        print("Đã dừng tất cả các luồng xử lý")