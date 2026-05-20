"""
Main menu for GoLike application
Supports both TikTok and Facebook platforms
Termux/Android compatible
"""
import os
import sys
import subprocess

# ============================================================================
# TERMUX/ANDROID COMPATIBILITY
# ============================================================================
from golike_core.termux import init_termux, get_adb_path, is_termux, fix_encoding

# Initialize encoding and Termux environment
fix_encoding()
init_termux()

# ============================================================================
# PRE-FLIGHT BOOTSTRAP
# ============================================================================

from boot.bootstrap import run_bootstrap, bootstrap_updater, check_and_download_missing_files

# Kiem tra --skip-bootstrap flag
skip_bootstrap = "--skip-bootstrap" in sys.argv

try:
    run_bootstrap(skip_download=skip_bootstrap)

    if not skip_bootstrap:
        import updater
        updater.ensure_system_complete()
except Exception as e:
    print(f"\033[1;31m[!] Loi trong qua trinh khoi tao: {e}\033[0m")

# ============================================================================
# ADB PATH SETUP
# ============================================================================

# Termux: Use termux ADB path
if is_termux():
    adb_path = get_adb_path()
    if adb_path and os.path.exists(adb_path):
        os.environ["PATH"] = os.path.dirname(adb_path) + os.pathsep + os.environ["PATH"]
else:
    # Non-Termux (Windows/Linux): Use local ADB folder
    local_adb_dir = os.path.join(os.getcwd(), "ADB")
    if os.path.exists(local_adb_dir):
        os.environ["PATH"] = local_adb_dir + os.pathsep + os.environ["PATH"]

    # Default workspace ADB (Windows path - Termux users will have their own)
    default_workspace_adb = r"D:\pythonadb\ADB"
    if os.path.exists(default_workspace_adb) and default_workspace_adb not in os.environ["PATH"]:
        os.environ["PATH"] = default_workspace_adb + os.pathsep + os.environ["PATH"]

# ============================================================================
# IMPORTS
# ============================================================================

from golike_core.logging import logger
from golike_core.security import CredentialManager, InputValidator
from golike_core.adb_manager import colored

from ui.console import menu, banner, check_for_updates, CURRENT_VERSION
from ui.adb_menu import adb_menu
from ui.system_panels import show_security_config, show_logs, run_tests, toggle_debug_mode
from ui.tiktok_flow import tiktok_menu
from ui.facebook_flow import facebook_menu


def run_facebook_selenium_bot() -> None:
    """Chay tool GoLike Facebook Selenium (ho tro API + DOM Click mode)"""
    print(colored("\n════════════════════════════════════════════════", "cyan"))
    print(colored("🚀 KHOI DONG TOOL GOLIKE FACEBOOK SELENIUM", "yellow"))
    print(colored("════════════════════════════════════════════════", "cyan"))
    print(colored("Tool Facebook Selenium dang khoi dong...", "white"))
    print(colored("  - API mode: Dung FB_WEB_API_FIXED.py goi Facebook API", "white"))
    print(colored("  - DOM mode: Click truc tiep tren m.facebook.com qua Selenium", "white"))

    try:
        result = subprocess.run([sys.executable, "golikefb_sele.py"])
        if result.returncode != 0:
            logger.error(f"Golikefb_sele.py da thoat voi ma loi: {result.returncode}")
    except KeyboardInterrupt:
        print(colored("\n👋 Da dong Tool Facebook Selenium.", "yellow"))
    except Exception as e:
        logger.error(f"Loi khi chay golikefb_sele.py: {e}")
        print(colored(f"❌ Da xay ra loi: {e}", "red"))

    print(colored("\n════════════════════════════════════════════════", "cyan"))
    input(colored("Nhan Enter de quay lai...", "white"))


def main() -> None:
    """Main function"""
    validator = InputValidator()
    cred_manager = CredentialManager()

    check_for_updates()
    logger.info("Khoi dong ung dung...")

    while True:
        menu()
        choose = input(colored("🥇 Nhap Lua Chon (0-9): ", "white")).strip()

        if choose == "0":
            print(colored("👋 Tam biet!", "green"))
            break
        elif choose == "3":
            run_facebook_selenium_bot()
        elif choose == "4":
            adb_menu()
            continue
        elif choose == "5":
            if cred_manager.clear_auth():
                cookie_file = "facebook_cookie.enc"
                if os.path.exists(cookie_file):
                    try:
                        os.remove(cookie_file)
                    except OSError:
                        pass
                print(colored("[✔] Da xoa credential!", "green"))
            else:
                print(colored("[!] Khong the xoa credential!", "red"))
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
            auth = cred_manager.get_auth()
            while not auth:
                auth = input(colored("📢 Nhap Authorization: ", "green")).strip()
                auth = validator.sanitize_string(auth, 500)
                if not validator.validate_auth_token(auth):
                    logger.warning("Token khong hop le! Phai tu 10-500 ky tu")
                    auth = ""
                    continue
                if auth:
                    if cred_manager.save_auth(auth):
                        logger.info("Da luu authorization token")
                        print(colored("✅ Da luu token an toan!", "green"))
                    else:
                        logger.error("Loi luu token!")
                        auth = ""
            tiktok_menu(auth)
        elif choose == "2":
            auth = cred_manager.get_auth()
            while not auth:
                auth = input(colored("📢 Nhap Authorization: ", "green")).strip()
                auth = validator.sanitize_string(auth, 500)
                if not validator.validate_auth_token(auth):
                    logger.warning("Token khong hop le! Phai tu 10-500 ky tu")
                    auth = ""
                    continue
                if auth:
                    if cred_manager.save_auth(auth):
                        logger.info("Da luu authorization token")
                        print(colored("✅ Da luu token an toan!", "green"))
                    else:
                        logger.error("Loi luu token!")
                        auth = ""
            facebook_menu(auth)
        else:
            logger.warning("Lua chon khong hop le!")


if __name__ == "__main__":
    main()