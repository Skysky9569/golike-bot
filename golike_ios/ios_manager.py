"""
Module quản lý thiết bị iOS (liệt kê và chọn UDID).
"""
import subprocess
import re
from typing import List, Dict, Optional
from golike_core.logging import logger

class IOSManager:
    @staticmethod
    def get_connected_devices() -> List[Dict[str, str]]:
        """
        Lấy danh sách thiết bị iOS đang kết nối (máy thật và simulator).
        Sử dụng lệnh: xcrun xctrace list devices
        """
        devices = []
        try:
            result = subprocess.run(['xcrun', 'xctrace', 'list', 'devices'], 
                                   capture_output=True, text=True, check=True)
            output = result.stdout
            
            # Phân tách các phần
            sections = re.split(r'== (Devices|Simulators) ==', output)
            
            # Phần Devices (Máy thật)
            if len(sections) > 2:
                device_lines = sections[2].strip().split('\n')
                for line in device_lines:
                    if not line.strip(): continue
                    # Format: Name (Version) (UDID)
                    match = re.search(r'^(.*?) \((.*?)\) \((.*?)\)$', line)
                    if match:
                        name, version, udid = match.groups()
                        # Loại bỏ Mac nội bộ nếu cần, nhưng cứ để lại cho chắc
                        if "MacBook" in name or "Mac mini" in name or "Mac Studio" in name:
                            continue
                        devices.append({
                            'name': name,
                            'version': version,
                            'udid': udid,
                            'type': 'Real Device'
                        })
            
            # Phần Simulators
            if len(sections) > 4:
                sim_lines = sections[4].strip().split('\n')
                for line in sim_lines:
                    if not line.strip(): continue
                    match = re.search(r'^(.*?) \((.*?)\) \((.*?)\)$', line)
                    if match:
                        name, version, udid = match.groups()
                        devices.append({
                            'name': name,
                            'version': version,
                            'udid': udid,
                            'type': 'Simulator'
                        })
                        
        except Exception as e:
            logger.error(f"Lỗi khi liệt kê thiết bị iOS: {e}")
            
        return devices

    @staticmethod
    def check_appium_server_status() -> bool:
        """Kiểm tra xem Appium Server có đang chạy hay không."""
        import requests
        try:
            response = requests.get("http://127.0.0.1:4723/status", timeout=3)
            if response.status_code == 200:
                data = response.json()
                return data.get("value", {}).get("ready", False)
        except Exception:
            pass
        return False

    def select_device(self) -> Optional[Dict[str, str]]:
        """Hiển thị menu chọn thiết bị iOS."""
        from golike_core.adb_manager import colored
        
        devices = self.get_connected_devices()
        if not devices:
            print(colored("❌ Không tìm thấy thiết bị iOS nào đang kết nối!", "red"))
            return None
            
        print(colored("\n📱 DANH SÁCH THIẾT BỊ iOS:", "yellow"))
        print(colored("════════════════════════════════════════════════", "white"))
        for idx, dev in enumerate(devices, 1):
            type_str = f"[{dev['type']}]"
            print(colored(f"  [{idx}] {type_str.ljust(13)} {dev['name']} (iOS {dev['version']})", "cyan"))
            print(colored(f"      UDID: {dev['udid']}", "white"))
            
        print(colored("════════════════════════════════════════════════", "white"))
        
        while True:
            choice = input(colored("👉 Chọn thiết bị (1, 2, ...) hoặc '0' để nhập thủ công: ", "green")).strip()
            if choice == '0':
                return None
            if choice.isdigit() and 1 <= int(choice) <= len(devices):
                return devices[int(choice) - 1]
            print(colored("❌ Lựa chọn không hợp lệ!", "red"))
