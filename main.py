"""
Main menu for GoLike application
Supports both TikTok and Facebook platforms
Termux/Android compatible
"""
import os
import sys
from typing import Optional

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
    print("\n\033[1;36m      python updater.py --repair\033[0m\n")
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
            print("\033[1;31m[!] THIẾU FILE HỆ THỐNG QUAN TRỌNG!\033[0m")
            print("\033[1;31m[!] Không thể tự động tải về. Vui lòng kiểm tra lại.\033[0m")
            print("\033[1;33m[!] Thử chạy: python main.py --skip-bootstrap\033[0m")
            print("\033[1;33m[!] Hoặc clone lại từ GitHub:\033[0m")
            print("\033[1;33m    git clone https://github.com/skysky9569/golike-bot.git\033[0m")
            print("\033[1;31m" + "=" * 60 + "\033[0m")
            sys.exit(1)
except KeyboardInterrupt:
    print("\n\033[1;33m[!] Đã hủy quá trình khởi tạo.\033[0m")
    sys.exit(0)
except Exception as e:
    print(f"\033[1;31m" + "=" * 60 + "\033[0m")
    print(f"\033[1;31m[!] LỖI KHỞI TẠO HỆ THỐNG: {e}\033[0m")
    print(f"\033[1;31m" + "=" * 60 + "\033[0m")
    print(f"\033[1;33m[!] Thử chạy: python main.py --skip-bootstrap\033[0m")
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

from ui.console import menu, banner, check_for_updates, CURRENT_VERSION, input_int
from ui.adb_menu import adb_menu
from ui.tiktok_flow import tiktok_menu
try:
    from ui.ios_flow import ios_tiktok_menu
    HAS_IOS_FLOW = True
except ImportError:
    HAS_IOS_FLOW = False
    ios_tiktok_menu = None
from ui.facebook_flow import facebook_menu

try:
    from golikefb_sele_desktop import sele_desktop_menu as fb_desktop_menu
    HAS_DESKTOP_SELE = True
except ImportError:
    HAS_DESKTOP_SELE = False
    fb_desktop_menu = None


def run_facebook_selenium_bot() -> None:
    """Chạy tool GoLike Facebook Selenium (hỗ trợ API + DOM Click mode) - Import trực tiếp thay vì subprocess."""
    print(colored("\n════════════════════════════════════════════════", "cyan"))
    print(colored("🚀 KHỞI ĐỘNG TOOL GOLIKE FACEBOOK SELENIUM", "yellow"))
    print(colored("════════════════════════════════════════════════", "cyan"))

    try:
        # Import golikefb_sele as module directly so sys.exit() works properly
        import importlib
        import golikefb_sele
        golikefb_sele.sele_menu()
    except SystemExit:
        # User chose 'exit' - propagate to exit main program
        raise
    except KeyboardInterrupt:
        print(colored("\n👋 Đã đóng Tool Facebook Selenium.", "yellow"))
    except Exception as e:
        logger.error(f"Lỗi khi chạy golikefb_sele.py: {e}")
        print(colored(f"❌ Đã xảy ra lỗi: {e}", "red"))
        input(colored("Nhấn Enter để quay lại...", "white"))

def run_quick_dom_tool() -> None:
    """Chạy module DOM Handler chính thức dưới dạng công cụ tương tác nhanh."""
    try:
        from golike_facebook.dom_handler import standalone_cli
        standalone_cli()
        input(colored("\nNhấn Enter để quay lại...", "white"))
    except Exception as e:
        print(colored(f"❌ Lỗi: {e}", "red"))
        input(colored("Nhấn Enter để quay lại...", "white"))


def prompt_and_save_token(cred_manager: CredentialManager, validator: InputValidator, label: Optional[str] = None) -> Optional[str]:
    """Hỏi thông tin token, g-auth, g-device-id và lưu lại. Trả về giá trị đã lưu dưới dạng JSON (nếu có g-auth) hoặc raw string."""
    from typing import Optional
    import uuid
    import json

    if not label:
        label = input(colored("Nhập nhãn cho token mới: ", "green")).strip()
        while not label:
            label = input(colored("Nhãn không được để trống. Nhập lại: ", "green")).strip()

    token = input(colored("Nhập authorization token: ", "green")).strip()
    while not validator.validate_auth_token(token):
        print(colored("Token không hợp lệ! Phải từ 10-500 ký tự", "red"))
        token = input(colored("Nhập lại authorization token: ", "green")).strip()

    g_auth = input(colored("Nhập g-auth token (Bắt buộc cho TikTok mới, hoặc ấn Enter để bỏ qua): ", "green")).strip() or None
    g_device_id = input(colored("Nhập g-device-id (Ấn Enter để tự động sinh UUID): ", "green")).strip() or None

    if g_auth and not g_device_id:
        g_device_id = str(uuid.uuid4())
        print(colored(f"💡 Tự động tạo g-device-id: {g_device_id}", "cyan"))

    # Chọn cơ chế token 't'
    print(colored("\n⚙️ CHỌN PHƯƠNG THỨC TẠO TOKEN 't' (TRÁNH LỖI 403 VERSION):", "cyan"))
    print(colored("  [1] Tự động sinh động theo thời gian hệ thống (Mặc định - Khuyên dùng)", "white"))
    print(colored("  [2] Sử dụng token tĩnh mặc định (VFZSak5FMUVRVFZQUkVrMVRYYzlQUT09)", "white"))
    print(colored("  [3] Nhập token 't' thủ công từ trình duyệt DevTools", "white"))

    choice = input(colored("Lựa chọn của bạn (1/2/3, mặc định 1): ", "green")).strip()

    if choice == "2":
        # Generate a fresh dynamic token instead of using a stale static one
        import time
        import base64
        t_val = str(int(time.time()))
        for _ in range(3):
            t_val = base64.b64encode(t_val.encode('utf-8')).decode('utf-8')
        t_token = t_val
        print(colored("✅ Đã tạo token 't' động mới cho bạn.", "green"))
    elif choice == "3":
        print(colored("💡 Hướng dẫn: Mở app.golike.net -> F12 -> Network -> bắt request đến gateway.golike.net -> copy giá trị header 't'", "cyan"))
        t_token = input(colored("Nhập token 't' thủ công: ", "green")).strip()
        while not t_token:
            t_token = input(colored("Token không được để trống. Nhập lại: ", "green")).strip()
        print(colored("✅ Đã ghi nhận token tĩnh thủ công.", "green"))
    else:
        t_token = None
        print(colored("✅ Đã chọn tự động sinh động theo thời gian hệ thống (Mặc định).", "green"))

    if cred_manager.save_auth(label, token, g_auth, g_device_id, t_token):
        print(colored(f"[✔] Đã lưu token với nhãn '{label}'!", "green"))
        if g_auth:
            return json.dumps({
                "authorization": token,
                "g-auth": g_auth,
                "g-device-id": g_device_id,
                "t": t_token
            })
        return token
    else:
        print(colored("[!] Lưu token thất bại!", "red"))
        return None


def auth_manager_menu() -> None:
    """Menu quản lý các authorization token"""
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
                # Check if it is a JSON with headers
                try:
                    import json
                    token_data = json.loads(token)
                    if isinstance(token_data, dict):
                        token = token_data.get("authorization", "")
                except Exception:
                    pass

                if token and len(token) > 14:
                    masked = token[:10] + "..." + token[-4:]
                else:
                    masked = token
                print(f"  [{i}] {label} ({masked})")
        else:
            print(colored("Chưa có token nào được lưu trữ.", "yellow"))

        print(colored("\nLựa chọn:", "white"))
        print(colored("   [1] ➕ Thêm token mới", "green"))
        print(colored("   [2] ❌ Xóa token", "red"))
        print(colored("   [0] 🔙 Quay lại menu chính", "white"))
        print(colored("════════════════════════════════════════════════", "cyan"))

        choice = input(colored("Nhập lựa chọn: ", "white")).strip()

        if choice == "0":
            break
        elif choice == "1":
            prompt_and_save_token(cred_manager, validator)
        elif choice == "2":
            # Xóa token
            if not tokens:
                print(colored("[!] Không có token nào để xóa!", "yellow"))
                continue

            print(colored("\nChọn token muốn xóa:", "red"))
            for i, label in enumerate(tokens, 1):
                print(f"  [{i}] {label}")

            try:
                del_choice = input(colored("Nhập số thứ tự token muốn xóa (hoặc Enter để hủy): ", "white")).strip()
                if not del_choice:
                    print(colored("Đã hủy xóa token.", "yellow"))
                    continue

                del_idx = int(del_choice)
                if 1 <= del_idx <= len(tokens):
                    label_to_delete = tokens[del_idx - 1]
                    confirm = input(colored(f"Bạn có chắc muốn xóa token '{label_to_delete}'? (y/n): ", "yellow")).strip().lower()
                    if confirm == 'y':
                        if cred_manager.delete_auth(label_to_delete):
                            print(colored(f"[✔] Đã xóa token '{label_to_delete}'!", "green"))
                        else:
                            print(colored("[!] Xóa token thất bại!", "red"))
                    else:
                        print(colored("Đã hủy.", "yellow"))
                else:
                    print(colored("Lựa chọn không hợp lệ!", "red"))
            except ValueError:
                print(colored("Lựa chọn không hợp lệ! Vui lòng nhập số.", "red"))
        else:
            print(colored("Lựa chọn không hợp lệ!", "yellow"))


def main() -> None:
    """Main function"""
    validator = InputValidator()
    cred_manager = CredentialManager()

    check_for_updates()
    logger.info("Khởi động ứng dụng...")

    while True:
        menu()
        choose = input(colored("🥇 Nhập Lựa Chọn (0-8): ", "white")).strip()

        if choose == "0":
            print(colored("👋 Tạm biệt!", "green"))
            break
        elif choose == "8":
            print(colored("\n🧹 Đang dọn dẹp các tiến trình Chrome & Driver chạy ngầm...", "yellow"))
            try:
                import golikefb_sele
                golikefb_sele.cleanup()
                print(colored("✅ Dọn dẹp hoàn tất! Hệ thống đã sạch sẽ.", "green"))
                input(colored("Nhấn Enter để quay lại...", "white"))
            except Exception as e:
                print(colored(f"❌ Lỗi khi dọn dẹp: {e}", "red"))
                input(colored("Nhấn Enter để quay lại...", "white"))
            continue
        elif choose == "9":
            run_quick_dom_tool()
            continue
        elif choose == "7":
            if HAS_IOS_FLOW and ios_tiktok_menu:
                ios_tiktok_menu()
            else:
                print(colored("\n❌ Chế độ iOS Automation chưa khả dụng trên thiết bị này.", "red"))
                print(colored("💡 Yêu cầu cài đặt: pip install facebook-wda tidevice", "yellow"))
                input(colored("\nNhấn Enter để quay lại...", "white"))
            continue
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
            # Facebook Desktop Selenium (cookie, facebook.com, F12)
            if HAS_DESKTOP_SELE and fb_desktop_menu:
                fb_desktop_menu()
            else:
                print(colored("❌ Facebook Desktop Selenium không khả dụng trên thiết bị này.", "red"))
                print(colored("💡 Tính năng này yêu cầu Chrome Desktop + Selenium (chỉ hỗ trợ Windows/Linux).", "yellow"))
                input(colored("Nhấn Enter để quay lại...", "white"))
            continue
        elif choose == "1":
            # TikTok menu
            if not cred_manager.has_any_token():
                # Chưa có token nào, yêu cầu nhập ngay tại chỗ
                auth_token = prompt_and_save_token(cred_manager, validator)
                if not auth_token:
                    continue
            else:
                labels = cred_manager.get_auth_labels()
                if len(labels) == 1:
                    auth_token = cred_manager.get_auth_by_label(labels[0])
                else:
                    # Nhiều token, yêu cầu chọn
                    print(colored("\nChọn token để sử dụng cho TikTok:", "cyan"))
                    for i, label in enumerate(labels, 1):
                        token = cred_manager.get_auth_by_label(label)
                        # Check if it is a JSON with headers
                        try:
                            import json
                            token_data = json.loads(token)
                            if isinstance(token_data, dict):
                                token = token_data.get("authorization", "")
                        except Exception:
                            pass

                        if token and len(token) > 14:
                            masked = token[:10] + "..." + token[-4:]
                        else:
                            masked = token
                        print(f"  [{i}] {label} ({masked})")
                    choice_idx = input_int("Nhập lựa chọn: ", minval=1, maxval=len(labels))
                    auth_token = cred_manager.get_auth_by_label(labels[choice_idx-1])
            tiktok_menu(auth_token)
        elif choose == "2":
            # Facebook menu
            if not cred_manager.has_any_token():
                # Chưa có token nào, yêu cầu nhập ngay tại chỗ
                auth_token = prompt_and_save_token(cred_manager, validator)
                if not auth_token:
                    continue
            else:
                labels = cred_manager.get_auth_labels()
                if len(labels) == 1:
                    auth_token = cred_manager.get_auth_by_label(labels[0])
                else:
                    # Nhiều token, yêu cầu chọn
                    print(colored("\nChọn token để sử dụng cho Facebook:", "cyan"))
                    for i, label in enumerate(labels, 1):
                        token = cred_manager.get_auth_by_label(label)
                        # Check if it is a JSON with headers
                        try:
                            import json
                            token_data = json.loads(token)
                            if isinstance(token_data, dict):
                                token = token_data.get("authorization", "")
                        except Exception:
                            pass

                        if token and len(token) > 14:
                            masked = token[:10] + "..." + token[-4:]
                        else:
                            masked = token
                        print(f"  [{i}] {label} ({masked})")
                    choice_idx = input_int("Nhập lựa chọn: ", minval=1, maxval=len(labels))
                    auth_token = cred_manager.get_auth_by_label(labels[choice_idx-1])
            facebook_menu(auth_token)
        else:
            logger.warning("Lựa chọn không hợp lệ!")


if __name__ == "__main__":
    main()