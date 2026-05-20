"""
Module xử lý tương tác với hệ thống GoLike
"""

import time
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class GoLikeModule:
    """Module xử lý tương tác với GoLike"""

    def __init__(self, driver=None):
        self.driver = driver
        self.current_job = None

    def login_golike(self, username, password):
        """Đăng nhập vào tài khoản GoLike"""
        if not self.driver:
            return False

        try:
            self.driver.get("https://app.golike.net/login")
            time.sleep(2)

            # Nhập thông tin đăng nhập
            username_field = self.driver.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/div/form/div[1]/input')
            username_field.clear()
            username_field.send_keys(username)

            password_field = self.driver.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/div/form/div[2]/div/input')
            password_field.clear()
            password_field.send_keys(password)

            login_button = self.driver.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/div/form/div[3]/button')
            login_button.click()

            return True
        except Exception as e:
            print(f"Lỗi đăng nhập GoLike: {e}")
            return False

    def navigate_to_facebook_jobs(self):
        """Điều hướng đến phần nhiệm vụ Facebook"""
        try:
            # Click vào menu nhiệm vụ
            job_menu = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[2]/div/div/div[2]'))
            )
            self.driver.execute_script("arguments[0].click();", job_menu)

            # Click vào Facebook
            fb_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[1]/div[2]/div[3]/div[1]/div'))
            )
            self.driver.execute_script("arguments[0].click();", fb_button)

            return True
        except Exception as e:
            print(f"Lỗi điều hướng đến Facebook jobs: {e}")
            return False

    def select_facebook_account(self, account_name=None, account_id=None):
        """Chọn tài khoản Facebook để chạy"""
        try:
            select_account = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.select-account"))
            )
            self.driver.execute_script("arguments[0].click();", select_account)
            time.sleep(2)
            return True
        except Exception as e:
            print(f"Lỗi chọn tài khoản Facebook: {e}")
            return False

    def check_rate_limit_error(self, page_source):
        """Kiểm tra xem có thông báo rate limit không"""
        rate_limit_keywords = [
            "thao tác quá nhanh", "quá nhanh", "rate limit", "thử lại sau", "vui lòng chờ"
        ]

        for keyword in rate_limit_keywords:
            if keyword in page_source.lower():
                return True
        return False

    def handle_rate_limit_and_wait(self):
        """Xử lý rate limit bằng cách chờ 6 giây rồi refresh"""
        print("Phát hiện rate limit, đang chờ 6 giây...")
        time.sleep(6)
        self.driver.refresh()
        print("Đã refresh trang sau khi chờ")
        return True