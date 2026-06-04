"""
Flow xử lý TikTok cho iOS sử dụng Appium.
"""
import sys
import time
from golike_core.logging import logger
from golike_core.adb_manager import colored
from golike_core.security import CredentialManager, InputValidator
from golike_core.api_client import GolikeAPIClient
from golike_ios.ios_automator import TikTokIOSAutomator
from golike_ios.ios_manager import IOSManager

def ios_tiktok_menu():
    """Menu chính cho TikTok iOS (Appium)"""
    print(colored("\n════════════════════════════════════════════════", "cyan"))
    print(colored("🍏 KHỞI ĐỘNG TOOL GOLIKE TIKTOK (iOS - APPIUM)", "yellow"))
    print(colored("════════════════════════════════════════════════", "cyan"))
    
    cred_manager = CredentialManager()
    validator = InputValidator()
    
    tokens = cred_manager.get_auth_labels()
    if not tokens:
        print(colored("❌ Bạn chưa có Token nào. Vui lòng thêm trong Quản lý Authorization Tokens (Menu 5).", "red"))
        input(colored("Nhấn Enter để quay lại...", "white"))
        return

    print(colored("\n[1] Lấy danh sách Token đã lưu", "white"))
    print(colored("[0] Quay lại", "white"))
    choice = input(colored("\nLựa chọn: ", "green")).strip()
    
    if choice != '1':
        return

    print(colored("\nDanh sách Tokens:", "cyan"))
    for i, label in enumerate(tokens, 1):
        print(colored(f"  [{i}] {label}", "white"))
    
    try:
        token_idx = int(input(colored("Chọn Token (1, 2, ...): ", "green")).strip()) - 1
        if token_idx < 0 or token_idx >= len(tokens):
            print(colored("Lựa chọn không hợp lệ!", "red"))
            return
    except ValueError:
        print(colored("Lựa chọn không hợp lệ!", "red"))
        return
        
    selected_label = tokens[token_idx]
    token = cred_manager.get_auth_by_label(selected_label)
    
    api_client = GolikeAPIClient()
    api_client.set_auth(token)

    # 1. Lấy danh sách tài khoản TikTok từ API
    try:
        print(colored("⏳ Đang lấy danh sách tài khoản TikTok...", "yellow"))
        accounts_resp = api_client.get_accounts(provider='tiktok')
        if not accounts_resp or accounts_resp.get("status") != 200 or not accounts_resp.get("data"):
            print(colored("❌ Không lấy được danh sách tài khoản. Kiểm tra lại Token!", "red"))
            input(colored("Nhấn Enter để quay lại...", "white"))
            return
        
        accounts_data = accounts_resp.get("data", [])
        if not accounts_data:
            print(colored("❌ Bạn chưa thêm tài khoản TikTok nào vào GoLike!", "red"))
            input(colored("Nhấn Enter để quay lại...", "white"))
            return

        print(colored("\n🆔 DANH SÁCH TÀI KHOẢN TIKTOK:", "yellow"))
        print(colored("════════════════════════════════════════════════", "white"))
        for idx, acc in enumerate(accounts_data, 1):
            print(colored(f"  [{idx}] {acc.get('unique_username', 'N/A')} (ID: {acc.get('id')})", "cyan"))
        print(colored("════════════════════════════════════════════════", "white"))

        while True:
            acc_input = input(colored("👉 Chọn số thứ tự tài khoản: ", "green")).strip()
            if acc_input.isdigit() and 1 <= int(acc_input) <= len(accounts_data):
                selected_acc = accounts_data[int(acc_input) - 1]
                account_id = str(selected_acc.get("id"))
                print(colored(f"✅ Đã chọn tài khoản: {selected_acc.get('unique_username')}", "green"))
                break
            else:
                print(colored("❌ Lựa chọn không hợp lệ!", "red"))

    except Exception as e:
        logger.error(f"Lỗi lấy danh sách tài khoản: {e}")
        print(colored(f"❌ Lỗi API: {e}", "red"))
        input(colored("Nhấn Enter để quay lại...", "white"))
        return

    # 2. Khởi tạo WDA
    ios_mgr = IOSManager()
    
    # Kiểm tra WDA Server
    print(colored("⏳ Đang kết nối WebDriverAgent Server (mặc định http://127.0.0.1:8100)...", "yellow"))
    # Bỏ qua check appium server, thay bằng check cổng 8100 hoặc bỏ qua

    selected_device = ios_mgr.select_device()
    
    if selected_device:
        platform_version = selected_device['version']
        device_name = selected_device['name']
        udid = selected_device['udid']
        print(colored(f"✅ Đã chọn: {device_name} (iOS {platform_version})", "green"))
    else:
        print(colored("\nCấu hình Appium thủ công:", "cyan"))
        platform_version = input(colored("iOS Version (ví dụ 16.4, mặc định 16.4): ", "green")).strip() or "16.4"
        device_name = input(colored("Device Name (ví dụ iPhone 14, mặc định iPhone 14): ", "green")).strip() or "iPhone 14"
        udid = input(colored("UDID (Bỏ qua nếu dùng Simulator): ", "green")).strip() or None
    
    # Chọn Bundle ID
    print(colored("\n📦 CHỌN BẢN TIKTOK ĐANG DÙNG:", "cyan"))
    print(colored("  [1] TikTok Global (com.zhiliaoapp.musically)", "white"))
    print(colored("  [2] TikTok VN (com.ss.iphone.ugc.Tiktok)", "white"))
    print(colored("  [3] TikTok VN (com.ss.iphone.ugc.Ame) - Khuyên dùng cho máy bạn", "yellow"))
    print(colored("  [4] Tự nhập Bundle ID khác", "white"))
    
    b_choice = input(colored("Lựa chọn (1-3, mặc định 3): ", "green")).strip()
    if b_choice == "1":
        bundle_id = "com.zhiliaoapp.musically"
    elif b_choice == "2":
        bundle_id = "com.ss.iphone.ugc.Tiktok"
    elif b_choice == "4":
        bundle_id = input(colored("Nhập Bundle ID: ", "green")).strip()
        while not bundle_id:
            bundle_id = input(colored("Bundle ID không được để trống: ", "green")).strip()
    else:
        bundle_id = "com.ss.iphone.ugc.Ame"
    
    print(colored(f"✅ Đã chọn Bundle ID: {bundle_id}", "green"))

    ios_automator = TikTokIOSAutomator(
        platform_version=platform_version, 
        device_name=device_name, 
        udid=udid,
        bundle_id=bundle_id
    )
    if not ios_automator.connect():
        print(colored("❌ Không thể kết nối Appium. Kiểm tra lại Appium Server!", "red"))
        input(colored("Nhấn Enter để quay lại...", "white"))
        return

    print(colored("\n▶️ BẮT ĐẦU CHẠY AUTO iOS...", "yellow"))
    print(colored("⚠️ CHÚ Ý: Locator Follow/Like đang là Placeholder. Hãy cập nhật trong golike_ios/ios_automator.py nếu cần.", "yellow"))
    
    try:
        # Vòng lặp lấy job
        while True:
            try:
                # Dùng chung API format với bản ADB/Android để đảm bảo ổn định
                jobs_url = f'/api/advertising/publishers/tiktok/jobs?account_id={account_id}&data=null'
                jobs_resp = api_client.get(jobs_url)
                
                if not isinstance(jobs_resp, dict):
                    logger.warning(f"API trả về định dạng lạ (không phải dict): {type(jobs_resp)}")
                    time.sleep(15)
                    continue

                if jobs_resp.get('status') != 200:
                    print(colored("Hết Job hoặc lỗi mạng. Đợi 15s...", "yellow"))
                    time.sleep(15)
                    continue
                
                raw_data = jobs_resp.get('data')
                if not raw_data:
                    print(colored("Hết Job. Đợi 15s...", "yellow"))
                    time.sleep(15)
                    continue

                # Xử lý: GoLike có thể trả về 1 Object hoặc 1 List
                if isinstance(raw_data, dict):
                    jobs = [raw_data]
                elif isinstance(raw_data, list):
                    jobs = raw_data
                else:
                    print(colored("Dữ liệu job không hợp lệ. Đợi 15s...", "yellow"))
                    time.sleep(15)
                    continue

                for job in jobs:
                    if not isinstance(job, dict): continue
                    job_id = job.get('id')
                    link = job.get('link', '')
                    job_type = job.get('type', 'follow')
                    object_id = job.get('object_id', '')
                    
                    print(colored(f"\n[+] Nhận Job: {job_type.upper()} - {job_id}", "cyan"))
                    print(colored(f"    Link: {link}", "white"))
                    
                    # Tự động mở link trên iOS
                    print(colored(f"    (iOS) Đang mở link: {link}", "yellow"))
                    ios_automator.open_url(link)
                    
                    if job_type == 'follow' or 'follow' in job_type:
                        success = ios_automator.click_follow()
                    else:
                        success = ios_automator.click_like()
                        
                    if success:
                        print(colored("    Báo cáo hoàn thành...", "cyan"))
                        # TikTok complete_job needs 'id' and 'account_id' inside job_data dict
                        job_data_to_complete = {
                            'id': job_id,
                            'account_id': account_id
                        }
                        res = api_client.complete_job('tiktok', job_data_to_complete)
                        if res and res.get('status') == 200:
                            reward = res.get('data', {}).get('prices', 0)
                            print(colored(f"    ✅ Thành công! Nhận {reward} VND", "green"))
                        else:
                            msg = res.get('message', 'Lỗi không xác định') if res else 'Không có phản hồi'
                            print(colored(f"    ❌ Báo cáo thất bại: {msg}", "red"))
                    else:
                        print(colored("    ❌ Bỏ qua job do lỗi UI.", "red"))
                        # skip_job mapping for tiktok is 'skip' endpoint in api_client
                        # However, api_client doesn't have a high-level skip_job, but it has report_job
                        job_data_to_skip = {
                            'id': job_id,
                            'account_id': account_id,
                            'object_id': object_id,
                            'type': job_type
                        }
                        try:
                            api_client.report_job('tiktok', job_data_to_skip)
                            # Also call the skip endpoint directly as api_client doesn't have skip_job method
                            api_client.post('/api/advertising/publishers/tiktok/skip-jobs', {
                                "ads_id": job_id,
                                "object_id": object_id,
                                "account_id": account_id,
                                "type": job_type
                            })
                        except:
                            pass
                        
                    print(colored("    Đợi 10s trước khi làm job tiếp theo...", "white"))
                    time.sleep(10)
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp job: {e}")
                time.sleep(5)
                
    except KeyboardInterrupt:
        print(colored("\n👋 Đã dừng Auto iOS.", "yellow"))
    except Exception as e:
        logger.error(f"Lỗi hệ thống iOS: {e}")
        print(colored(f"❌ Lỗi: {e}", "red"))
    finally:
        ios_automator.close()
        input(colored("Nhấn Enter để quay lại menu chính...", "white"))
