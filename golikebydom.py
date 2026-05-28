import os
import sys
import time
import json
import requests
import subprocess
import re

# Thiết lập encoding UTF-8 cho Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, 'strict')

# Thiết lập timezone Việt Nam
import pytz
from datetime import datetime
tz = pytz.timezone("Asia/Ho_Chi_Minh")

AUTH_FILE = "Authorization.txt"
ADB_CONFIG_FILE = "adb_config.json"
ADB_PATH = r"D:\pythonadb\ADB\adb.exe"

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
    print(colored("📱 Nhập 2 để Quản lý thiết bị ADB", "cyan"))
    print(colored("🥈 Nhập 3 Để Xóa Authorization Hiện Tại", "red"))

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

# ============ ADB Functions ============

def check_adb():
    """Kiểm tra ADB có sẵn không"""
    try:
        result = subprocess.run([ADB_PATH, 'version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return True
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return False

def get_adb_devices():
    """Lấy danh sách thiết bị ADB đang kết nối"""
    try:
        result = subprocess.run([ADB_PATH, 'devices'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            devices = []
            for line in lines[1:]:  # Bỏ dòng header
                parts = line.split('\t')
                if len(parts) >= 2:
                    devices.append({'id': parts[0], 'status': parts[1]})
            return devices
    except Exception:
        pass
    return []

def connect_adb_wifi(ip, port=5555):
    """Kết nối thiết bị qua ADB WiFi"""
    try:
        result = subprocess.run([ADB_PATH, 'connect', f'{ip}:{port}'], capture_output=True, text=True, timeout=10)
        return result.returncode == 0 and 'connected' in result.stdout.lower()
    except Exception:
        return False

def disconnect_adb_wifi(ip, port=5555):
    """Ngắt kết nối ADB WiFi"""
    try:
        subprocess.run([ADB_PATH, 'disconnect', f'{ip}:{port}'], capture_output=True, timeout=5)
        return True
    except Exception:
        return False

def restart_adb_server():
    """Restart ADB server để kết nối lại qua USB"""
    try:
        print(colored("🔄 Đang tắt ADB server...", "cyan"))
        subprocess.run([ADB_PATH, 'kill-server'], capture_output=True, timeout=5)
        time.sleep(1)
        print(colored("🔄 Đang khởi động ADB server...", "cyan"))
        subprocess.run([ADB_PATH, 'start-server'], capture_output=True, timeout=5)
        time.sleep(2)
        return True
    except Exception as e:
        print(colored(f"❌ Lỗi restart ADB: {e}", "red"))
        return False

def open_link_adb(link, device_id=None):
    """Mở link bằng ADB trên thiết bị Android"""
    try:
        cmd = [ADB_PATH]
        if device_id:
            cmd.extend(['-s', device_id])
        cmd.extend(['shell', 'am', 'start', '-a', 'android.intent.action.VIEW', '-d', link])
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False

def get_adb_device_info(device_id):
    """Lấy thông tin thiết bị ADB"""
    try:
        cmd = [ADB_PATH, '-s', device_id, 'shell', 'getprop', 'ro.product.model']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        model = result.stdout.strip() if result.returncode == 0 else "Unknown"

        cmd = [ADB_PATH, '-s', device_id, 'shell', 'getprop', 'ro.build.version.release']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        android_version = result.stdout.strip() if result.returncode == 0 else "Unknown"

        return f"{model} (Android {android_version})"
    except Exception:
        return "Unknown"

def save_adb_config(config):
    """Lưu cấu hình ADB"""
    with open(ADB_CONFIG_FILE, "w", encoding="utf8") as f:
        json.dump(config, f, indent=2)

def load_adb_config():
    """Đọc cấu hình ADB"""
    if os.path.exists(ADB_CONFIG_FILE):
        try:
            with open(ADB_CONFIG_FILE, "r", encoding="utf8") as f:
                return json.load(f)
        except:
            pass
    return {"devices": [], "current_device": None, "open_method": "termux"}

def adb_menu():
    """Menu quản lý ADB"""
    while True:
        os.system("clear" if os.name == "posix" else "cls")
        print(colored("════════════════════════════════════════════════", "white"))
        print(colored("📱 QUẢN LÝ THIẾT BỊ ADB", "yellow"))
        print(colored("════════════════════════════════════════════════", "white"))

        if not check_adb():
            print(colored("❌ ADB không được cài đặt hoặc không có trong PATH!", "red"))
            print(colored("   Hãy cài đặt Android SDK Platform Tools", "yellow"))
            input(colored("Nhấn Enter để quay lại...", "white"))
            return

        devices = get_adb_devices()
        config = load_adb_config()

        print(colored(f"📊 Thiết bị đang kết nối: {len(devices)}", "cyan"))
        if devices:
            for idx, dev in enumerate(devices, 1):
                device_id = dev['id']
                status = dev['status']
                if status == 'device':
                    info = get_adb_device_info(device_id)
                    status_icon = "✅"
                elif status == 'unauthorized':
                    info = "N/A (chưa authorize)"
                    status_icon = "⚠️"
                else:
                    info = "N/A (offline)"
                    status_icon = "❌"
                marker = "👉 " if config.get("current_device") == device_id else "   "
                print(colored(f"{marker}[{idx}] {device_id} [{status_icon} {status}] - {info}", "white"))
        else:
            print(colored("   Không có thiết bị nào đang kết nối", "yellow"))

        print(colored("════════════════════════════════════════════════", "white"))
        print(colored("🔌 Nhập 1 : Kết nối thiết bị qua USB", "yellow"))
        print(colored("📶 Nhập 2 : Kết nối thiết bị qua WiFi", "yellow"))
        print(colored("📱 Nhập 3 : Chọn thiết bị để sử dụng", "yellow"))
        print(colored("🔓 Nhập 4 : Ngắt kết nối thiết bị WiFi", "yellow"))
        print(colored("📋 Nhập 5 : Xem danh sách thiết bị đã lưu", "yellow"))
        print(colored("🗑️  Nhập 6 : Xóa thiết bị đã lưu", "yellow"))
        print(colored("⚙️  Nhập 7 : Chọn cách mở link (ADB/Termux)", "yellow"))
        print(colored("🔙 Nhập 0 : Quay lại menu chính", "yellow"))
        print(colored("════════════════════════════════════════════════", "white"))

        choice = input(colored("✅ Chọn: ", "cyan")).strip()

        if choice == "0":
            return
        elif choice == "1":
            # Kết nối USB
            print(colored("════════════════════════════════════════════════", "white"))
            print(colored("🔄 Đang restart ADB server để kết nối qua USB...", "cyan"))
            if restart_adb_server():
                print(colored("✅ Đã restart ADB server!", "green"))
                print(colored("   Hãy đảm bảo:", "yellow"))
                print(colored("   1. Điện thoại đã kết nối qua USB", "yellow"))
                print(colored("   2. Đã bật USB Debugging trên điện thoại", "yellow"))
                print(colored("   3. Đã authorize máy tính trên điện thoại", "yellow"))
                print(colored("   4. Nhấn 'Allow' khi popup hiện lên", "yellow"))
                input(colored("Nhấn Enter để quét thiết bị...", "white"))
                # Quét lại thiết bị
                devices = get_adb_devices()
                if devices:
                    print(colored(f"✅ Tìm thấy {len(devices)} thiết bị!", "green"))
                    for dev in devices:
                        device_id = dev['id']
                        status = dev['status']
                        if status == 'device':
                            info = get_adb_device_info(device_id)
                            status_icon = "✅"
                        elif status == 'unauthorized':
                            info = "N/A (chưa authorize)"
                            status_icon = "⚠️"
                        else:
                            info = "N/A (offline)"
                            status_icon = "❌"
                        print(colored(f"   - {device_id} [{status_icon} {status}] - {info}", "white"))
                else:
                    print(colored("❌ Không tìm thấy thiết bị nào!", "red"))
                input(colored("Nhấn Enter để tiếp tục...", "white"))
            else:
                print(colored("❌ Restart ADB thất bại!", "red"))
                input(colored("Nhấn Enter để tiếp tục...", "white"))

        elif choice == "2":
            # Kết nối WiFi
            print(colored("════════════════════════════════════════════════", "white"))
            ip_input = input(colored("📡 Nhập IP thiết bị (ví dụ: 192.168.1.100 hoặc 192.168.1.100:5555): ", "green")).strip()
            
            ip = ip_input
            port = 5555
            if ":" in ip_input:
                parts = ip_input.split(":")
                if len(parts) == 2:
                    ip = parts[0]
                    if parts[1].isdigit():
                        port = int(parts[1])
            
            if ":" not in ip_input:
                port_input = input(colored("🔌 Nhập port (mặc định 5555): ", "green")).strip()
                port = int(port_input) if port_input.isdigit() else 5555

            print(colored(f"🔄 Đang kết nối đến {ip}:{port}...", "cyan"))
            if connect_adb_wifi(ip, port):
                print(colored(f"✅ Kết nối thành công!", "green"))
                # Lưu vào config
                if ip not in config.get("devices", []):
                    config.setdefault("devices", []).append(ip)
                    save_adb_config(config)
                time.sleep(2)
            else:
                print(colored(f"❌ Kết nối thất bại!", "red"))
                print(colored("   Hãy đảm bảo:", "yellow"))
                print(colored("   1. Thiết bị đã bật USB Debugging", "yellow"))
                print(colored("   2. Thiết bị đã bật ADB over WiFi", "yellow"))
                print(colored("   3. Điện thoại và máy tính cùng mạng WiFi", "yellow"))
                input(colored("Nhấn Enter để tiếp tục...", "white"))

        elif choice == "3":
            # Chọn thiết bị
            if not devices:
                print(colored("❌ Không có thiết bị nào đang kết nối!", "red"))
                input(colored("Nhấn Enter để tiếp tục...", "white"))
                continue

            print(colored("════════════════════════════════════════════════", "white"))
            dev_choice = input(colored("📱 Nhập số thứ tự thiết bị: ", "green")).strip()
            if dev_choice.isdigit() and 1 <= int(dev_choice) <= len(devices):
                selected = devices[int(dev_choice) - 1]['id']
                config["current_device"] = selected
                save_adb_config(config)
                print(colored(f"✅ Đã chọn thiết bị: {selected}", "green"))
                time.sleep(2)
            else:
                print(colored("❌ Lựa chọn không hợp lệ!", "red"))
                time.sleep(1)

        elif choice == "4":
            # Ngắt kết nối WiFi
            print(colored("════════════════════════════════════════════════", "white"))
            saved_devices = config.get("devices", [])
            if not saved_devices:
                print(colored("❌ Không có thiết bị WiFi nào đã lưu!", "yellow"))
                input(colored("Nhấn Enter để tiếp tục...", "white"))
                continue

            print(colored("📋 Danh sách thiết bị WiFi:", "cyan"))
            for idx, ip in enumerate(saved_devices, 1):
                print(colored(f"   [{idx}] {ip}", "white"))

            dev_choice = input(colored("🔓 Nhập số để ngắt kết nối (0 để hủy): ", "green")).strip()
            if dev_choice == "0":
                continue
            if dev_choice.isdigit() and 1 <= int(dev_choice) <= len(saved_devices):
                ip = saved_devices[int(dev_choice) - 1]
                if disconnect_adb_wifi(ip):
                    print(colored(f"✅ Đã ngắt kết nối {ip}", "green"))
                    saved_devices.remove(ip)
                    save_adb_config(config)
                else:
                    print(colored(f"❌ Không thể ngắt kết nối {ip}", "red"))
                time.sleep(2)

        elif choice == "5":
            # Xem danh sách đã lưu
            print(colored("════════════════════════════════════════════════", "white"))
            saved_devices = config.get("devices", [])
            if saved_devices:
                print(colored("📋 Thiết bị đã lưu:", "cyan"))
                for ip in saved_devices:
                    print(colored(f"   - {ip}", "white"))
            else:
                print(colored("❌ Chưa có thiết bị nào được lưu", "yellow"))
            input(colored("Nhấn Enter để tiếp tục...", "white"))

        elif choice == "6":
            # Xóa thiết bị đã lưu
            print(colored("════════════════════════════════════════════════", "white"))
            saved_devices = config.get("devices", [])
            if not saved_devices:
                print(colored("❌ Không có thiết bị nào để xóa!", "yellow"))
                input(colored("Nhấn Enter để tiếp tục...", "white"))
                continue

            print(colored("📋 Danh sách thiết bị:", "cyan"))
            for idx, ip in enumerate(saved_devices, 1):
                print(colored(f"   [{idx}] {ip}", "white"))

            dev_choice = input(colored("🗑️  Nhập số để xóa (0 để hủy): ", "green")).strip()
            if dev_choice == "0":
                continue
            if dev_choice.isdigit() and 1 <= int(dev_choice) <= len(saved_devices):
                ip = saved_devices[int(dev_choice) - 1]
                saved_devices.remove(ip)
                save_adb_config(config)
                print(colored(f"✅ Đã xóa {ip}", "green"))
                time.sleep(2)

        elif choice == "7":
            # Chọn cách mở link
            print(colored("════════════════════════════════════════════════", "white"))
            print(colored("⚙️  Chọn cách mở link:", "cyan"))
            print(colored("   1. Mở bằng ADB (tự động trên thiết bị)", "white"))
            print(colored("   2. Mở bằng Termux (chỉ trên Android)", "white"))
            print(colored("   3. Mở thủ công (hiển thị link)", "white"))

            method_choice = input(colored("✅ Chọn: ", "green")).strip()
            if method_choice == "1":
                config["open_method"] = "adb"
                save_adb_config(config)
                print(colored("✅ Đã chọn: Mở bằng ADB", "green"))
            elif method_choice == "2":
                config["open_method"] = "termux"
                save_adb_config(config)
                print(colored("✅ Đã chọn: Mở bằng Termux", "green"))
            elif method_choice == "3":
                config["open_method"] = "manual"
                save_adb_config(config)
                print(colored("✅ Đã chọn: Mở thủ công", "green"))
            else:
                print(colored("❌ Lựa chọn không hợp lệ!", "red"))
            time.sleep(2)

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
        choose = input(colored("🥇 Nhập Lựa Chọn (1, 2 hoặc 3): ", "white")).strip()
        if choose == "3":
            clear_auth()
            continue
        elif choose == "2":
            adb_menu()
            continue
        elif choose == "1":
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

    # Load ADB config
    adb_config = load_adb_config()
    open_method = adb_config.get("open_method", "termux")
    current_device = adb_config.get("current_device")

    # Hiển thị cấu hình ADB
    print(colored("════════════════════════════════════════════════", "white"))
    print(colored("📱 Cấu hình ADB:", "cyan"))
    print(colored(f"   Cách mở link: {open_method}", "white"))
    if current_device:
        print(colored(f"   Thiết bị: {current_device}", "white"))
    else:
        print(colored(f"   Thiết bị: Chưa chọn (sử dụng thiết bị mặc định)", "yellow"))
    print(colored("════════════════════════════════════════════════", "white"))

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
            # Mở link theo phương thức đã chọn
            opened = False
            if open_method == "adb":
                # Mở bằng ADB
                if open_link_adb(link, current_device):
                    opened = True
                    print(colored(f"📱 Đã mở link bằng ADB", "green"), end="\r")
                else:
                    print(colored(f"❌ Không thể mở bằng ADB", "red"), end="\r")
            elif open_method == "termux":
                # Mở bằng Termux
                try:
                    code = os.system(f"termux-open-url {link}")
                    if code == 0:
                        opened = True
                except:
                    pass
            # Nếu không mở được, hiển thị link
            if not opened:
                print(colored(f"🔗 Link: {link}", "yellow"))
                print(colored("   Vui lòng mở thủ công...", "cyan"))
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