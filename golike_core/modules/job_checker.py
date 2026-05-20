"""
Module kiểm tra và xử lý job với chức năng rate limit
"""

import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class JobChecker:
    """Module kiểm tra và xử lý job với chức năng rate limit"""

    def __init__(self, driver):
        self.driver = driver
        self.rate_limit_detected = False

    def check_and_handle_job(self):
        """Kiểm tra và xử lý job, bao gồm cả việc phát hiện rate limit"""
        try:
            # Kiểm tra xem có job mới không
            job_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.card.hand, div.card.card-primary")

            # Kiểm tra rate limit
            if self.check_rate_limit_detected():
                print("Phát hiện rate limit, đang chờ 6 giây...")
                self.handle_rate_limit()
                return {"status": "rate_limited", "message": "Đã xử lý rate limit"}

            if job_elements:
                # Xử lý job đầu tiên
                first_job = job_elements[0]
                return self.process_job(first_job)
            else:
                # Không có job, kiểm tra xem có cần refresh không
                return self.check_and_refresh_if_needed()

        except Exception as e:
            return {"status": "error", "message": f"Lỗi khi kiểm tra job: {str(e)}"}

    def check_rate_limit_detected(self):
        """Kiểm tra xem có đang bị rate limit không"""
        try:
            # Kiểm tra có thông báo "thao tác quá nhanh" không
            toast_elements = self.driver.find_elements(By.CSS_SELECTOR, ".toast-message")
            for element in toast_elements:
                if "quá nhanh" in element.text.lower() or "thao tác quá nhanh" in element.text.lower():
                    return True
            return False
        except:
            return False

    def handle_rate_limit(self):
        """Xử lý khi phát hiện rate limit"""
        print("Đang chờ 6 giây do rate limit...")
        time.sleep(6)  # Chờ 6 giây

        # Refresh trang để tiếp tục
        self.driver.refresh()
        print("Đã refresh trang sau khi chờ")

    def process_job(self, job_element):
        """Xử lý một job cụ thể"""
        try:
            # Click vào job
            job_element.click()

            # Kiểm tra rate limit sau khi click
            if self.check_rate_limit_detected():
                self.handle_rate_limit()
                return {"status": "rate_limited", "message": "Đã xử lý rate limit"}

            return {"status": "success", "message": "Xử lý job thành công"}
        except Exception as e:
            return {"status": "error", "message": f"Lỗi xử lý job: {str(e)}"}

    def check_and_refresh_if_needed(self):
        """Kiểm tra và refresh nếu cần thiết"""
        # Kiểm tra nếu không có job trong một thời gian dài thì refresh
        print("Không có job, đang refresh...")
        self.driver.refresh()
        time.sleep(2)
        return {"status": "refreshed", "message": "Đã refresh trang"}