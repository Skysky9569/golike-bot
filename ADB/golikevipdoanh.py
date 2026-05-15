import os
import sys
import time
import json
import requests

# Thiết lập timezone Việt Nam
import pytz
from datetime import datetime
tz = pytz.timezone("Asia/Ho_Chi_Minh")

AUTH_FILE = "Authorization.txt"

def colored(text, color):
    colors = {
        "yellow": "\033[1;33m",
        "pink": "\033[1;35m",
        "cyan": "\033[1;36m",
        "white": "\033[1;97m",
        "green": "\033[1;32m",
        "red": "\033[1;31m",
        "reset": "\033[0m"
    }
    return colors.get(color, "") + text + colors["reset"]

def banner():
    os.system("clear" if os.name == "posix" else "cls")
    banner_text = f"""
{colored('██████  ████████████████', 'yellow')}
{colored('██      ██  █Bóng  X                   ███  ', 'pink')}
{colored('██████  ████Siêu đẹp trai và đáng yêu  ███  ', 'cyan')}
{colored('██      ██ █   Trần Đức Doanh   ██ ', 'white')}
{colored('██████  ████████████████████████', 'green')}
{colored('╚═╝     ╚═╝         ╚═╝    ╚════╝  ╚════╝ ╚═════╝', 'red')}
{colored('Tool By: Bóng X            Phiên Bản: 1.0', 'white')}
{colored('════════════════════════════════════════════════', 'white')}
{colored('👑 Tool  Bóng x: 💀 Tik - Tok💀', 'white')}
{colored('🆔 Tên   : 👑 BÓNG X 👑', 'white')}
{colored('📱 Tik Tok : https://www.tiktok.com/@doanh21105', 'white')}
{colored('🌅 Zalo     : 🧠0865526740🧠', 'white')}
{colored('❤️‍🔥 Telegram : ⚡https://t.me/doanhvip1⚡', 'white')}
{colored('════════════════════════════════════════════════', 'white')}
{colored('⚠️ Lưu ý    : 🌟Tool Sử Dụng Cho Android🌟', 'white')}
{colored('════════════════════════════════════════════════', 'white')}
"""
    print(banner_text)

def read_auth():
    if os.path.exists(AUTH_FILE):
        with open(AUTH_FILE, "r", encoding="utf8") as f:
            return f.read().strip()
    return ""

def write_auth(auth):
    with open(AUTH_FILE, "w", encoding="utf8") as f:
        f.write(auth.strip())

def clear_auth():
    if os.path.exists(AUTH_FILE):
        os.remove(AUTH_FILE)
        print(colored(f"[✔] Đã xóa {AUTH_FILE}!", "green"))
    else:
        print(colored(f"[!] File {AUTH_FILE} không tồn tại!", "yellow"))

def menu():
    banner()
    print(colored("🆔 Địa chỉ Ip  : 🚨192.168.1.1🚨", "white"))
    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("🥇 Nhập 1 để vào Tool Tiktok", "white"))
    print(colored("🥈 Nhập 2 Để Xóa Authorization Hiện Tại", "red"))

def build_headers(auth):
    return {
        'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8',
        'Referer': 'https://app.golike.net/',
        'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': "Windows",
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'T': 'VFZSak1FMTZZM3BOZWtFd1RtYzlQUT09',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
        "Authorization": auth,
        'Content-Type': 'application/json;charset=utf-8'
    }

def get_tiktok_accounts(headers):
    try:
        res = requests.get('https://gateway.golike.net/api/tiktok-account', headers=headers, timeout=10)
        return res.json()
    except Exception as e:
        print(colored(f"Lỗi kết nối API: {e}", "red"))
        return {}

def get_jobs(account_id, headers):
    try:
        url = f'https://gateway.golike.net/api/advertising/publishers/tiktok/jobs?account_id={account_id}&data=null'
        res = requests.get(url, headers=headers, timeout=10)
        return res.json()
    except Exception as e:
        print(colored(f"Lỗi lấy job: {e}", "red"))
        return {}

def complete_job(ads_id, account_id, headers):
    try:
        url = 'https://gateway.golike.net/api/advertising/publishers/tiktok/complete-jobs'
        data = {
            "ads_id": ads_id,
            "account_id": account_id,
            "async": True,
            "data": None
        }
        res = requests.post(url, data=json.dumps(data), headers=headers, timeout=15)
        return res.json()
    except Exception as e:
        print(colored(f"Lỗi hoàn thành job: {e}", "red"))
        return {}

def report_job(ads_id, object_id, account_id, job_type, headers):
    data1 = {
        "description": "Báo cáo hoàn thành thất bại",
        "users_advertising_id": ads_id,
        "type": "ads",
        "provider": "tiktok",
        "fb_id": account_id,
        "error_type": 6
    }
    try:
        requests.post('https://gateway.golike.net/api/report/send', data=json.dumps(data1), headers=headers, timeout=8)
    except: pass

    data2 = {
        "ads_id": ads_id,
        "object_id": object_id,
        "account_id": account_id,
        "type": job_type
    }
    try:
        requests.post('https://gateway.golike.net/api/advertising/publishers/tiktok/skip-jobs', data=json.dumps(data2), headers=headers, timeout=8)
    except: pass

def show_accounts(accounts):
    print(colored("🚨 Địa chỉ Ip  : 👀192.168.1.1👀", "white"))
    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("🆔 Danh sách acc Tik Tok :", "yellow"))
    print(colored("════════════════════════════════════════════════", "white"))
    data = accounts.get("data", [])
    if not isinstance(data, list) or not data:
        print(colored("Không có tài khoản TikTok nào!", "red"))
        return
    for idx, acc in enumerate(data, 1):
        print(colored(f"[{idx}] 🆔 : {acc.get('unique_username', 'N/A')} ♦️ : ✅", "cyan"))
    print(colored("════════════════════════════════════════════════", "white"))

def input_int(prompt, color="green", minval=1):
    while True:
        value = input(colored(prompt, color)).strip()
        if value.isdigit() and int(value) >= minval:
            return int(value)
        print(colored(f"Vui lòng nhập số nguyên >= {minval}!", "red"))

def main():
    # Bỏ kiểm tra version/tool bảo trì để tool luôn chạy
    while True:
        menu()
        choose = input(colored("🥇 Nhập Lựa Chọn (1 hoặc 2): ", "white")).strip()
        if choose == "2":
            clear_auth()
            continue
        if choose == "1":
            break

    auth = read_auth()
    while not auth:
        auth = input(colored("📢 Nhập Authorization: ", "green")).strip()
        if auth:
            write_auth(auth)
    headers = build_headers(auth)
    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("🚀 Đăng nhập thành công! Đang vào Tool Tiktok...", "green"))
    time.sleep(1)
    # Lấy danh sách acc
    accounts = get_tiktok_accounts(headers)
    if not accounts or accounts.get("status") != 200 or not accounts.get("data"):
        print(colored("🚨 Authorization hoặc T sai hoặc không có tài khoản. Hãy nhập lại!", "red"))
        sys.exit()
    show_accounts(accounts)
    # Chọn acc
    while True:
        idacc = input(colored("☀️ Nhập ID Acc Tiktok Vào: ", "green")).strip()
        acc_obj = next((a for a in accounts.get("data", []) if a.get("unique_username") == idacc), None)
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
        print(colored("💥 Nhập 12 : Kết hợp cả Like và Follow", "yellow"))
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
    while True:
        if checkdoiacc >= doiacc:
            show_accounts(accounts)
            idacc = input(colored("⚡ Job fail đạt giới hạn, nhập acc mới: ", "red")).strip()
            acc_obj = next((a for a in accounts.get("data", []) if a.get("unique_username") == idacc), None)
            if acc_obj:
                account_id = acc_obj.get("id")
                checkdoiacc = 0
            else:
                print(colored("⚠️ Acc này chưa được thêm vào golike or id sai", "red"))
                continue
        # Nhận job
        print(colored("🔎 Đang Tìm Nhiệm vụ:>        ", "pink"), end="\r")
        nhanjob = get_jobs(account_id, headers)
        if not nhanjob or not nhanjob.get("data"):
            time.sleep(10)
            continue
        # Check job trùng
        if prev_job and prev_job.get("data", {}).get("link") == nhanjob.get("data", {}).get("link") and prev_job.get("data", {}).get("type") == nhanjob.get("data", {}).get("type"):
            print(colored("🏚️ Job trùng với job trước đó - Bỏ qua!", "red"), end="\r")
            time.sleep(2)
            if nhanjob.get("data"):
                report_job(nhanjob["data"].get("id"), nhanjob["data"].get("object_id"), account_id, nhanjob["data"].get("type"), headers)
            continue
        prev_job = nhanjob
        if nhanjob.get("status") == 200:
            data = nhanjob["data"]
            ads_id = data.get("id")
            link = data.get("link")
            object_id = data.get("object_id")
            job_type = data.get("type")
            if not link:
                print(colored("🗑️ Job die - Không có link!", "red"), end="\r")
                time.sleep(2)
                report_job(ads_id, object_id, account_id, job_type, headers)
                continue
            if job_type not in lam:
                report_job(ads_id, object_id, account_id, job_type, headers)
                print(colored(f"❌ Đã bỏ qua job {job_type}!", "yellow"), end="\r")
                time.sleep(1)
                continue
            # Mở link (nếu chạy trên Termux Android, nếu không hãy mở tay)
            opened = False
            try:
                code = os.system(f"termux-open-url {link}")
                if code == 0:
                    opened = True
            except:
                pass
            if not opened:
                print(colored(f"Vui lòng mở link thủ công: {link}", "yellow"))
            for t in range(delay, -1, -1):
                print(colored(f"⏰ Đợi {t} giây ...", "cyan"), end="\r")
                time.sleep(1)
            # Nhận tiền
            ok = False
            for lan in range(1, 3 if lannhan == "y" else 2):
                nhantien = complete_job(ads_id, account_id, headers)
                if nhantien.get("status") == 200:
                    ok = True
                    dem += 1
                    tien = nhantien["data"].get("prices", 0)
                    tong += tien
                    now = datetime.now(tz).strftime("%H:%M:%S")
                    print(colored(f"| {dem} | {now} | success | {nhantien['data'].get('type', '')} | Ẩn ID | +{tien} | {tong}", "green"))
                    checkdoiacc = 0
                    break
                elif lan == 2:
                    break
                print(colored(f"⏰ Đang Nhận Tiền Lần 2:>        ", "pink"), end="\r")
            if not ok:
                report_job(ads_id, object_id, account_id, job_type, headers)
                print(colored("⚠️ Đã bỏ qua job:>        ", "red"), end="\r")
                time.sleep(1)
                checkdoiacc += 1
        else:
            time.sleep(10)

if __name__ == "__main__":
    main()