"""
Configuration management for Golike application
"""
import os
import json
from dataclasses import dataclass, asdict
from typing import Optional
from pathlib import Path


@dataclass
class AppConfig:
    """Cấu hình ứng dụng với type hints

    Attributes:
        api_base_url: URL cơ sở cho API Golike
        api_timeout: Timeout cho API requests (giây)
        log_level: Mức độ logging
        max_retry: Số lần retry tối đa
        adb_path: Đường dẫn đến ADB executable
        wifi_port: Port mặc định cho ADB WiFi
    """
    api_base_url: str
    api_timeout: int
    log_level: str
    max_retry: int
    adb_path: str
    wifi_port: int

    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Load cấu hình từ environment variables

        Returns:
            AppConfig: Cấu hình được load từ environment
        """
        return cls(
            api_base_url=os.getenv('API_BASE_URL', 'https://gateway.golike.net'),
            api_timeout=int(os.getenv('API_TIMEOUT', '10')),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            max_retry=int(os.getenv('MAX_RETRY', '3')),
            adb_path=os.getenv('ADB_PATH', r'D:\pythonadb\ADB\adb.exe'),
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
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)


# Load cấu hình toàn cục
CONFIG = AppConfig.from_env()
