"""
System info panels: security config, logs, tests, debug mode.
"""
import os

from golike_core.logging import logger
from golike_core.config import CONFIG
from golike_core.adb_manager import colored


def show_security_config() -> None:
    """Hien thi cau hinh bao mat"""
    from golike_core.security import CredentialManager

    print(colored("\n════════════════════════════════════════════════", "cyan"))
    print(colored("🔐 CAU HINH BAO MAT", "yellow"))
    print(colored("════════════════════════════════════════════════", "cyan"))

    print(colored("\n📁 Credential Storage:", "white"))
    cred_manager = CredentialManager()
    if os.path.exists(cred_manager.credential_file):
        print(colored("   ✅ Credential file ton tai (da ma hoa)", "green"))
        print(colored(f"   📄 File: {cred_manager.credential_file}", "white"))
    else:
        print(colored("   ❌ Chua co credential", "yellow"))

    cookie_file = "facebook_cookie.enc"
    if os.path.exists(cookie_file):
        print(colored("   ✅ Facebook cookie ton tai (da ma hoa)", "green"))
        print(colored(f"   📄 File: {cookie_file}", "white"))
    else:
        print(colored("   ❌ Chua co Facebook cookie", "yellow"))

    session_file = "tiktok_session.enc"
    if os.path.exists(session_file):
        print(colored("   ✅ TikTok session ton tai (da ma hoa)", "green"))
        print(colored(f"   📄 File: {session_file}", "white"))
    else:
        print(colored("   ❌ Chua co TikTok session", "yellow"))

    print(colored("\n⚙️  Application Config:", "white"))
    print(colored(f"   📂 ADB Path: {CONFIG.adb_path}", "white"))
    print(colored(f"   🌐 API Base URL: {CONFIG.api_base_url}", "white"))
    print(colored(f"   ⏱️  API Timeout: {CONFIG.api_timeout}s", "white"))
    print(colored(f"   📊 Log Level: {CONFIG.log_level}", "white"))
    print(colored(f"   🔄 Max Retry: {CONFIG.max_retry}", "white"))
    print(colored(f"   📶 WiFi Port: {CONFIG.wifi_port}", "white"))

    print(colored("\n════════════════════════════════════════════════", "cyan"))
    input(colored("Nhan Enter de quay lai...", "white"))


def show_logs() -> None:
    """Hien thi logs gan day"""
    print(colored("\n════════════════════════════════════════════════", "cyan"))
    print(colored("📊 LOGS", "yellow"))
    print(colored("════════════════════════════════════════════════", "cyan"))
    print(colored("   📁 Logs duoc luu trong thu muc logs/", "white"))
    print(colored("════════════════════════════════════════════════", "cyan"))
    input(colored("Nhan Enter de quay lai...", "white"))


def run_tests() -> None:
    """Chay test suite"""
    print(colored("\n════════════════════════════════════════════════", "cyan"))
    print(colored("🧪 TEST SUITE", "yellow"))
    print(colored("════════════════════════════════════════════════", "cyan"))
    print(colored("   📋 Chay pytest de test cac module", "white"))
    print(colored("   💡 Command: python -m pytest tests/ -v", "green"))
    print(colored("════════════════════════════════════════════════", "cyan"))
    input(colored("Nhan Enter de quay lai...", "white"))


def toggle_debug_mode() -> None:
    """Toggle debug mode"""
    print(colored("\n════════════════════════════════════════════════", "cyan"))
    print(colored("🔧 DEBUG MODE", "yellow"))
    print(colored("════════════════════════════════════════════════", "cyan"))

    current_level = logger._logger.level
    if current_level == 10:
        logger.set_level('INFO')
        print(colored("   ✅ Da tat debug mode (INFO)", "green"))
    else:
        logger.set_level('DEBUG')
        print(colored("   ✅ Da bat debug mode (DEBUG)", "green"))

    print(colored("\n════════════════════════════════════════════════", "cyan"))
    input(colored("Nhan Enter de quay lai...", "white"))