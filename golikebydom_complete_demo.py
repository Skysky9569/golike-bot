"""
GOLIKEBYDOM COMPLETE DEMO - Bản demo hoàn chỉnh kết hợp 4 giai đoạn
File này demo tất cả các cải tiến trước khi apply vào file chính

Giai đoạn 1: Security Fixes
- Secure credential storage (mã hóa)
- Input validation
- Remove hardcoded data
- Environment variables support

Giai đoạn 2: Error Handling & Logging
- Comprehensive logging system
- Proper exception handling
- Error recovery mechanisms
- Debug mode

Giai đoạn 3: Code Organization
- Split thành multiple modules (trong cùng file)
- Separation of concerns
- Type hints và docstrings
- Configuration management system

Giai đoạn 4: Testing Framework
- Unit tests structure
- API mocking support
"""

import os
import sys
import json
import logging
import traceback
import hashlib
import base64
import subprocess
import time
import requests
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from pathlib import Path
from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime
from unittest.mock import Mock, patch

# Import UI automation module
try:
    from tiktok_automation import TikTokUIAutomator
    UI_AUTOMATION_AVAILABLE = True
except ImportError:
    UI_AUTOMATION_AVAILABLE = False
    logger = logging.getLogger("golikebydom")
    logger.warning("tiktok_automation module không khả dụng. UI automation sẽ bị tắt.")

# Thiết lập encoding UTF-8 cho Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, 'strict')

# Thiết lập timezone Việt Nam
import pytz
tz = pytz.timezone("Asia/Ho_Chi_Minh")


# ============================================================================
# GIAI ĐOẠN 1: SECURITY FIXES
# ============================================================================

# ============ Configuration Management ============

@dataclass
class AppConfig:
    """Cấu hình ứng dụng với type hints

    Attributes:
        adb_path: Đường dẫn đến ADB executable
        api_base_url: URL cơ sở cho API
        api_timeout: Timeout cho API requests (giây)
        log_level: Mức độ logging
        max_retry: Số lần retry tối đa
        wifi_port: Port mặc định cho ADB WiFi
    """
    adb_path: str
    api_base_url: str
    api_timeout: int
    log_level: str
    max_retry: int
    wifi_port: int

    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Load cấu hình từ environment variables

        Returns:
            AppConfig: Cấu hình được load từ environment
        """
        return cls(
            adb_path=os.getenv('ADB_PATH', r'D:\pythonadb\ADB\adb.exe'),
            api_base_url=os.getenv('API_BASE_URL', 'https://gateway.golike.net'),
            api_timeout=int(os.getenv('API_TIMEOUT', '10')),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            max_retry=int(os.getenv('MAX_RETRY', '3')),
            wifi_port=int(os.getenv('WIFI_PORT', '5555'))
        )

    @classmethod
    def from_file(cls, filepath: str) -> 'AppConfig':
        """Load cấu hình từ file JSON

        Args:
            filepath: Đường dẫn đến file cấu hình

        Returns:
            AppConfig: Cấu hình được load từ file
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls(**data)
        except FileNotFoundError:
            print(f"[!] File cấu hình {filepath} không tồn tại, dùng mặc định")
            return cls.from_env()
        except json.JSONDecodeError as e:
            print(f"[!] Lỗi JSON trong file cấu hình: {e}")
            return cls.from_env()

    def save(self, filepath: str) -> None:
        """Lưu cấu hình ra file JSON

        Args:
            filepath: Đường dẫn để lưu file cấu hình
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)


# Load cấu hình toàn cục
CONFIG = AppConfig.from_env()
ADB_PATH = CONFIG.adb_path
ADB_CONFIG_FILE = "adb_config.json"
APP_CONFIG_FILE = "app_config.json"


# ============ Secure Credential Storage ============

class CredentialManager:
    """Quản lý credential với mã hóa

    Sử dụng XOR encryption với Base64 encoding để bảo vệ
    authorization token.
    """

    def __init__(self, key: Optional[str] = None):
        """Khởi tạo CredentialManager

        Args:
            key: Khóa mã hóa (nếu None sẽ dùng key mặc định)
        """
        self.key = key or self._generate_key()
        self.credential_file = "secure_credentials.enc"

    @staticmethod
    def _generate_key() -> str:
        """Tạo khóa mã hóa từ machine ID

        Returns:
            str: Khóa mã hóa 32 ký tự
        """
        import platform
        machine_id = platform.node() + platform.machine()
        return hashlib.sha256(machine_id.encode()).hexdigest()[:32]

    def _encrypt(self, data: str) -> str:
        """Mã hóa dữ liệu (XOR + Base64)

        Args:
            data: Dữ liệu cần mã hóa

        Returns:
            str: Dữ liệu đã mã hóa (Base64)
        """
        key_bytes = self.key.encode()
        data_bytes = data.encode()
        encrypted = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data_bytes)])
        return base64.b64encode(encrypted).decode()

    def _decrypt(self, encrypted: str) -> str:
        """Giải mã dữ liệu

        Args:
            encrypted: Dữ liệu đã mã hóa

        Returns:
            str: Dữ liệu gốc hoặc chuỗi rỗng nếu thất bại
        """
        try:
            key_bytes = self.key.encode()
            encrypted_bytes = base64.b64decode(encrypted)
            decrypted = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(encrypted_bytes)])
            return decrypted.decode()
        except Exception:
            return ""

    def save_auth(self, auth_token: str) -> bool:
        """Lưu authorization token đã mã hóa

        Args:
            auth_token: Authorization token cần lưu

        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            encrypted = self._encrypt(auth_token)
            with open(self.credential_file, 'w', encoding='utf-8') as f:
                f.write(encrypted)
            return True
        except Exception as e:
            print(f"[!] Lỗi lưu credential: {e}")
            return False

    def get_auth(self) -> Optional[str]:
        """Lấy authorization token

        Returns:
            Optional[str]: Token hoặc None nếu không tồn tại
        """
        if not os.path.exists(self.credential_file):
            return None
        try:
            with open(self.credential_file, 'r', encoding='utf-8') as f:
                encrypted = f.read().strip()
            decrypted = self._decrypt(encrypted)
            return decrypted if decrypted else None
        except Exception:
            return None

    def clear_auth(self) -> bool:
        """Xóa authorization token

        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            if os.path.exists(self.credential_file):
                os.remove(self.credential_file)
            return True
        except Exception as e:
            print(f"[!] Lỗi xóa credential: {e}")
            return False


# ============ Input Validation ============

class ValidationError(Exception):
    """Exception cho validation error"""
    pass


class InputValidator:
    """Validator cho input người dùng

    Cung cấp các method để validate và sanitize input
    từ người dùng.
    """

    @staticmethod
    def validate_ip(ip: str) -> bool:
        """Validate địa chỉ IP

        Args:
            ip: Địa chỉ IP cần validate

        Returns:
            bool: True nếu hợp lệ, False nếu không
        """
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        parts = ip.split('.')
        return all(0 <= int(part) <= 255 for part in parts)

    @staticmethod
    def validate_port(port: int) -> bool:
        """Validate port number

        Args:
            port: Port number cần validate

        Returns:
            bool: True nếu hợp lệ (1-65535), False nếu không
        """
        return 1 <= port <= 65535

    @staticmethod
    def validate_auth_token(token: str) -> bool:
        """Validate authorization token format

        Args:
            token: Token cần validate

        Returns:
            bool: True nếu hợp lệ, False nếu không
        """
        if not token or not token.strip():
            return False
        if len(token) < 10 or len(token) > 500:
            return False
        return True

    @staticmethod
    def sanitize_string(input_str: str, max_length: int = 100) -> str:
        """Sanitize string input

        Args:
            input_str: Chuỗi cần sanitize
            max_length: Độ dài tối đa

        Returns:
            str: Chuỗi đã được sanitize
        """
        if not input_str:
            return ""
        sanitized = input_str.strip()[:max_length]
        dangerous_chars = ['\0', '\r', '\n']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        return sanitized

    @staticmethod
    def validate_account_id(account_id: str) -> bool:
        """Validate account ID

        Args:
            account_id: Account ID cần validate

        Returns:
            bool: True nếu hợp lệ, False nếu không
        """
        if not account_id or not account_id.strip():
            return False
        return account_id.replace('_', '').replace('-', '').isalnum()


# ============ Secure Headers Builder ============

class SecureHeaderBuilder:
    """Builder cho HTTP headers với security considerations"""

    def __init__(self, auth_token: str):
        """Khởi tạo SecureHeaderBuilder

        Args:
            auth_token: Authorization token
        """
        self.auth_token = auth_token

    def build(self) -> Dict[str, str]:
        """Build headers với security defaults

        Returns:
            Dict[str, str]: Headers dictionary
        """
        headers = {
            'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8',
            'Referer': 'https://app.golike.net/',
            'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': "Windows",
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
            'Authorization': self.auth_token,
            'Content-Type': 'application/json;charset=utf-8'
        }
        # Load T token từ environment thay vì hardcoded
        t_token = os.getenv('API_T_TOKEN')
        if t_token:
            headers['T'] = t_token
        return headers


# ============================================================================
# GIAI ĐOẠN 2: ERROR HANDLING & LOGGING
# ============================================================================

# ============ Logging System ============

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

        self._logger = logging.getLogger("golikebydom")
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
        log_file = log_dir / f"golikebydom_{datetime.now().strftime('%Y%m%d')}.log"
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


# ============ Custom Exceptions ============

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


# ============ Error Recovery ============

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
    exceptions: tuple = (Exception,),
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


# ============ Error Handler ============

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


# ============================================================================
# GIAI ĐOẠN 3: CODE ORGANIZATION
# ============================================================================

# ============ API Client Module ============

class APIClient:
    """Client cho API calls

    Xử lý tất cả các request đến API server với
    proper error handling và retry logic.
    """

    def __init__(self, base_url: str, timeout: int = 10):
        """Khởi tạo APIClient

        Args:
            base_url: URL cơ sở cho API
            timeout: Timeout mặc định cho requests
        """
        self.base_url = base_url
        self.timeout = timeout
        self._auth_token: Optional[str] = None

    def set_auth(self, auth_token: str) -> None:
        """Set authorization token

        Args:
            auth_token: Authorization token
        """
        self._auth_token = auth_token

    def _build_headers(self) -> Dict[str, str]:
        """Build headers cho request

        Returns:
            Dict[str, str]: Headers dictionary
        """
        headers = {
            'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8',
            'Referer': 'https://app.golike.net/',
            'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': "Windows",
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
            'Content-Type': 'application/json;charset=utf-8'
        }
        if self._auth_token:
            headers['Authorization'] = self._auth_token
        t_token = os.getenv('API_T_TOKEN')
        if t_token:
            headers['T'] = t_token
        return headers

    @retry_on_error(max_retries=3, exceptions=(requests.RequestException,), logger_instance=logger)
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET request với retry

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Dict[str, Any]: Response data

        Raises:
            APIError: Nếu request thất bại
        """
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(
                url,
                params=params,
                headers=self._build_headers(),
                timeout=self.timeout
            )
            return response.json()
        except requests.RequestException as e:
            raise APIError(f"GET request failed: {e}")

    @retry_on_error(max_retries=3, exceptions=(requests.RequestException,), logger_instance=logger)
    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """POST request với retry

        Args:
            endpoint: API endpoint
            data: Request body data

        Returns:
            Dict[str, Any]: Response data

        Raises:
            APIError: Nếu request thất bại
        """
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.post(
                url,
                data=json.dumps(data) if data else None,
                headers=self._build_headers(),
                timeout=self.timeout
            )
            return response.json()
        except requests.RequestException as e:
            raise APIError(f"POST request failed: {e}")


# ============ ADB Manager Module ============

class ADBDevice:
    """Represent một thiết bị ADB"""

    def __init__(self, device_id: str, status: str):
        """Khởi tạo ADBDevice

        Args:
            device_id: ID của thiết bị
            status: Trạng thái thiết bị
        """
        self.device_id = device_id
        self.status = status
        self._info: Optional[str] = None

    @property
    def info(self) -> str:
        """Lấy thông tin thiết bị

        Returns:
            str: Thông tin thiết bị
        """
        if self._info is None:
            self._info = self._fetch_device_info()
        return self._info

    def _fetch_device_info(self) -> str:
        """Fetch thông tin thiết bị từ ADB

        Returns:
            str: Thông tin thiết bị
        """
        try:
            cmd = [ADB_PATH, '-s', self.device_id, 'shell', 'getprop', 'ro.product.model']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            model = result.stdout.strip() if result.returncode == 0 else "Unknown"

            cmd = [ADB_PATH, '-s', self.device_id, 'shell', 'getprop', 'ro.build.version.release']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            android_version = result.stdout.strip() if result.returncode == 0 else "Unknown"

            return f"{model} (Android {android_version})"
        except Exception:
            return "Unknown"


class ADBManager:
    """Quản lý các thiết bị ADB

    Cung cấp interface để quản lý kết nối và thao tác
    với các thiết bị ADB.
    """

    def __init__(self, adb_path: str):
        """Khởi tạo ADBManager

        Args:
            adb_path: Đường dẫn đến ADB executable
        """
        self.adb_path = adb_path

    def check_adb(self) -> bool:
        """Kiểm tra ADB có sẵn không

        Returns:
            bool: True nếu ADB available, False nếu không
        """
        try:
            result = subprocess.run([self.adb_path, 'version'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def get_devices(self) -> List[ADBDevice]:
        """Lấy danh sách thiết bị đang kết nối

        Returns:
            List[ADBDevice]: Danh sách thiết bị
        """
        try:
            result = subprocess.run([self.adb_path, 'devices'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                devices = []
                for line in lines[1:]:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        devices.append(ADBDevice(parts[0], parts[1]))
                return devices
        except Exception:
            pass
        return []

    def connect_wifi(self, ip: str, port: int = 5555) -> bool:
        """Kết nối thiết bị qua WiFi

        Args:
            ip: Địa chỉ IP
            port: Port number

        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            result = subprocess.run(
                [self.adb_path, 'connect', f'{ip}:{port}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0 and 'connected' in result.stdout.lower()
        except Exception:
            return False

    def disconnect_wifi(self, ip: str, port: int = 5555) -> bool:
        """Ngắt kết nối WiFi

        Args:
            ip: Địa chỉ IP
            port: Port number

        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            subprocess.run([self.adb_path, 'disconnect', f'{ip}:{port}'], capture_output=True, timeout=5)
            return True
        except Exception:
            return False

    def restart_server(self) -> bool:
        """Restart ADB server

        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            logger.info("Đang tắt ADB server...")
            subprocess.run([self.adb_path, 'kill-server'], capture_output=True, timeout=5)
            time.sleep(1)
            logger.info("Đang khởi động ADB server...")
            subprocess.run([self.adb_path, 'start-server'], capture_output=True, timeout=5)
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Lỗi restart ADB: {e}")
            return False

    def open_link(self, link: str, device_id: Optional[str] = None) -> bool:
        """Mở link trên thiết bị

        Args:
            link: URL cần mở
            device_id: ID thiết bị (nếu None dùng thiết bị mặc định)

        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            cmd = [self.adb_path]
            if device_id:
                cmd.extend(['-s', device_id])
            cmd.extend(['shell', 'am', 'start', '-a', 'android.intent.action.VIEW', '-d', link])
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False

    def get_device_wifi_ip(self, device_id: str) -> Optional[str]:
        """Lấy IP WiFi từ thiết bị ADB

        Args:
            device_id: ID của thiết bị ADB

        Returns:
            Optional[str]: IP address hoặc None nếu không lấy được
        """
        try:
            result = subprocess.run(
                [self.adb_path, '-s', device_id, 'shell', 'ip', 'addr', 'show', 'wlan0'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return self._extract_ip_from_output(result.stdout)
            return None
        except Exception:
            return None

    @staticmethod
    def _extract_ip_from_output(output: str) -> Optional[str]:
        """Extract IP từ output của ip addr show

        Args:
            output: Output từ lệnh ip addr show

        Returns:
            Optional[str]: IP address hoặc None nếu không tìm thấy
        """
        match = re.search(r'inet (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', output)
        if match:
            return match.group(1)
        return None


# ============ Job Processor Module ============

class JobType(Enum):
    """Các loại job"""
    LIKE = "like"
    FOLLOW = "follow"


class Job:
    """Represent một job"""

    def __init__(self, job_id: str, link: str, job_type: str, object_id: str):
        """Khởi tạo Job

        Args:
            job_id: ID của job
            link: Link TikTok
            job_type: Loại job (like/follow)
            object_id: ID object
        """
        self.job_id = job_id
        self.link = link
        self.job_type = job_type
        self.object_id = object_id

    def __repr__(self) -> str:
        return f"Job(id={self.job_id}, type={self.job_type})"


class JobProcessor(ABC):
    """Base class cho job processor"""

    @abstractmethod
    def process(self, job: Job) -> bool:
        """Xử lý job

        Args:
            job: Job cần xử lý

        Returns:
            bool: True nếu thành công, False nếu không
        """
        pass


class ADBJobProcessor(JobProcessor):
    """Job processor sử dụng ADB"""

    def __init__(self, adb_manager: ADBManager, device_id: Optional[str] = None):
        """Khởi tạo ADBJobProcessor

        Args:
            adb_manager: ADBManager instance
            device_id: ID thiết bị (nếu None dùng thiết bị mặc định)
        """
        self.adb_manager = adb_manager
        self.device_id = device_id

    def process(self, job: Job) -> bool:
        """Xử lý job bằng ADB

        Args:
            job: Job cần xử lý

        Returns:
            bool: True nếu thành công, False nếu không
        """
        return self.adb_manager.open_link(job.link, self.device_id)


class TermuxJobProcessor(JobProcessor):
    """Job processor sử dụng Termux"""

    def process(self, job: Job) -> bool:
        """Xử lý job bằng Termux

        Args:
            job: Job cần xử lý

        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            code = os.system(f"termux-open-url {job.link}")
            return code == 0
        except Exception:
            return False


class ManualJobProcessor(JobProcessor):
    """Job processor manual (hiển thị link)"""

    def process(self, job: Job) -> bool:
        """Xử lý job manual

        Args:
            job: Job cần xử lý

        Returns:
            bool: Luôn trả về True (user tự mở)
        """
        print(f"🔗 Link: {job.link}")
        print("   Vui lòng mở thủ công...")
        return True


class JobProcessorFactory:
    """Factory để tạo job processor"""

    @staticmethod
    def create(method: str, adb_manager: Optional[ADBManager] = None, device_id: Optional[str] = None) -> JobProcessor:
        """Tạo job processor

        Args:
            method: Phương thức (adb/termux/manual)
            adb_manager: ADBManager instance (cần cho adb)
            device_id: ID thiết bị (cần cho adb)

        Returns:
            JobProcessor: Job processor instance

        Raises:
            ValueError: Nếu method không hợp lệ
        """
        if method == "adb":
            if not adb_manager:
                raise ValueError("ADBManager required for ADB method")
            return ADBJobProcessor(adb_manager, device_id)
        elif method == "termux":
            return TermuxJobProcessor()
        elif method == "manual":
            return ManualJobProcessor()
        else:
            raise ValueError(f"Unknown method: {method}")


# ============================================================================
# GIAI ĐOẠN 4: TESTING FRAMEWORK
# ============================================================================

class TestSuite:
    """Test suite cho ứng dụng"""

    def __init__(self):
        """Khởi tạo TestSuite"""
        self.validator = InputValidator()
        self.config = AppConfig.from_env()
        self.cred_manager = CredentialManager()
        self.error_handler = ErrorHandler()

    def run_all_tests(self) -> Dict[str, Any]:
        """Chạy tất cả tests

        Returns:
            Dict[str, Any]: Kết quả tests
        """
        results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'tests': []
        }

        # Test IP validation
        results['tests'].append(self._test_ip_validation())

        # Test Port validation
        results['tests'].append(self._test_port_validation())

        # Test Token validation
        results['tests'].append(self._test_token_validation())

        # Test String sanitization
        results['tests'].append(self._test_string_sanitization())

        # Test Account ID validation
        results['tests'].append(self._test_account_id_validation())

        # Test Config
        results['tests'].append(self._test_config())

        # Test Credential encryption
        results['tests'].append(self._test_credential_encryption())

        # Calculate totals
        results['total'] = len(results['tests'])
        results['passed'] = sum(1 for t in results['tests'] if t['passed'])
        results['failed'] = results['total'] - results['passed']

        return results

    def _test_ip_validation(self) -> Dict[str, Any]:
        """Test IP validation"""
        test_cases = [
            ("192.168.1.1", True),
            ("256.1.1.1", False),
            ("192.168.1", False),
            ("invalid", False),
        ]

        passed = 0
        for ip, expected in test_cases:
            result = self.validator.validate_ip(ip)
            if result == expected:
                passed += 1

        return {
            'name': 'IP Validation',
            'total': len(test_cases),
            'passed': passed,
            'passed': passed == len(test_cases)
        }

    def _test_port_validation(self) -> Dict[str, Any]:
        """Test Port validation"""
        test_cases = [
            (5555, True),
            (80, True),
            (0, False),
            (70000, False),
            (-1, False),
        ]

        passed = 0
        for port, expected in test_cases:
            result = self.validator.validate_port(port)
            if result == expected:
                passed += 1

        return {
            'name': 'Port Validation',
            'total': len(test_cases),
            'passed': passed,
            'passed': passed == len(test_cases)
        }

    def _test_token_validation(self) -> Dict[str, Any]:
        """Test Token validation"""
        test_cases = [
            ("a" * 10, True),
            ("a" * 100, True),
            ("", False),
            ("a" * 9, False),
            ("a" * 501, False),
        ]

        passed = 0
        for token, expected in test_cases:
            result = self.validator.validate_auth_token(token)
            if result == expected:
                passed += 1

        return {
            'name': 'Token Validation',
            'total': len(test_cases),
            'passed': passed,
            'passed': passed == len(test_cases)
        }

    def _test_string_sanitization(self) -> Dict[str, Any]:
        """Test String sanitization"""
        test_cases = [
            ("normal text", 100, "normal text"),
            ("  spaces  ", 100, "spaces"),
            ("text\r\nwith\nnewlines", 100, "textwithnewlines"),
            ("a" * 200, 50, "a" * 50),
        ]

        passed = 0
        for input_str, max_length, expected in test_cases:
            result = self.validator.sanitize_string(input_str, max_length)
            if result == expected:
                passed += 1

        return {
            'name': 'String Sanitization',
            'total': len(test_cases),
            'passed': passed,
            'passed': passed == len(test_cases)
        }

    def _test_account_id_validation(self) -> Dict[str, Any]:
        """Test Account ID validation"""
        test_cases = [
            ("user123", True),
            ("user_123", True),
            ("user-456", True),
            ("user@123", False),
            ("", False),
        ]

        passed = 0
        for account_id, expected in test_cases:
            result = self.validator.validate_account_id(account_id)
            if result == expected:
                passed += 1

        return {
            'name': 'Account ID Validation',
            'total': len(test_cases),
            'passed': passed,
            'passed': passed == len(test_cases)
        }

    def _test_config(self) -> Dict[str, Any]:
        """Test Config"""
        try:
            config = AppConfig.from_env()
            passed = (
                config.api_base_url == "https://gateway.golike.net" and
                config.api_timeout == 10 and
                config.log_level == "INFO" and
                config.max_retry == 3 and
                config.wifi_port == 5555
            )
        except Exception:
            passed = False

        return {
            'name': 'Config Loading',
            'total': 1,
            'passed': 1 if passed else 0,
            'passed': passed
        }

    def _test_credential_encryption(self) -> Dict[str, Any]:
        """Test Credential encryption"""
        try:
            test_token = "test_token_12345"
            self.cred_manager.save_auth(test_token)
            retrieved = self.cred_manager.get_auth()
            passed = retrieved == test_token
            self.cred_manager.clear_auth()
        except Exception:
            passed = False

        return {
            'name': 'Credential Encryption',
            'total': 1,
            'passed': 1 if passed else 0,
            'passed': passed
        }


# ============================================================================
# UI FUNCTIONS
# ============================================================================

def colored(text: str, color: str, bold: bool = False) -> str:
    """Helper cho colored output

    Args:
        text: Text cần màu
        color: Màu (yellow, pink, cyan, white, green, red)
        bold: Có tô đậm không

    Returns:
        str: Text đã được thêm màu
    """
    colors = {
        "yellow": "\033[33m",
        "pink": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[97m",
        "green": "\033[32m",
        "red": "\033[31m",
        "reset": "\033[0m"
    }
    bold_code = "\033[1m" if bold else ""
    return bold_code + colors.get(color, "") + text + colors["reset"]


def banner():
    """Hiển thị banner"""
    os.system("clear" if os.name == "posix" else "cls")
    banner_text = f"""
{colored(':))', 'yellow')}
{colored('════════════════════════════════════════════════', 'white')}
{colored('👑 Tool  Đóm Remake: ', 'white')}
{colored('🆔 Tên   : 👑 Đóm Remake 👑', 'white')}
{colored('📱 Tik Tok : :D', 'white')}
{colored('🌅 Zalo     : 🧠Đóm Remake🧠', 'white')}
{colored('❤️‍🔥 Telegram : :D', 'white')}
{colored('════════════════════════════════════════════════', 'white')}
{colored('⚠️ Lưu ý    : 🌟Tool Sử Dụng Cho Android/Pc🌟', 'white')}
{colored('🔐 Bảo mật  : Credential đã mã hóa, Input validated', 'green')}
{colored('📝 Logging   : Comprehensive logging system', 'green')}
{colored('🏗️  Code Org  : Modular architecture with type hints', 'green')}
{colored('🧪 Testing   : Built-in test suite', 'green')}
{colored('════════════════════════════════════════════════', 'white')}
"""
    print(banner_text)


def menu() -> None:
    """Menu chính"""
    banner()
    print(colored("🆔 Địa chỉ Ip  : 🚨DDOM DOMDMD M🚨", "white"))
    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("🥇 Nhập 1 để vào Tool Tiktok", "white"))
    print(colored("📱 Nhập 2 để Quản lý thiết bị ADB", "cyan"))
    print(colored("🥈 Nhập 3 Để Xóa Authorization Hiện Tại", "red"))
    print(colored("⚙️  Nhập 4 để xem cấu hình bảo mật", "green"))
    print(colored("📊 Nhập 5 để xem Logs", "yellow"))
    print(colored("🧪 Nhập 6 để chạy Tests", "magenta"))
    print(colored("🔧 Nhập 7 để Debug Mode", "blue"))
    print(colored("🤖 Nhập 8 để xem hướng dẫn cài UI Automation", "purple"))


def show_security_config() -> None:
    """Hiển thị cấu hình bảo mật"""
    print(colored("\n════════════════════════════════════════════════", "cyan"))
    print(colored("🔐 CẤU HÌNH BẢO MẬT", "yellow"))
    print(colored("════════════════════════════════════════════════", "cyan"))

    print(colored("\n📁 Credential Storage:", "white"))
    cred_manager = CredentialManager()
    if os.path.exists(cred_manager.credential_file):
        print(colored("   ✅ Credential file tồn tại (đã mã hóa)", "green"))
        print(colored(f"   📄 File: {cred_manager.credential_file}", "white"))
    else:
        print(colored("   ❌ Chưa có credential", "yellow"))

    print(colored("\n⚙️  Application Config:", "white"))
    print(colored(f"   📂 ADB Path: {CONFIG.adb_path}", "white"))
    print(colored(f"   🌐 API Base URL: {CONFIG.api_base_url}", "white"))
    print(colored(f"   ⏱️  API Timeout: {CONFIG.api_timeout}s", "white"))
    print(colored(f"   📊 Log Level: {CONFIG.log_level}", "white"))
    print(colored(f"   🔄 Max Retry: {CONFIG.max_retry}", "white"))
    print(colored(f"   📶 WiFi Port: {CONFIG.wifi_port}", "white"))

    print(colored("\n🔒 Security Features:", "white"))
    print(colored("   ✅ Credential encryption (XOR + Base64)", "green"))
    print(colored("   ✅ Input validation (IP, Port, Account ID)", "green"))
    print(colored("   ✅ String sanitization", "green"))
    print(colored("   ✅ Environment variables support", "green"))
    print(colored("   ✅ No hardcoded sensitive data", "green"))

    print(colored("\n📝 Environment Variables:", "white"))
    env_vars = ['ADB_PATH', 'API_BASE_URL', 'API_TIMEOUT', 'LOG_LEVEL', 'MAX_RETRY', 'WIFI_PORT', 'API_T_TOKEN']
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if var == 'API_T_TOKEN':
                print(colored(f"   ✅ {var}: {value[:10]}... (ẩn)", "green"))
            else:
                print(colored(f"   ✅ {var}: {value}", "green"))
        else:
            print(colored(f"   ⚪ {var}: (dùng giá trị mặc định)", "yellow"))

    print(colored("\n════════════════════════════════════════════════", "cyan"))
    input(colored("Nhấn Enter để quay lại...", "white"))


def show_logs() -> None:
    """Hiển thị logs gần đây"""
    print(colored("\n════════════════════════════════════════════════", "cyan"))
    print(colored("📊 LOGS", "yellow"))
    print(colored("════════════════════════════════════════════════", "cyan"))

    log_dir = Path("logs")
    if not log_dir.exists():
        print(colored("   ❌ Chưa có logs", "yellow"))
        input(colored("Nhấn Enter để quay lại...", "white"))
        return

    # Hiển thị log files
    log_files = sorted(log_dir.glob("*.log"))
    if not log_files:
        print(colored("   ❌ Không có file log", "yellow"))
        input(colored("Nhấn Enter để quay lại...", "white"))
        return

    print(colored(f"\n📁 Có {len(log_files)} file log:", "white"))
    for log_file in log_files[-5:]:  # Hiển thị 5 file gần nhất
        print(colored(f"   - {log_file.name}", "white"))

    # Hiển thị error logs
    error_log = log_dir / "errors.log"
    if error_log.exists():
        print(colored(f"\n❌ Error logs ({error_log.name}):", "red"))
        try:
            with open(error_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            print(colored(f"   Tổng số lỗi: {len(lines)}", "white"))
            if lines:
                print(colored("\n   5 lỗi gần đây:", "yellow"))
                for line in lines[-5:]:
                    try:
                        error = json.loads(line.strip())
                        print(colored(f"   - {error['type']}: {error['message'][:50]}...", "white"))
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(colored(f"   Lỗi đọc error log: {e}", "red"))

    print(colored("\n════════════════════════════════════════════════", "cyan"))
    input(colored("Nhấn Enter để quay lại...", "white"))


def run_tests() -> None:
    """Chạy test suite"""
    print(colored("\n════════════════════════════════════════════════", "cyan"))
    print(colored("🧪 TEST SUITE", "yellow"))
    print(colored("════════════════════════════════════════════════", "cyan"))

    test_suite = TestSuite()
    results = test_suite.run_all_tests()

    print(colored(f"\n📊 Test Results:", "white"))
    print(colored(f"   Total: {results['total']}", "white"))
    print(colored(f"   Passed: {results['passed']}", "green"))
    print(colored(f"   Failed: {results['failed']}", "red"))

    print(colored(f"\n📋 Test Details:", "white"))
    for test in results['tests']:
        status = colored("✅", "green") if test['passed'] else colored("❌", "red")
        print(colored(f"   {status} {test['name']}: {test['passed']}/{test['total']}", "white"))

    print(colored("\n════════════════════════════════════════════════", "cyan"))
    input(colored("Nhấn Enter để quay lại...", "white"))


def toggle_debug_mode() -> None:
    """Toggle debug mode"""
    print(colored("\n════════════════════════════════════════════════", "cyan"))
    print(colored("🔧 DEBUG MODE", "yellow"))
    print(colored("════════════════════════════════════════════════", "cyan"))

    current_level = logger._logger.level
    if current_level == logging.DEBUG:
        logger.set_level('INFO')
        print(colored("   ✅ Đã tắt debug mode (INFO)", "green"))
    else:
        logger.set_level('DEBUG')
        print(colored("   ✅ Đã bật debug mode (DEBUG)", "green"))

    print(colored("\n💡 Debug mode hiển thị:", "white"))
    print(colored("   - Tất cả debug messages", "white"))
    print(colored("   - Chi tiết về API calls", "white"))
    print(colored("   - Chi tiết về ADB operations", "white"))

    print(colored("\n════════════════════════════════════════════════", "cyan"))
    input(colored("Nhấn Enter để quay lại...", "white"))


def show_uiautomator2_setup_guide() -> None:
    """Hiển thị hướng dẫn cài đặt uiautomator2"""
    print(colored("\n════════════════════════════════════════════════", "cyan"))
    print(colored("🤖 HƯỚNG DẪN CÀI ĐẶT UI AUTOMATION", "yellow"))
    print(colored("════════════════════════════════════════════════", "cyan"))

    print(colored("\n📦 Bước 1: Cài đặt uiautomator2 trên máy tính", "white"))
    print(colored("   Chạy lệnh sau trong terminal:", "yellow"))
    print(colored("   pip install uiautomator2", "green"))

    print(colored("\n📱 Bước 2: Cài đặt trên thiết bị Android", "white"))
    print(colored("   1. Đảm bảo thiết bị đã kết nối qua ADB", "yellow"))
    print(colored("   2. Chạy lệnh sau để cài APK:", "yellow"))
    print(colored("   python -m uiautomator2 init", "green"))
    print(colored("   3. Hoặc chạy lệnh:", "yellow"))
    print(colored("   u2 init", "green"))

    print(colored("\n⚠️  Lưu ý quan trọng:", "red"))
    print(colored("   - Thiết bị phải đã bật USB Debugging", "white"))
    print(colored("   - Thiết bị phải đã authorize máy tính", "white"))
    print(colored("   - APK sẽ được tự động cài vào thiết bị", "white"))
    print(colored("   - Chỉ cần cài 1 lần, sau đó tool sẽ tự động kết nối", "white"))

    print(colored("\n🔍 Kiểm tra cài đặt:", "white"))
    print(colored("   Chạy lệnh sau để kiểm tra:", "yellow"))
    print(colored("   python -c \"import uiautomator2 as u2; d = u2.connect(); print(d.info)\"", "green"))

    print(colored("\n✅ Tính năng sau khi cài:", "green"))
    print(colored("   - Tự động tìm và click nút Follow", "white"))
    print(colored("   - Tự động tìm và click nút Like", "white"))
    print(colored("   - Verify trạng thái sau khi click", "white"))
    print(colored("   - Retry khi không tìm thấy element", "white"))

    print(colored("\n❌ Nếu gặp lỗi:", "red"))
    print(colored("   - 'uiautomator2 not found': Chạy pip install uiautomator2", "white"))
    print(colored("   - 'Device not found': Kiểm tra kết nối ADB", "white"))
    print(colored("   - 'Permission denied': Kiểm tra USB Debugging", "white"))

    print(colored("\n════════════════════════════════════════════════", "cyan"))
    input(colored("Nhấn Enter để quay lại...", "white"))


# ============================================================================
# ADB MENU
# ============================================================================

def adb_menu() -> None:
    """Menu quản lý ADB"""
    validator = InputValidator()
    cred_manager = CredentialManager()
    adb_manager = ADBManager(ADB_PATH)
    error_handler = ErrorHandler()

    while True:
        os.system("clear" if os.name == "posix" else "cls")
        print(colored("════════════════════════════════════════════════", "white"))
        print(colored("📱 QUẢN LÝ THIẾT BỊ ADB", "yellow"))
        print(colored("════════════════════════════════════════════════", "white"))

        if not adb_manager.check_adb():
            print(colored("❌ ADB không được cài đặt hoặc không có trong PATH!", "red"))
            print(colored("   Hãy cài đặt Android SDK Platform Tools", "yellow"))
            input(colored("Nhấn Enter để quay lại...", "white"))
            return

        devices = adb_manager.get_devices()
        config = load_adb_config()

        print(colored(f"📊 Thiết bị đang kết nối: {len(devices)}", "cyan"))
        if devices:
            for idx, dev in enumerate(devices, 1):
                device_id = dev.device_id
                status = dev.status
                if status == 'device':
                    info = dev.info
                    status_icon = "✅"
                elif status == 'unauthorized':
                    info = "N/A (chưa authorize)"
                    status_icon = "⚠️"
                else:
                    info = "N/A (offline)"
                    status_icon = "❌"
                marker = "👉 " if config.get("current_device") == device_id else "   "
                print(colored(f"{marker}[{idx}] {device_id} [{status_icon} {status}] - {info}", "white"))
        else:
            print(colored("   Không có thiết bị nào đang kết nối", "yellow"))

        print(colored("════════════════════════════════════════════════", "white"))
        print(colored("🔌 Nhập 1 : Kết nối thiết bị qua USB", "yellow"))
        print(colored("📶 Nhập 2 : Kết nối thiết bị qua WiFi", "yellow"))
        print(colored("📱 Nhập 3 : Chọn thiết bị để sử dụng", "yellow"))
        print(colored("🔓 Nhập 4 : Ngắt kết nối thiết bị WiFi", "yellow"))
        print(colored("📋 Nhập 5 : Xem danh sách thiết bị đã lưu", "yellow"))
        print(colored("🗑️  Nhập 6 : Xóa thiết bị đã lưu", "yellow"))
        print(colored("⚙️  Nhập 7 : Chọn cách mở link (ADB/Termux)", "yellow"))
        print(colored("🔙 Nhập 0 : Quay lại menu chính", "yellow"))
        print(colored("════════════════════════════════════════════════", "white"))

        choice = input(colored("✅ Chọn: ", "cyan")).strip()

        if choice == "0":
            return
        elif choice == "1":
            print(colored("════════════════════════════════════════════════", "white"))
            print(colored("🔄 Đang restart ADB server để kết nối qua USB...", "cyan"))
            if adb_manager.restart_server():
                print(colored("✅ Đã restart ADB server!", "green"))
                print(colored("   Hãy đảm bảo:", "yellow"))
                print(colored("   1. Điện thoại đã kết nối qua USB", "yellow"))
                print(colored("   2. Đã bật USB Debugging trên điện thoại", "yellow"))
                print(colored("   3. Đã authorize máy tính trên điện thoại", "yellow"))
                print(colored("   4. Nhấn 'Allow' khi popup hiện lên", "yellow"))
                input(colored("Nhấn Enter để quét thiết bị...", "white"))
                devices = adb_manager.get_devices()
                if devices:
                    print(colored(f"✅ Tìm thấy {len(devices)} thiết bị!", "green"))
                    for dev in devices:
                        device_id = dev.device_id
                        status = dev.status
                        if status == 'device':
                            info = dev.info
                            status_icon = "✅"
                        elif status == 'unauthorized':
                            info = "N/A (chưa authorize)"
                            status_icon = "⚠️"
                        else:
                            info = "N/A (offline)"
                            status_icon = "❌"
                        print(colored(f"   - {device_id} [{status_icon} {status}] - {info}", "white"))
                else:
                    print(colored("❌ Không tìm thấy thiết bị nào!", "red"))
                input(colored("Nhấn Enter để tiếp tục...", "white"))
            else:
                print(colored("❌ Restart ADB thất bại!", "red"))
                input(colored("Nhấn Enter để tiếp tục...", "white"))

        elif choice == "2":
            print(colored("════════════════════════════════════════════════", "white"))
            ip = input(colored("📡 Nhập IP thiết bị (ví dụ: 192.168.1.100): ", "green")).strip()
            ip = validator.sanitize_string(ip, 15)

            if not validator.validate_ip(ip):
                print(colored("❌ IP không hợp lệ!", "red"))
                input(colored("Nhấn Enter để tiếp tục...", "white"))
                continue

            port_input = input(colored("🔌 Nhập port (mặc định 5555): ", "green")).strip()
            if port_input and port_input.isdigit():
                port = int(port_input)
                if not validator.validate_port(port):
                    print(colored("❌ Port không hợp lệ! Phải từ 1-65535", "red"))
                    input(colored("Nhấn Enter để tiếp tục...", "white"))
                    continue
            else:
                port = CONFIG.wifi_port

            print(colored(f"🔄 Đang kết nối đến {ip}:{port}...", "cyan"))
            if adb_manager.connect_wifi(ip, port):
                print(colored(f"✅ Kết nối thành công!", "green"))
                if ip not in config.get("devices", []):
                    config.setdefault("devices", []).append(ip)
                    save_adb_config(config)
                time.sleep(2)
            else:
                print(colored(f"❌ Kết nối thất bại!", "red"))
                print(colored("   Hãy đảm bảo:", "yellow"))
                print(colored("   1. Thiết bị đã bật USB Debugging", "yellow"))
                print(colored("   2. Thiết bị đã bật ADB over WiFi", "yellow"))
                print(colored("   3. Điện thoại và máy tính cùng mạng WiFi", "yellow"))
                input(colored("Nhấn Enter để tiếp tục...", "white"))

        elif choice == "3":
            if not devices:
                print(colored("❌ Không có thiết bị nào đang kết nối!", "red"))
                input(colored("Nhấn Enter để tiếp tục...", "white"))
                continue

            print(colored("════════════════════════════════════════════════", "white"))
            dev_choice = input(colored("📱 Nhập số thứ tự thiết bị: ", "green")).strip()
            if dev_choice.isdigit() and 1 <= int(dev_choice) <= len(devices):
                selected = devices[int(dev_choice) - 1]
                device_id = selected.device_id
                config["current_device"] = device_id
                save_adb_config(config)
                print(colored(f"✅ Đã chọn thiết bị: {device_id}", "green"))

                # Tự động phát hiện IP WiFi
                wifi_ip = adb_manager.get_device_wifi_ip(device_id)
                if wifi_ip:
                    print(colored(f"📶 IP WiFi của thiết bị: {wifi_ip}", "cyan"))
                    print(colored(f"💡 Dùng IP này để kết nối WiFi: {wifi_ip}:5555", "yellow"))
                else:
                    print(colored("⚠️ Không thể phát hiện IP WiFi", "yellow"))

                time.sleep(3)
            else:
                print(colored("❌ Lựa chọn không hợp lệ!", "red"))
                time.sleep(1)

        elif choice == "4":
            print(colored("════════════════════════════════════════════════", "white"))
            saved_devices = config.get("devices", [])
            if not saved_devices:
                print(colored("❌ Không có thiết bị WiFi nào đã lưu!", "yellow"))
                input(colored("Nhấn Enter để tiếp tục...", "white"))
                continue

            print(colored("📋 Danh sách thiết bị WiFi:", "cyan"))
            for idx, ip in enumerate(saved_devices, 1):
                print(colored(f"   [{idx}] {ip}", "white"))

            dev_choice = input(colored("🔓 Nhập số để ngắt kết nối (0 để hủy): ", "green")).strip()
            if dev_choice == "0":
                continue
            if dev_choice.isdigit() and 1 <= int(dev_choice) <= len(saved_devices):
                ip = saved_devices[int(dev_choice) - 1]
                if adb_manager.disconnect_wifi(ip):
                    print(colored(f"✅ Đã ngắt kết nối {ip}", "green"))
                    saved_devices.remove(ip)
                    save_adb_config(config)
                else:
                    print(colored(f"❌ Không thể ngắt kết nối {ip}", "red"))
                time.sleep(2)

        elif choice == "5":
            print(colored("══════════════════════════════════════════════", "white"))
            saved_devices = config.get("devices", [])
            if saved_devices:
                print(colored("📋 Thiết bị đã lưu:", "cyan"))
                for ip in saved_devices:
                    print(colored(f"   - {ip}", "white"))
            else:
                print(colored("❌ Chưa có thiết bị nào được lưu", "yellow"))
            input(colored("Nhấn Enter để tiếp tục...", "white"))

        elif choice == "6":
            print(colored("════════════════════════════════════════════════", "white"))
            saved_devices = config.get("devices", [])
            if not saved_devices:
                print(colored("❌ Không có thiết bị nào để xóa!", "yellow"))
                input(colored("Nhấn Enter để tiếp tục...", "white"))
                continue

            print(colored("📋 Danh sách thiết bị:", "cyan"))
            for idx, ip in enumerate(saved_devices, 1):
                print(colored(f"   [{idx}] {ip}", "white"))

            dev_choice = input(colored("🗑️  Nhập số để xóa (0 để hủy): ", "green")).strip()
            if dev_choice == "0":
                continue
            if dev_choice.isdigit() and 1 <= int(dev_choice) <= len(saved_devices):
                ip = saved_devices[int(dev_choice) - 1]
                saved_devices.remove(ip)
                save_adb_config(config)
                print(colored(f"✅ Đã xóa {ip}", "green"))
                time.sleep(2)

        elif choice == "7":
            print(colored("════════════════════════════════════════════════", "white"))
            print(colored("⚙️  Chọn cách mở link:", "cyan"))
            print(colored("   1. Mở bằng ADB (tự động trên thiết bị)", "white"))
            print(colored("   2. Mở bằng Termux (chỉ trên Android)", "white"))
            print(colored("   3. Mở thủ công (hiển thị link)", "white"))

            method_choice = input(colored("✅ Chọn: ", "green")).strip()
            if method_choice == "1":
                config["open_method"] = "adb"
                save_adb_config(config)
                print(colored("✅ Đã chọn: Mở bằng ADB", "green"))
            elif method_choice == "2":
                config["open_method"] = "termux"
                save_adb_config(config)
                print(colored("✅ Đã chọn: Mở bằng Termux", "green"))
            elif method_choice == "3":
                config["open_method"] = "manual"
                save_adb_config(config)
                print(colored("✅ Đã chọn: Mở thủ công", "green"))
            else:
                print(colored("❌ Lựa chọn không hợp lệ!", "red"))
            time.sleep(2)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_adb_config() -> Dict[str, Any]:
    """Đọc cấu hình ADB

    Returns:
        Dict[str, Any]: Cấu hình ADB
    """
    if os.path.exists(ADB_CONFIG_FILE):
        try:
            with open(ADB_CONFIG_FILE, "r", encoding="utf8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"devices": [], "current_device": None, "open_method": "termux"}


def save_adb_config(config: Dict[str, Any]) -> None:
    """Lưu cấu hình ADB

    Args:
        config: Cấu hình ADB
    """
    with open(ADB_CONFIG_FILE, "w", encoding="utf8") as f:
        json.dump(config, f, indent=2)


def input_int(prompt: str, color: str = "green", minval: int = 1) -> int:
    """Input số nguyên với validation

    Args:
        prompt: Prompt hiển thị
        color: Màu của prompt
        minval: Giá trị tối thiểu

    Returns:
        int: Số nguyên đã nhập
    """
    validator = InputValidator()
    while True:
        value = input(colored(prompt, color)).strip()
        if value.isdigit() and int(value) >= minval:
            return int(value)
        print(colored(f"Vui lòng nhập số nguyên >= {minval}!", "red"))


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main() -> None:
    """Main function"""
    validator = InputValidator()
    cred_manager = CredentialManager()
    error_handler = ErrorHandler()

    # Lưu cấu hình app
    CONFIG.save(APP_CONFIG_FILE)

    logger.info("Khởi động ứng dụng...")

    while True:
        menu()
        choose = input(colored("🥇 Nhập Lựa Chọn (1-8): ", "white")).strip()
        if choose == "3":
            if cred_manager.clear_auth():
                print(colored(f"[✔] Đã xóa credential!", "green"))
            else:
                print(colored(f"[!] Không thể xóa credential!", "red"))
            continue
        elif choose == "2":
            adb_menu()
            continue
        elif choose == "4":
            show_security_config()
            continue
        elif choose == "5":
            show_logs()
            continue
        elif choose == "6":
            run_tests()
            continue
        elif choose == "7":
            toggle_debug_mode()
            continue
        elif choose == "8":
            show_uiautomator2_setup_guide()
            continue
        elif choose == "1":
            break

    # Nhập authorization với validation
    auth = cred_manager.get_auth()
    while not auth:
        auth = input(colored("📢 Nhập Authorization: ", "green")).strip()
        auth = validator.sanitize_string(auth, 500)
        if not validator.validate_auth_token(auth):
            print(colored("❌ Token không hợp lệ! Phải từ 10-500 ký tự", "red"))
            auth = ""
            continue
        if auth:
            if cred_manager.save_auth(auth):
                logger.info("Đã lưu authorization token")
                print(colored("✅ Đã lưu token an toàn!", "green"))
            else:
                print(colored("❌ Lỗi lưu token!", "red"))
                auth = ""

    # Build headers với security
    header_builder = SecureHeaderBuilder(auth)
    headers = header_builder.build()

    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("🚀 Đăng nhập thành công! Đang vào Tool Tiktok...", "green"))
    logger.info("Đăng nhập thành công")
    time.sleep(1)

    # Load ADB config
    adb_config = load_adb_config()
    open_method = adb_config.get("open_method", "termux")
    current_device = adb_config.get("current_device")

    # Hiển thị cấu hình ADB
    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("📱 Cấu hình ADB:", "cyan"))
    print(colored(f"   Cách mở link: {open_method}", "white"))
    if current_device:
        print(colored(f"   Thiết bị: {current_device}", "white"))
    else:
        print(colored(f"   Thiết bị: Chưa chọn (sử dụng thiết bị mặc định)", "yellow"))
    print(colored("════════════════════════════════════════════════", "white"))

    # Lấy danh sách acc
    api_client = APIClient(base_url=CONFIG.api_base_url, timeout=CONFIG.api_timeout)
    api_client.set_auth(auth)

    try:
        accounts = api_client.get('/api/tiktok-account')
    except APIError as e:
        logger.error(f"Lỗi lấy danh sách tài khoản: {e}")
        error_handler.handle_exception(e, {'action': 'get_accounts'})
        print(colored("🚨 Lỗi kết nối API! Hãy kiểm tra lại.", "red"))
        sys.exit()

    if not accounts or accounts.get("status") != 200 or not accounts.get("data"):
        print(colored("🚨 Authorization hoặc T sai hoặc không có tài khoản. Hãy nhập lại!", "red"))
        logger.error("Authorization không hợp lệ hoặc không có tài khoản")
        sys.exit()

    # Hiển thị danh sách acc
    print(colored("🚨 Địa chỉ Ip  : 👀192.168.1.1👀", "white"))
    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("🆔 Danh sách acc Tik Tok :", "yellow"))
    print(colored("════════════════════════════════════════════════", "white"))
    data = accounts.get("data", [])
    if not isinstance(data, list) or not data:
        print(colored("Không có tài khoản TikTok nào!", "red"))
        sys.exit()
    for idx, acc in enumerate(data, 1):
        print(colored(f"[{idx}] 🆔 : {acc.get('unique_username', 'N/A')} ♦️ : ✅", "cyan"))
    print(colored("════════════════════════════════════════════════", "white"))

    # Chọn acc với validation
    while True:
        idacc = input(colored("☀️ Nhập ID Acc Tiktok Vào: ", "green")).strip()
        idacc = validator.sanitize_string(idacc, 50)
        acc_obj = next((a for a in accounts.get("data", []) if a.get("unique_username") == idacc), None)
        if acc_obj:
            account_id = acc_obj.get("id")
            break
        print(colored("💀 Acc này chưa được thêm vào golike or id sai", "red"))

    # Nhập thông số job
    delay = input_int("👀 Nhập thời gian làm job : ")
    while True:
        lannhan = input(colored("🛑 Nhận tiền lần 2 nếu lần 1 fail? (y/n): ", "green")).strip().lower()
        if lannhan in {"y", "n"}:
            break
        print(colored("📢 Nhập sai hãy nhập lại!!!", "red"))
    doiacc = input_int("📆 Số job fail để đổi acc TikTok (nhập 1 nếu k muốn dừng) : ")
    while True:
        print(colored("════════════════════════════════════════════════", "white"))
        print(colored("♦️ ✈ Nhập 1 : Chỉ nhận nhiệm vụ Follow", "yellow"))
        print(colored("🔥 ✈ Nhập 2 : Chỉ nhận nhiệm vụ like", "yellow"))
        print(colored("💥 Nhập 12 : Kết hợp cả Like và Follow", "yellow"))
        print(colored("════════════════════════════════════════════════", "white"))
        chedo = input(colored("✅ Chọn lựa chọn: ", "cyan")).strip()
        if chedo in {"1", "2", "12"}:
            break
    lam = ["follow"] if chedo == "1" else ["like"] if chedo == "2" else ["follow", "like"]

    # Bắt đầu vòng lặp làm job
    dem = tong = checkdoiacc = 0
    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("|🆔| ⏱️ ┊ Status | Số Jos | ID Acc | Xu | Tổng", "cyan"))
    print(colored("════════════════════════════════════════════════", "white"))
    prev_job = None

    # Tạo job processor
    adb_manager = ADBManager(ADB_PATH)
    try:
        job_processor = JobProcessorFactory.create(
            open_method,
            adb_manager=adb_manager,
            device_id=current_device
        )
    except ValueError as e:
        logger.error(f"Lỗi tạo job processor: {e}")
        print(colored(f"❌ Lỗi tạo job processor: {e}", "red"))
        sys.exit()

    # Tạo UI automator nếu có sẵn
    ui_automator = None
    if UI_AUTOMATION_AVAILABLE:
        try:
            ui_automator = TikTokUIAutomator(device_id=current_device)
            logger.info("UI Automation đã sẵn sàng")
        except Exception as e:
            logger.warning(f"Không thể tạo UI automator: {e}")
            ui_automator = None

    while True:
        if checkdoiacc >= doiacc:
            print(colored("🚨 Địa chỉ Ip  : 👀192.168.1.1👀", "white"))
            print(colored("════════════════════════════════════════════════", "white"))
            print(colored("🆔 Danh sách acc Tik Tok :", "yellow"))
            print(colored("══════════════════════════════════════════════", "white"))
            for idx, acc in enumerate(data, 1):
                print(colored(f"[{idx}] 🆔 : {acc.get('unique_username', 'N/A')} ♦️ : ✅", "cyan"))
            print(colored("════════════════════════════════════════════════", "white"))

            idacc = input(colored("⚡ Job fail đạt giới hạn, nhập acc mới: ", "red")).strip()
            idacc = validator.sanitize_string(idacc, 50)
            acc_obj = next((a for a in accounts.get("data", []) if a.get("unique_username") == idacc), None)
            if acc_obj:
                account_id = acc_obj.get("id")
                checkdoiacc = 0
            else:
                print(colored("⚠️ Acc này chưa được thêm vào golike or id sai", "red"))
                continue

        # Nhận job
        print(colored("🔎 Đang Tìm Nhiệm vụ:>        ", "pink"), end="\r")
        try:
            nhanjob = api_client.get(f'/api/advertising/publishers/tiktok/jobs?account_id={account_id}&data=null')
        except APIError as e:
            logger.error(f"Lỗi lấy job: {e}")
            time.sleep(10)
            continue

        if not nhanjob or not nhanjob.get("data"):
            time.sleep(10)
            continue

        # Check job trùng
        if prev_job and prev_job.get("data", {}).get("link") == nhanjob.get("data", {}).get("link") and prev_job.get("data", {}).get("type") == nhanjob.get("data", {}).get("type"):
            print(colored("🏚️ Job trùng với job trước đó - Bỏ qua!", "red"), end="\r")
            logger.warning("Job trùng lặp, bỏ qua")
            time.sleep(2)
            if nhanjob.get("data"):
                try:
                    api_client.post('/api/report/send', {
                        "description": "Báo cáo hoàn thành thất bại",
                        "users_advertising_id": nhanjob["data"].get("id"),
                        "type": "ads",
                        "provider": "tiktok",
                        "fb_id": account_id,
                        "error_type": 6
                    })
                    api_client.post('/api/advertising/publishers/tiktok/skip-jobs', {
                        "ads_id": nhanjob["data"].get("id"),
                        "object_id": nhanjob["data"].get("object_id"),
                        "account_id": account_id,
                        "type": nhanjob["data"].get("type")
                    })
                except APIError as e:
                    logger.error(f"Lỗi báo cáo job trùng: {e}")
            continue
        prev_job = nhanjob

        if nhanjob.get("status") == 200:
            job_data = nhanjob["data"]
            ads_id = job_data.get("id")
            link = job_data.get("link")
            object_id = job_data.get("object_id")
            job_type = job_data.get("type")
            if not link:
                print(colored("🗑️ Job die - Không có link!", "red"), end="\r")
                logger.warning("Job không có link, bỏ qua")
                time.sleep(2)
                try:
                    api_client.post('/api/report/send', {
                        "description": "Báo cáo hoàn thành thất bại",
                        "users_advertising_id": ads_id,
                        "type": "ads",
                        "provider": "tiktok",
                        "fb_id": account_id,
                        "error_type": 6
                    })
                    api_client.post('/api/advertising/publishers/tiktok/skip-jobs', {
                        "ads_id": ads_id,
                        "object_id": object_id,
                        "account_id": account_id,
                        "type": job_type
                    })
                except APIError as e:
                    logger.error(f"Lỗi báo cáo job die: {e}")
                continue
            if job_type not in lam:
                try:
                    api_client.post('/api/report/send', {
                        "description": "Báo cáo hoàn thành thất bại",
                        "users_advertising_id": ads_id,
                        "type": "ads",
                        "provider": "tiktok",
                        "fb_id": account_id,
                        "error_type": 6
                    })
                    api_client.post('/api/advertising/publishers/tiktok/skip-jobs', {
                        "ads_id": ads_id,
                        "object_id": object_id,
                        "account_id": account_id,
                        "type": job_type
                    })
                except APIError as e:
                    logger.error(f"Lỗi báo cáo job không hợp lệ: {e}")
                print(colored(f"❌ Đã bỏ qua job {job_type}!", "yellow"), end="\r")
                time.sleep(1)
                continue

            # Mở link theo phương thức đã chọn
            logger.info(f"Mở link job {job_type}: {link[:50]}...")
            opened = job_processor.process(Job(ads_id, link, job_type, object_id))

            if not opened and open_method == "adb":
                print(colored(f"❌ Không thể mở bằng ADB", "red"), end="\r")
                print(colored(f"🔗 Link: {link}", "yellow"))
                print(colored("   Vui lòng mở thủ công...", "cyan"))

            # UI Automation: Tìm và click nút Follow/Like
            ui_success = False
            ui_message = ""
            if ui_automator and job_type in ["follow", "like"]:
                print(colored(f"🤖 Đang thực hiện UI automation cho {job_type}...", "cyan"), end="\r")
                ui_success, ui_message = ui_automator.process_job(job_type)
                logger.info(f"UI automation {job_type}: {ui_message}")

                if ui_success:
                    print(colored(f"✅ UI automation thành công: {ui_message}", "green"), end="\r")
                else:
                    print(colored(f"⚠️ UI automation: {ui_message}", "yellow"), end="\r")

            # Đợi theo delay đã cấu hình
            for t in range(delay, -1, -1):
                print(colored(f"⏰ Đợi {t} giây ...", "cyan"), end="\r")
                time.sleep(1)

            # Nhận tiền
            ok = False
            for lan in range(1, 3 if lannhan == "y" else 2):
                try:
                    logger.info(f"Đang nhận tiền lần {lan} cho job {job_type} (ads_id: {ads_id})...")
                    nhantien = api_client.post('/api/advertising/publishers/tiktok/complete-jobs', {
                        "ads_id": ads_id,
                        "account_id": account_id,
                        "async": True,
                        "data": None
                    })
                    if nhantien.get("status") == 200:
                        ok = True
                        dem += 1
                        tien = nhantien["data"].get("prices", 0)
                        tong += tien
                        now = datetime.now(tz).strftime("%H:%M:%S")
                        print(colored(f"| {dem} | {now} | success | {nhantien['data'].get('type', '')} | Ẩn ID | +{tien} | {tong}", "green", bold=True))
                        logger.info(f"Job hoàn thành: {nhantien['data'].get('type')}, +{tien} xu")
                        checkdoiacc = 0
                        break
                    elif lan == 1:
                        print(colored("⚠️ Lần 1 thất bại - Đang thử lần 2...", "yellow"), end="\r")
                    elif lan == 2:
                        break
                except APIError as e:
                    logger.error(f"Lỗi nhận tiền lần {lan}: {e}")
                    if lan == 1:
                        print(colored("⚠️ Lần 1 thất bại - Đang thử lần 2...", "yellow"), end="\r")

            if not ok:
                print(colored("❌ Nhận tiền thất bại 2 lần - Đã skip job", "red", bold=True))
                try:
                    api_client.post('/api/report/send', {
                        "description": "Báo cáo hoàn thành thất bại",
                        "users_advertising_id": ads_id,
                        "type": "ads",
                        "provider": "tiktok",
                        "fb_id": account_id,
                        "error_type": 6
                    })
                    api_client.post('/api/advertising/publishers/tiktok/skip-jobs', {
                        "ads_id": ads_id,
                        "object_id": object_id,
                        "account_id": account_id,
                        "type": job_type
                    })
                except APIError as e:
                    logger.error(f"Lỗi báo cáo job fail: {e}")
                time.sleep(1)
                checkdoiacc += 1
        else:
            time.sleep(10)


if __name__ == "__main__":
    main()
