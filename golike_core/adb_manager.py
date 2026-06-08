"""
Module Quản lý ADB cho ứng dụng GoLike
Quản lý kết nối và thao tác với thiết bị ADB.
"""
import os
import re
import json
import time
import subprocess
from typing import Optional, Dict, Any, List

from .config import CONFIG
from .logging import logger

ADB_CONFIG_FILE = "adb_config.json"


def load_adb_config() -> Dict[str, Any]:
    """Đọc cấu hình ADB

    Returns:
        Dict[str, Any]: Cấu hình ADB
    """
    if os.path.exists(ADB_CONFIG_FILE):
        try:
            with open(ADB_CONFIG_FILE, "r", encoding="utf8") as f:
                config = json.load(f)
                # Đảm bảo selected_adb_path tồn tại
                if "selected_adb_path" not in config:
                    config["selected_adb_path"] = None
                return config
        except (json.JSONDecodeError, IOError) as e:
            logger.debug(f"Lỗi đọc adb_config.json: {e}")
    # Cấu hình mặc định
    return {"devices": [], "current_device": None, "open_method": "termux", "selected_adb_path": None}


def save_adb_config(config: Dict[str, Any]) -> None:
    """Lưu cấu hình ADB

    Args:
        config: Cấu hình ADB
    """
    with open(ADB_CONFIG_FILE, "w", encoding="utf8") as f:
        json.dump(config, f, indent=2)


def colored(text: str, color: str, bold: bool = False, attrs: Optional[List[str]] = None) -> str:
    """Hỗ trợ in văn bản có màu

    Args:
        text: Nội dung cần in
        color: Màu sắc (yellow, pink, cyan, white, green, red)
        bold: Có in đậm không
        attrs: Danh sách thuộc tính bổ sung (ví dụ: ["bold"])

    Returns:
        str: Văn bản đã được gắn mã màu
    """
    colors = {
        "yellow": "\033[33m",
        "pink": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[97m",
        "green": "\033[32m",
        "red": "\033[31m",
        "magenta": "\033[35m",
        "blue": "\033[34m",
        "reset": "\033[0m"
    }
    codes = []
    if bold or (attrs and "bold" in attrs):
        codes.append("\033[1m")
    codes.append(colors.get(color, ""))
    return "".join(codes) + text + colors["reset"]


class ADBManager:
    """Quản lý các thiết bị ADB

    Cung cấp giao diện để quản lý kết nối và thao tác
    với các thiết bị ADB.
    """

    def __init__(self, adb_path: Optional[str] = None):
        """Khởi tạo ADBManager

        Args:
            adb_path: Đường dẫn đến file thực thi ADB (nếu None sẽ tự tìm)
        """
        self.adb_path = adb_path if adb_path else self._find_adb_path()
        self.selected_device: Optional[str] = None

    def _find_system_adb(self):
        """Tìm đường dẫn ADB của hệ thống"""
        try:
            result = subprocess.run(["which", "adb"], capture_output=True, text=True)
            if result.returncode == 0:
                return "adb"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return "adb"

    def _find_adb_path(self) -> str:
        """Tìm đường dẫn adb.exe, ưu tiên thư mục ADB nội bộ của dự án"""
        # 1. Ưu tiên 1: Thư mục ADB cạnh file main.py hiện tại
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        local_path = os.path.join(base_dir, "ADB", "adb.exe")
        if os.path.exists(local_path):
            # Kiểm tra xem đang ở Windows hay là file thực thi hợp lệ
            if os.name == 'nt':  # Windows
                logger.info(f"Sử dụng local ADB: {local_path}")
                return local_path
            else:
                # Trên các hệ thống không phải Windows, thử dùng system ADB
                system_adb = self._find_system_adb()
                if system_adb != "adb":
                    logger.info(f"Sử dụng local ADB: {local_path} -> {system_adb}")
                return system_adb

        # 2. Ưu tiên 2: Kiểm tra PATH môi trường
        try:
            result = subprocess.run(["adb", "version"], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                logger.info("Sử dụng ADB từ PATH hệ thống")
                return "adb"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # 3. Ưu tiên 3: Từ biến môi trường ADB_PATH hoặc config
        try:
            config_path = CONFIG.adb_path
            if config_path and os.path.exists(config_path):
                # Kiểm tra đường dẫn cấu hình có hợp lệ cho nền tảng hiện tại không
                if os.path.exists(config_path) and (os.name == 'nt' or not config_path.endswith('.exe')):
                    logger.info(f"Sử dụng ADB từ config: {config_path}")
                    return config_path
        except Exception:
            pass

        # 4. Fallback: Đường dẫn cố định
        common_path = r"D:\pythonadb\ADB\adb.exe"
        if os.path.exists(common_path) and os.name == 'nt':
            logger.info(f"Sử dụng ADB path mặc định: {common_path}")
            return common_path

        # 5. Cuối cùng: Dùng system adb
        logger.warning("Không tìm thấy ADB, sử dụng 'adb' từ system PATH")
        return "adb"

    def check_adb(self) -> bool:
        """Kiểm tra ADB có sẵn không

        Returns:
            bool: True nếu ADB có sẵn, False nếu không
        """
        try:
            result = subprocess.run([self.adb_path, 'version'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def check_connected_devices(self) -> List[str]:
        """Lay danh sach cac thiet bi ADB dang ket noi"""
        try:
            result = subprocess.run(
                [self.adb_path, "devices"],
                capture_output=True,
                text=True,
                timeout=10
            )
            output = result.stdout.strip().splitlines()

            unauthorized_devices = [line.split()[0] for line in output[1:] if line.strip() and "unauthorized" in line]
            if unauthorized_devices:
                print(colored("\n⚠️  CANH BAO: THIET BI CHUA DUOC UY QUYEN (UNAUTHORIZED)! ⚠️", "red", attrs=["bold"]))
                for ud in unauthorized_devices:
                    print(colored(f"👉 ID: {ud} -> Hay MO DIEN THOAI len va bam 'CHO PHEP GO LOI USB' (Allow USB Debugging)!", "yellow", bold=True))
                print(colored("═════════════════════════════════════════════════════════════════", "red"))

            devices = [line.split()[0] for line in output[1:] if line.strip() and "device" in line]
            return devices
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.error(f"Loi ket noi ADB: {e}")
            return []

    def select_device(self) -> Optional[str]:
        """Cho phep nguoi dung chon thiet bi ket noi truc quan"""
        devices = self.check_connected_devices()

        if not devices:
            logger.error("Khong co thiet bi ADB nao duoc ket noi.")
            return None

        print(colored("\n🔌 Thiet bi ADB dang ket noi:", "cyan"))
        for i, device in enumerate(devices, start=1):
            print(colored(f"{i}. {device}", "white"))

        while True:
            try:
                choice = input(colored("👉 Chon so thiet bi de ket noi: ", "green")).strip()
                if choice.isdigit():
                    choice_idx = int(choice)
                    if 1 <= choice_idx <= len(devices):
                        self.selected_device = devices[choice_idx - 1]
                        logger.info(f"🔌 Da chon thiet bi: {self.selected_device}")
                        return self.selected_device
                    else:
                        print(colored("⚠️ Lua chon khong hop le, thu lai.", "yellow"))
                else:
                    print(colored("⚠️ Vui long nhap so hop le.", "yellow"))
            except KeyboardInterrupt:
                logger.info("Da huy chon thiet bi.")
                return None

    def open_link(self, link: str, device_id: Optional[str] = None) -> bool:
        """Mo link tren thiet bi

        Args:
            link: URL can mo
            device_id: ID thiet bi (neu None dung thiet bi mac dinh hoac da chon)

        Returns:
            bool: True neu thanh cong, False neu khong
        """
        try:
            target_device = device_id if device_id else self.selected_device
            cmd = [self.adb_path]
            if target_device:
                cmd.extend(['-s', target_device])
            cmd.extend(['shell', 'am', 'start', '-a', 'android.intent.action.VIEW', '-d', link])
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def connect_wifi(self, ip: str, port: int = 5555) -> bool:
        """Ket noi thiet bi qua WiFi

        Args:
            ip: Dia chi IP Dien thoai
            port: Cong ket noi WiFi (mac dinh 5555)

        Returns:
            bool: True neu thanh cong, False neu that bai
        """
        try:
            result = subprocess.run(
                [self.adb_path, 'connect', f'{ip}:{port}'],
                capture_output=True,
                text=True,
                timeout=15
            )
            return result.returncode == 0 and 'connected' in result.stdout.lower()
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"Loi ket noi WiFi: {e}")
            return False

    def pair_wifi(self, ip: str, port: int, pairing_code: str) -> bool:
        """Ghep noi thiet bi qua WiFi (Android 11+)

        Args:
            ip: Dia chi IP
            port: Cong ghep noi (Pairing port)
            pairing_code: Ma ghep noi (6 chu so)

        Returns:
            bool: True neu ghep noi thanh cong
        """
        try:
            logger.info(f"Dang ghep noi ADB voi {ip}:{port} bang ma {pairing_code}...")
            # ADB pair requires input of pairing code, but we can try to pass it if adb version supports it
            # Or use a process with stdin
            process = subprocess.Popen(
                [self.adb_path, 'pair', f'{ip}:{port}'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(input=f"{pairing_code}\n", timeout=15)
            
            if "Successfully paired" in stdout:
                logger.info(f"Ghep noi thanh cong voi {ip}:{port}")
                return True
            else:
                logger.error(f"Ghep noi that bai: {stdout} {stderr}")
                return False
        except Exception as e:
            logger.error(f"Loi khi ghep noi ADB: {e}")
            return False

    def disconnect_wifi(self, ip: str, port: int = 5555) -> bool:
        """Ngat ket noi WiFi khoi thiet bi"""
        try:
            subprocess.run([self.adb_path, 'disconnect', f'{ip}:{port}'], capture_output=True, timeout=5)
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def restart_server(self) -> bool:
        """Khoi dong lai ADB server de lam sach ket noi"""
        try:
            logger.info("Dang tat ADB daemon server...")
            subprocess.run([self.adb_path, 'kill-server'], capture_output=True, timeout=5)
            time.sleep(1)
            logger.info("Dang khoi tao lai ADB daemon server...")
            subprocess.run([self.adb_path, 'start-server'], capture_output=True, timeout=5)
            time.sleep(2)
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"Loi restart ADB server: {e}")
            return False

    def get_device_wifi_ip(self, device_id: str) -> Optional[str]:
        """Tu dong truy van dia chi WiFi cuc bo tu thiet bi dang ket noi ADB"""
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
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    @staticmethod
    def _extract_ip_from_output(output: str) -> Optional[str]:
        """Ham Helper trich xuat chuoi IP tu command output bang regex"""
        match = re.search(r'inet (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', output)
        if match:
            return match.group(1)
        return None