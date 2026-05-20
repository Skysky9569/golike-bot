"""
Module chính cho hệ thống GoLike tái cấu trúc
"""

from golike_core.modules.config_manager import ConfigManager
from golike_core.modules.job_processor import JobProcessor
from golike_core.modules.facebook_automation import FacebookAutomationModule
from golike_core.modules.golike_handler import GoLikeModule
from golike_core.modules.config_manager import ConfigManager as ConfigMgr

import os
import sys

class GoLikeManager:
    """Lớp quản lý chính cho hệ thống GoLike"""

    def __init__(self):
        # Khởi tạo các module cần thiết
        self.config_manager = ConfigMgr()
        self.job_processor = JobProcessor()
        self.facebook_automation = FacebookAutomationModule()
        self.golike_handler = GoLikeModule()

        # Tải cấu hình
        self.config = self.config_manager.load_delay_config()

    def run_single_mode(self):
        """Chạy chế độ đơn lẻ"""
        pass

    def run_parallel_mode(self):
        """Chạy chế độ song song"""
        pass

    def setup_delay_config(self):
        """Cấu hình delay"""
        pass

def main():
    # Khởi tạo hệ thống
    manager = GoLikeManager()

    # Menu lựa chọn
    print("1. Chạy đơn lẻ")
    print("2. Chạy song song")
    print("3. Cấu hình")
    print("0. Thoát")

    # Xử lý lựa chọn người dùng
    lua_chon = input("Chọn chế độ: ")

    if lua_chon == "1":
        manager.run_single_mode()
    elif lua_chon == "2":
        manager.run_parallel_mode()
    elif lua_chon == "3":
        manager.setup_delay_config()

if __name__ == "__main__":
    main()