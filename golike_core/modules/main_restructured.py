"""
Tập tin chính cho hệ thống GoLike - phiên bản tái cấu trúc
"""

import os
import sys
from golike_core.modules.config_manager import ConfigManager
from golike_core.modules.job_processor import JobProcessor
from golike_core.modules.facebook_automation import FacebookAutomationModule
from golike_core.modules.golike_handler import GoLikeModule
from golike_core.modules.browser_manager import BrowserManager

def main():
    """Hàm chính của ứng dụng"""
    print("GoLike Bot - Hệ thống tự động")
    print("=" * 40)

    # Khởi tạo các module cần thiết
    config_manager = ConfigManager()
    job_processor = JobProcessor()
    browser_manager = BrowserManager()

    # Tải cấu hình
    config = config_manager.load_delay_config()
    print(f"Đã tải cấu hình delay: {config.get('delay_between_jobs', 10)} giây")

    # Menu lựa chọn
    while True:
        print("\n1. Chạy đơn lẻ")
        print("2. Chạy song song")
        print("3. Cấu hình")
        print("0. Thoát")

        choice = input("Chọn chế độ: ").strip()

        if choice == "0":
            print("Tạm biệt!")
            break
        elif choice == "1":
            print("Chạy đơn lẻ...")
        elif choice == "2":
            print("Chạy song song...")
        elif choice == "3":
            print("Cấu hình...")
        else:
            print("Lựa chọn không hợp lệ")

if __name__ == "__main__":
    main()