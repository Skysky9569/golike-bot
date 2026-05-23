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
try:
    from golike_core.termux import init_termux, get_adb_path, is_termux, fix_encoding
    from boot.bootstrap import run_bootstrap, bootstrap_updater, check_and_download_missing_files
except ImportError:
    print("\033[1;31m" + "=" * 60 + "\033[0m")
    print("\033[1;31m[!] THIẾU FILE HỆ THỐNG QUAN TRỌNG (GOLIKE_CORE / BOOT)!\033[0m")
    print("\033[1;33m[!] Điều này thường xảy ra khi quá trình cập nhật bị gián đoạn hoặc bị lỗi.\033[0m")
    print("\033[1;32m[👉] CÁCH KHẮC PHỤC: Hãy chạy lệnh sau để tự động tải bù các file còn thiếu:\033[0m")
    print("\n\033[1;36m      python updater.py\033[0m\n")
    print("\033[1;31m" + "=" * 60 + "\033[0m")
    sys.exit(1)

# Initialize encoding and Termux environment
fix_encoding()
init_termux()

# Kiem tra --skip-bootstrap flag
skip_bootstrap = "--skip-bootstrap" in sys.argv

# ============================================================================
# SYSTEM INTEGRITY CHECK - Dam bao du file truoc khi vao tool
# ============================================================================

try:
    run_bootstrap(skip_download=skip_bootstrap)

    if not skip_bootstrap:
        import updater
        if not updater.ensure_system_complete():
            print("\033[1;31m" + "=" * 60 + "\033[0m")
            print("\033[1;31m[!] THIEU FILE HE THONG QUAN TRONG!\033[0m")
            print("\033[1;31m[!] Khong the tu dong tai ve. Vui long kiem tra lai.\033[0m")
            print("\033[1;33m[!] Thu chay: python main.py --skip-bootstrap\033[0m")
            print("\033[1;33m[!] Hoac clone lai tu GitHub:\033[0m")
            print("\033[1;33m    git clone https://github.com/skysky9569/golike-bot.git\033[0m")
            print("\033[1;31m" + "=" * 60 + "\033[0m")
            sys.exit(1)
except KeyboardInterrupt:
    print("\n\033[1;33m[!] Da huy qua trinh khoi tao.\033[0m")
    sys.exit(0)
except Exception as e:
    print(f"\033[1;31m" + "=" * 60 + "\033[0m")
    print(f"\033[1;31m[!] LOI KHOI TAO HE THONG: {e}\033[0m")
    print(f"\033[1;31m" + "=" * 60 + "\033[0m")
    print(f"\033[1;33m[!] Thu chay: python main.py --skip-bootstrap\033[0m")
    sys.exit(1)

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


def auth_manager_menu() -> None:
    """Menu untuk quản lý các authorization token"""
    cred_manager = CredentialManager()
    validator = InputValidator()

    while True:
        print(colored("\n════════════════════════════════════════════════", "cyan"))
        print(colored("🔐 QUẢN LÝ AUTHORIZATION TOKENS", "yellow"))
        print(colored("════════════════════════════════════════════════", "cyan"))

        tokens = cred_manager.get_auth_labels()
        if tokens:
            print(colored("Danh sách token hiện có:", "white"))
            for i, label in enumerate(tokens, 1):
                token = cred_manager.get_auth_by_label(label)
                if token and len(token) > 14:
                    masked = token[:10] + "..." + token[-4:]
                else:
                    masked = token
                print(f"  [{i}] {label} ({masked})")
        else:
            print(colored("Chưa có token nào được lưu trữ.", "yellow"))

        print(colored("\nLựa chọn:", "white"))
        print(colored("   [1] ➕ Thêm token mới", "green"))
        print(colored("   [0] 🔙 Quay lại menu chính", "white"))
        print(colored("════════════════════════════════════════════════", "cyan"))

        choice = input(colored("Nhap lua chon: ", "white")).strip()

        if choice == "0":
            break
        elif choice == "1":
            # Thêm token mới
            label = input(colored("Nhap nhan cho token moi: ", "green")).strip()
            while not label:
                label = input(colored("Nhan khong duoc de trong. Nhap lai: ", "green")).strip()

            token = input(colored("Nhap authorization token: ", "green")).strip()
            while not validator.validate_auth_token(token):
                print(colored("Token khong hop le! Phai tu 10-500 ky tu", "red"))
                token = input(colored("Nhap lai authorization token: ", "green")).strip()

            if cred_manager.save_auth(label, token):
                print(colored(f"[✔] Da luu token voi nhan '{label}'!", "green"))
            else:
                print(colored("[!] Luu token that bai!", "red"))
        else:
            print(colored("Lua chon khong hop le!", "yellow"))


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
            # Thay đổi tùy chọn 5 thành Quản lý authorization tokens
            auth_manager_menu()
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
            # TikTok menu
            if not cred_manager.has_any_token():
                # Chưa có token nào, yêu cầu nhập ngay tại chỗ
                label = input(colored("Nhap nhan cho token moi: ", "green")).strip()
                while not label:
                    label = input(colored("Nhan khong duoc de trong. Nhap lai: ", "green")).strip()
                token = input(colored("Nhap authorization token: ", "green")).strip()
                while not validator.validate_auth_token(token):
                    print(colored("Token khong hop le! Phai tu 10-500 ky tu", "red"))
                    token = input(colored("Nhap lai authorization token: ", "green")).strip()
                cred_manager.save_auth(label, token)
                auth_token = token
                print(colored(f"[✔] Da luu token voi nhan '{label}' va dang su dung!", "green"))
            else:
                labels = cred_manager.get_auth_labels()
                if len(labels) == 1:
                    auth_token = cred_manager.get_auth_by_label(labels[0])
                else:
                    # Nhiều token, yêu cầu chọn
                    print(colored("\nChon token de su dung cho TikTok:", "cyan"))
                    for i, label in enumerate(labels, 1):
                        token = cred_manager.get_auth_by_label(label)
                        if token and len(token) > 14:
                            masked = token[:10] + "..." + token[-4:]
                        else:
                            masked = token
                        print(f"  [{i}] {label} ({masked})")
                    choice_idx = input_int("Nhap lua chon: ", minval=1, maxval=len(labels))
                    auth_token = cred_manager.get_auth_by_label(labels[choice_idx-1])
            tiktok_menu(auth_token)
        elif choose == "2":
            # Facebook menu
            if not cred_manager.has_any_token():
                # Chưa có token nào, yêu cầu nhập ngay tại chỗ
                label = input(colored("Nhap nhan cho token moi: ", "green")).strip()
                while not label:
                    label = input(colored("Nhan khong duoc de trong. Nhap lai: ", "green")).strip()
                token = input(colored("Nhap authorization token: ", "green")).strip()
                while not validator.validate_auth_token(token):
                    print(colored("Token khong hop le! Phai tu 10-500 ky tu", "red"))
                    token = input(colored("Nhap lai authorization token: ", "green")).strip()
                cred_manager.save_auth(label, token)
                auth_token = token
                print(colored(f"[✔] Da luu token voi nhan '{label}' va dang su dung!", "green"))
            else:
                labels = cred_manager.get_auth_labels()
                if len(labels) == 1:
                    auth_token = cred_manager.get_auth_by_label(labels[0])
                else:
                    # Nhiều token, yêu cầu chọn
                    print(colored("\nChon token de su dung cho Facebook:", "cyan"))
                    for i, label in enumerate(labels, 1):
                        token = cred_manager.get_auth_by_label(label)
                        if token and len(token) > 14:
                            masked = token[:10] + "..." + token[-4:]
                        else:
                            masked = token
                        print(f"  [{i}] {label} ({masked})")
                    choice_idx = input_int("Nhap lua chon: ", minval=1, maxval=len(labels))
                    auth_token = cred_manager.get_auth_by_label(labels[choice_idx-1])
            facebook_menu(auth_token)
        else:
            logger.warning("Lua chon khong hop le!")


if __name__ == "__main__":
    main()