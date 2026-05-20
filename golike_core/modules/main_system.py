"""
Module tổng quan cho hệ thống GoLike
"""

import os
import sys

# Import các module đã tạo
from golike_core.modules import config_manager, job_processor, facebook_automation
from golike_core.modules import golike_handler, browser_manager

class GoLikeSystem:
    """Lớp tổng quan cho hệ thống GoLike"""

    def __init__(self):
        self.config_manager = config_manager.ConfigManager()
        self.job_processor = job_processor.JobProcessor()
        self.facebook_automation = facebook_automation.FacebookAutomationModule()
        self.golike_handler = golike_handler.GoLikeModule()
        self.browser_manager = browser_manager.BrowserManager()

    def initialize(self):
        """Khởi tạo hệ thống"""
        print("Hệ thống GoLike đã được khởi tạo")
        return True

# Khởi tạo hệ thống
system = GoLikeSystem()
system.initialize()