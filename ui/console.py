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


def _load_version() -> str:
    """Doc phien ban tu version.json, fallback hardcoded neu file loi/thieu"""
    try:
        _vfile = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "version.json")
        with open(_vfile, "r", encoding="utf-8") as _f:
            return json.load(_f).get("version", "1.5.5")
    except (json.JSONDecodeError, IOError):
        return "1.5.5"


CURRENT_VERSION = _load_version()


def input_int(prompt: str, color: str = "green", minval: int = 1) -> int:
    """Helper de input so nguyen

    Args:
        prompt: Noi dung prompt
        color: Mau cua text
        minval: Gia tri toi thieu

    Returns:
        int: So nguyen nguoi dung nhap
    """
    while True:
        try:
            val = int(input(colored(prompt, color)).strip())
            if val >= minval:
                return val
            logger.warning(f"Gia tri phai >= {minval}!")
        except ValueError:
            logger.warning("Vui long nhap so nguyen!")


def get_public_ip() -> str:
    """Lay dia chi IP cong cong hien tai"""
    import requests
    try:
        response = requests.get("https://api.ipify.org", timeout=5)
        if response.status_code == 200:
            return response.text.strip()
    except requests.RequestException:
        logger.debug("Khong the lay IP tu ipify.org")
    try:
        response = requests.get("https://ifconfig.me/ip", timeout=5)
        if response.status_code == 200:
            return response.text.strip()
    except requests.RequestException:
        logger.debug("Khong the lay IP tu ifconfig.me")
    return "Khong xac dinh"


def check_for_updates():
    """Uy thac toan bo quy trinh kiem tra cap nhat sang Module updater.py"""
    try:
        import updater
        updater.run_version_check(CURRENT_VERSION)
    except Exception:
        logger.warning("He thong Updater gap loi ky thuat, bo qua buoc check version.")


def banner():
    """Hien thi banner"""
    os.system("clear" if os.name == "posix" else "cls")
    try:
        _vfile = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "version.json")
        with open(_vfile, "r", encoding="utf-8") as _f:
            _vdata = json.load(_f)
        _changelog = _vdata.get("changelog", "Tu dong kiem tra va tai file con thieu tu GitHub")
    except (json.JSONDecodeError, IOError):
        _changelog = "Tu dong kiem tra va tai file con thieu tu GitHub"

    banner_text = f"""
{colored(':)', 'yellow')}
{colored('========================================', 'white')}
{colored('Tool By Dome: Golike v' + CURRENT_VERSION, 'cyan', bold=True)}
{colored('========================================', 'white')}
{colored('⚠️  Luu y    : Tool Su Dung Cho Android/PC', 'white')}
{colored('🔐 Bao mat  : Credential da ma hoa, Input validated', 'green')}
{colored('🔄 Cap nhat : ' + _changelog, 'green')}
{colored('🏗️  Code Org : Cau truc Modular chuyen nghiep', 'green')}
{colored('========================================', 'white')}
"""
    print(banner_text)


def menu() -> None:
    """Menu chinh hien thi danh sach chuc nang"""
    banner()
    print(colored(f"🆔 Dia chi Ip  : 🚨 {get_public_ip()} 🚨", "white"))
    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("⚡ CHUC NANG CHINH:", "cyan", bold=True))
    print(colored("   [1] 🥇 Vao Tool TikTok (Auto ADB)", "white"))
    print(colored("   [2] 📱 Vao Tool Facebook (API)", "cyan"))
    print(colored("   [3] 🔥 Vao Tool Facebook (Selenium - API + DOM Click)", "yellow"))
    print(colored("\n🛠️  HE THONG & CAU HINH:", "cyan", bold=True))
    print(colored("   [4] 📶 Cai Dat Ket Noi ADB WiFi/USB", "cyan"))
    print(colored("   [5] 🥈 Xoa Authorization Hien Tai", "red"))
    print(colored("   [6] ⚙️  Xem Cau Hinh Bao Mat", "green"))
    print(colored("   [7] 📊 Xem He Thong Logs", "white"))
    print(colored("   [8] 🧪 Chay Bo Thu Nghiem (Tests)", "magenta"))
    print(colored("   [9] 🔧 Bat/Tat Debug Mode", "blue"))
    print(colored("   [0] 🔙 Thoat Chuong Trinh", "white"))
    print(colored("════════════════════════════════════════════════", "white"))