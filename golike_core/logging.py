"""
Logging module for Golike application
"""
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Formatter với màu sắc cho console output"""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


class AppLogger:
    """Logger tùy chỉnh cho ứng dụng"""

    _instance: Optional['AppLogger'] = None
    _logger: Optional[logging.Logger] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._logger is not None:
            return

        self._logger = logging.getLogger("golike")
        self._logger.setLevel(logging.DEBUG)

        # Xóa handlers cũ
        self._logger.handlers.clear()

        # Console handler với màu sắc
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self._logger.addHandler(console_handler)

        # File handler
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"golike_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self._logger.addHandler(file_handler)

    def debug(self, message: str) -> None:
        """Log debug message"""
        self._logger.debug(message)

    def info(self, message: str) -> None:
        """Log info message"""
        self._logger.info(message)

    def warning(self, message: str) -> None:
        """Log warning message"""
        self._logger.warning(message)

    def error(self, message: str, exc_info: bool = False) -> None:
        """Log error message"""
        self._logger.error(message, exc_info=exc_info)

    def critical(self, message: str, exc_info: bool = False) -> None:
        """Log critical message"""
        self._logger.critical(message, exc_info=exc_info)

    def exception(self, message: str) -> None:
        """Log exception với traceback"""
        self._logger.exception(message)

    def set_level(self, level: str) -> None:
        """Set log level"""
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        self._logger.setLevel(level_map.get(level.upper(), logging.INFO))


# Global logger instance
logger = AppLogger()
