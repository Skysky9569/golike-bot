"""
Console UI helpers for Golike application
colored output, input helpers, banner, menu.
"""
import os
import json
import time
from typing import Optional

from golike_core.logging import logger
from golike_core.adb_manager import colored
from golike_core.termux import get_platform_name


def _load_version() -> str:
    """Doc phien ban tu version.json, fallback hardcoded neu file loi/thieu"""
    try:
        _vfile = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "version.json")
        with open(_vfile, "r", encoding="utf-8") as _f:
            return json.load(_f).get("version", "1.5.5")
    except (json.JSONDecodeError, IOError):
        return "1.5.5"


CURRENT_VERSION = _load_version()


def input_int(prompt: str, color: str = "green", minval: int = 1, maxval: Optional[int] = None) -> int:
    """Helper de input so nguyen

    Args:
        prompt: Noi dung prompt
        color: Mau cua text
        minval: Gia tri toi thieu
        maxval: Gia tri toi da

    Returns:
        int: So nguyen nguoi dung nhap
    """
    while True:
        try:
            val = int(input(colored(prompt, color)).strip())
            if val < minval:
                logger.warning(f"Giá trị phải >= {minval}!")
                continue
            if maxval is not None and val > maxval:
                logger.warning(f"Giá trị phải <= {maxval}!")
                continue
            return val
        except ValueError:
            logger.warning("Vui lòng nhập số nguyên!")


def get_public_ip() -> str:
    """Lay dia chi IP cong cong hien tai"""
    import requests
    try:
        response = requests.get("https://api.ipify.org", timeout=5)
        if response.status_code == 200:
            return response.text.strip()
    except requests.RequestException:
        logger.debug("Không thể lấy IP từ ipify.org")
    try:
        response = requests.get("https://ifconfig.me/ip", timeout=5)
        if response.status_code == 200:
            return response.text.strip()
    except requests.RequestException:
        logger.debug("Không thể lấy IP từ ifconfig.me")
    return "Không xác định"


def check_for_updates():
    """Uy thac toan bo quy trinh kiem tra cap nhat sang Module updater.py"""
    try:
        import updater
        updater.run_version_check(CURRENT_VERSION)
    except Exception:
        logger.warning("Hệ thống Updater gặp lỗi kỹ thuật, bỏ qua bước kiểm tra phiên bản.")


def banner():
    """Hien thi banner"""
    os.system("clear" if os.name == "posix" else "cls")
    try:
        _vfile = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "version.json")
        with open(_vfile, "r", encoding="utf-8") as _f:
            _vdata = json.load(_f)
        _changelog = _vdata.get("changelog", "Tự động kiểm tra và tải file còn thiếu từ GitHub")
    except (json.JSONDecodeError, IOError):
        _changelog = "Tự động kiểm tra và tải file còn thiếu từ GitHub"

    banner_text = f"""
{colored(':)', 'yellow')}
{colored('========================================', 'white')}
{colored('Tool By Dome: Golike v' + CURRENT_VERSION, 'cyan', bold=True)}
{colored('========================================', 'white')}
{colored('⚠️  Lưu ý    : Tool Sử Dụng Cho Android/PC', 'white')}
{colored('🔐 Bảo mật  : Credential đã mã hóa, Input validated', 'green')}
{colored('🔄 Cập nhật : ' + _changelog, 'green')}
{colored('🏗️  Cấu trúc : Thiết kế dạng Module chuyên nghiệp', 'green')}
{colored('========================================', 'white')}
"""
    print(banner_text)


def menu() -> None:
    """Menu chinh hien thi danh sach chuc nang"""
    banner()
    print(colored(f"🆔 Địa chỉ IP  : 🚨 {get_public_ip()} 🚨", "white"))
    print(colored(f"💻 Hệ điều hành : 🍏 {get_platform_name()}", "white"))
    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("⚡ CHỨC NĂNG CHÍNH:", "cyan", bold=True))
    print(colored("   [1] 🥇 Vào Tool TikTok (Auto ADB)", "white"))
    print(colored("   [2] 📱 Vào Tool Facebook (API Chạy Ngầm - Tốc độ)", "cyan"))
    print(colored("   [3] 🔥 Vào Tool Facebook (Selenium - An Toàn/DOM)", "yellow"))
    print(colored("   [7] 🍏 Vào Tool TikTok (iOS - Appium)", "green"))
    print(colored("   [9] 🛠️  Quick FB Interaction (DOM Tool)", "magenta"))
    print(colored("\n🛠️  HỆ THỐNG & CẤU HÌNH:", "cyan", bold=True))
    print(colored("   [4] 📶 Cài Đặt Kết Nối ADB WiFi/USB", "cyan"))
    print(colored("   [5] 🥈 Quản Lý Authorization Tokens", "green"))
    print(colored("   [6] 🖥️ Tool Facebook Desktop (Cookie + facebook.com)", "magenta"))
    print(colored("   [8] 🧹 Dọn dẹp Chrome & Driver (Tối ưu hệ thống)", "yellow"))
    print(colored("   [0] 🔙 Thoát Chương Trình", "white"))
    print(colored("════════════════════════════════════════════════", "white"))