"""
Module tổng hợp hệ thống GoLike với chức năng xử lý rate limit
"""

import time
import json
from selenium import webdriver

class GoLikeSystem:
    """Hệ thống tổng hợp GoLike"""

    def __init__(self):
        self.driver = None
        self.is_running = False

    def initialize_driver(self):
        """Khởi tạo trình duyệt"""
        try:
            options = webdriver.ChromeOptions()
            self.driver = webdriver.Chrome(options=options)
            return True
        except Exception as e:
            print(f"Lỗi khởi tạo trình duyệt: {e}")
            return False

    def check_rate_limit_and_wait(self):
        """Kiểm tra và chờ khi có rate limit"""
        if self.detect_rate_limit():
            print("Phát hiện rate limit, đang chờ 6 giây...")
            time.sleep(6)
            return True
        return False

    def detect_rate_limit(self):
        """Kiểm tra xem có thông báo rate limit không"""
        try:
            # Kiểm tra các phần tử toast message
            toast_elements = self.driver.find_elements("css selector", ".toast-message")
            for element in toast_elements:
                text = element.text.lower()
                if "quá nhanh" in text or "thao tác quá nhanh" in text:
                    return True
            return False
        except:
            return False

    def handle_rate_limit_and_continue(self):
        """Xử lý rate limit và tiếp tục"""
        if self.detect_rate_limit():
            print("Đang xử lý rate limit, chờ 6 giây...")
            time.sleep(6)

            # Refresh trang để tiếp tục
            self.driver.refresh()
            time.sleep(2)
            return True
        return False

# Module sử dụng:
# system = GoLikeSystem()
# if system.check_rate_limit_and_wait():
#     system.handle_rate_limit_and_continue()