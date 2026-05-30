"""
TikTok job processing menu with ADB/uiautomator2 support.
"""
import os
import re
import sys
import time

def check_keyboard_pause():
    try:
        import msvcrt
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            if ch in (b'\r', b'\n'):
                while msvcrt.kbhit():
                    msvcrt.getch()
                print("\n⏸️ [TẠM DỪNG] Đã tạm dừng tool. Nhấn 'r' để tiếp tục...")
                while True:
                    original_time_sleep(0.1)
                    if msvcrt.kbhit():
                        resume_ch = msvcrt.getch().lower()
                        if resume_ch == b'r':
                            while msvcrt.kbhit():
                                msvcrt.getch()
                            print("▶️ [TIẾP TỤC] Đang chạy tiếp...")
                            break
    except Exception:
        pass

original_time_sleep = time.sleep
def paused_sleep(seconds):
    check_keyboard_pause()
    secs = int(seconds)
    if secs > 1:
        for _ in range(secs):
            check_keyboard_pause()
            original_time_sleep(1)
        fraction = seconds - secs
        if fraction > 0:
            original_time_sleep(fraction)
    else:
        original_time_sleep(seconds)

time.sleep = paused_sleep
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import random

import requests

from golike_core.logging import logger
from golike_core.config import CONFIG
from golike_core.adb_manager import ADBManager, load_adb_config, save_adb_config, colored
from golike_core.api_client import GolikeAPIClient
from golike_core.security import CredentialManager, InputValidator
from golike_core.job_processors import (
    Job, JobProcessorFactory, U2JobProcessor, _call_process_job
)
from ui.console import input_int, get_public_ip

# Import UI automation module
try:
    from tiktok_automation import TikTokUIAutomator
    UI_AUTOMATION_AVAILABLE = True
except ImportError:
    UI_AUTOMATION_AVAILABLE = False
    logger.warning("tiktok_automation module khong kha dung. UI automation se bi tat.")

# Timezone setup
try:
    import pytz
    tz = pytz.timezone("Asia/Ho_Chi_Minh")
except ImportError:
    tz = None


def extract_username_from_link(link: str) -> Optional[str]:
    """Extract TikTok username tu link profile/video.

    Args:
        link: TikTok URL

    Returns:
        Username (khong co @) hoac None neu khong extract duoc
    """
    if not link:
        return None

    url = link.strip()

    if 'vt.tiktok.com' in url or 'vm.tiktok.com' in url:
        try:
            resp = requests.head(url, allow_redirects=True, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36'
            })
            url = resp.url
        except requests.RequestException:
            try:
                resp = requests.get(url, allow_redirects=True, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36'
                })
                url = resp.url
            except requests.RequestException:
                pass

    match = re.search(r'/@([^/?\s]+)', url)
    if match:
        return match[1]

    return None


def _process_single_job(
    api_client: GolikeAPIClient,
    ads_id: str,
    link: str,
    object_id: str,
    account_id: str,
    job_type: str,
    ui_automator,
    job_processor,
    delay_min: int,
    delay_max: int,
    open_method: str,
    search_mode: bool,
    stt: int = 0,
    tong: int = 0,
) -> Tuple[bool, int, bool]:
    """Xu ly mot job don le: mo link, UI auto, nhan tien.

    Args:
        api_client: GolikeAPIClient instance
        ads_id: Job advertising ID
        link: URL can mo
        object_id: Object ID cua job
        account_id: Account ID dang dung
        job_type: Loai job (follow/like)
        ui_automator: TikTokUIAutomator instance hoac None
        job_processor: JobProcessor instance
        delay_min: Thoi gian delay toi thieu
        delay_max: Thoi gian delay toi da
        open_method: Phuong thuc mo link (adb/u2/search)
        search_mode: Dang o che do search khong
        stt: So thu tu job
        tong: Tong tien hien tai

    Returns:
        Tuple[bool, int, bool]: (ok, reward, not_found_skip)
    """
    # Mo link hoac search user
    if search_mode and job_type == "follow":
        username = extract_username_from_link(link)
        if not username:
            logger.warning(f"Không lấy được username từ link: {link[:60]}")
            actual_delay = random.randint(delay_min, delay_max)
            for t in range(actual_delay, -1, -1):
                print(colored(f"⏰ Đợi {t} giây ...", "cyan"), end="\r")
                time.sleep(1)
            return False, 0, False

        if ui_automator:
            print(colored(f"🔍 Đang tìm kiếm user '{username}' trong app TikTok...", "cyan"), end="\r")
            search_ok, search_msg = ui_automator.search_user(username, timeout=5, retry_count=3)
            if search_ok:
                print(colored(f"✅ {search_msg}", "green"))
            else:
                print(colored(f"❌ {search_msg}", "red"))
                ui_automator.clear_search_text()
                actual_delay = random.randint(delay_min, delay_max)
                for t in range(actual_delay, -1, -1):
                    print(colored(f"⏰ Đợi {t} giây ...", "cyan"), end="\r")
                    time.sleep(1)
                return False, 0, False
        else:
            logger.error("UI Automation không khả dụng, không thể tìm kiếm!")
            return False, 0, False
    elif search_mode and job_type == "like":
        logger.info(f"Chế độ tìm kiếm - ADB mở link like: {link[:50]}...")
        job_processor.process(Job(ads_id, link, job_type, object_id))
    else:
        logger.info(f"Mở link nhiệm vụ {job_type}: {link[:50]}...")
        opened = job_processor.process(Job(ads_id, link, job_type, object_id))

        if not opened and open_method == "adb":
            print(colored(f"❌ Không thể mở bằng ADB", "red"), end="\r")
            print(colored(f"🔗 Link: {link}", "yellow"))
            print(colored("   Vui lòng mở thủ công...", "cyan"))

    # UI Automation
    if ui_automator and job_type in ["follow", "like"]:
        print(colored(f"🤖 Đang thực hiện tự động click cho {job_type}...", "cyan"), end="\r")
        ui_success, ui_message, ui_not_found = _call_process_job(ui_automator, job_type)
        logger.info(f"Tự động click {job_type}: {ui_message}")

        if ui_not_found:
            print(colored(f"🚫 Không tìm thấy nút {job_type} sau 2 lần → Bỏ qua nhiệm vụ!", "red", bold=True))
            _skip_job(api_client, ads_id, object_id, account_id, job_type)
            return False, 0, True  # not_found_skip = True
        elif ui_success:
            print(colored(f"✅ Tự động click thành công: {ui_message}", "green"))
        else:
            print(colored(f"⚠️ Tự động click cảnh báo: {ui_message}", "yellow"))

    # Doi theo delay
    actual_delay = random.randint(delay_min, delay_max)
    
    # Random mot thoi diem trong luc cho de vuot xem video khac (chi ap dung cho job like)
    # Thuong la vao khoang 1/3 hoac 2/3 thoi gian cho
    vuot_luc = random.choice([actual_delay // 3, actual_delay * 2 // 3]) if job_type == "like" else -1
    
    for t in range(actual_delay, -1, -1):
        print(colored(f"⏰ Đợi {t} giây ...       ", "cyan"), end="\r")
        time.sleep(1)
        # Hanh vi nguoi dung: Trong luc doi thi luot sang xem video khac (chi ap dung cho job like)
        if ui_automator and job_type == "like" and t == vuot_luc:
            print(colored(f"⏰ Đợi {t} giây (Đang vuốt lướt xem video tiếp theo...)    ", "cyan"), end="\r")
            ui_automator.scroll_down_only()

    # Xoa text search neu search mode
    if search_mode and ui_automator:
        ui_automator.clear_search_text()
        print(colored("🧹 Đã xóa chữ tìm kiếm", "cyan"), end="\r")

    # Nhan tien
    return _claim_payment(api_client, ads_id, account_id, job_type, stt=stt, tong=tong)


def _skip_job(api_client: GolikeAPIClient, ads_id: str, object_id: str, account_id: str, job_type: str) -> None:
    """Bao cao va skip job that bai."""
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
        logger.error(f"Lỗi bỏ qua nhiệm vụ: {e}")


def _claim_payment(
    api_client: GolikeAPIClient,
    ads_id: str,
    account_id: str,
    job_type: str,
    stt: int = 0,
    tong: int = 0,
) -> Tuple[bool, int, bool]:
    """Nhan tien job, co retry.

    Returns:
        Tuple[bool, int, bool]: (ok, reward, not_found_skip) — always False for not_found_skip
    """
    ok = False
    reward = 0
    for lan in range(1, 3):
        try:
            logger.info(f"Đang nhận tiền lần {lan} cho nhiệm vụ {job_type} (ads_id: {ads_id})...")
            nhantien = api_client.post('/api/advertising/publishers/tiktok/complete-jobs', {
                "ads_id": ads_id,
                "account_id": account_id,
                "async": True,
                "data": None
            })
            if nhantien.get("status") == 200:
                ok = True
                reward = nhantien["data"].get("prices", 0)
                job_type = nhantien['data'].get('type', '')
                message = nhantien.get('message')
                now = datetime.now(tz).strftime("%H:%M:%S") if tz else time.strftime("%H:%M:%S")
                
                print(colored(f"| {stt} | {now} | thành công | {job_type} | +{reward} | {tong + reward} |", "green", bold=True))
                if message:
                    print(colored(f"   └── Thông báo từ hệ thống: {message}", "cyan"))
                
                logger.info(f"Nhiệm vụ hoàn thành: {job_type}, +{reward} xu" + (f" - {message}" if message else ""))
                break
            elif lan == 1:
                print(colored("⚠️ Lần 1 thất bại - Đang thử lần 2...", "yellow"), end="\r")
        except Exception as e:
            logger.error(f"Lỗi nhận tiền lần {lan}: {e}")
            if lan == 1:
                print(colored("⚠️ Lần 1 thất bại - Đang thử lần 2...", "yellow"), end="\r")

    return ok, reward, False


def tiktok_menu(auth_token: str) -> None:
    """Menu TikTok

    Args:
        auth_token: Authorization token
    """
    validator = InputValidator()
    cred_manager = CredentialManager()

    adb_config = load_adb_config()
    saved_open_method = adb_config.get("open_method")
    saved_device = adb_config.get("current_device")

    open_method = "adb"
    current_device = None
    adb_manager = None

    # 1. Thử tải sử dụng cấu hình cũ
    use_saved = False
    if saved_open_method == "adb" and saved_device:
        logger.info(f"Phát hiện thiết bị ADB đã chọn trước đó: {saved_device}")
        chon_saved = input(colored("👉 Bạn muốn tiếp tục chạy và Auto Click trên thiết bị này? (y/n, Enter là Có): ", "green")).strip().lower()
        if chon_saved in ["y", "yes", ""]:
            use_saved = True
            open_method = "adb"
            current_device = saved_device
            adb_manager = ADBManager()
            adb_manager.selected_device = current_device
            logger.info(f"Tái sử dụng thiết bị ADB đã lưu: {current_device}")
    elif saved_open_method == "u2":
        saved_ip_port = adb_config.get("current_device", "")
        if saved_ip_port:
            logger.info(f"Thiết bị uiautomator2 đã lưu: {saved_ip_port}")
            chon_saved = input(colored("👉 Bạn muốn tiếp tục dùng thiết bị này? (y/n, Enter là Có): ", "green")).strip().lower()
            if chon_saved in ["y", "yes", ""]:
                if UI_AUTOMATION_AVAILABLE:
                    print(colored(f"⏳ Đang kiểm tra kết nối uiautomator2 đến thiết bị đã lưu {saved_ip_port}...", "yellow"))
                    test_automator = TikTokUIAutomator(device_id=saved_ip_port)
                    if test_automator.connect():
                        print(colored("✅ Kết nối uiautomator2 thành công!", "green", bold=True))
                        test_automator.disconnect()
                        use_saved = True
                        open_method = "u2"
                        current_device = saved_ip_port
                        adb_manager = ADBManager()
                        logger.info(f"Tái sử dụng thiết bị u2: {current_device}")
                    else:
                        print(colored(f"❌ Kết nối uiautomator2 thất bại đến {saved_ip_port}!", "red", bold=True))
                        print(colored("Vui lòng thiết lập kết nối mới.", "yellow"))
                        use_saved = False
                else:
                    use_saved = True
                    open_method = "u2"
                    current_device = saved_ip_port
                    adb_manager = ADBManager()
                    logger.info(f"Tái sử dụng thiết bị u2: {current_device}")
    elif saved_open_method in ["termux", "manual"]:
        method_desc = "Termux" if saved_open_method == "termux" else "Chế độ Thủ công (Bạn tự Click bằng tay)"
        logger.info(f"Phương thức mở link trước đó: {method_desc}")
        chon_saved = input(colored("👉 Bạn muốn tiếp tục giữ nguyên phương thức này? (y/n, Enter là Có): ", "green")).strip().lower()
        if chon_saved in ["y", "yes", ""]:
            use_saved = True
            open_method = saved_open_method
            logger.info(f"Tái sử dụng phương thức: {open_method}")
    elif saved_open_method == "search":
        logger.info("Phương thức trước đó: Tìm kiếm user TikTok để Follow")
        if saved_device:
            logger.info(f"Thiết bị đã chọn: {saved_device}")
        chon_saved = input(colored("👉 Bạn muốn tiếp tục dùng chế độ tìm kiếm? (y/n, Enter là Có): ", "green")).strip().lower()
        if chon_saved in ["y", "yes", ""]:
            use_saved = True
            open_method = "search"
            current_device = saved_device
            adb_manager = ADBManager()
            if saved_device:
                adb_manager.selected_device = saved_device
            logger.info("Tái sử dụng phương thức: search")

    # 2. Nếu không dùng lại cấu hình cũ, thiết lập mới
    if not use_saved:
        while True:
            print(colored("════════════════════════════════════════════════", "white"))
            print(colored("📱 Cấu hình Kết nối & Auto Click:", "cyan", bold=True))
            print(colored("   [1] ⭐ Chạy TỰ ĐỘNG: Mở Link & Tự Auto Click (Dùng ADB cho PC/Giả lập)", "white"))
            print(colored("   [2] 📱 Chạy qua WiFi (uiautomator2): Nhập IP:Port điện thoại để kết nối", "cyan"))
            print(colored("   [3] ✍️  Chạy Thủ Công: Chỉ hiện Link, bạn TỰ CLICK BẰNG TAY trên điện thoại", "white"))
            print(colored("   [4] 🔍 Tìm kiếm user TikTok để Follow (dùng thanh search trong app)", "yellow"))
            print(colored("════════════════════════════════════════════════", "white"))

            while True:
                conn_choice = input(colored("👉 Chọn phương thức kết nối (1-4, Mặc định 1): ", "green")).strip()
                if conn_choice in ["1", ""]:
                    open_method = "adb"
                    break
                elif conn_choice == "2":
                    open_method = "u2"
                    break
                elif conn_choice == "3":
                    open_method = "manual"
                    break
                elif conn_choice == "4":
                    open_method = "search"
                    break
                else:
                    logger.warning("Lựa chọn không hợp lệ, hãy thử lại!")

            if open_method == "adb":
                adb_manager = ADBManager()
                current_device = adb_manager.select_device()
                if not current_device:
                    logger.warning("Chưa chọn được thiết bị cụ thể! Hệ thống sẽ cố kết nối đến ADB mặc định...")
                adb_config["open_method"] = "adb"
                adb_config["current_device"] = current_device
                save_adb_config(adb_config)
                break
            elif open_method == "u2":
                print(colored("\n📡 KẾT NỐI UIAUTOMATOR2 QUA WIFI:", "cyan"))
                u2_connected = False
                while True:
                    ip_port = input(colored("👉 Nhập IP:Port điện thoại (ví dụ: 192.168.1.10:5555 hoặc 192.168.1.10) hoặc nhập 'quay lai' để chọn lại phương thức: ", "green")).strip()
                    if ip_port.lower() in ["quay lai", "quay lại", "back", "q"]:
                        break
                    
                    if ":" in ip_port:
                        parts = ip_port.split(":")
                        if len(parts) == 2 and parts[1].isdigit() and parts[0]:
                            pass
                        else:
                            logger.warning("Định dạng không hợp lệ! Nhập dạng IP:Port hoặc chỉ IP (vd: 192.168.1.10:5555)")
                            continue
                    elif ip_port:
                        ip_port = f"{ip_port}:5555"
                    else:
                        logger.warning("Vui lòng nhập IP:Port hoặc IP!")
                        continue
                    
                    current_device = ip_port
                    if UI_AUTOMATION_AVAILABLE:
                        print(colored(f"⏳ Đang kiểm tra kết nối uiautomator2 đến {current_device}...", "yellow"))
                        test_automator = TikTokUIAutomator(device_id=current_device)
                        if test_automator.connect():
                            print(colored("✅ Kết nối uiautomator2 thành công!", "green", bold=True))
                            test_automator.disconnect()
                            u2_connected = True
                            break
                        else:
                            print(colored(f"❌ Kết nối uiautomator2 thất bại đến {current_device}!", "red", bold=True))
                            print(colored("Vui lòng kiểm tra xem:", "yellow"))
                            print(colored("  1. Điện thoại đã bật chế độ gỡ lỗi USB (USB Debugging) chưa?", "yellow"))
                            print(colored("  2. Điện thoại và máy tính/Termux có kết nối chung một mạng Wifi không?", "yellow"))
                            print(colored("  3. Cổng port hoặc địa chỉ IP có chính xác không?", "yellow"))
                            print(colored("  4. Đã khởi động dịch vụ uiautomator2 trên điện thoại chưa?", "yellow"))
                            
                            chon_thu_lai = input(colored("👉 Bạn có muốn thử lại địa chỉ khác? (y/n, Enter là Có): ", "green")).strip().lower()
                            if chon_thu_lai not in ["y", "yes", ""]:
                                break
                    else:
                        print(colored("⚠️ Module uiautomator2 không khả dụng. Bỏ qua kiểm tra kết nối.", "yellow"))
                        u2_connected = True
                        break
                
                if u2_connected:
                    adb_manager = ADBManager()
                    logger.info(f"Sẽ kết nối uiautomator2 đến: {current_device}")
                    save_choice = input(colored("💾 Lưu thiết bị này lại để dùng nhanh lần sau? (y/n, Enter là Có): ", "green")).strip().lower()
                    if save_choice in ["y", "yes", ""]:
                        adb_config["open_method"] = "u2"
                        adb_config["current_device"] = current_device
                        save_adb_config(adb_config)
                        logger.info(f"Đã lưu thiết bị: {current_device}")
                    else:
                        adb_config["open_method"] = "u2"
                        adb_config["current_device"] = None
                        save_adb_config(adb_config)
                    break
                else:
                    continue
            elif open_method == "search":
                adb_manager = ADBManager()
                current_device = adb_manager.select_device()
                if not current_device:
                    logger.warning("Chưa chọn được thiết bị cụ thể!")
                adb_config["open_method"] = "search"
                adb_config["current_device"] = current_device
                save_adb_config(adb_config)
                break
            else:
                adb_config["open_method"] = open_method
                adb_config["current_device"] = None
                save_adb_config(adb_config)
                break

    # Lấy danh sách acc
    api_client = GolikeAPIClient()
    api_client.set_auth(auth_token)

    try:
        accounts = api_client.get('/api/tiktok-account')
    except Exception as e:
        logger.error(f"Lỗi lấy danh sách tài khoản: {e}")
        print(colored("🚨 Lỗi kết nối API! Hãy kiểm tra lại.", "red"))
        input(colored("Nhấn Enter để quay lại...", "white"))
        return

    if not accounts or accounts.get("status") != 200 or not accounts.get("data"):
        print(colored("🚨 Token Authorization sai hoặc không có tài khoản. Hãy nhập lại!", "red"))
        logger.error("Authorization không hợp lệ hoặc không có tài khoản")
        input(colored("Nhấn Enter để quay lại...", "white"))
        return

    print(colored(f"🚨 Địa chỉ IP  : 👀{get_public_ip()}👀", "white"))
    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("🆔 Danh sách acc TikTok :", "yellow"))
    print(colored("════════════════════════════════════════════════", "white"))
    data = accounts.get("data", [])
    if not isinstance(data, list) or not data:
        print(colored("Không có tài khoản TikTok nào!", "red"))
        input(colored("Nhấn Enter để quay lại...", "white"))
        return
    for idx, acc in enumerate(data, 1):
        print(colored(f"[{idx}] 🆔 : {acc.get('unique_username', 'N/A')} ♦️ : ✅", "cyan"))
    print(colored("════════════════════════════════════════════════", "white"))

    print(colored("Hướng dẫn: Bạn có thể nhập số thứ tự hoặc ID tài khoản.", "cyan"))
    while True:
        acc_input = input(colored("☀️ Nhập số thứ tự hoặc ID Acc Tiktok: ", "green")).strip()
        if acc_input.isdigit() and 1 <= int(acc_input) <= len(data):
            acc_index = int(acc_input) - 1
            acc_obj = data[acc_index]
            account_id = acc_obj.get("id")
            logger.info(f"Đã chọn tài khoản [{acc_input}]: {acc_obj.get('unique_username', 'N/A')}")
            break
        elif acc_input:
            acc_obj = next((a for a in data if a.get("unique_username") == acc_input), None)
            if acc_obj:
                account_id = acc_obj.get("id")
                break
            else:
                logger.warning("Acc này chưa được thêm vào GoLike hoặc ID sai")
        else:
            logger.warning("Vui lòng nhập số thứ tự hoặc ID hợp lệ!")

    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("⏳ CẤU HÌNH GIẢ LẬP HÀNH VI (CHỐNG BAN):", "cyan", bold=True))
    
    # Delay giữa các thao tác
    try:
        v = input(colored("⏱️  Delay giữa các thao tác (giây, nhập '18-28' hoặc Enter để dùng mặc định): ", "green")).strip()
        if not v: v = "18-28"
        delay_action_min, delay_action_max = map(int, v.split("-"))
    except Exception:
        delay_action_min, delay_action_max = 18, 28
        
    # Delay giua 2 nhiem vu
    try:
        v = input(colored("⏱️  Delay giữa 2 nhiệm vụ (giây, nhập '25-45' hoặc Enter để dùng mặc định): ", "green")).strip()
        if not v: v = "25-45"
        delay_job_min, delay_job_max = map(int, v.split("-"))
    except Exception:
        delay_job_min, delay_job_max = 25, 45

    # So job de nghi
    try:
        v = input(colored("📆 Sau bao nhiêu nhiệm vụ thì nghỉ (nhập '40' hoặc Enter để dùng mặc định): ", "green")).strip()
        if not v: v = "40"
        break_jobs = int(v)
    except Exception:
        break_jobs = 40

    # Thoi gian nghi tu min-max
    try:
        v = input(colored("⏱️  Thời gian nghỉ (giây, nhập '300-600' hoặc Enter để dùng mặc định): ", "green")).strip()
        if not v: v = "300-600"
        break_delay_min, break_delay_max = map(int, v.split("-"))
    except Exception:
        break_delay_min, break_delay_max = 300, 600

    logger.info(f"Cấu hình delay: Action ({delay_action_min}-{delay_action_max}s), Job ({delay_job_min}-{delay_job_max}s), Break after {break_jobs} jobs ({break_delay_min}-{break_delay_max}s)")
    print(colored("════════════════════════════════════════════════", "white"))

    doiacc = input_int("📆 Số nhiệm vụ thất bại để đổi acc TikTok (nhập 1 nếu không muốn đổi): ")
    while True:
        print(colored("════════════════════════════════════════════════", "white"))
        print(colored("♦️ ✈ Nhập 1 : Chỉ nhận nhiệm vụ Follow", "yellow"))
        print(colored("🔥 ✈ Nhập 2 : Chỉ nhận nhiệm vụ Like", "yellow"))
        print(colored("💥 ✈ Nhập 12 : Kết hợp cả Like và Follow", "yellow"))
        print(colored("🔍 Nhập 3 : Search Follow (thanh tìm kiếm) + ADB Like (mở link)", "yellow"))
        print(colored("════════════════════════════════════════════════", "white"))
        chedo = input(colored("✅ Chọn lựa chọn: ", "cyan")).strip()
        if chedo in {"1", "2", "12", "3"}:
            break

    if chedo == "1":
        lam = ["follow"]
    elif chedo == "2":
        lam = ["like"]
    elif chedo == "12":
        lam = ["follow", "like"]
    elif chedo == "3":
        lam = ["follow", "like"]
    else:
        lam = ["follow"]

    search_mode = (chedo == "3")

    search_timeout = 5
    search_retry = 3
    if search_mode:
        print(colored("════════════════════════════════════════════════", "white"))
        print(colored("🔍 Cấu hình tìm kiếm:", "cyan", bold=True))
        try:
            v = input(colored("⏱️  Thời gian chờ tối đa khi tìm kiếm (giây, mặc định 5): ", "green")).strip()
            search_timeout = int(v) if v else 5
        except ValueError:
            search_timeout = 5
        try:
            v = input(colored("🔄 Số lần thử lại nếu không tìm thấy kết quả (mặc định 3): ", "green")).strip()
            search_retry = int(v) if v else 3
        except ValueError:
            search_retry = 3
        logger.info(f"Search timeout: {search_timeout}s | Retry: {search_retry} lần")

    # Bat dau vong lap lam job
    dem = tong = checkdoiacc = 0
    jobs_completed_for_break = 0
    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("|🆔| ⏱️ ┊ Trạng thái | Số Job | ID Acc | Xu | Tổng", "cyan"))
    print(colored("════════════════════════════════════════════════", "white"))
    prev_job = None

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

    ui_automator = None
    if UI_AUTOMATION_AVAILABLE:
        try:
            ui_automator = TikTokUIAutomator(device_id=current_device)
            is_connected = True
            if open_method == "u2":
                is_connected = ui_automator.connect()
            
            if is_connected:
                logger.info("UI Automation đã sẵn sàng")
                print(colored("🤖 [Hệ thống] Đã kích hoạt thành công Module Auto Click!", "green", bold=True))
            else:
                logger.error("Không thể kết nối đến uiautomator2")
                print(colored("❌ Không thể kết nối đến uiautomator2! Thiết bị không online.", "red", bold=True))
                ui_automator = None
                if open_method == "u2":
                    print(colored("🚨 Chế độ uiautomator2 yêu cầu kết nối hoạt động. Dừng chạy bot.", "red", bold=True))
                    input(colored("Nhấn Enter để quay lại...", "white"))
                    return
        except Exception as e:
            logger.warning(f"Không thể tạo UI automator: {e}")
            print(colored(f"⚠️ Không thể khởi động UI automator: {e}", "yellow"))
            ui_automator = None
            if open_method == "u2":
                print(colored("🚨 Chế độ uiautomator2 yêu cầu kết nối hoạt động. Dừng chạy bot.", "red", bold=True))
                input(colored("Nhấn Enter để quay lại...", "white"))
                return

    if open_method == "u2" and isinstance(job_processor, U2JobProcessor) and ui_automator and ui_automator._u2:
        job_processor._u2_device = ui_automator._u2
        logger.info("Đã inject u2 device chung vào U2JobProcessor")

    while True:
        # Doi acc neu vuot gioi han fail
        if checkdoiacc >= doiacc:
            _send_telegram_limit_notify(data, account_id)
            account_id = _select_new_account(data, account_id, checkdoiacc)
            checkdoiacc = 0

        # Nhan job
        print(colored("🔎 Đang tìm nhiệm vụ:>        ", "magenta"), end="\r")
        try:
            nhanjob = api_client.get(f'/api/advertising/publishers/tiktok/jobs?account_id={account_id}&data=null')
        except Exception as e:
            logger.error(f"Lỗi lấy job: {e}")
            no_job_wait = random.randint(22, 30)
            for t in range(no_job_wait, -1, -1):
                print(colored(f"⏳ Không có nhiệm vụ. Đợi {t}s để thử lại...    ", "yellow"), end="\r")
                time.sleep(1)
            continue

        if not nhanjob or not nhanjob.get("data"):
            no_job_wait = random.randint(22, 30)
            for t in range(no_job_wait, -1, -1):
                print(colored(f"⏳ Không có nhiệm vụ. Đợi {t}s để thử lại...    ", "yellow"), end="\r")
                time.sleep(1)
            continue

        # Check job trung
        if prev_job and prev_job.get("data", {}).get("link") == nhanjob.get("data", {}).get("link") and prev_job.get("data", {}).get("type") == nhanjob.get("data", {}).get("type"):
            logger.warning("Nhiệm vụ trùng lặp, bỏ qua")
            _duplicate_job_skip(api_client, nhanjob, account_id)
            time.sleep(2)
            continue
        prev_job = nhanjob

        if nhanjob.get("status") == 200:
            job_data = nhanjob["data"]
            ads_id = job_data.get("id")
            link = job_data.get("link")
            object_id = job_data.get("object_id")
            job_type = job_data.get("type")
        else:
            no_job_wait = random.randint(22, 30)
            for t in range(no_job_wait, -1, -1):
                print(colored(f"⏳ Không có nhiệm vụ. Đợi {t}s để thử lại...    ", "yellow"), end="\r")
                time.sleep(1)
            continue

        if not link:
            logger.warning("Nhiệm vụ không có link, bỏ qua")
            _skip_job(api_client, ads_id, object_id, account_id, job_type)
            time.sleep(2)
            continue

        if job_type not in lam:
            _skip_job(api_client, ads_id, object_id, account_id, job_type)
            print(colored(f"❌ Đã bỏ qua nhiệm vụ {job_type}!", "yellow"), end="\r")
            time.sleep(1)
            continue

        # Xu ly job chinh
        ok, reward, not_found = _process_single_job(
            api_client, ads_id, link, object_id, account_id,
            job_type, ui_automator, job_processor,
            delay_action_min, delay_action_max, open_method, search_mode,
            stt=dem + 1, tong=tong
        )

        if not_found:
            checkdoiacc += 1
            continue

        if ok:
            dem += 1
            tong += reward
            checkdoiacc = 0
            jobs_completed_for_break += 1
            
            # Kiem tra nghi giai lao
            if break_jobs > 0 and jobs_completed_for_break >= break_jobs:
                rest_time = random.randint(break_delay_min, break_delay_max)
                print(colored(f"\n💤 Đã làm {break_jobs} nhiệm vụ. Chờ hệ thống nghỉ giải lao {rest_time} giây để tránh bị quét...", "yellow", bold=True))
                for t in range(rest_time, -1, -1):
                    print(colored(f"⏰ Nghỉ ngơi: Đợi {t} giây ...    ", "cyan"), end="\r")
                    time.sleep(1)
                print(" " * 50, end="\r")
                jobs_completed_for_break = 0
            else:
                job_wait = random.randint(delay_job_min, delay_job_max)
                for t in range(job_wait, -1, -1):
                    print(colored(f"⏰ Chuẩn bị nhận nhiệm vụ tiếp theo: Đợi {t} giây ...    ", "cyan"), end="\r")
                    time.sleep(1)
                print(" " * 50, end="\r")
        else:
            logger.warning("Nhận tiền thất bại sau 2 lần retry → Bỏ qua nhiệm vụ")
            _skip_job(api_client, ads_id, object_id, account_id, job_type)
            time.sleep(1)
            checkdoiacc += 1


def _send_telegram_limit_notify(data: List[Dict], account_id: str) -> None:
    """Gui thong bao Telegram khi acc dat gioi han (fail limit / max job)"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        telegram_enabled = os.getenv('TELEGRAM_ENABLED', '').lower() in ('true', '1', 'yes')
        if not telegram_enabled:
            if os.path.exists("config_golike_sele.json"):
                with open("config_golike_sele.json", "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    telegram_enabled = cfg.get("telegram_enabled", False)
                    
        if not telegram_enabled:
            return
            
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
        chat_id = os.getenv('TELEGRAM_CHAT_ID', '').strip()
        
        if not bot_token or not chat_id:
            return
            
        acc_obj = next((a for a in data if a.get("id") == account_id), None)
        username = acc_obj.get("unique_username", "N/A") if acc_obj else "N/A"
        
        now = datetime.now(tz).strftime("%H:%M:%S") if tz else time.strftime("%H:%M:%S")
        ip = get_public_ip()
        
        # Format message: acc: [tên_acc] đạt max job
        message = f"🚨 <b>GoLike TikTok Alert</b>\n" \
                  f"acc: {username} đạt max job\n" \
                  f"IP: {ip}\n" \
                  f"Thời gian: {now}"
                  
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        params = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        requests.post(url, json=params, timeout=10)
        logger.info(f"Đã gửi thông báo Telegram cho acc {username} đạt max job")
    except Exception as e:
        logger.error(f"Lỗi gửi thông báo Telegram: {e}")


def _select_new_account(data: List[Dict], account_id: str, checkdoiacc: int) -> str:
    """Hien thi lai danh sach va chon acc moi."""
    print(colored(f"🚨 Địa chỉ IP  : 👀{get_public_ip()}👀", "white"))
    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("🆔 Danh sách acc TikTok :", "yellow"))
    print(colored("════════════════════════════════════════════════", "white"))
    for idx, acc in enumerate(data, 1):
        print(colored(f"[{idx}] 🆔 : {acc.get('unique_username', 'N/A')} ♦️ : ✅", "cyan"))
    print(colored("════════════════════════════════════════════════", "white"))
    while True:
        acc_input = input(colored("⚡ Nhiệm vụ thất bại đạt giới hạn, nhập số thứ tự hoặc ID acc mới: ", "red")).strip()
        if acc_input.isdigit() and 1 <= int(acc_input) <= len(data):
            acc_index = int(acc_input) - 1
            acc_obj = data[acc_index]
            new_id = acc_obj.get("id")
            logger.info(f"Đã chọn tài khoản [{acc_input}]: {acc_obj.get('unique_username', 'N/A')}")
            return new_id
        elif acc_input:
            acc_obj = next((a for a in data if a.get("unique_username") == acc_input), None)
            if acc_obj:
                return acc_obj.get("id")
            else:
                logger.warning("Acc này chưa được thêm vào GoLike hoặc ID sai")
        else:
            logger.warning("Vui lòng nhập số thứ tự hoặc ID hợp lệ!")


def _duplicate_job_skip(api_client: GolikeAPIClient, nhanjob: Dict, account_id: str) -> None:
    """Skip job trung lap."""
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
        logger.error(f"Lỗi báo cáo nhiệm vụ trùng: {e}")