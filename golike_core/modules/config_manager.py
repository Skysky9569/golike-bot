"""
Module cấu hình hệ thống cho GoLike
"""

import json
import os

class ConfigManager:
    """Module quản lý cấu hình hệ thống"""

    def __init__(self, config_file="app_config.json"):
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self):
        """Tải cấu hình từ file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Lỗi tải cấu hình: {e}")
                return {}
        return {}

    def get_config_value(self, key, default=None):
        """Lấy giá trị cấu hình theo key"""
        return self.config.get(key, default)

    def set_config_value(self, key, value):
        """Thiết lập giá trị cấu hình"""
        self.config[key] = value
        self._save_config()

    def _save_config(self):
        """Lưu cấu hình vào file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Lỗi lưu cấu hình: {e}")

    def load_delay_config(self, config_path="config_golike_sele.json"):
        """Tải cấu hình delay từ file"""
        default_config = {
            "delay_between_jobs": 10,
            "delay_after_api_call": 3.5,
            "delay_after_complete": 4,
            "delay_after_report_error": 1.5,
            "delay_on_job_hunt_retry": 12,
            "delay_between_accounts": 60,
            "timeout_driver_load": 10,
            "timeout_wait_element": 8,
            "sleep_on_reset": 30,
            "sleep_on_cool_down": 300,
            "delay_after_reset_click": 3.5,
            "sleep_on_hunt_retry": 10,
            "switch_server_minutes": 0
        }

        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge với default config
                    for key, value in default_config.items():
                        if key not in loaded_config:
                            loaded_config[key] = value
                    return loaded_config
            except Exception as e:
                print(f"Lỗi tải cấu hình delay: {e}")
                return default_config
        return default_config