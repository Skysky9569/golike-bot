"""
ADB WiFi/USB management menu.
"""
import os
import time

from golike_core.adb_manager import ADBManager, load_adb_config, save_adb_config, colored
from golike_core.security import InputValidator


def adb_menu() -> None:
    """Menu quan ly ket noi ADB WiFi/USB nang cao"""
    validator = InputValidator()
    adb_manager = ADBManager()

    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print(colored("════════════════════════════════════════════════", "cyan", bold=True))
        print(colored("📶 QUAN LY KET NOI THIET BI ADB WIFI/USB", "yellow", bold=True))
        print(colored("════════════════════════════════════════════════", "cyan"))

        if not adb_manager.check_adb():
            print(colored("❌ Khong tim thay adb.exe! Hay kiem tra thu muc ADB.", "red"))
            input(colored("Nhan Enter de quay lai...", "white"))
            return

        devices = adb_manager.check_connected_devices()
        config = load_adb_config()

        print(colored(f"📊 Thiet bi dang ket noi (Online): {len(devices)}", "green"))
        if devices:
            for idx, device_id in enumerate(devices, 1):
                marker = "👉 " if config.get("current_device") == device_id else "   "
                print(colored(f"{marker}[{idx}] 🆔 {device_id} [✅ Device Online]", "white"))
        else:
            print(colored("   ⚠️ Hien tai khong co thiet bi ADB nao dang ket noi online", "yellow"))

        print(colored("════════════════════════════════════════════════", "cyan"))
        print(colored("🔌 Nhap 1 : Khoi dong lai ADB Server (Sua loi ngat ket noi USB)", "yellow"))
        print(colored("📶 Nhap 2 : Ket noi thiet bi qua IP WiFi (Khong can day)", "yellow"))
        print(colored("📱 Nhap 3 : Chon thiet bi mac dinh de su dung", "yellow"))
        print(colored("🔓 Nhap 4 : Ngat ket noi thiet bi WiFi", "yellow"))
        print(colored("📋 Nhap 5 : Xem danh sach IP WiFi da luu", "yellow"))
        print(colored("🗑️  Nhap 6 : Xoa IP WiFi khoi bo nho luu tru", "yellow"))
        print(colored("🔙 Nhap 0 : Quay lai Menu Chinh", "yellow"))
        print(colored("════════════════════════════════════════════════", "cyan"))

        choice = input(colored("👉 Chon chuc nang: ", "green")).strip()

        if choice == "0":
            return
        elif choice == "1":
            print(colored("\n🔄 Dang khoi dong lai ADB Server...", "cyan"))
            if adb_manager.restart_server():
                print(colored("✅ Da khoi dong lai ADB Server thanh cong!", "green"))
                print(colored("💡 Meo: Dam bao ban da bat USB Debugging tren dien thoai.", "white"))
                input(colored("Nhan Enter de quet lai danh sach thiet bi...", "white"))
            else:
                print(colored("❌ Loi khi khoi dong lai ADB!", "red"))
                input(colored("Nhan Enter de tiep tuc...", "white"))

        elif choice == "2":
            print(colored("\n📡 KET NOI QUA WIFI:", "cyan"))
            ip = input(colored("👉 Nhap dia chi IP Dien thoai (vi du: 192.168.1.10): ", "green")).strip()
            ip = validator.sanitize_string(ip, 15)

            if not validator.validate_ip(ip):
                print(colored("❌ IP khong hop le! Vui long kiem tra lai.", "red"))
                input(colored("Nhan Enter de quay lai...", "white"))
                continue

            port_input = input(colored("👉 Nhap Cong (Port) ket noi (Mac dinh 5555): ", "green")).strip()
            if port_input and port_input.isdigit():
                port = int(port_input)
                if not validator.validate_port(port):
                    print(colored("❌ Cong khong hop le (phai tu 1-65535)!", "red"))
                    input(colored("Nhan Enter de tiep tuc...", "white"))
                    continue
            else:
                port = 5555

            print(colored(f"🔄 Dang tien hanh ket noi den {ip}:{port}...", "cyan"))
            if adb_manager.connect_wifi(ip, port):
                print(colored("✅ Ket noi WiFi thanh cong ruc ro!", "green"))
                saved_devices = config.get("devices", [])
                if ip not in saved_devices:
                    saved_devices.append(ip)
                    config["devices"] = saved_devices
                    save_adb_config(config)
                time.sleep(2)
            else:
                print(colored("❌ Khong the ket noi WiFi den thiet bi!", "red"))
                print(colored("💡 Luu y: Dien thoai va PC phai chung mot mang WiFi.", "yellow"))
                print(colored("💡 Can cam cap USB lan dau de kich hoat port WiFi.", "yellow"))
                input(colored("Nhan Enter de tiep tuc...", "white"))

        elif choice == "3":
            if not devices:
                print(colored("❌ Danh sach rong, khong co thiet bi online de chon!", "red"))
                input(colored("Nhan Enter de tiep tuc...", "white"))
                continue

            print(colored("\n📱 CHON THIET BI MAC DINH:", "cyan"))
            dev_choice = input(colored("👉 Nhap so thu tu thiet bi: ", "green")).strip()
            if dev_choice.isdigit() and 1 <= int(dev_choice) <= len(devices):
                device_id = devices[int(dev_choice) - 1]
                config["current_device"] = device_id
                save_adb_config(config)
                print(colored(f"✅ Da chon thiet bi lam mac dinh: {device_id}", "green"))

                wifi_ip = adb_manager.get_device_wifi_ip(device_id)
                if wifi_ip:
                    print(colored(f"📶 Dia chi WiFi cuc bo cua thiet bi la: {wifi_ip}", "cyan"))
                    print(colored(f"💡 Goi y: Dung {wifi_ip}:5555 de ket noi khong day!", "yellow"))
                time.sleep(3)
            else:
                print(colored("❌ Lua chon khong hop le!", "red"))
                time.sleep(1)

        elif choice == "4":
            saved_devices = config.get("devices", [])
            if not saved_devices:
                print(colored("❌ Khong co thiet bi WiFi nao duoc luu trong bo nho!", "yellow"))
                input(colored("Nhan Enter de quay lai...", "white"))
                continue

            print(colored("\n📋 Danh sach IP WiFi dang luu:", "cyan"))
            for idx, ip in enumerate(saved_devices, 1):
                print(colored(f"   [{idx}] {ip}", "white"))

            dev_choice = input(colored("👉 Chon so de ngat ket noi (0 de huy): ", "green")).strip()
            if dev_choice == "0":
                continue
            if dev_choice.isdigit() and 1 <= int(dev_choice) <= len(saved_devices):
                ip = saved_devices[int(dev_choice) - 1]
                if adb_manager.disconnect_wifi(ip):
                    print(colored(f"✅ Da ngat ket noi thanh cong khoi {ip}", "green"))
                    saved_devices.remove(ip)
                    config["devices"] = saved_devices
                    save_adb_config(config)
                else:
                    print(colored(f"❌ Khong the ngat ket noi khoi {ip}!", "red"))
                time.sleep(2)

        elif choice == "5":
            saved_devices = config.get("devices", [])
            if saved_devices:
                print(colored("\n📋 LICH SU THIET BI WIFI DA LUU:", "cyan"))
                for ip in saved_devices:
                    print(colored(f"   🔹 {ip}", "white"))
            else:
                print(colored("\n❌ Bo nho rong, chua luu thiet bi nao.", "yellow"))
            input(colored("Nhan Enter de tiep tuc...", "white"))

        elif choice == "6":
            saved_devices = config.get("devices", [])
            if not saved_devices:
                print(colored("❌ Danh sach trong rong!", "yellow"))
                input(colored("Nhan Enter de quay lai...", "white"))
                continue

            print(colored("\n📋 CHON DIA CHI DE XOA KHOI BO NHO:", "cyan"))
            for idx, ip in enumerate(saved_devices, 1):
                print(colored(f"   [{idx}] {ip}", "white"))

            dev_choice = input(colored("👉 Nhap so de xoa (0 de huy): ", "green")).strip()
            if dev_choice == "0":
                continue
            if dev_choice.isdigit() and 1 <= int(dev_choice) <= len(saved_devices):
                ip = saved_devices[int(dev_choice) - 1]
                saved_devices.remove(ip)
                config["devices"] = saved_devices
                save_adb_config(config)
                print(colored(f"✅ Da xoa thanh cong dia chi IP: {ip}", "green"))
                time.sleep(2)