from selenium import webdriver as selenium_driver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    
)
import webdriver_manager
from webdriver_manager.chrome import ChromeDriverManager
import time
# import cv2
# import numpy as np
import sys
import os
import re
import requests
import json
from datetime import datetime
from typing import Optional, Tuple, List
from dataclasses import dataclass, field
from enum import Enum
import logging
import io
from time import sleep
import atexit

def cleanup():
    print("\n[!] Đang dọn dẹp và tắt hoàn toàn Chrome (tránh chạy nền)...")
    try:
        if 'driver' in globals():
            driver.quit()
    except Exception as e:
        print(f"Lỗi khi đóng driver: {e}")
    finally:
        if sys.platform == 'win32':
            os.system("taskkill /f /im chromedriver.exe /T >nul 2>&1")

atexit.register(cleanup)

# ================== HỆ THỐNG TỰ ĐỘNG CẬP NHẬT ==================
CURRENT_VERSION = "1.0.0"

# BẠN HÃY THAY "Tên_Tài_Khoản_Của_Bạn" BẰNG TÊN USER GITHUB CỦA BẠN VÀO ĐÂY NHÉ!
UPDATE_URL = "https://raw.githubusercontent.com/skysky9569/golike-bot/main/golikefb_sele.py"

def kiem_tra_cap_nhat():
    print(f"[*] Đang kiểm tra cập nhật (Phiên bản hiện tại: v{CURRENT_VERSION})...")
    try:
        # Gọi GET HTTP để lấy nội dung code mới nhất từ GitHub
        r = requests.get(UPDATE_URL, timeout=8)
        if r.status_code == 200:
            server_code = r.text
            
            # Quét VERSION trong code mới nhất trên server
            import re
            match = re.search(r'CURRENT_VERSION\s*=\s*["\']([^"\']+)["\']', server_code)
            
            if match:
                latest_ver = match.group(1)
                if latest_ver != CURRENT_VERSION:
                    print(f"\n[🔥] PHÁT HIỆN PHIÊN BẢN MỚI v{latest_ver}!")
                    print("[*] Đang tự động tải về và ghi đè cập nhật...")
                    
                    # Tự ghi đè file hiện tại
                    with open(__file__, "w", encoding="utf-8") as f:
                        f.write(server_code)
                        
                    print("[✅] Cập nhật thành công! Vui lòng bật lại tool để áp dụng.")
                    sys.exit(0)
                else:
                    print("[✓] Đang chạy phiên bản mới nhất.")
    except Exception:
        print("[!] Không thể kết nối tới server cập nhật (bỏ qua).")

# SAU KHI BẠN ĐÃ TẠO GITHUB VÀ SỬA XONG LINK "UPDATE_URL" Ở TRÊN,
# HÃY XOÁ DẤU THĂNG (#) Ở DÒNG DƯỚI ĐỂ BẬT AUTO UPDATE NHÉ:
kiem_tra_cap_nhat()
# ==============================================================

# ======== NHẬP API TỪ tesst.py ========
from FB_WEB_API_FIXED import FB_API
from golike_core.security import CredentialManager
from curl_cffi import requests as cffi_requests

# Fix encoding cho Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

cookie_file = "facebook_cookie.enc"
cred_manager = CredentialManager()

def get_cookie_from_user():
    """Yêu cầu người dùng nhập cookie Facebook mới"""
    while True:
        print("\n--- NHẬP COOKIE FACEBOOK MỚI ---")
        cookie_input = input("Nhập cookie Facebook (hoặc nhập 'exit' để thoát): ").strip()

        if cookie_input.lower() == 'exit':
            print("Thoát chương trình.")
            sys.exit()

        if not cookie_input:
            print("❌ Cookie không được để trống!")
            continue

        # Kiểm tra cookie có hợp lệ không
        print("🔍 Đang kiểm tra cookie...")
        try:
            fb_test = FB_API(cookie_input)
            kq_test = fb_test.login()

            if isinstance(kq_test, dict) and 'err' in kq_test:
                print(f"❌ Cookie không hợp lệ: {kq_test['err']}")
                print("Vui lòng nhập lại cookie khác.")
                continue
            else:
                print("✅ Cookie hợp lệ!")
                print(f"  - User ID: {fb_test.session.user_id}")
                print(f"  - Token: {fb_test.session.token[:20]}...")

                # Lưu cookie vào file
                encrypted = cred_manager._encrypt(cookie_input)
                with open(cookie_file, 'w', encoding='utf-8') as f:
                    f.write(encrypted)
                print(f"✅ Đã lưu cookie vào file: {cookie_file}")
                return cookie_input
        except Exception as e:
            print(f"❌ Lỗi khi kiểm tra cookie: {str(e)}")
            continue

def load_cookie():
    """Tải cookie từ file hoặc yêu cầu nhập mới"""
    # Kiểm tra file cookie có tồn tại không
    if os.path.exists(cookie_file):
        print(f"\n📁 Tìm thấy file cookie: {cookie_file}")

        # Hỏi người dùng muốn dùng cookie đã lưu hay nhập mới
        choice = input("Dùng cookie đã lưu? (y/n): ").strip().lower()

        if choice == 'y' or choice == 'yes':
            try:
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    encrypted = f.read().strip()
                cookie_fb = cred_manager._decrypt(encrypted)
                print("✅ Đã tải cookie từ file.")
                return cookie_fb
            except Exception as e:
                print(f"❌ Không thể đọc file cookie: {str(e)}")
                print("Vui lòng nhập cookie mới.")
                return get_cookie_from_user()
        else:
            return get_cookie_from_user()
    else:
        print(f"\n📁 Không tìm thấy file cookie: {cookie_file}")
        return get_cookie_from_user()

cookie_fb = load_cookie()
Fb = None
if cookie_fb:
    Fb = FB_API(cookie_fb)
    Fb.login()

def map_job_type(job_text):
    job_text = job_text.lower()
    if "like cho fanpage" in job_text: return "lik_page"
    if "theo dõi" in job_text: return "follow"
    if "love" in job_text or "tim" in job_text: return "love"
    if "haha" in job_text: return "haha"
    if "wow" in job_text: return "wow"
    if "sad" in job_text or "buồn" in job_text: return "sad"
    if "angry" in job_text or "phẫn nộ" in job_text: return "angry"
    if "like" in job_text: return "like"
    return "unknown"

def getidpost(lk:str):
    import re
    # Thử lấy ID trực tiếp từ link (ví dụ: facebook.com/123456789)
    m = re.search(r'facebook\.com/(?:profile\.php\?id=)?(\d+)', lk)
    if m:
        return m.group(1)
    m = re.search(r'fbid=(\d+)', lk)
    if m:
        return m.group(1)
        
    headers = {
        'accept': '*/*',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://id.traodoisub.com',
        'referer': 'https://id.traodoisub.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    }
    try:
        response = cffi_requests.post('https://id.traodoisub.com/api.php', headers=headers, data={'link': lk})
        js = response.json()
        if "success" in js:
            uid = js.get('post_id', '')
            if not uid:
                uid = js.get('id', '')
            return str(uid) if uid else 0
    except Exception as e:
        print("Lỗi getidpost:", e)
    return 0

def get_golike_credentials():
    """Tải thông tin đăng nhập GoLike từ file cấu hình cục bộ (bảo mật)"""
    config_file = "config_golike.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            saved_user = data.get("username", "")
            print(f"\n📁 Tìm thấy thông tin tài khoản GoLike: {saved_user}")
            
            choice = input("Dùng tài khoản GoLike đã lưu? (y/n): ").strip().lower()
            if choice in ['y', 'yes', '']:
                print("✅ Đang tải tài khoản GoLike...")
                return saved_user, data.get("password", "")
            else:
                print("🔄 Bạn đã chọn thay đổi tài khoản GoLike.")
        except Exception:
            pass
            
    print("\n" + "="*40)
    print("    CẤU HÌNH TÀI KHOẢN GOLIKE BAN ĐẦU    ")
    print("="*40)
    username = input("[?] Nhập tên đăng nhập GoLike: ").strip()
    password = input("[?] Nhập mật khẩu GoLike: ").strip()
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump({"username": username, "password": password}, f, indent=4)
        print("=> Đã lưu thông tin vào file config_golike.json (file này đã được ẩn khỏi GitHub).")
    except:
        pass
    return username, password

# ========================================


print("Đang khởi động trình duyệt Chrome...", flush=True)
options = Options()
options.add_argument("--lang=en-US")
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("--disable-infobars")
options.add_argument("--disable-extensions")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--log-level=3")
options.add_argument("user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")
driver = selenium_driver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

driver.set_window_position(100, 100)
driver.set_window_size(500, 700)
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined })
    """
})

# Lấy thông tin đăng nhập an toàn
golike_user, golike_pass = get_golike_credentials()

driver.get("https://app.golike.net/login")

tk = driver.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/div/form/div[1]/input')
tk.clear()
tk.send_keys(golike_user)
print("Đã nhập tài khoản GoLike.")

mk = driver.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/div/form/div[2]/div/input')
mk.clear()
mk.send_keys(golike_pass)
print("Đã nhập mật khẩu GoLike.")

dn = driver.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/div/form/div[3]/button')
dn.click()
print("dn")

input("enter neu da giai xong capcha")

nhiemvu = driver.find_element(By.XPATH, '//*[@id="app"]/div/div[2]/div/div/div[2]')
nhiemvu.click()

fb = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[1]/div[2]/div[3]/div[1]/div')))
fb.click()

sleep(3)
#check tb
try:
    tb = WebDriverWait(driver, 3).until(
        EC.element_to_be_clickable((By.CLASS_NAME, 'swal2-title'))
    )
    tb.click()
    print("Đã ấn ok thông báo")
    ndtb = driver.find_element(By.ID, 'swal2-content')
    print(ndtb.text)

    oktb = WebDriverWait(driver, 3).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR,'.swal2-confirm.swal2-styled'))
    )
    oktb.click()
except TimeoutException:
    print("Không có thông báo nào.")

try:
    # Bấm vào nút Chọn tài khoản
    doiacc = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "div.select-account"))
    )
    doiacc.click()
    sleep(2)
    
    # Lấy danh sách các tài khoản
    accounts = driver.find_elements(By.CSS_SELECTOR, "div.card.shadow-200.mt-1")
    valid_accounts = []
    
    for acc in accounts:
        try:
            # Lấy tên từ thẻ span bên trong div.col-8
            name = acc.find_element(By.CSS_SELECTOR, "div.col-8 span").text
            acc_id = acc.get_attribute("id")
            if acc_id:
                valid_accounts.append((acc, name, acc_id))
        except:
            pass
            
    # In danh sách cho user chọn
    for i, (acc, name, acc_id) in enumerate(valid_accounts, start=1):
        print(f"{i}. {name} | ID: {acc_id}")
        
    chon_acc = int(input("Chọn acc chạy: "))
    valid_accounts[chon_acc-1][0].click()
    print("Đã chọn tài khoản, đang chờ load job...")

    # Bắt đầu vòng lặp lấy job tự động
    while True:
        try:
            print("\n================== TÌM JOB MỚI ==================")
            # Chờ danh sách job xuất hiện
            try:
                first_job = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.card.mb-2.hand"))
                )
            except TimeoutException:
                print("Chưa thấy job, đang thử nhấn nút tải lại (refresh)...")
                try:
                    reload_btn = driver.find_element(By.CSS_SELECTOR, "button.loader-new")
                    reload_btn.click()
                    sleep(15)
                except:
                    pass
                continue # Quay lại đầu vòng lặp để tìm lại

            # Lấy thông tin chi tiết của job để in ra
            try:
                job_id = first_job.find_element(By.CSS_SELECTOR, "h6.font-id b").text
                job_type = first_job.find_element(By.CSS_SELECTOR, "span.block-text-2").text
                job_price = first_job.find_element(By.CSS_SELECTOR, "span.hold-prices").text
                
                print(f"[*] Đã tìm thấy Job:")
                print(f" - ID: {job_id}")
                print(f" - Loại: {job_type}")
                print(f" - Giá tiền: {job_price} coin")
            except Exception as e:
                print("Không thể trích xuất đầy đủ thông tin job:", e)
                job_type = ""

            first_job.click()
            print("Đã click vào job đầu tiên thành công!")
            sleep(1) # Nghỉ 1 chút sau khi click job
            
            # Lưu lại tab gốc
            original_window = driver.current_window_handle
            
            # Chờ popup chọn cách làm việc hiện ra và click "Trình duyệt"
            try:
                chrome_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//h6[text()='Trình duyệt']/ancestor::a"))
                )
            except TimeoutException:
                print("Lỗi: Không tìm thấy tuỳ chọn làm việc qua trình duyệt. Bỏ qua job này.")
                driver.refresh()
                sleep(2)
                continue
                
            # Lấy link trực tiếp từ nút bấm
            job_link = chrome_btn.get_attribute("href")
            print(f"Link Facebook từ nút bấm: {job_link}")
            
            chrome_btn.click()
            print("Đã chọn làm việc qua Trình duyệt (Chrome)")
            sleep(1.5) # Chờ 1 chút để tab mới mở lên hẳn
            
            # Chờ tab mới (tab Facebook) xuất hiện
            WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
            
            # Chuyển sang tab mới
            for window_handle in driver.window_handles:
                if window_handle != original_window:
                    driver.switch_to.window(window_handle)
                    break
                    
            # Lấy URL của tab mới (để log)
            opened_tab_url = driver.current_url
            
            # Giả vờ lướt tab Facebook khoảng 2 giây để trông tự nhiên hơn
            sleep(2)
            
            # Đóng tab mới
            print("Đang đóng tab Facebook vừa mở...")
            driver.close()
            
            # Quay lại tab GoLike
            driver.switch_to.window(original_window)
            sleep(1) # Nghỉ ngơi 1 xíu khi vừa quay lại
            
            # ================= THỰC HIỆN JOB QUA API =================
            action_type = map_job_type(job_type)
            uid = getidpost(job_link)
            
            print(f"[*] Phân tích Job: Action='{action_type}', UID='{uid}'")
            
            success = False
            if uid and Fb:
                try:
                    if action_type == "follow": success = Fb.FOLLOW(str(uid)).get('success', False)
                    elif action_type == "lik_page": success = Fb.LIKE_PAGE(str(uid)).get('success', False)
                    elif action_type == "like": success = Fb.REACTION("LIKE", str(uid)).get('success', False)
                    elif action_type == "love": success = Fb.REACTION("LOVE", str(uid)).get('success', False)
                    elif action_type == "haha": success = Fb.REACTION("HAHA", str(uid)).get('success', False)
                    elif action_type == "wow": success = Fb.REACTION("WOW", str(uid)).get('success', False)
                    elif action_type == "sad": success = Fb.REACTION("SAD", str(uid)).get('success', False)
                    elif action_type == "angry": success = Fb.REACTION("ANGRY", str(uid)).get('success', False)
                    print(f"=> Kết quả gọi API Facebook: {'THÀNH CÔNG' if success else 'THẤT BẠI'}")
                except Exception as e:
                    print(f"=> Lỗi khi gọi API Facebook: {e}")
            else:
                print("=> Không tìm được UID hoặc chưa đăng nhập API FB.")
                
            # ================= XỬ LÝ TRÊN SELENIUM =================
            need_skip = not success
            
            # Chờ thêm 2-3s trước khi bấm báo cáo để Golike/Facebook kịp đồng bộ hệ thống ngầm
            print("Đang chờ 2.5s để hệ thống đồng bộ trước khi xác nhận...")
            sleep(2.5)
            
            if success:
                print("Đang ấn Hoàn thành...")
                try:
                    hoan_thanh = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//h6[contains(text(), 'Hoàn thành')]"))
                    )
                    driver.execute_script("arguments[0].click();", hoan_thanh)
                    print("Đã click Hoàn thành!")
                    
                    # Chậm lại 1.5s để popup hiện rõ text (tránh quét quá nhanh khi nó chưa render xong)
                    sleep(4)
                    
                    # Chờ thông báo hiện lên
                    try:
                        popup_title = WebDriverWait(driver, 20).until(
                            EC.visibility_of_element_located((By.ID, "swal2-title"))
                        ).text
                        popup_content = driver.find_element(By.ID, "swal2-content").text
                        
                        print(f"=> Thông báo từ GoLike: [{popup_title}] {popup_content}")
                        
                        # Click OK để đóng popup
                        ok_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, ".swal2-confirm.swal2-styled"))
                        )
                        ok_btn.click()
                        
                        # Nếu tiêu đề hoặc nội dung thông báo có lỗi
                        if "lỗi" in popup_title.lower() or "thất bại" in popup_title.lower() or "lỗi" in popup_content.lower() or "thất bại" in popup_content.lower():
                            print("Phát hiện lỗi, bắt buộc chuyển sang Báo cáo lỗi và Bỏ qua...")
                            need_skip = True
                        else:
                            need_skip = False
                    except Exception as e:
                        print("Không đọc được popup thông báo (có thể không hiện).")
                        
                except Exception as e:
                    print("Không tìm thấy nút Hoàn thành:", e)
                    need_skip = True
                    
            if need_skip:
                print("Đang ấn Báo cáo lỗi...")
                try:
                    # Nút Báo lỗi ở màn hình chính
                    bao_loi = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//h6[contains(text(), 'Báo lỗi')]/ancestor::div[contains(@class, 'row')]"))
                    )
                    driver.execute_script("arguments[0].click();", bao_loi)
                    sleep(1.5)
                    
                    # Phân loại lý do báo lỗi
                    ly_do_text = "Tôi không muốn làm Job này"
                    if not uid or uid == 0 or uid == "0":
                        ly_do_text = "Không tìm thấy bài viết"
                    else:
                        # Nếu API báo lỗi hoặc hoàn thành thất bại
                        ly_do_text = "Báo cáo hoàn thành thất bại"
                        
                    print(f"-> Chọn lý do: {ly_do_text}")
                    ly_do = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, f"//h6[contains(text(), '{ly_do_text}')]/ancestor::div[contains(@class, 'row')]"))
                    )
                    driver.execute_script("arguments[0].click();", ly_do)
                    
                    # Nút Gửi báo cáo
                    gui_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Gửi báo cáo')]"))
                    )
                    driver.execute_script("arguments[0].click();", gui_btn)
                    print("Đã click Gửi báo cáo!")
                    
                    sleep(1.5) # Chờ popup báo cáo thành công hiện lên
                    try:
                        ok_btn_baoloi = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, ".swal2-confirm.swal2-styled"))
                        )
                        driver.execute_script("arguments[0].click();", ok_btn_baoloi)
                        print("Đã ấn OK đóng thông báo báo cáo!")
                    except Exception as e:
                        print("Không thấy popup báo cáo thành công hoặc đã tự đóng.")
                        
                    print("Đã hoàn tất Báo cáo lỗi và Bỏ qua!")
                except Exception as e:
                    print("Không tìm thấy nút Báo lỗi hoặc quá trình báo lỗi thất bại:", e)
            
            # Đợi 5 giây trước khi thực hiện job tiếp theo
            print("Đợi 5s trước khi tìm job tiếp theo...")
            sleep(5)
            
        except Exception as e:
            print(f"Lỗi trong quá trình chạy (sẽ thử lại sau 3s): {e}")
            sleep(3)

except KeyboardInterrupt:
    print("\n[!] Đã nhận lệnh dừng (Ctrl+C). Đang thoát...")
except Exception as e:
    print("Lỗi hệ thống trong luồng chính: ", e)