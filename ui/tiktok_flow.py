"""
TikTok job processing menu with ADB/uiautomator2 support.
"""
import os
import re
import sys
import time
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

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
    delay: int,
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
        delay: Thoi gian delay giua cac job
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
            logger.warning(f"Khong extract duoc username tu link: {link[:60]}")
            for t in range(delay, -1, -1):
                print(colored(f"⏰ Doi {t} giay ...", "cyan"), end="\r")
                time.sleep(1)
            return False, 0, False

        if ui_automator:
            print(colored(f"🔍 Dang tim kiem user '{username}' trong app TikTok...", "cyan"), end="\r")
            search_ok, search_msg = ui_automator.search_user(username, timeout=5, retry_count=3)
            if search_ok:
                print(colored(f"✅ {search_msg}", "green"))
            else:
                print(colored(f"❌ {search_msg}", "red"))
                ui_automator.clear_search_text()
                for t in range(delay, -1, -1):
                    print(colored(f"⏰ Doi {t} giay ...", "cyan"), end="\r")
                    time.sleep(1)
                return False, 0, False
        else:
            logger.error("UI Automation khong kha dung, khong the search!")
            return False, 0, False
    elif search_mode and job_type == "like":
        logger.info(f"Search mode - ADB mo link like: {link[:50]}...")
        job_processor.process(Job(ads_id, link, job_type, object_id))
    else:
        logger.info(f"Mo link job {job_type}: {link[:50]}...")
        opened = job_processor.process(Job(ads_id, link, job_type, object_id))

        if not opened and open_method == "adb":
            print(colored(f"❌ Khong the mo bang ADB", "red"), end="\r")
            print(colored(f"🔗 Link: {link}", "yellow"))
            print(colored("   Vui long mo thu cong...", "cyan"))

    # UI Automation
    if ui_automator and job_type in ["follow", "like"]:
        print(colored(f"🤖 Dang thuc hien UI automation cho {job_type}...", "cyan"), end="\r")
        ui_success, ui_message, ui_not_found = _call_process_job(ui_automator, job_type)
        logger.info(f"UI automation {job_type}: {ui_message}")

        if ui_not_found:
            print(colored(f"🚫 Khong tim thay nut {job_type} sau 2 lan → Skip job!", "red", bold=True))
            _skip_job(api_client, ads_id, object_id, account_id, job_type)
            return False, 0, True  # not_found_skip = True
        elif ui_success:
            print(colored(f"✅ UI automation thanh cong: {ui_message}", "green"))
        else:
            print(colored(f"⚠️ UI automation canh bao: {ui_message}", "yellow"))

    # Doi theo delay
    for t in range(delay, -1, -1):
        print(colored(f"⏰ Doi {t} giay ...", "cyan"), end="\r")
        time.sleep(1)

    # Xoa text search neu search mode
    if search_mode and ui_automator:
        ui_automator.clear_search_text()
        print(colored("🧹 Da xoa text search", "cyan"), end="\r")

    # Nhan tien
    return _claim_payment(api_client, ads_id, account_id, job_type, stt=stt, tong=tong)


def _skip_job(api_client: GolikeAPIClient, ads_id: str, object_id: str, account_id: str, job_type: str) -> None:
    """Bao cao va skip job that bai."""
    try:
        api_client.post('/api/report/send', {
            "description": "Bao cao hoan thanh that bai",
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
        logger.error(f"Loi skip job: {e}")


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
            logger.info(f"Dang nhan tien lan {lan} cho job {job_type} (ads_id: {ads_id})...")
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
                message = nhantien['data'].get('message', 'Success')
                now = datetime.now(tz).strftime("%H:%M:%S") if tz else time.strftime("%H:%M:%S")
                print(colored(f"| {stt} | {now} | success | {job_type} | +{reward} | {tong + reward} | {message}", "green", bold=True))
                logger.info(f"Job hoan thanh: {job_type}, +{reward} xu - {message}")
                break
            elif lan == 1:
                print(colored("⚠️ Lan 1 that bai - Dang thu lan 2...", "yellow"), end="\r")
        except Exception as e:
            logger.error(f"Loi nhan tien lan {lan}: {e}")
            if lan == 1:
                print(colored("⚠️ Lan 1 that bai - Dang thu lan 2...", "yellow"), end="\r")

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

    # 1. Thu tai su dung cau hinh cu
    use_saved = False
    if saved_open_method == "adb" and saved_device:
        logger.info(f"Phat hien thiet bi ADB da chon truoc do: {saved_device}")
        chon_saved = input(colored("👉 Ban muon tiep tuc chay va Auto Click tren thiet bi nay? (y/n, Enter la Co): ", "green")).strip().lower()
        if chon_saved in ["y", "yes", ""]:
            use_saved = True
            open_method = "adb"
            current_device = saved_device
            adb_manager = ADBManager()
            adb_manager.selected_device = current_device
            logger.info(f"Tai su dung thiet bi ADB da luu: {current_device}")
    elif saved_open_method == "u2":
        saved_ip_port = adb_config.get("current_device", "")
        if saved_ip_port:
            logger.info(f"Thiet bi uiautomator2 da luu: {saved_ip_port}")
            chon_saved = input(colored("👉 Ban muon tiep tuc dung thiet bi nay? (y/n, Enter la Co): ", "green")).strip().lower()
            if chon_saved in ["y", "yes", ""]:
                use_saved = True
                open_method = "u2"
                current_device = saved_ip_port
                adb_manager = ADBManager()
                logger.info(f"Tai su dung thiet bi u2: {current_device}")
    elif saved_open_method in ["termux", "manual"]:
        method_desc = "Termux" if saved_open_method == "termux" else "Che do Thu cong (Ban tu Click bang tay)"
        logger.info(f"Phuong thuc mo link truoc do: {method_desc}")
        chon_saved = input(colored("👉 Ban muon tiep tuc giu nguyen phuong thuc nay? (y/n, Enter la Co): ", "green")).strip().lower()
        if chon_saved in ["y", "yes", ""]:
            use_saved = True
            open_method = saved_open_method
            logger.info(f"Tai su dung phuong thuc: {open_method}")
    elif saved_open_method == "search":
        logger.info("Phuong thuc truoc do: Tim kiem user TikTok de Follow")
        if saved_device:
            logger.info(f"Thiet bi da chon: {saved_device}")
        chon_saved = input(colored("👉 Ban muon tiep tuc dung che do tim kiem? (y/n, Enter la Co): ", "green")).strip().lower()
        if chon_saved in ["y", "yes", ""]:
            use_saved = True
            open_method = "search"
            current_device = saved_device
            adb_manager = ADBManager()
            if saved_device:
                adb_manager.selected_device = saved_device
            logger.info("Tai su dung phuong thuc: search")

    # 2. Neu khong dung lai cau hinh cu, thiet lap moi
    if not use_saved:
        print(colored("════════════════════════════════════════════════", "white"))
        print(colored("📱 Cau hinh Ket noi & Auto Click:", "cyan", bold=True))
        print(colored("   [1] ⭐ Chay TU DONG: Mo Link & Tu Auto Click (Dung ADB cho PC/Gia lap)", "white"))
        print(colored("   [2] 📱 Chay qua WiFi (uiautomator2): Nhap IP:Port dien thoai de ket noi", "cyan"))
        print(colored("   [3] ✍️  Chay Thu Cong: Chi hien Link, ban TU CLICK BANG TAY tren dien thoai", "white"))
        print(colored("   [4] 🔍 Tim kiem user TikTok de Follow (dung thanh search trong app)", "yellow"))
        print(colored("════════════════════════════════════════════════", "white"))

        while True:
            conn_choice = input(colored("👉 Chon phuong thuc ket noi (1-4, Mac dinh 1): ", "green")).strip()
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
                logger.warning("Lua chon khong hop le, hay thu lai!")

        if open_method == "adb":
            adb_manager = ADBManager()
            current_device = adb_manager.select_device()
            if not current_device:
                logger.warning("Chua chon duoc thiet bi cu the! He thong se co ket noi den ADB mac dinh...")
            adb_config["open_method"] = "adb"
            adb_config["current_device"] = current_device
            save_adb_config(adb_config)
        elif open_method == "u2":
            print(colored("\n📡 KET NOI UIAUTOMATOR2 QUA WIFI:", "cyan"))
            while True:
                ip_port = input(colored("👉 Nhap IP:Port dien thoai (vi du: 192.168.1.10:5555): ", "green")).strip()
                parts = ip_port.split(":")
                if len(parts) == 2 and parts[1].isdigit() and parts[0]:
                    break
                logger.warning("Dinh dang khong hop le! Nhap dang IP:Port (vd: 192.168.1.10:5555)")
            current_device = ip_port
            adb_manager = ADBManager()
            logger.info(f"Se ket noi uiautomator2 den: {current_device}")
            save_choice = input(colored("💾 Luu thiet bi nay lai de dung nhanh lan sau? (y/n, Enter la Co): ", "green")).strip().lower()
            if save_choice in ["y", "yes", ""]:
                adb_config["open_method"] = "u2"
                adb_config["current_device"] = current_device
                save_adb_config(adb_config)
                logger.info(f"Da luu thiet bi: {current_device}")
            else:
                adb_config["open_method"] = "u2"
                adb_config["current_device"] = None
                save_adb_config(adb_config)
        elif open_method == "search":
            adb_manager = ADBManager()
            current_device = adb_manager.select_device()
            if not current_device:
                logger.warning("Chua chon duoc thiet bi cu the!")
            adb_config["open_method"] = "search"
            adb_config["current_device"] = current_device
            save_adb_config(adb_config)
        else:
            adb_config["open_method"] = open_method
            adb_config["current_device"] = None
            save_adb_config(adb_config)

    # Lay danh sach acc
    api_client = GolikeAPIClient()
    api_client.set_auth(auth_token)

    try:
        accounts = api_client.get('/api/tiktok-account')
    except Exception as e:
        logger.error(f"Loi lay danh sach tai khoan: {e}")
        print(colored("🚨 Loi ket noi API! Hay kiem tra lai.", "red"))
        input(colored("Nhan Enter de quay lai...", "white"))
        return

    if not accounts or accounts.get("status") != 200 or not accounts.get("data"):
        print(colored("🚨 Authorization hoac T sai hoac khong co tai khoan. Hay nhap lai!", "red"))
        logger.error("Authorization khong hop le hoac khong co tai khoan")
        input(colored("Nhan Enter de quay lai...", "white"))
        return

    print(colored(f"🚨 Dia chi Ip  : 👀{get_public_ip()}👀", "white"))
    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("🆔 Danh sach acc Tik Tok :", "yellow"))
    print(colored("════════════════════════════════════════════════", "white"))
    data = accounts.get("data", [])
    if not isinstance(data, list) or not data:
        print(colored("Khong co tai khoan TikTok nao!", "red"))
        input(colored("Nhan Enter de quay lai...", "white"))
        return
    for idx, acc in enumerate(data, 1):
        print(colored(f"[{idx}] 🆔 : {acc.get('unique_username', 'N/A')} ♦️ : ✅", "cyan"))
    print(colored("════════════════════════════════════════════════", "white"))

    print(colored("Huong dan: Ban co the nhap so thu tu hoac ID tai khoan.", "cyan"))
    while True:
        acc_input = input(colored("☀️ Nhap so thu tu hoac ID Acc Tiktok: ", "green")).strip()
        if acc_input.isdigit() and 1 <= int(acc_input) <= len(data):
            acc_index = int(acc_input) - 1
            acc_obj = data[acc_index]
            account_id = acc_obj.get("id")
            logger.info(f"Da chon tai khoan [{acc_input}]: {acc_obj.get('unique_username', 'N/A')}")
            break
        elif acc_input:
            acc_obj = next((a for a in data if a.get("unique_username") == acc_input), None)
            if acc_obj:
                account_id = acc_obj.get("id")
                break
            else:
                logger.warning("Acc nay chua duoc them vao golike or id sai")
        else:
            logger.warning("Vui long nhap so thu tu hoac ID hop le!")

    delay = input_int("👀 Nhap thoi gian lam job : ")

    doiacc = input_int("📆 So job fail de doi acc TikTok (nhap 1 neu k muon dung) : ")
    while True:
        print(colored("════════════════════════════════════════════════", "white"))
        print(colored("♦️ ✈ Nhap 1 : Chi nhan nhiem vu Follow", "yellow"))
        print(colored("🔥 ✈ Nhap 2 : Chi nhan nhiem vu like", "yellow"))
        print(colored("💥 ✈ Nhap 12 : Ket hop ca Like va Follow", "yellow"))
        print(colored("🔍 Nhap 3 : Search Follow (thanh search) + ADB Like (mo link)", "yellow"))
        print(colored("════════════════════════════════════════════════", "white"))
        chedo = input(colored("✅ Chon lua chon: ", "cyan")).strip()
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
        print(colored("🔍 Cau hinh Tim kiem:", "cyan", bold=True))
        try:
            v = input(colored("⏱️  Thoi gian cho toi da khi search (giay, mac dinh 5): ", "green")).strip()
            search_timeout = int(v) if v else 5
        except ValueError:
            search_timeout = 5
        try:
            v = input(colored("🔄 So lan thu lai neu khong tim thay ket qua (mac dinh 3): ", "green")).strip()
            search_retry = int(v) if v else 3
        except ValueError:
            search_retry = 3
        logger.info(f"Search timeout: {search_timeout}s | Retry: {search_retry} lan")

    # Bat dau vong lap lam job
    dem = tong = checkdoiacc = 0
    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("|🆔| ⏱️ ┊ Status | So Jos | ID Acc | Xu | Tong", "cyan"))
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
        logger.error(f"Loi tao job processor: {e}")
        print(colored(f"❌ Loi tao job processor: {e}", "red"))
        input(colored("Nhan Enter de quay lai...", "white"))
        return

    ui_automator = None
    if UI_AUTOMATION_AVAILABLE:
        try:
            ui_automator = TikTokUIAutomator(device_id=current_device)
            if open_method == "u2":
                ui_automator.connect()
            logger.info("UI Automation da san sang")
            print(colored("🤖 [He Thong] Da kich hoat thanh cong Module Auto Click!", "green", bold=True))
        except Exception as e:
            logger.warning(f"Khong the tao UI automator: {e}")
            print(colored(f"⚠️ Khong the khoi dong UI automator: {e}", "yellow"))
            ui_automator = None

    if open_method == "u2" and isinstance(job_processor, U2JobProcessor) and ui_automator and ui_automator._u2:
        job_processor._u2_device = ui_automator._u2
        logger.info("Da inject u2 device chung vao U2JobProcessor")

    while True:
        # Doi acc neu vuot gioi han fail
        if checkdoiacc >= doiacc:
            _select_new_account(data, account_id, checkdoiacc)

        # Nhan job
        print(colored("🔎 Dang Tim Nhiem vu:>        ", "pink"), end="\r")
        try:
            nhanjob = api_client.get(f'/api/advertising/publishers/tiktok/jobs?account_id={account_id}&data=null')
        except Exception as e:
            logger.error(f"Loi lay job: {e}")
            time.sleep(10)
            continue

        if not nhanjob or not nhanjob.get("data"):
            time.sleep(10)
            continue

        # Check job trung
        if prev_job and prev_job.get("data", {}).get("link") == nhanjob.get("data", {}).get("link") and prev_job.get("data", {}).get("type") == nhanjob.get("data", {}).get("type"):
            logger.warning("Job trung lap, bo qua")
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
            time.sleep(10)
            continue

        if not link:
            logger.warning("Job khong co link, bo qua")
            _skip_job(api_client, ads_id, object_id, account_id, job_type)
            time.sleep(2)
            continue

        if job_type not in lam:
            _skip_job(api_client, ads_id, object_id, account_id, job_type)
            print(colored(f"❌ Da bo qua job {job_type}!", "yellow"), end="\r")
            time.sleep(1)
            continue

        # Xu ly job chinh
        ok, reward, not_found = _process_single_job(
            api_client, ads_id, link, object_id, account_id,
            job_type, ui_automator, job_processor,
            delay, open_method, search_mode,
            stt=dem + 1, tong=tong
        )

        if not_found:
            checkdoiacc += 1
            continue

        if ok:
            dem += 1
            tong += reward
            checkdoiacc = 0
        else:
            logger.warning("Nhan tien that bai sau 2 lan retry → Skip job")
            _skip_job(api_client, ads_id, object_id, account_id, job_type)
            time.sleep(1)
            checkdoiacc += 1


def _select_new_account(data: List[Dict], account_id: str, checkdoiacc: int) -> str:
    """Hien thi lai danh sach va chon acc moi."""
    print(colored(f"🚨 Dia chi Ip  : 👀{get_public_ip()}👀", "white"))
    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("🆔 Danh sach acc Tik Tok :", "yellow"))
    print(colored("════════════════════════════════════════════════", "white"))
    for idx, acc in enumerate(data, 1):
        print(colored(f"[{idx}] 🆔 : {acc.get('unique_username', 'N/A')} ♦️ : ✅", "cyan"))
    print(colored("════════════════════════════════════════════════", "white"))
    while True:
        acc_input = input(colored("⚡ Job fail dat gioi han, nhap so thu tu hoac ID acc moi: ", "red")).strip()
        if acc_input.isdigit() and 1 <= int(acc_input) <= len(data):
            acc_index = int(acc_input) - 1
            acc_obj = data[acc_index]
            new_id = acc_obj.get("id")
            logger.info(f"Da chon tai khoan [{acc_input}]: {acc_obj.get('unique_username', 'N/A')}")
            return new_id
        elif acc_input:
            acc_obj = next((a for a in data if a.get("unique_username") == acc_input), None)
            if acc_obj:
                return acc_obj.get("id")
            else:
                logger.warning("Acc nay chua duoc them vao golike or id sai")
        else:
            logger.warning("Vui long nhap so thu tu hoac ID hop le!")


def _duplicate_job_skip(api_client: GolikeAPIClient, nhanjob: Dict, account_id: str) -> None:
    """Skip job trung lap."""
    try:
        api_client.post('/api/report/send', {
            "description": "Bao cao hoan thanh that bai",
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
        logger.error(f"Loi bao cao job trung: {e}")