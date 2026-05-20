"""
Module xử lý lỗi và log cho hệ thống GoLike
"""

import logging
import traceback
from datetime import datetime

class ErrorHandler:
    """Module xử lý lỗi và ghi log"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_logger()

    def setup_logger(self):
        """Thiết lập logger"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def handle_exception(self, exception, context=""):
        """Xử lý ngoại lệ"""
        self.logger.error(f"Lỗi xảy ra {context}: {str(exception)}")
        self.logger.error(f"Chi tiết: {traceback.format_exc()}")
        return {"status": "error", "message": str(exception)}

    def log_info(self, message):
        """Ghi log thông tin"""
        self.logger.info(message)

    def log_error(self, message):
        """Ghi log lỗi"""
        self.logger.error(message)

    def log_warning(self, message):
        """Ghi log cảnh báo"""
        self.logger.warning(message)