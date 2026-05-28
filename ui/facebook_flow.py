"""
Facebook job processing menu.
"""
import os
import time
from typing import Optional

from golike_core.logging import logger
from golike_core.adb_manager import colored
from golike_core.api_client import GolikeAPIClient
from golike_core.security import CredentialManager, InputValidator
from golike_core.utils.safe_logger import safe_log
from golike_facebook.facebook_client import FacebookJobProcessor
from ui.console import input_int


def facebook_menu(auth_token: str) -> None:
    """Menu Facebook

    Args:
        auth_token: Authorization token
    """
    validator = InputValidator()
    cred_manager = CredentialManager()
    cookie_file = "facebook_cookie.enc"

    def get_fb_cookie() -> Optional[str]:
        if not os.path.exists(cookie_file):
            return None
        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                encrypted = f.read().strip()
            decrypted = cred_manager._decrypt(encrypted)
            return decrypted if decrypted else None
        except (IOError, ValueError):
            return None

    def save_fb_cookie(cookie: str) -> bool:
        try:
            encrypted = cred_manager._encrypt(cookie)
            with open(cookie_file, 'w', encoding='utf-8') as f:
                f.write(encrypted)
            return True
        except (IOError, ValueError) as e:
            logger.error(f"Lỗi lưu cookie: {e}")
            return False

    cookie = get_fb_cookie()
    if cookie:
        logger.info("Đã tìm thấy Facebook Cookie lưu sẵn trong hệ thống.")
        change = input(colored("🔄 Bạn có muốn xóa và nhập Cookie FB mới không? (y/N): ", "yellow")).strip().lower()
        if change == 'y':
            cookie = None
            if os.path.exists(cookie_file):
                os.remove(cookie_file)
                logger.info("Đã xóa Cookie FB cũ!")

    while not cookie:
        cookie = input(colored("📢 Nhập Facebook Cookie: ", "green")).strip()
        # Validate TRƯỚC sanitize để không làm mất dữ liệu hợp lệ
        if not validator.validate_cookie(cookie):
            logger.warning("Cookie không hợp lệ!")
            cookie = ""
            continue
        # Sanitize sau khi validate thành công
        cookie = validator.sanitize_string(cookie, 1000)
        if cookie:
            if save_fb_cookie(cookie):
                logger.info("Đã lưu Facebook cookie")
            else:
                logger.error("Lỗi lưu cookie!")
                cookie = ""

    api_client = GolikeAPIClient()
    api_client.set_auth(auth_token)

    try:
        accounts = api_client.get_accounts(provider='facebook')
        logger.debug(f"API Response: {safe_log(accounts)}")
    except Exception as e:
        logger.error(f"Lỗi lấy danh sách account Facebook: {e}")
        print(colored("🚨 Lỗi kết nối API!", "red"))
        input(colored("Nhấn Enter để quay lại...", "white"))
        return

    if not accounts or accounts.get("status") != 200 or not accounts.get("data"):
        print(colored("🚨 Không có tài khoản Facebook nào!", "red"))
        input(colored("Nhấn Enter để quay lại...", "white"))
        return

    raw_data = accounts.get("data", {})
    if isinstance(raw_data, dict):
        data = raw_data.get("data", [])
    elif isinstance(raw_data, list):
        data = raw_data
    else:
        data = []

    print(colored("\n🆔 Danh sách account Facebook:", "yellow"))
    print(colored("════════════════════════════════════════════════", "cyan"))
    if not isinstance(data, list) or not data:
        print(colored("Không có tài khoản Facebook nào!", "red"))
        input(colored("Nhấn Enter để quay lại...", "white"))
        return

    for idx, acc in enumerate(data, 1):
        print(colored(f"[{idx}] 🆔: {acc.get('fb_name', 'N/A')} | ID: {acc.get('fb_id', 'N/A')}", "cyan"))
    print(colored("════════════════════════════════════════════════", "cyan"))

    while True:
        acc_choice = input(colored("☀️ Nhập số thứ tự account: ", "green")).strip()
        if acc_choice.isdigit() and 1 <= int(acc_choice) <= len(data):
            selected = data[int(acc_choice) - 1]
            fb_id = selected.get('fb_id')
            account_db_id = selected.get('id')
            break
        print(colored("❌ Lựa chọn không hợp lệ!", "red"))

    delay = input_int("👀 Nhập thời gian làm job: ")
    while True:
        lannhan = input(colored("🛑 Nhận tiền lần 2 nếu lần 1 fail? (y/n): ", "green")).strip().lower()
        if lannhan in {"y", "n"}:
            break
        logger.warning("Nhập sai hãy nhập lại!!!")

    doiacc = input_int("♻️ Số job fail để đổi acc (nhập 1 nếu không muốn dùng): ")
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

    processor = FacebookJobProcessor(api_client, fb_id, cookie, internal_id=account_db_id)
    dem = tong = checkdoiacc = 0
    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("|🆔| ⏱️ ┊ Trạng thái | Số Job | Loại | Xu | Tổng", "cyan"))
    print(colored("════════════════════════════════════════════════", "white"))

    while True:
        if checkdoiacc >= doiacc:
            logger.warning("Job fail đạt giới hạn, chọn acc mới!")
            input(colored("Nhấn Enter để tiếp...", "white"))
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
                print(colored(f"| {dem} | {now} | thành công | {result.get('type', job_type)} | +{tien} | {tong}", "green"))
                checkdoiacc = 0
            else:
                reason = result.get("reason", "unknown")
                if reason == "no_jobs":
                    for i in range(5, 0, -1):
                        print(colored(f"⏳ Hết nhiệm vụ tạm thời, tự động tìm lại sau {i} giây...", "yellow"), end="\r")
                        time.sleep(1)
                    print(" " * 60, end="\r")
                    break

                print(colored(f"| - | - | thất bại | {job_type} | 0 | {tong}  🚨 Lý do: {reason}", "red"))
                checkdoiacc += 1

        time.sleep(delay)