"""
Module xử lý rate limiting và delay tự động
"""

import time
import re

class RateLimitHandler:
    """Module xử lý giới hạn tần suất và delay tự động"""

    @staticmethod
    def check_for_rate_limit_error(page_source):
        """Kiểm tra xem có thông báo rate limit không"""
        # Kiểm tra các từ khóa thường thấy trong thông báo rate limit
        rate_limit_indicators = [
            "thao tác quá nhanh",
            "quá nhanh",
            "rate limit",
            "thử lại",
            "chờ",
            "timeout"
        ]

        for indicator in rate_limit_indicators:
            if indicator in page_source.lower():
                return True
        return False

    @staticmethod
    def handle_rate_limit_and_retry(action_callback, delay_seconds=6):
        """Xử lý rate limit và thử lại sau khi delay"""
        print("Đã phát hiện rate limit. Đang chờ 6 giây trước khi tiếp tục...")
        time.sleep(delay_seconds)

        # Gọi lại hàm xử lý
        try:
            result = action_callback()
            return result
        except Exception as e:
            print(f"Lỗi khi thực hiện lại hành động: {e}")
            return None

    @staticmethod
    def auto_delay_on_rate_limit(page_source, base_delay=6):
        """Tự động delay khi phát hiện rate limit"""
        if RateLimitHandler.check_for_rate_limit_error(page_source):
            print("Phát hiện rate limit, đang delay 6 giây...")
            time.sleep(base_delay)
            return True
        return False

# Ví dụ sử dụng:
# if RateLimitHandler.auto_delay_on_rate_limit(driver.page_source):
#     # Đã delay, có thể tiếp tục thực hiện
#     pass