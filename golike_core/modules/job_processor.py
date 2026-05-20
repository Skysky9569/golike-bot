"""
Module xử lý các nhiệm vụ (jobs) cho hệ thống GoLike
"""

import time
import json

class JobProcessor:
    """Module xử lý các nhiệm vụ tự động"""

    def __init__(self):
        self.current_job = None
        self.job_results = []
        self.is_processing = False

    def process_job(self, job_data):
        """Xử lý một nhiệm vụ"""
        try:
            job_type = job_data.get('type', '')
            job_url = job_data.get('url', '')

            # Xử lý theo loại job
            if job_type == 'follow':
                return self._process_follow_job(job_url)
            elif job_type == 'like':
                return self._process_like_job(job_url)
            elif job_type == 'like_page':
                return self._process_like_page_job(job_url)
            else:
                return {"success": False, "error": "Loại job không được hỗ trợ"}
        except Exception as e:
            return {"success": False, "error": f"Lỗi xử lý job: {str(e)}"}

    def _process_follow_job(self, url):
        """Xử lý nhiệm vụ follow"""
        # Logic xử lý follow
        try:
            # Thực hiện follow trên Facebook
            return {"success": True, "message": "Follow thành công"}
        except Exception as e:
            return {"success": False, "error": f"Lỗi follow: {str(e)}"}

    def _process_like_job(self, url):
        """Xử lý nhiệm vụ like"""
        # Logic xử lý like
        try:
            # Thực hiện like trên Facebook
            return {"success": True, "message": "Like thành công"}
        except Exception as e:
            return {"success": False, "error": f"Lỗi like: {str(e)}"}

    def _process_like_page_job(self, url):
        """Xử lý nhiệm vụ like page"""
        # Logic xử lý like page
        try:
            # Thực hiện like page
            return {"success": True, "message": "Like page thành công"}
        except Exception as e:
            return {"success": False, "error": f"Lỗi like page: {str(e)}"}

    def handle_rate_limit_and_wait(self, driver, check_rate_limit_func):
        """Xử lý rate limit và chờ 6 giây trước khi refresh"""
        if check_rate_limit_func(driver.page_source):
            print("Phát hiện rate limit, đang chờ 6 giây...")
            time.sleep(6)
            # Sau khi chờ xong, refresh lại trang
            driver.refresh()
            print("Đã refresh trang sau khi chờ")
            return True
        return False