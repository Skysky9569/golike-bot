"""
Ví dụ sử dụng các module đã tạo
"""

import time
from selenium import webdriver
from golike_core.modules.job_checker import JobChecker
from golike_core.modules.golike_handler_updated import GoLikeModule

def main():
    # Khởi tạo trình duyệt
    driver = webdriver.Chrome()
    driver.get("https://app.golike.net")

    # Khởi tạo các module
    job_checker = JobChecker(driver)
    golike_module = GoLikeModule(driver)

    # Vòng lặp kiểm tra job
    while True:
        try:
            # Kiểm tra rate limit trước khi thực hiện bất kỳ thao tác nào
            if job_checker.check_rate_limit_and_wait():
                print("Đang chờ do rate limit...")
                time.sleep(6)
                driver.refresh()
                continue

            # Kiểm tra job mới
            result = job_checker.check_and_handle_job()

            if result["status"] == "rate_limited":
                print("Đã xử lý rate limit, tiếp tục vòng lặp")
                time.sleep(6)
                continue

            elif result["status"] == "success":
                print("Xử lý job thành công")

            # Chờ trước khi kiểm tra job tiếp theo
            time.sleep(5)

        except KeyboardInterrupt:
            print("Đã dừng bởi người dùng")
            break
        except Exception as e:
            print(f"Lỗi trong quá trình chạy: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()