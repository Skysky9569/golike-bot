"""
Main menu for Golike application
Supports both TikTok and Facebook platforms
"""
import os
import sys
import time
import json
import subprocess
import requests
import re
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
from datetime import datetime
from golike_core.security import CredentialManager, InputValidator
from golike_core.api_client import GolikeAPIClient
from golike_core.config import CONFIG
from golike_core.logging import logger

# Import UI automation module
try:
    from tiktok_automation import TikTokUIAutomator
    UI_AUTOMATION_AVAILABLE = True
except ImportError:
    UI_AUTOMATION_AVAILABLE = False
    logger.warning("tiktok_automation module không khả dụng. UI automation sẽ bị tắt.")
# ----------------------------------------------------------------------------
# TỰ ĐỘNG CẤU HÌNH ĐƯỜNG DẪN HỆ THỐNG CHO ADB
# Đảm bảo uiautomator2 và các thư viện phụ luôn tìm thấy file adb.exe cục bộ
# ----------------------------------------------------------------------------
local_adb_dir = os.path.join(os.getcwd(), "ADB")
if os.path.exists(local_adb_dir):
    os.environ["PATH"] = local_adb_dir + os.pathsep + os.environ["PATH"]

default_workspace_adb = r"D:\pythonadb\ADB"
if os.path.exists(default_workspace_adb) and default_workspace_adb not in os.environ["PATH"]:
    os.environ["PATH"] = default_workspace_adb + os.pathsep + os.environ["PATH"]

# Thiết lập timezone Việt Nam
try:
    import pytz
    tz = pytz.timezone("Asia/Ho_Chi_Minh")
except ImportError:
    tz = None


# ============================================================================
# SYSTEM VERSION & CONFIG
# ============================================================================

CURRENT_VERSION = "1.5.1"
UPDATE_URL = "https://raw.githubusercontent.com/skysky9569/golike-bot/main/main.py"

ADB_PATH = CONFIG.adb_path
ADB_CONFIG_FILE = "adb_config.json"


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


# ============================================================================
# API CLIENT
# ============================================================================

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

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET request

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Dict[str, Any]: Response data
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
            logger.error(f"GET request failed: {e}")
            return {}

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """POST request

        Args:
            endpoint: API endpoint
            data: Request body data

        Returns:
            Dict[str, Any]: Response data
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
            logger.error(f"POST request failed: {e}")
            return {}


# ============================================================================
# ADB MANAGER
# ============================================================================

class ADBManager:
    """Quản lý các thiết bị ADB

    Cung cấp interface để quản lý kết nối và thao tác
    với các thiết bị ADB.
    """

    def __init__(self, adb_path: Optional[str] = None):
        """Khởi tạo ADBManager

        Args:
            adb_path: Đường dẫn đến ADB executable (nếu None sẽ tự tìm)
        """
        self.adb_path = adb_path if adb_path else self._find_adb_path()
        self.selected_device: Optional[str] = None

    def _find_adb_path(self) -> str:
        """Tìm đường dẫn adb.exe, ưu tiên thư mục ADB nội bộ của dự án"""
        # 1. Thử đường dẫn tương đối trong dự án
        local_path = os.path.join(os.getcwd(), "ADB", "adb.exe")
        if os.path.exists(local_path):
            logger.info(f"Sử dụng local ADB: {local_path}")
            return local_path
            
        # 2. Thử đường dẫn tuyệt đối mặc định của workspace
        common_path = r"D:\pythonadb\ADB\adb.exe"
        if os.path.exists(common_path):
            logger.info(f"Sử dụng ADB path: {common_path}")
            return common_path

        # 3. Thử từ config nếu có
        try:
            config_path = CONFIG.adb_path
            if config_path and os.path.exists(config_path):
                return config_path
        except Exception:
            pass

        # 4. Dự phòng dùng lệnh hệ thống
        logger.warning("Không tìm thấy local adb.exe, sử dụng system adb...")
        return "adb"

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

    def check_connected_devices(self) -> List[str]:
        """Lấy danh sách các thiết bị ADB đang kết nối"""
        try:
            result = subprocess.run(
                [self.adb_path, "devices"],
                capture_output=True,
                text=True,
                timeout=10
            )
            output = result.stdout.strip().splitlines()
            devices = [line.split()[0] for line in output[1:] if line.strip() and "device" in line]
            return devices
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.error(f"Lỗi kết nối ADB: {e}")
            return []

    def select_device(self) -> Optional[str]:
        """Cho phép người dùng chọn thiết bị kết nối trực quan"""
        devices = self.check_connected_devices()

        if not devices:
            logger.error("Không có thiết bị ADB nào được kết nối.")
            return None

        print(colored("\n🔌 Thiết bị ADB đang kết nối:", "cyan"))
        for i, device in enumerate(devices, start=1):
            print(colored(f"{i}. {device}", "white"))

        while True:
            try:
                choice = input(colored("👉 Chọn số thiết bị để kết nối: ", "green")).strip()
                if choice.isdigit():
                    choice_idx = int(choice)
                    if 1 <= choice_idx <= len(devices):
                        self.selected_device = devices[choice_idx - 1]
                        logger.info(f"🔌 Đã chọn thiết bị: {self.selected_device}")
                        return self.selected_device
                    else:
                        print(colored("⚠️ Lựa chọn không hợp lệ, thử lại.", "yellow"))
                else:
                    print(colored("⚠️ Vui lòng nhập số hợp lệ.", "yellow"))
            except KeyboardInterrupt:
                logger.info("Đã hủy chọn thiết bị.")
                return None

    def open_link(self, link: str, device_id: Optional[str] = None) -> bool:
        """Mở link trên thiết bị

        Args:
            link: URL cần mở
            device_id: ID thiết bị (nếu None dùng thiết bị mặc định hoặc đã chọn)

        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            target_device = device_id if device_id else self.selected_device
            cmd = [self.adb_path]
            if target_device:
                cmd.extend(['-s', target_device])
            cmd.extend(['shell', 'am', 'start', '-a', 'android.intent.action.VIEW', '-d', link])
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False

    def connect_wifi(self, ip: str, port: int = 5555) -> bool:
        """Kết nối thiết bị qua WiFi
        
        Args:
            ip: Địa chỉ IP Điện thoại
            port: Cổng kết nối WiFi (mặc định 5555)
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            result = subprocess.run(
                [self.adb_path, 'connect', f'{ip}:{port}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0 and 'connected' in result.stdout.lower()
        except Exception as e:
            logger.error(f"Lỗi kết nối WiFi: {e}")
            return False

    def disconnect_wifi(self, ip: str, port: int = 5555) -> bool:
        """Ngắt kết nối WiFi khỏi thiết bị"""
        try:
            subprocess.run([self.adb_path, 'disconnect', f'{ip}:{port}'], capture_output=True, timeout=5)
            return True
        except Exception:
            return False

    def restart_server(self) -> bool:
        """Khởi động lại ADB server để làm sạch kết nối"""
        try:
            logger.info("Đang tắt ADB daemon server...")
            subprocess.run([self.adb_path, 'kill-server'], capture_output=True, timeout=5)
            time.sleep(1)
            logger.info("Đang khởi tạo lại ADB daemon server...")
            subprocess.run([self.adb_path, 'start-server'], capture_output=True, timeout=5)
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Lỗi restart ADB server: {e}")
            return False

    def get_device_wifi_ip(self, device_id: str) -> Optional[str]:
        """Tự động truy vấn địa chỉ WiFi cục bộ từ thiết bị đang kết nối ADB"""
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
        """Hàm Helper trích xuất chuỗi IP từ command output bằng regex"""
        match = re.search(r'inet (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', output)
        if match:
            return match.group(1)
        return None


# ============================================================================
# JOB PROCESSOR
# ============================================================================

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


def input_int(prompt: str, color: str = "green", minval: int = 1) -> int:
    """Helper để input số nguyên
    
    Args:
        prompt: Nội dung prompt
        color: Màu của text
        minval: Giá trị tối thiểu
        
    Returns:
        int: Số nguyên người dùng nhập
    """
    while True:
        value = input(colored(prompt, color)).strip()
        if value.isdigit() and int(value) >= minval:
            return int(value)
        print(colored(f"Vui lòng nhập số nguyên >= {minval}!", "red"))


_CACHED_IP = None

def get_public_ip() -> str:
    """Lấy địa chỉ IP công cộng thật của máy (được cache)"""
    global _CACHED_IP
    if _CACHED_IP is not None:
        return _CACHED_IP
    
    urls = ["https://api.ipify.org", "https://ifconfig.me/ip", "https://icanhazip.com"]
    for url in urls:
        try:
            r = requests.get(url, timeout=1.5)
            if r.status_code == 200:
                _CACHED_IP = r.text.strip()
                return _CACHED_IP
        except Exception:
            continue
            
    try:
        import socket
        _CACHED_IP = socket.gethostbyname(socket.gethostname())
        return _CACHED_IP
    except Exception:
        pass
        
    _CACHED_IP = "Chưa xác định"
    return _CACHED_IP


def check_for_updates():
    """Kiểm tra và tự động cập nhật file main.py từ Github"""
    # Đảm bảo ANSI color hoạt động trên Windows Terminal cũ
    if sys.platform == 'win32':
        os.system('color')
        
    print(colored(f"[*] Đang kiểm tra cập nhật hệ thống (Phiên bản: v{CURRENT_VERSION})...", "cyan"))
    try:
        r = requests.get(UPDATE_URL, timeout=10)
        if r.status_code == 200:
            server_code = r.text
            import re
            match = re.search(r'CURRENT_VERSION\s*=\s*["\']([^"\']+)["\']', server_code)
            if match:
                latest_ver = match.group(1)
                if latest_ver != CURRENT_VERSION:
                    print(colored(f"\n[🔥] PHÁT HIỆN PHIÊN BẢN MỚI HƠN: v{latest_ver}!", "yellow", bold=True))
                    chon = input(colored("👉 Bạn có muốn tự động tải và ghi đè cập nhật? (y/n, Enter là có): ", "green")).strip().lower()
                    if chon in ['y', 'yes', '']:
                        print(colored("[*] Đang cài đặt phiên bản mới...", "cyan"))
                        file_path = os.path.abspath(__file__)
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(server_code)
                        print(colored("[✅] Cập nhật thành công! Vui lòng gõ lại `python main.py` để áp dụng.", "green", bold=True))
                        sys.exit(0)
                    else:
                        print(colored(f"[*] Đã bỏ qua. Tiếp tục chạy phiên bản hiện tại v{CURRENT_VERSION}.", "white"))
                else:
                    print(colored("[✓] Tool đã ở phiên bản mới nhất.", "green"))
    except Exception:
        print(colored("[!] Không kết nối được Github Server để kiểm tra cập nhật (bỏ qua).", "yellow"))


def banner():
    """Hiển thị banner"""
    os.system("clear" if os.name == "posix" else "cls")
    banner_text = f"""
{colored(':))', 'yellow')}
{colored('════════════════════════════════════════════════', 'white')}
{colored('👑 Tool By Đóme: >😘 Golike 💕 v' + CURRENT_VERSION, 'cyan', bold=True)}
{colored('════════════════════════════════════════════════', 'white')}
{colored('⚠️ Lưu ý    : 🌟Tool Sử Dụng Cho Android/Pc🌟', 'white')}
{colored('🔐 Bảo mật  : Credential đã mã hóa, Input validated', 'green')}
{colored('🔄 Cập nhật : Tự động kiểm tra bản mới từ Github', 'green')}
{colored('🏗️  Code Org  : Cấu trúc Modular chuyên nghiệp', 'green')}
{colored('════════════════════════════════════════════════', 'white')}
"""
    print(banner_text)


def menu() -> None:
    """Menu chính hiển thị danh sách chức năng"""
    banner()
    print(colored(f"🆔 Địa chỉ Ip  : 🚨 {get_public_ip()} 🚨", "white"))
    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("⚡ CHỨC NĂNG CHÍNH:", "cyan", bold=True))
    print(colored("   [1] 🥇 Vào Tool TikTok (Auto ADB)", "white"))
    print(colored("   [2] 📱 Vào Tool Facebook (API)", "cyan"))
    print(colored("   [3] 🔥 Vào Tool Facebook (Selenium)", "yellow"))
    print(colored("\n🛠️  HỆ THỐNG & CẤU HÌNH:", "cyan", bold=True))
    print(colored("   [4] 📶 Cài Đặt Kết Nối ADB WiFi/USB", "cyan"))
    print(colored("   [5] 🥈 Xóa Authorization Hiện Tại", "red"))
    print(colored("   [6] ⚙️  Xem Cấu Hình Bảo Mật", "green"))
    print(colored("   [7] 📊 Xem Hệ Thống Logs", "white"))
    print(colored("   [8] 🧪 Chạy Bộ Thử Nghiệm (Tests)", "magenta"))
    print(colored("   [9] 🔧 Bật/Tắt Debug Mode", "blue"))
    
    print(colored("   [0] 🔙 Thoát Chương Trình", "white"))
    print(colored("════════════════════════════════════════════════", "white"))


def adb_menu() -> None:
    """Menu quản lý kết nối ADB WiFi/USB nâng cao"""
    validator = InputValidator()
    adb_manager = ADBManager()

    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print(colored("════════════════════════════════════════════════", "cyan", bold=True))
        print(colored("📶 QUẢN LÝ KẾT NỐI THIẾT BỊ ADB WIFI/USB", "yellow", bold=True))
        print(colored("════════════════════════════════════════════════", "cyan"))

        if not adb_manager.check_adb():
            print(colored("❌ Không tìm thấy adb.exe! Hãy kiểm tra thư mục ADB.", "red"))
            input(colored("Nhấn Enter để quay lại...", "white"))
            return

        devices = adb_manager.check_connected_devices()
        config = load_adb_config()

        print(colored(f"📊 Thiết bị đang kết nối (Online): {len(devices)}", "green"))
        if devices:
            for idx, device_id in enumerate(devices, 1):
                marker = "👉 " if config.get("current_device") == device_id else "   "
                print(colored(f"{marker}[{idx}] 🆔 {device_id} [✅ Device Online]", "white"))
        else:
            print(colored("   ⚠️ Hiện tại không có thiết bị ADB nào đang kết nối online", "yellow"))

        print(colored("════════════════════════════════════════════════", "cyan"))
        print(colored("🔌 Nhập 1 : Khởi động lại ADB Server (Sửa lỗi ngắt kết nối USB)", "yellow"))
        print(colored("📶 Nhập 2 : Kết nối thiết bị qua IP WiFi (Không cần dây)", "yellow"))
        print(colored("📱 Nhập 3 : Chọn thiết bị mặc định để sử dụng", "yellow"))
        print(colored("🔓 Nhập 4 : Ngắt kết nối thiết bị WiFi", "yellow"))
        print(colored("📋 Nhập 5 : Xem danh sách IP WiFi đã lưu", "yellow"))
        print(colored("🗑️  Nhập 6 : Xóa IP WiFi khỏi bộ nhớ lưu trữ", "yellow"))
        print(colored("🔙 Nhập 0 : Quay lại Menu Chính", "yellow"))
        print(colored("════════════════════════════════════════════════", "cyan"))

        choice = input(colored("👉 Chọn chức năng: ", "green")).strip()

        if choice == "0":
            return
        elif choice == "1":
            print(colored("\n🔄 Đang khởi động lại ADB Server...", "cyan"))
            if adb_manager.restart_server():
                print(colored("✅ Đã khởi động lại ADB Server thành công!", "green"))
                print(colored("💡 Mẹo: Đảm bảo bạn đã bật USB Debugging trên điện thoại.", "white"))
                input(colored("Nhấn Enter để quét lại danh sách thiết bị...", "white"))
            else:
                print(colored("❌ Lỗi khi khởi động lại ADB!", "red"))
                input(colored("Nhấn Enter để tiếp tục...", "white"))

        elif choice == "2":
            print(colored("\n📡 KẾT NỐI QUA WIFI:", "cyan"))
            ip = input(colored("👉 Nhập địa chỉ IP Điện thoại (ví dụ: 192.168.1.10): ", "green")).strip()
            ip = validator.sanitize_string(ip, 15)

            if not validator.validate_ip(ip):
                print(colored("❌ IP không hợp lệ! Vui lòng kiểm tra lại.", "red"))
                input(colored("Nhấn Enter để quay lại...", "white"))
                continue

            port_input = input(colored("👉 Nhập Cổng (Port) kết nối (Mặc định 5555): ", "green")).strip()
            if port_input and port_input.isdigit():
                port = int(port_input)
                if not validator.validate_port(port):
                    print(colored("❌ Cổng không hợp lệ (phải từ 1-65535)!", "red"))
                    input(colored("Nhấn Enter để tiếp tục...", "white"))
                    continue
            else:
                port = 5555

            print(colored(f"🔄 Đang tiến hành kết nối đến {ip}:{port}...", "cyan"))
            if adb_manager.connect_wifi(ip, port):
                print(colored("✅ Kết nối WiFi thành công rực rỡ!", "green"))
                saved_devices = config.get("devices", [])
                if ip not in saved_devices:
                    saved_devices.append(ip)
                    config["devices"] = saved_devices
                    save_adb_config(config)
                time.sleep(2)
            else:
                print(colored("❌ Không thể kết nối WiFi đến thiết bị!", "red"))
                print(colored("💡 Lưu ý: Điện thoại và PC phải chung một mạng WiFi.", "yellow"))
                print(colored("💡 Cần cắm cáp USB lần đầu để kích hoạt port WiFi.", "yellow"))
                input(colored("Nhấn Enter để tiếp tục...", "white"))

        elif choice == "3":
            if not devices:
                print(colored("❌ Danh sách rỗng, không có thiết bị online để chọn!", "red"))
                input(colored("Nhấn Enter để tiếp tục...", "white"))
                continue

            print(colored("\n📱 CHỌN THIẾT BỊ MẶC ĐỊNH:", "cyan"))
            dev_choice = input(colored("👉 Nhập số thứ tự thiết bị: ", "green")).strip()
            if dev_choice.isdigit() and 1 <= int(dev_choice) <= len(devices):
                device_id = devices[int(dev_choice) - 1]
                config["current_device"] = device_id
                save_adb_config(config)
                print(colored(f"✅ Đã chọn thiết bị làm mặc định: {device_id}", "green"))

                # Tự động truy vấn IP WiFi
                wifi_ip = adb_manager.get_device_wifi_ip(device_id)
                if wifi_ip:
                    print(colored(f"📶 Địa chỉ WiFi cục bộ của thiết bị là: {wifi_ip}", "cyan"))
                    print(colored(f"💡 Gợi ý: Dùng {wifi_ip}:5555 để kết nối không dây!", "yellow"))
                time.sleep(3)
            else:
                print(colored("❌ Lựa chọn không hợp lệ!", "red"))
                time.sleep(1)

        elif choice == "4":
            saved_devices = config.get("devices", [])
            if not saved_devices:
                print(colored("❌ Không có thiết bị WiFi nào được lưu trong bộ nhớ!", "yellow"))
                input(colored("Nhấn Enter để quay lại...", "white"))
                continue

            print(colored("\n📋 Danh sách IP WiFi đang lưu:", "cyan"))
            for idx, ip in enumerate(saved_devices, 1):
                print(colored(f"   [{idx}] {ip}", "white"))

            dev_choice = input(colored("👉 Chọn số để ngắt kết nối (0 để hủy): ", "green")).strip()
            if dev_choice == "0":
                continue
            if dev_choice.isdigit() and 1 <= int(dev_choice) <= len(saved_devices):
                ip = saved_devices[int(dev_choice) - 1]
                if adb_manager.disconnect_wifi(ip):
                    print(colored(f"✅ Đã ngắt kết nối thành công khỏi {ip}", "green"))
                    saved_devices.remove(ip)
                    config["devices"] = saved_devices
                    save_adb_config(config)
                else:
                    print(colored(f"❌ Không thể ngắt kết nối khỏi {ip}!", "red"))
                time.sleep(2)

        elif choice == "5":
            saved_devices = config.get("devices", [])
            if saved_devices:
                print(colored("\n📋 LỊCH SỬ THIẾT BỊ WIFI ĐÃ LƯU:", "cyan"))
                for ip in saved_devices:
                    print(colored(f"   🔹 {ip}", "white"))
            else:
                print(colored("\n❌ Bộ nhớ rỗng, chưa lưu thiết bị nào.", "yellow"))
            input(colored("Nhấn Enter để tiếp tục...", "white"))

        elif choice == "6":
            saved_devices = config.get("devices", [])
            if not saved_devices:
                print(colored("❌ Danh sách trống rỗng!", "yellow"))
                input(colored("Nhấn Enter để quay lại...", "white"))
                continue

            print(colored("\n📋 CHỌN ĐỊA CHỈ ĐỂ XÓA KHỎI BỘ NHỚ:", "cyan"))
            for idx, ip in enumerate(saved_devices, 1):
                print(colored(f"   [{idx}] {ip}", "white"))

            dev_choice = input(colored("👉 Nhập số để xóa (0 để hủy): ", "green")).strip()
            if dev_choice == "0":
                continue
            if dev_choice.isdigit() and 1 <= int(dev_choice) <= len(saved_devices):
                ip = saved_devices[int(dev_choice) - 1]
                saved_devices.remove(ip)
                config["devices"] = saved_devices
                save_adb_config(config)
                print(colored(f"✅ Đã xóa thành công địa chỉ IP: {ip}", "green"))
                time.sleep(2)



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

    # Facebook cookie
    cookie_file = "facebook_cookie.enc"
    if os.path.exists(cookie_file):
        print(colored("   ✅ Facebook cookie tồn tại (đã mã hóa)", "green"))
        print(colored(f"   📄 File: {cookie_file}", "white"))
    else:
        print(colored("   ❌ Chưa có Facebook cookie", "yellow"))

    # TikTok session
    session_file = "tiktok_session.enc"
    if os.path.exists(session_file):
        print(colored("   ✅ TikTok session tồn tại (đã mã hóa)", "green"))
        print(colored(f"   📄 File: {session_file}", "white"))
    else:
        print(colored("   ❌ Chưa có TikTok session", "yellow"))

    print(colored("\n⚙️  Application Config:", "white"))
    print(colored(f"   📂 ADB Path: {CONFIG.adb_path}", "white"))
    print(colored(f"   🌐 API Base URL: {CONFIG.api_base_url}", "white"))
    print(colored(f"   ⏱️  API Timeout: {CONFIG.api_timeout}s", "white"))
    print(colored(f"   📊 Log Level: {CONFIG.log_level}", "white"))
    print(colored(f"   🔄 Max Retry: {CONFIG.max_retry}", "white"))
    print(colored(f"   📶 WiFi Port: {CONFIG.wifi_port}", "white"))

    print(colored("\n════════════════════════════════════════════════", "cyan"))
    input(colored("Nhấn Enter để quay lại...", "white"))


def show_logs() -> None:
    """Hiển thị logs gần đây"""
    print(colored("\n════════════════════════════════════════════════", "cyan"))
    print(colored("📊 LOGS", "yellow"))
    print(colored("════════════════════════════════════════════════", "cyan"))
    print(colored("   📁 Logs được lưu trong thư mục logs/", "white"))
    print(colored("════════════════════════════════════════════════", "cyan"))
    input(colored("Nhấn Enter để quay lại...", "white"))


def run_tests() -> None:
    """Chạy test suite"""
    print(colored("\n════════════════════════════════════════════════", "cyan"))
    print(colored("🧪 TEST SUITE", "yellow"))
    print(colored("════════════════════════════════════════════════", "cyan"))
    print(colored("   📋 Chạy pytest để test các module", "white"))
    print(colored("   💡 Command: python -m pytest tests/ -v", "green"))
    print(colored("════════════════════════════════════════════════", "cyan"))
    input(colored("Nhấn Enter để quay lại...", "white"))


def toggle_debug_mode() -> None:
    """Toggle debug mode"""
    print(colored("\n════════════════════════════════════════════════", "cyan"))
    print(colored("🔧 DEBUG MODE", "yellow"))
    print(colored("════════════════════════════════════════════════", "cyan"))

    current_level = logger._logger.level
    if current_level == 10:  # DEBUG level
        logger.set_level('INFO')
        print(colored("   ✅ Đã tắt debug mode (INFO)", "green"))
    else:
        logger.set_level('DEBUG')
        print(colored("   ✅ Đã bật debug mode (DEBUG)", "green"))

    print(colored("\n════════════════════════════════════════════════", "cyan"))
    input(colored("Nhấn Enter để quay lại...", "white"))


def tiktok_menu(auth_token: str) -> None:
    """Menu TikTok

    Args:
        auth_token: Authorization token
    """
    validator = InputValidator()
    cred_manager = CredentialManager()

    # Load ADB config
    adb_config = load_adb_config()
    saved_open_method = adb_config.get("open_method")
    saved_device = adb_config.get("current_device")

    open_method = "adb"  # Giá trị mặc định
    current_device = None
    adb_manager = None

    # 1. Thử tái sử dụng cấu hình cũ để tăng tốc trải nghiệm
    use_saved = False
    if saved_open_method == "adb" and saved_device:
        print(colored(f"\n[💡] Phát hiện thiết bị ADB đã chọn trước đó: {saved_device}", "cyan"))
        chon_saved = input(colored("👉 Bạn muốn tiếp tục chạy và Auto Click trên thiết bị này? (y/n, Enter là Có): ", "green")).strip().lower()
        if chon_saved in ["y", "yes", ""]:
            use_saved = True
            open_method = "adb"
            current_device = saved_device
            adb_manager = ADBManager()
            adb_manager.selected_device = current_device  # Gán thiết bị đã lưu
            logger.info(f"Tái sử dụng thiết bị ADB đã lưu: {current_device}")
    elif saved_open_method in ["termux", "manual"]:
        method_desc = "Termux" if saved_open_method == "termux" else "Chế độ Thủ công (Bạn tự Click bằng tay)"
        print(colored(f"\n[💡] Phương thức mở link trước đó: {method_desc}", "cyan"))
        chon_saved = input(colored("👉 Bạn muốn tiếp tục giữ nguyên phương thức này? (y/n, Enter là Có): ", "green")).strip().lower()
        if chon_saved in ["y", "yes", ""]:
            use_saved = True
            open_method = saved_open_method
            logger.info(f"Tái sử dụng phương thức: {open_method}")

    # 2. Nếu không dùng lại cấu hình cũ, tiến hành thiết lập mới rõ ràng
    if not use_saved:
        print(colored("════════════════════════════════════════════════", "white"))
        print(colored("📱 Cấu hình Kết nối & Auto Click:", "cyan", bold=True))
        print(colored("   [1] ⭐ Chạy TỰ ĐỘNG: Mở Link & Tự Auto Click (Dùng ADB cho PC/Giả lập)", "white"))
        print(colored("   [2] 📱 Chạy qua Termux: Tự động mở link trên Android (Không Auto Click)", "cyan"))
        print(colored("   [3] ✍️  Chạy Thủ Công: Chỉ hiện Link, bạn TỰ CLICK BẰNG TAY trên điện thoại", "white"))
        print(colored("════════════════════════════════════════════════", "white"))

        while True:
            conn_choice = input(colored("👉 Chọn phương thức kết nối (1-3, Mặc định 1): ", "green")).strip()
            if conn_choice in ["1", ""]:
                open_method = "adb"
                break
            elif conn_choice == "2":
                open_method = "termux"
                break
            elif conn_choice == "3":
                open_method = "manual"
                break
            else:
                print(colored("⚠️ Lựa chọn không hợp lệ, hãy thử lại!", "yellow"))

        if open_method == "adb":
            # Tự khởi tạo ADBManager và cho phép chọn thiết bị
            adb_manager = ADBManager() 
            current_device = adb_manager.select_device()
            if not current_device:
                print(colored("⚠️ Chưa chọn được thiết bị cụ thể! Hệ thống sẽ cố kết nối đến ADB mặc định...", "yellow"))
            
            # Lưu lại cấu hình để dùng nhanh lần sau
            adb_config["open_method"] = "adb"
            adb_config["current_device"] = current_device
            save_adb_config(adb_config)
        else:
            adb_config["open_method"] = open_method
            adb_config["current_device"] = None
            save_adb_config(adb_config)

    # Lấy danh sách acc
    api_client = APIClient(base_url=CONFIG.api_base_url, timeout=CONFIG.api_timeout)
    api_client.set_auth(auth_token)

    try:
        accounts = api_client.get('/api/tiktok-account')
    except Exception as e:
        logger.error(f"Lỗi lấy danh sách tài khoản: {e}")
        print(colored("🚨 Lỗi kết nối API! Hãy kiểm tra lại.", "red"))
        input(colored("Nhấn Enter để quay lại...", "white"))
        return

    if not accounts or accounts.get("status") != 200 or not accounts.get("data"):
        print(colored("🚨 Authorization hoặc T sai hoặc không có tài khoản. Hãy nhập lại!", "red"))
        logger.error("Authorization không hợp lệ hoặc không có tài khoản")
        input(colored("Nhấn Enter để quay lại...", "white"))
        return

    # Hiển thị danh sách acc
    print(colored(f"🚨 Địa chỉ Ip  : 👀{get_public_ip()}👀", "white"))
    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("🆔 Danh sách acc Tik Tok :", "yellow"))
    print(colored("════════════════════════════════════════════════", "white"))
    data = accounts.get("data", [])
    if not isinstance(data, list) or not data:
        print(colored("Không có tài khoản TikTok nào!", "red"))
        input(colored("Nhấn Enter để quay lại...", "white"))
        return
    for idx, acc in enumerate(data, 1):
        print(colored(f"[{idx}] 🆔 : {acc.get('unique_username', 'N/A')} ♦️ : ✅", "cyan"))
    print(colored("════════════════════════════════════════════════", "white"))

    # Chọn acc với validation
    while True:
        idacc = input(colored("☀️ Nhập ID Acc Tiktok Vào: ", "green")).strip()
        idacc = validator.sanitize_string(idacc, 50)
        acc_obj = next((a for a in data if a.get("unique_username") == idacc), None)
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
        print(colored("💥 ✈ Nhập 12 : Kết hợp cả Like và Follow", "yellow"))
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
    if adb_manager is None:
        adb_manager = ADBManager()
    try:
        job_processor = JobProcessorFactory.create(
            open_method,
            adb_manager=adb_manager,
            device_id=current_device
        )
    except ValueError as e:
        logger.error(f"Lỗi tạo job processor: {e}")
        print(colored(f"❌ Lỗi tạo job processor: {e}", "red"))
        input(colored("Nhấn Enter để quay lại...", "white"))
        return

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
            print(colored(f"🚨 Địa chỉ Ip  : 👀{get_public_ip()}👀", "white"))
            print(colored("════════════════════════════════════════════════", "white"))
            print(colored("🆔 Danh sách acc Tik Tok :", "yellow"))
            print(colored("════════════════════════════════════════════════", "white"))
            for idx, acc in enumerate(data, 1):
                print(colored(f"[{idx}] 🆔 : {acc.get('unique_username', 'N/A')} ♦️ : ✅", "cyan"))
            print(colored("════════════════════════════════════════════════", "white"))

            idacc = input(colored("⚡ Job fail đạt giới hạn, nhập acc mới: ", "red")).strip()
            idacc = validator.sanitize_string(idacc, 50)
            acc_obj = next((a for a in data if a.get("unique_username") == idacc), None)
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
        except Exception as e:
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
                except Exception as e:
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
                except Exception as e:
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
                except Exception as e:
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
                        now = datetime.now(tz).strftime("%H:%M:%S") if tz else time.strftime("%H:%M:%S")
                        print(colored(f"| {dem} | {now} | success | {nhantien['data'].get('type', '')} | Ẩn ID | +{tien} | {tong}", "green", bold=True))
                        logger.info(f"Job hoàn thành: {nhantien['data'].get('type')}, +{tien} xu")
                        checkdoiacc = 0
                        break
                    elif lan == 1:
                        print(colored("⚠️ Lần 1 thất bại - Đang thử lần 2...", "yellow"), end="\r")
                    elif lan == 2:
                        break
                except Exception as e:
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
                except Exception as e:
                    logger.error(f"Lỗi báo cáo job fail: {e}")
                time.sleep(1)
                checkdoiacc += 1
        else:
            time.sleep(10)


def facebook_menu(auth_token: str) -> None:
    """Menu Facebook

    Args:
        auth_token: Authorization token
    """
    from golike_core.security import CredentialManager, InputValidator
    from golike_core.api_client import GolikeAPIClient
    from golike_facebook.facebook_client import FacebookJobProcessor

    validator = InputValidator()
    cred_manager = CredentialManager()
    cookie_file = "facebook_cookie.enc"

    # Lưu cookie riêng cho Facebook
    def get_fb_cookie() -> Optional[str]:
        if not os.path.exists(cookie_file):
            return None
        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                encrypted = f.read().strip()
            decrypted = cred_manager._decrypt(encrypted)
            return decrypted if decrypted else None
        except Exception:
            return None

    def save_fb_cookie(cookie: str) -> bool:
        try:
            encrypted = cred_manager._encrypt(cookie)
            with open(cookie_file, 'w', encoding='utf-8') as f:
                f.write(encrypted)
            return True
        except Exception as e:
            print(colored(f"[!] Lỗi lưu cookie: {e}", "red"))
            return False

    # Lấy cookie
    cookie = get_fb_cookie()
    if cookie:
        print(colored("✅ Đã tìm thấy Facebook Cookie lưu sẵn trong hệ thống.", "cyan"))
        change = input(colored("🔄 Bạn có muốn xóa và nhập Cookie FB mới không? (y/N): ", "yellow")).strip().lower()
        if change == 'y':
            cookie = None
            if os.path.exists(cookie_file):
                os.remove(cookie_file)
                print(colored("🗑️ Đã xóa Cookie FB cũ!", "red"))

    while not cookie:
        cookie = input(colored("📢 Nhập Facebook Cookie: ", "green")).strip()
        cookie = validator.sanitize_string(cookie, 1000)
        if not validator.validate_cookie(cookie):
            print(colored("❌ Cookie không hợp lệ!", "red"))
            cookie = ""
            continue
        if cookie:
            if save_fb_cookie(cookie):
                logger.info("Đã lưu Facebook cookie")
                print(colored("✅ Đã lưu cookie an toàn!", "green"))
            else:
                print(colored("❌ Lỗi lưu cookie!", "red"))
                cookie = ""

    # Lấy danh sách account Facebook
    api_client = GolikeAPIClient()
    api_client.set_auth(auth_token)

    try:
        accounts = api_client.get_accounts(provider='facebook')
        logger.debug(f"API Response: {accounts}")
    except Exception as e:
        logger.error(f"Lỗi lấy danh sách account Facebook: {e}")
        print(colored("🚨 Lỗi kết nối API!", "red"))
        input(colored("Nhấn Enter để quay lại...", "white"))
        return

    if not accounts or accounts.get("status") != 200 or not accounts.get("data"):
        print(colored("🚨 Không có tài khoản Facebook nào!", "red"))
        input(colored("Nhấn Enter để quay lại...", "white"))
        return

    # API trả về data lồng nhau: response.data = {data: [...], verify_object_id, link_group}
    raw_data = accounts.get("data", {})
    if isinstance(raw_data, dict):
        data = raw_data.get("data", [])
    elif isinstance(raw_data, list):
        data = raw_data
    else:
        data = []

    # Hiển thị danh sách account
    print(colored("\n🆔 Danh sách account Facebook:", "yellow"))
    print(colored("════════════════════════════════════════════════", "cyan"))
    if not isinstance(data, list) or not data:
        print(colored("Không có tài khoản Facebook nào!", "red"))
        input(colored("Nhấn Enter để quay lại...", "white"))
        return

    for idx, acc in enumerate(data, 1):
        print(colored(f"[{idx}] 🆔: {acc.get('fb_name', 'N/A')} | ID: {acc.get('fb_id', 'N/A')}", "cyan"))
    print(colored("════════════════════════════════════════════════", "cyan"))

    # Chọn account
    while True:
        acc_choice = input(colored("☀️ Nhập số thứ tự account: ", "green")).strip()
        if acc_choice.isdigit() and 1 <= int(acc_choice) <= len(data):
            selected = data[int(acc_choice) - 1]
            fb_id = selected.get('fb_id')
            account_db_id = selected.get('id')
            break
        print(colored("❌ Lựa chọn không hợp lệ!", "red"))

    # Nhập thông số job
    delay = input_int("👀 Nhập thời gian làm job: ")
    while True:
        lannhan = input(colored("🛑 Nhận tiền lần 2 nếu lần 1 fail? (y/n): ", "green")).strip().lower()
        if lannhan in {"y", "n"}:
            break
        print(colored("📢 Nhập sai hãy nhập lại!!!", "red"))
    doiacc = input_int("📆 Số job fail để đổi acc (nhập 1 nếu k muốn dừng): ")
    while True:
        print(colored("════════════════════════════════════════════════", "white"))
        print(colored("♦️ ✈ Nhập 1 : Chỉ nhận nhiệm vụ Like", "yellow"))
        print(colored("🔥 ✈ Nhập 2 : Chỉ nhận nhiệm vụ Like Page", "yellow"))
        print(colored("💥 ✈ Nhập 3 : Chỉ nhận nhiệm vụ Comment", "yellow"))
        print(colored("👍 ✈ Nhập 4 : Chỉ nhận nhiệm vụ Follow", "yellow"))
        print(colored("😊 ✈ Nhập 5 : Chỉ nhận nhiệm vụ Reaction", "yellow"))
        print(colored("🌟 ✈ Nhập 12345 : Kết hợp tất cả", "yellow"))
        print(colored("════════════════════════════════════════════════", "white"))
        chedo = input(colored("✅ Chọn lựa chọn: ", "cyan")).strip()
        if chedo in {"1", "2", "3", "4", "5", "12345"}:
            break
    lam = []
    if "1" in chedo:
        lam.append("like")
    if "2" in chedo:
        lam.append("like_page")
    if "3" in chedo:
        lam.append("comment")
    if "4" in chedo:
        lam.append("follow")
    if "5" in chedo:
        lam.append("reaction")

    # Bắt đầu vòng lặp làm job
    processor = FacebookJobProcessor(api_client, fb_id, cookie, internal_id=account_db_id)
    dem = tong = checkdoiacc = 0
    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("|🆔| ⏱️ ┊ Status | Số Jos | Type | Xu | Tổng", "cyan"))
    print(colored("════════════════════════════════════════════════", "white"))

    while True:
        if checkdoiacc >= doiacc:
            print(colored("🚨 Job fail đạt giới hạn, chọn acc mới!", "red"))
            input(colored("Nhấn Enter để tiếp...", "white"))
            # Hiển thị lại danh sách account
            print(colored("\n🆔 Danh sách account Facebook:", "yellow"))
            print(colored("════════════════════════════════════════════════", "cyan"))
            for idx, acc in enumerate(data, 1):
                print(colored(f"[{idx}] 🆔: {acc.get('fb_name', 'N/A')} | ID: {acc.get('fb_id', 'N/A')}", "cyan"))
            print(colored("════════════════════════════════════════════════", "cyan"))

            acc_choice = input(colored("☀️ Nhập số thứ tự account mới: ", "green")).strip()
            if acc_choice.isdigit() and 1 <= int(acc_choice) <= len(data):
                selected = data[int(acc_choice) - 1]
                fb_id = selected.get('fb_id')
                account_db_id = selected.get('id')
                processor = FacebookJobProcessor(api_client, fb_id, cookie, internal_id=account_db_id)
                checkdoiacc = 0
            else:
                continue

        # Xử lý từng loại job
        for job_type in lam:
            result = processor.process_job(
                job_type=job_type,
                retry_on_fail=(lannhan == "y"),
                max_retries=2
            )

            if result["success"]:
                dem += 1
                tien = result.get("reward", 0)
                tong += tien
                now = time.strftime("%H:%M:%S")
                print(colored(f"| {dem} | {now} | success | {result.get('type', job_type)} | +{tien} | {tong}", "green"))
                checkdoiacc = 0
            else:
                reason = result.get("reason", "unknown")
                if reason == "no_jobs":
                    for i in range(5, 0, -1):
                        print(colored(f"⏳ Hết job tạm thời, tự động tìm lại sau {i} giây...", "yellow"), end="\r")
                        time.sleep(1)
                    print(" " * 60, end="\r") # Xóa dòng chữ đếm ngược đi cho sạch sẽ
                    break
                    
                print(colored(f"| - | - | fail | {job_type} | 0 | {tong}  🚨 Lý do: {reason}", "red"))
                checkdoiacc += 1

        # Đợi trước khi lấy job tiếp
        time.sleep(delay)


def run_facebook_selenium_bot() -> None:
    """Chạy tool GoLike Facebook Selenium (file độc lập)"""
    print(colored("\n════════════════════════════════════════════════", "cyan"))
    print(colored("🚀 KHỞI ĐỘNG TOOL GOLIKE FACEBOOK SELENIUM", "yellow"))
    print(colored("════════════════════════════════════════════════", "cyan"))
    print(colored("Tool Facebook Selenium đang khởi động trong cửa sổ mới...", "white"))
    
    try:
        # Khởi chạy file golikefb_sele.py bằng trình thông dịch hiện tại
        result = subprocess.run([sys.executable, "golikefb_sele.py"])
        if result.returncode != 0:
            logger.error(f"Golikefb_sele.py đã thoát với mã lỗi: {result.returncode}")
    except KeyboardInterrupt:
        print(colored("\n👋 Đã đóng Tool Facebook Selenium.", "yellow"))
    except Exception as e:
        logger.error(f"Lỗi khi chạy golikefb_sele.py: {e}")
        print(colored(f"❌ Đã xảy ra lỗi: {e}", "red"))
    
    print(colored("\n════════════════════════════════════════════════", "cyan"))
    input(colored("Nhấn Enter để quay lại...", "white"))


def main() -> None:
    """Main function"""
    validator = InputValidator()
    cred_manager = CredentialManager()

    # Tự động kiểm tra cập nhật khi mở tool
    check_for_updates()
    
    logger.info("Khởi động ứng dụng...")

    while True:
        menu()
        choose = input(colored("🥇 Nhập Lựa Chọn (0-9): ", "white")).strip()

        if choose == "0":
            print(colored("👋 Tạm biệt!", "green"))
            break
        elif choose == "3":
            # Facebook Selenium
            run_facebook_selenium_bot()
        elif choose == "4":
            # ADB WiFi Manager Menu mới
            adb_menu()
            continue
        elif choose == "5":
            if cred_manager.clear_auth():
                # Xóa cả Facebook cookie
                cookie_file = "facebook_cookie.enc"
                if os.path.exists(cookie_file):
                    try:
                        os.remove(cookie_file)
                    except Exception:
                        pass
                print(colored(f"[✔] Đã xóa credential!", "green"))
            else:
                print(colored(f"[!] Không thể xóa credential!", "red"))
            continue
        elif choose == "6":
            show_security_config()
            continue
        elif choose == "7":
            show_logs()
            continue
        elif choose == "8":
            run_tests()
            continue
        elif choose == "9":
            toggle_debug_mode()
            continue
        elif choose == "1":
            # TikTok
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
            tiktok_menu(auth)
        elif choose == "2":
            # Facebook
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
            facebook_menu(auth)
        else:
            print(colored("❌ Lựa chọn không hợp lệ!", "red"))


if __name__ == "__main__":
    main()
