"""
iOS Automation module using Appium.
"""
from golike_core.logging import logger

try:
    from appium import webdriver
    from appium.options.ios import XCUITestOptions
    from appium.webdriver.common.appiumby import AppiumBy
    APPIUM_AVAILABLE = True
except ImportError:
    APPIUM_AVAILABLE = False
    logger.warning("Appium-Python-Client not installed. iOS automation will not work.")

import time

class TikTokIOSAutomator:
    def __init__(self, platform_version="16.4", device_name="iPhone 14", udid=None, bundle_id="com.zhiliaoapp.musically"):
        """Khởi tạo kết nối với Appium Server"""
        self.platform_version = platform_version
        self.device_name = device_name
        self.udid = udid
        self.bundle_id = bundle_id
        self.driver = None

    def connect(self) -> bool:
        """Kết nối tới thiết bị iOS thông qua Appium Server."""
        if not APPIUM_AVAILABLE:
            logger.error("Vui lòng cài đặt: pip install Appium-Python-Client")
            return False

        options = XCUITestOptions()
        options.platform_name = "iOS"
        options.platform_version = self.platform_version
        options.device_name = self.device_name
        options.automation_name = "XCUITest"
        
        # com.zhiliaoapp.musically là bundle ID của TikTok Global.
        # com.ss.iphone.ugc.Tiktok là bundle ID của TikTok VN.
        options.bundle_id = self.bundle_id 
        
        if self.udid:
            options.udid = self.udid

        try:
            # Giả định Appium chạy ở localhost:4723
            self.driver = webdriver.Remote(
                command_executor="http://127.0.0.1:4723",
                options=options
            )
            logger.info("✅ Kết nối Appium thành công.")
            return True
        except Exception as e:
            logger.error(f"Lỗi kết nối Appium: {e}")
            return False

    def close(self):
        if self.driver:
            self.driver.quit()
            logger.info("Đã ngắt kết nối Appium.")

    def click_follow(self) -> bool:
        """Thực hiện click Follow trên TikTok iOS."""
        if not self.driver:
            return False
            
        try:
            # PLACEHOLDER: Sửa lại Locator này bằng Appium Inspector sau
            logger.info("Đang tìm nút Follow (iOS)...")
            follow_btn = self.driver.find_element(AppiumBy.ACCESSIBILITY_ID, "Follow")
            follow_btn.click()
            logger.info("✅ Đã click Follow (iOS).")
            return True
        except Exception as e:
            logger.error(f"Không tìm thấy hoặc click lỗi nút Follow: {e}")
            return False
            
    def click_like(self) -> bool:
        """Thực hiện click Like trên TikTok iOS."""
        if not self.driver:
            return False
            
        try:
            # PLACEHOLDER: Sửa lại Locator này bằng Appium Inspector sau
            logger.info("Đang tìm nút Like (iOS)...")
            like_btn = self.driver.find_element(AppiumBy.ACCESSIBILITY_ID, "Like")
            like_btn.click()
            logger.info("✅ Đã click Like (iOS).")
            return True
        except Exception as e:
            logger.error(f"Không tìm thấy hoặc click lỗi nút Like: {e}")
            return False
