"""
Error handling module for Golike application
"""
import time
import traceback
import json
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime
from .logging import logger


class AppError(Exception):
    """Base exception cho ứng dụng"""
    pass


class ConfigurationError(AppError):
    """Lỗi cấu hình"""
    pass


class CredentialError(AppError):
    """Lỗi credential"""
    pass


class APIError(AppError):
    """Lỗi API"""
    pass


class ADBError(AppError):
    """Lỗi ADB"""
    pass


class NetworkError(AppError):
    """Lỗi mạng"""
    pass


class FacebookError(AppError):
    """Lỗi Facebook API"""
    pass


class RetryPolicy:
    """Chính sách retry"""

    def __init__(self, max_retries: int = 3, backoff_factor: float = 1.0):
        """Khởi tạo RetryPolicy

        Args:
            max_retries: Số lần retry tối đa
            backoff_factor: Hệ số backoff
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def get_delay(self, attempt: int) -> float:
        """Tính toán delay cho lần retry

        Args:
            attempt: Số lần thử hiện tại

        Returns:
            float: Delay tính toán được
        """
        return self.backoff_factor * (2 ** (attempt - 1))


def retry_on_error(
    max_retries: int = 3,
    exceptions: Tuple = (Exception,),
    backoff_factor: float = 1.0,
    logger_instance: Optional[AppLogger] = None
):
    """Decorator để retry function khi có lỗi

    Args:
        max_retries: Số lần retry tối đa
        exceptions: Tuple các exception cần retry
        backoff_factor: Hệ số backoff
        logger_instance: Logger instance

    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            policy = RetryPolicy(max_retries, backoff_factor)
            last_exception = None

            for attempt in range(1, policy.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < policy.max_retries:
                        delay = policy.get_delay(attempt)
                        if logger_instance:
                            logger_instance.warning(
                                f"{func.__name__} thất bại (lần {attempt}/{policy.max_retries}), "
                                f"retry sau {delay}s. Lỗi: {str(e)}"
                            )
                        time.sleep(delay)
                    else:
                        if logger_instance:
                            logger_instance.error(
                                f"{func.__name__} thất bại sau {policy.max_retries} lần retry. "
                                f"Lỗi cuối: {str(e)}"
                            )
            raise last_exception
        return wrapper
    return decorator


class ErrorHandler:
    """Xử lý lỗi tập trung"""

    def __init__(self, logger_instance: Optional[AppLogger] = None):
        """Khởi tạo ErrorHandler

        Args:
            logger_instance: Logger instance
        """
        self.logger = logger_instance or logger
        self.error_log_file = Path("logs") / "errors.log"

    def handle_exception(self, exc: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """Xử lý exception

        Args:
            exc: Exception cần xử lý
            context: Context thông tin
        """
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'type': type(exc).__name__,
            'message': str(exc),
            'traceback': traceback.format_exc(),
            'context': context or {}
        }

        # Log ra console
        self.logger.error(f"Exception: {type(exc).__name__}: {str(exc)}", exc_info=True)

        # Lưu vào file error log
        self._save_error_log(error_info)

    def _save_error_log(self, error_info: Dict[str, Any]) -> None:
        """Lưu error log vào file

        Args:
            error_info: Thông tin lỗi
        """
        try:
            self.error_log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.error_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(error_info, ensure_ascii=False) + '\n')
        except Exception as e:
            self.logger.error(f"Không thể lưu error log: {e}")

    def get_recent_errors(self, count: int = 10) -> List[Dict[str, Any]]:
        """Lấy danh sách lỗi gần đây

        Args:
            count: Số lỗi cần lấy

        Returns:
            List[Dict[str, Any]]: Danh sách lỗi
        """
        errors = []
        try:
            if self.error_log_file.exists():
                with open(self.error_log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                for line in lines[-count:]:
                    try:
                        errors.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            self.logger.error(f"Không thể đọc error log: {e}")
        return errors
