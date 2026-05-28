"""
ADB WiFi/USB management menu.
"""
import os
import time

from golike_core.adb_manager import ADBManager, load_adb_config, save_adb_config, colored
from golike_core.security import InputValidator


def adb_menu() -> None:
    """Menu quản lý kết nối ADB WiFi/USB nâng cao"""
    validator = InputValidator()
    adb_manager = ADBManager()

    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print(colored("════════════════════════════════════════════════", "cyan", bold=True))
        print(colored("📶 QUẢN LÝ KẾT NỐI THIẾT BỊ ADB WIFI/USB", "yellow", bold=True))
        print(colored("════════════════════════════════════════════════", "cyan"))

        if not adb_manager.check_adb():
            print(colored("❌ Không tìm thấy adb.exe! Hãy kiểm tra thư mục ADB.", "red"))
            input(colored("Nhấn Enter để quay lại...", "white"))
            return

        devices = adb_manager.check_connected_devices()
        config = load_adb_config()

        print(colored(f"📊 Thiết bị đang kết nối (Online): {len(devices)}", "green"))
        if devices:
            for idx, device_id in enumerate(devices, 1):
                marker = "👉 " if config.get("current_device") == device_id else "   "
                print(colored(f"{marker}[{idx}] 🆔 {device_id} [✅ Thiết bị Online]", "white"))
        else:
            print(colored("   ⚠️ Hiện tại không có thiết bị ADB nào đang kết nối online", "yellow"))

        print(colored("════════════════════════════════════════════════", "cyan"))
        print(colored("🔌 Nhập 1 : Khởi động lại ADB Server (Sửa lỗi ngắt kết nối USB)", "yellow"))
        print(colored("📶 Nhập 2 : Kết nối thiết bị qua IP WiFi (Không cần dây)", "yellow"))
        print(colored("📱 Nhập 3 : Chọn thiết bị mặc định để sử dụng", "yellow"))
        print(colored("🔓 Nhập 4 : Ngắt kết nối thiết bị WiFi", "yellow"))
        print(colored("📋 Nhập 5 : Xem danh sách IP WiFi đã lưu", "yellow"))
        print(colored("🗑️  Nhập 6 : Xóa IP WiFi khỏi bộ nhớ lưu trữ", "yellow"))
        print(colored("🔙 Nhập 0 : Quay lại Menu Chính", "yellow"))
        print(colored("════════════════════════════════════════════════", "cyan"))

        choice = input(colored("👉 Chọn chức năng: ", "green")).strip()

        if choice == "0":
            return
        elif choice == "1":
            print(colored("\n🔄 Đang khởi động lại ADB Server...", "cyan"))
            if adb_manager.restart_server():
                print(colored("✅ Đã khởi động lại ADB Server thành công!", "green"))
                print(colored("💡 Mẹo: Đảm bảo bạn đã bật USB Debugging trên điện thoại.", "white"))
                input(colored("Nhấn Enter để quét lại danh sách thiết bị...", "white"))
            else:
                print(colored("❌ Lỗi khi khởi động lại ADB!", "red"))
                input(colored("Nhấn Enter để tiếp tục...", "white"))

        elif choice == "2":
            print(colored("\n📡 KẾT NỐI QUA WIFI:", "cyan"))
            ip_input = input(colored("👉 Nhập địa chỉ IP Điện thoại (ví dụ: 192.168.1.10 hoặc 192.168.1.10:5555): ", "green")).strip()
            
            ip = ip_input
            port = 5555
            if ":" in ip_input:
                parts = ip_input.split(":")
                if len(parts) == 2:
                    ip = parts[0]
                    if parts[1].isdigit():
                        port = int(parts[1])
            
            ip = validator.sanitize_string(ip, 15)

            if not validator.validate_ip(ip):
                print(colored("❌ IP không hợp lệ! Vui lòng kiểm tra lại.", "red"))
                input(colored("Nhấn Enter để quay lại...", "white"))
                continue

            if ":" not in ip_input:
                port_input = input(colored("👉 Nhập Cổng (Port) kết nối (Mặc định 5555): ", "green")).strip()
                if port_input and port_input.isdigit():
                    port = int(port_input)
                    if not validator.validate_port(port):
                        print(colored("❌ Cổng không hợp lệ (phải từ 1-65535)!", "red"))
                        input(colored("Nhấn Enter để tiếp tục...", "white"))
                        continue
                else:
                    port = 5555

            print(colored(f"🔄 Đang tiến hành kết nối đến {ip}:{port}...", "cyan"))
            if adb_manager.connect_wifi(ip, port):
                print(colored("✅ Kết nối WiFi thành công rực rỡ!", "green"))
                saved_devices = config.get("devices", [])
                if ip not in saved_devices:
                    saved_devices.append(ip)
                    config["devices"] = saved_devices
                    save_adb_config(config)
                time.sleep(2)
            else:
                print(colored("❌ Không thể kết nối WiFi đến thiết bị!", "red"))
                print(colored("💡 Lưu ý: Điện thoại và PC phải chung một mạng WiFi.", "yellow"))
                print(colored("💡 Cần cắm cáp USB lần đầu để kích hoạt port WiFi.", "yellow"))
                input(colored("Nhấn Enter để tiếp tục...", "white"))

        elif choice == "3":
            if not devices:
                print(colored("❌ Danh sách rỗng, không có thiết bị online để chọn!", "red"))
                input(colored("Nhấn Enter để tiếp tục...", "white"))
                continue

            print(colored("\n📱 CHỌN THIẾT BỊ MẶC ĐỊNH:", "cyan"))
            dev_choice = input(colored("👉 Nhập số thứ tự thiết bị: ", "green")).strip()
            if dev_choice.isdigit() and 1 <= int(dev_choice) <= len(devices):
                device_id = devices[int(dev_choice) - 1]
                config["current_device"] = device_id
                save_adb_config(config)
                print(colored(f"✅ Đã chọn thiết bị làm mặc định: {device_id}", "green"))

                wifi_ip = adb_manager.get_device_wifi_ip(device_id)
                if wifi_ip:
                    print(colored(f"📶 Địa chỉ WiFi cục bộ của thiết bị là: {wifi_ip}", "cyan"))
                    print(colored(f"💡 Gợi ý: Dùng {wifi_ip}:5555 để kết nối không dây!", "yellow"))
                time.sleep(3)
            else:
                print(colored("❌ Lựa chọn không hợp lệ!", "red"))
                time.sleep(1)

        elif choice == "4":
            saved_devices = config.get("devices", [])
            if not saved_devices:
                print(colored("❌ Không có thiết bị WiFi nào được lưu trong bộ nhớ!", "yellow"))
                input(colored("Nhấn Enter để quay lại...", "white"))
                continue

            print(colored("\n📋 Danh sách IP WiFi đang lưu:", "cyan"))
            for idx, ip in enumerate(saved_devices, 1):
                print(colored(f"   [{idx}] {ip}", "white"))

            dev_choice = input(colored("👉 Chọn số để ngắt kết nối (0 để hủy): ", "green")).strip()
            if dev_choice == "0":
                continue
            if dev_choice.isdigit() and 1 <= int(dev_choice) <= len(saved_devices):
                ip = saved_devices[int(dev_choice) - 1]
                if adb_manager.disconnect_wifi(ip):
                    print(colored(f"✅ Đã ngắt kết nối thành công khỏi {ip}", "green"))
                    saved_devices.remove(ip)
                    config["devices"] = saved_devices
                    save_adb_config(config)
                else:
                    print(colored(f"❌ Không thể ngắt kết nối khỏi {ip}!", "red"))
                time.sleep(2)

        elif choice == "5":
            saved_devices = config.get("devices", [])
            if saved_devices:
                print(colored("\n📋 LỊCH SỬ THIẾT BỊ WIFI ĐÃ LƯU:", "cyan"))
                for ip in saved_devices:
                    print(colored(f"   🔹 {ip}", "white"))
            else:
                print(colored("\n❌ Bộ nhớ rỗng, chưa lưu thiết bị nào.", "yellow"))
            input(colored("Nhấn Enter để tiếp tục...", "white"))

        elif choice == "6":
            saved_devices = config.get("devices", [])
            if not saved_devices:
                print(colored("❌ Danh sách trống rỗng!", "yellow"))
                input(colored("Nhấn Enter để quay lại...", "white"))
                continue

            print(colored("\n📋 CHỌN ĐỊA CHỈ ĐỂ XÓA KHỎI BỘ NHỚ:", "cyan"))
            for idx, ip in enumerate(saved_devices, 1):
                print(colored(f"   [{idx}] {ip}", "white"))

            dev_choice = input(colored("👉 Nhập số để xóa (0 để hủy): ", "green")).strip()
            if dev_choice == "0":
                continue
            if dev_choice.isdigit() and 1 <= int(dev_choice) <= len(saved_devices):
                ip = saved_devices[int(dev_choice) - 1]
                saved_devices.remove(ip)
                config["devices"] = saved_devices
                save_adb_config(config)
                print(colored(f"✅ Đã xóa thành công địa chỉ IP: {ip}", "green"))
                time.sleep(2)