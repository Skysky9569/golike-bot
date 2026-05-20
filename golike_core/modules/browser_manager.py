"""
Module quản lý trình duyệt và tự động hóa
"""

import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

class BrowserManager:
    """Module quản lý trình duyệt"""

    def __init__(self):
        self.driver = None
        self.is_initialized = False

    def setup_browser(self, headless=False):
        """Thiết lập trình duyệt"""
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")

        if headless:
            options.add_argument("--headless")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        self.is_initialized = True
        return self.driver

    def close_browser(self):
        """Đóng trình duyệt"""
        if self.driver and self.is_initialized:
            self.driver.quit()
            self.is_initialized = False

    def navigate_to_url(self, url):
        """Điều hướng đến URL"""
        if self.driver and self.is_initialized:
            self.driver.get(url)
            return True
        return False