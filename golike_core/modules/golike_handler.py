"""
Module xử lý tương tác với hệ thống GoLike
"""

import time
import json
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
            # Click vào nút chọn tài khoản
            select_account = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.select-account"))
            )
            self.driver.execute_script("arguments[0].click();", select_account)
            time.sleep(2)

            return True
        except Exception as e:
            print(f"Lỗi chọn tài khoản Facebook: {e}")
            return False