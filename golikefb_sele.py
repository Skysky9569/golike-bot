from selenium import webdriver as selenium_driver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import webdriver_manager
from webdriver_manager.chrome import ChromeDriverManager
import time
import sys
import os
import re
import requests
import json
from datetime import datetime
from time import sleep
import atexit
import threading

# ======== ĐẢM BẢO SCRIPT DIRECTORY TRONG PYTHON PATH ========
# Lấy đường dẫn tuyệt đối của file đang chạy (golikefb_sele.py)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# ======== NHẬP API VÀ LIÊN KẾT CỦA BỘ TOOL ========
try:
    from FB_WEB_API_FIXED import FB_API
except ImportError as e:
    print(f"[LỖI NGHIÊM TRỌNG] Không tìm thấy module: FB_WEB_API_FIXED.py")
    print(f"  - Script đang chạy từ: {SCRIPT_DIR}")
    print(f"  - Vui lòng đảm bảo file FB_WEB_API_FIXED.py nằm trong cùng thư mục với golikefb_sele.py")
    print(f"  - Chi tiết lỗi: {e}")
    sys.exit(1)

try:
    from golike_core.security import CredentialManager
except ImportError:
    print("[CẢNH BÁO] Không tìm thấy golike_core.security, tool có thể không hoạt động đầy đủ")
    # Tạo placeholder để script không bị crash
    class CredentialManager:
        def __init__(self, key=None):
            pass
        def _encrypt(self, data):
            return data
        def _decrypt(self, encrypted):
            return encrypted
from curl_cffi import requests as cffi_requests

# Fix encoding cho Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Quản lý bộ trình duyệt đang chạy
active_drivers = []
drivers_lock = threading.Lock()

def cleanup():
    print("\n[!] Đang dọn dẹp và tắt hoàn toàn trình duyệt (tránh chạy nền)...")
    
    # 1. Duyệt qua danh sách driver đang chạy để đóng nhẹ nhàng giải phóng RAM
    with drivers_lock:
        for drv in active_drivers:
            try:
                drv.quit()
            except:
                pass
        active_drivers.clear()

    # 2. Dọn dẹp cứng các tiến trình cứng đầu trên Windows
    if sys.platform == 'win32':
        import subprocess
        try:
            # Dùng PowerShell quét và tắt THẬT SẠCH các chrome.exe tự động do Selenium bật 
            # (Dựa vào cổng remote-debugging-port) -> Đảm bảo TUYỆT ĐỐI KHÔNG TẮT NHẦM Chrome cá nhân của bạn!
            ps_cmd = (
                "Get-WmiObject Win32_Process -Filter \"Name = 'chrome.exe'\" | "
                "Where-Object { $_.CommandLine -like '*--remote-debugging-port*' } | "
                "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
            )
            subprocess.run(["powershell", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
            
        # Tắt driver
        os.system("taskkill /f /im chromedriver.exe /T >nul 2>&1")

def handle_exit_signal(signum, frame):
    print("\n[🛑] Đã nhận lệnh dừng Tool (Ctrl+C). Tiến hành thu dọn tài nguyên...")
    cleanup()
    sys.exit(1)

# Đăng ký dọn dẹp khi tắt tool thông thường
atexit.register(cleanup)

# Đăng ký dọn dẹp cưỡng bức khi ấn Ctrl+C hoặc bị đóng đột ngột
import signal
try:
    signal.signal(signal.SIGINT, handle_exit_signal)
    signal.signal(signal.SIGTERM, handle_exit_signal)
except ValueError:
    pass

# ================== HỆ THỐNG TỰ ĐỘNG CẬP NHẬT ==================
CURRENT_VERSION = "1.6.0" # Nâng cấp v1.6.0: Kiểm tra tính năng quản lý session Chrome đa luồng - Chỉ tắt driver của luồng bị lỗi, không ảnh hưởng session khác
UPDATE_URL = "https://raw.githubusercontent.com/skysky9569/golike-bot/main/golikefb_sele.py"

def kiem_tra_cap_nhat():
    print(f"[*] Đang kiểm tra cập nhật (Phiên bản hiện tại: v{CURRENT_VERSION})...")
    try:
        r = requests.get(UPDATE_URL, timeout=8)
        if r.status_code == 200:
            server_code = r.text
            import re
            match = re.search(r'CURRENT_VERSION\s*=\s*["\']([^"\']+)["\']', server_code)
            if match:
                latest_ver = match.group(1)
                if latest_ver != CURRENT_VERSION:
                    print(f"\n[🔥] PHÁT HIỆN PHIÊN BẢN MỚI v{latest_ver}!")
                    # HỎI Ý KIẾN NGƯỜI DÙNG TRƯỚC KHI UPDATE
                    chon = input("👉 Bạn có muốn tải và cài đặt bản cập nhật này không? (y/n, Enter là có): ").strip().lower()
                    if chon in ['y', 'yes', '']:
                        print("[*] Đang tải về và ghi đè cập nhật...")
                        with open(__file__, "w", encoding="utf-8") as f:
                            f.write(server_code)
                        print("[✅] Cập nhật thành công! Vui lòng bật lại tool để áp dụng.")
                        sys.exit(0)
                    else:
                        print("[*] Bạn đã chọn bỏ qua cập nhật. Chạy phiên bản hiện tại.")
                else:
                    print("[✓] Đang chạy phiên bản mới nhất.")
    except Exception:
        print("[!] Không thể kết nối tới server cập nhật (bỏ qua).")

# Bật auto-update
kiem_tra_cap_nhat()

# ================= CHIA SẺ HÀM LOGIC CHUNG =================
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

def getidpost(lk: str):
    # Thử dùng TraoDoiSub API trước vì nó quy đổi cực kỳ chuẩn cho mọi loại link post/profile/video...
    headers = {
        'accept': '*/*',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://id.traodoisub.com',
        'referer': 'https://id.traodoisub.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    }
    try:
        response = cffi_requests.post('https://id.traodoisub.com/api.php', headers=headers, data={'link': lk}, timeout=10)
        js = response.json()
        if "success" in js:
            uid = js.get('post_id', '') or js.get('id', '')
            if uid: return str(uid)
    except Exception:
        pass
        
    # Dự phòng bằng Regex nếu API bên thứ 3 gặp sự cố
    import re
    m = re.search(r'profile\.php\?id=(\d+)', lk)
    if m: return m.group(1)
    
    m = re.search(r'fbid=(\d+)', lk)
    if m: return m.group(1)
    
    # Chỉ lấy UID dạng facebook.com/123 khi không có posts/videos/photos để tránh nhận nhầm ID tác giả
    if "/posts/" not in lk and "/videos/" not in lk and "/photos/" not in lk:
        m = re.search(r'facebook\.com/(\d+)', lk)
        if m: return m.group(1)
        
    return "0"

# ================================================================
# ==================== CHẾ ĐỘ 1: CHẠY ĐƠN LẺ ====================
# ================================================================
cookie_file = "facebook_cookie.enc"
cred_manager = CredentialManager()

def get_cookie_from_user():
    while True:
        print("\n--- NHẬP COOKIE FACEBOOK MỚI ---")
        cookie_input = input("Nhập cookie Facebook (hoặc nhập 'exit' để thoát): ").strip()
        if cookie_input.lower() == 'exit':
            sys.exit()
        if not cookie_input:
            print("❌ Cookie không được để trống!")
            continue
        print("🔍 Đang kiểm tra cookie...")
        try:
            fb_test = FB_API(cookie_input)
            kq_test = fb_test.login()
            if isinstance(kq_test, dict) and 'err' in kq_test:
                print(f"❌ Cookie không hợp lệ: {kq_test['err']}")
                continue
            else:
                print("✅ Cookie hợp lệ!")
                encrypted = cred_manager._encrypt(cookie_input)
                with open(cookie_file, 'w', encoding='utf-8') as f:
                    f.write(encrypted)
                return cookie_input
        except Exception as e:
            print(f"❌ Lỗi khi kiểm tra cookie: {e}")

def load_cookie():
    if os.path.exists(cookie_file):
        print(f"\n📁 Tìm thấy file cookie: {cookie_file}")
        choice = input("Dùng cookie đã lưu? (y/n): ").strip().lower()
        if choice in ['y', 'yes', '']:
            try:
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    encrypted = f.read().strip()
                return cred_manager._decrypt(encrypted)
            except Exception:
                return get_cookie_from_user()
        else:
            return get_cookie_from_user()
    else:
        return get_cookie_from_user()

def get_golike_credentials():
    config_file = "config_golike.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            saved_user = data.get("username", "")
            print(f"\n📁 Tìm thấy thông tin tài khoản GoLike: {saved_user}")
            choice = input("Dùng tài khoản GoLike đã lưu? (y/n): ").strip().lower()
            if choice in ['y', 'yes', '']:
                return saved_user, data.get("password", "")
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
    except: pass
    return username, password

def run_single_mode():
    print("\n🚀 Bắt đầu thiết lập chế độ Chạy đơn lẻ 1 tài khoản...")
    cookie_fb = load_cookie()
    Fb = None
    if cookie_fb:
        Fb = FB_API(cookie_fb)
        Fb.login()

    golike_user, golike_pass = get_golike_credentials()

    print("\nĐang khởi động Chrome...", flush=True)
    options = Options()
    options.add_argument("--lang=en-US")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--no-sandbox")
    options.add_argument("user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")

    driver = selenium_driver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    with drivers_lock:
        active_drivers.append(driver)
    driver.set_window_position(100, 100)
    driver.set_window_size(500, 750)
    
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', { get: () => undefined })"
    })

    try:
        driver.get("https://app.golike.net/login")
        
        tk = driver.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/div/form/div[1]/input')
        tk.clear()
        tk.send_keys(golike_user)
        
        mk = driver.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/div/form/div[2]/div/input')
        mk.clear()
        mk.send_keys(golike_pass)
        
        dn = driver.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/div/form/div[3]/button')
        dn.click()
        
        input("\n👉 Vui lòng tự giải Captcha trên màn hình trình duyệt (nếu có).\nSau khi giải xong, ấn phím [ENTER] tại đây để tiếp tục...")
        
        nhiemvu = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[2]/div/div/div[2]')))
        driver.execute_script("arguments[0].click();", nhiemvu)
        
        fb_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[1]/div[2]/div[3]/div[1]/div')))
        driver.execute_script("arguments[0].click();", fb_btn)
        sleep(3)

        try:
            tb = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CLASS_NAME, 'swal2-title')))
            print(f"Thông báo từ GoLike: {tb.text}")
            ok_btn = driver.find_element(By.CSS_SELECTOR, '.swal2-confirm.swal2-styled')
            driver.execute_script("arguments[0].click();", ok_btn)
        except TimeoutException:
            pass

        try:
            doiacc = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.select-account")))
            driver.execute_script("arguments[0].click();", doiacc)
            sleep(2)
            
            accounts = driver.find_elements(By.CSS_SELECTOR, "div.card.shadow-200.mt-1")
            valid_accounts = []
            for acc in accounts:
                try:
                    name = acc.find_element(By.CSS_SELECTOR, "div.col-8 span").text
                    acc_id = acc.get_attribute("id") or ""
                    valid_accounts.append((acc, name, acc_id))
                except: pass
            
            print("\n--- CHỌN TÀI KHOẢN CÀY ---")
            for i, (acc, name, acc_id) in enumerate(valid_accounts, start=1):
                print(f"{i}. {name} | UID: {acc_id}")
            
            chon_acc = int(input("👉 Nhập số để chọn nick chạy: "))
            selected_node, name_run, uid_run = valid_accounts[chon_acc-1]
            driver.execute_script("arguments[0].click();", selected_node)
            print(f"🚀 ✅ ĐANG CHẠY ACC: {name_run} | UID: {uid_run}")
            sleep(3)
            
            # VÒNG LẶP CHẠY CHÍNH
            failed_load_count = 0 # Bộ đếm số lần không tìm thấy Job liên tiếp
            while True:
                try:
                    print("\n================== TÌM JOB MỚI ==================")
                    try:
                        WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.card.hand, div.card.card-primary")))
                        failed_load_count = 0 # Khởi động lại đếm khi tìm thấy Job thành công
                    except TimeoutException:
                        # Kiểm tra Popup Lỗi của GoLike khi không tải được danh sách
                        try:
                            popup = driver.find_element(By.ID, "swal2-content")
                            if popup.is_displayed():
                                txt = popup.text
                                if "danh sách Job" in txt or "Lỗi" in txt or "không tải được" in txt.lower():
                                    print(f"\n⚠️ PHÁT HIỆN GOLIKE LỖI TẢI JOB: [{txt}]")
                                    # Đóng popup
                                    try:
                                        ok_pop = driver.find_element(By.CSS_SELECTOR, ".swal2-confirm.swal2-styled")
                                        driver.execute_script("arguments[0].click();", ok_pop)
                                    except: pass
                                    sleep(2)
                                    
                                    # Thực hiện Reset: Ấn lại Nhiệm vụ -> Facebook và chờ 30s nguội
                                    print("🔄 Đang thực hiện làm mới trang: Quay lại Nhiệm vụ -> Facebook...")
                                    try:
                                        nv = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[2]/div/div/div[2]')))
                                        driver.execute_script("arguments[0].click();", nv)
                                        sleep(3.5)
                                        
                                        fb_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[1]/div[2]/div[3]/div[1]/div')))
                                        driver.execute_script("arguments[0].click();", fb_btn)
                                    except Exception as err:
                                        print(f"❌ Lỗi thao tác Reset: {err}")
                                    
                                    print("⏳ Nghỉ ngơi 30 giây trước khi thử quét tiếp...")
                                    sleep(30)
                                    failed_load_count = 0 # Reset đếm
                                    continue
                        except: pass

                        failed_load_count += 1
                        # Kiểm tra nếu quá 10 lần hụt Job
                        if failed_load_count >= 10:
                            print(f"\n🚨 CẢNH BÁO: Đã hụt Job {failed_load_count} lần liên tiếp! Thực hiện Tự Động Reset trang...")
                            failed_load_count = 0 # Khởi tạo lại
                            try:
                                # Quay lại menu Nhiệm vụ
                                nv = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[2]/div/div/div[2]')))
                                driver.execute_script("arguments[0].click();", nv)
                                sleep(3.5)
                                # Click lại Facebook để tải lại trang Job sạch sẽ
                                fb_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[1]/div[2]/div[3]/div[1]/div')))
                                driver.execute_script("arguments[0].click();", fb_btn)
                                print("✅ Đã làm mới xong trang. Đang nghỉ 30 giây nguội hệ thống...")
                            except Exception as e:
                                print(f"❌ Lỗi trong lúc tự động Reset: {e}")
                            sleep(30)
                            continue

                        print(f"Không thấy Job nào (Lần {failed_load_count}/10). Đang ấn Tải lại...")
                        try:
                            reload_btn = driver.find_element(By.CSS_SELECTOR, "button.loader-new")
                            driver.execute_script("arguments[0].click();", reload_btn)
                            sleep(12)
                        except: pass
                        continue

                    jobs = driver.find_elements(By.CSS_SELECTOR, "div.card.hand, div.card.card-primary")
                    if not jobs: continue
                    first_job = jobs[0]
                    
                    try:
                        job_id = first_job.find_element(By.CSS_SELECTOR, "h6.font-id b").text
                        job_type_raw = first_job.find_element(By.CSS_SELECTOR, "span.block-text-2").text
                        print(f"[*] Phát hiện Job: ID {job_id} | Loại: {job_type_raw}")
                    except: job_type_raw = ""
                    
                    driver.execute_script("arguments[0].click();", first_job)
                    sleep(1.5)
                    
                    orig_window = driver.current_window_handle
                    try:
                        chrome_btn = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((By.XPATH, "//h6[text()='Trình duyệt']/ancestor::a")))
                        fb_job_url = chrome_btn.get_attribute("href")
                        chrome_btn.click()
                    except TimeoutException:
                        print("Lỗi: Không tìm thấy lựa chọn trình duyệt. Bỏ qua.")
                        driver.refresh()
                        sleep(3)
                        continue
                    
                    # Xử lý tab
                    WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
                    for h in driver.window_handles:
                        if h != orig_window:
                            driver.switch_to.window(h)
                            break
                    sleep(2)
                    driver.close()
                    driver.switch_to.window(orig_window)
                    sleep(1)
                    
                    # GỌI API
                    j_type = map_job_type(job_type_raw)
                    uid = getidpost(fb_job_url)
                    success = False
                    
                    if uid and uid != "0":
                        print(f"=> Phân tích UID thành công: {uid}. Đang gọi API...")
                        sleep(1.5)
                        try:
                            if j_type == "follow":
                                res = Fb.FOLLOW(uid)
                                print(f"API Follow: {res}")
                                success = res.get("success", False)
                            elif j_type == "lik_page":
                                res = Fb.LIKE_PAGE(uid)
                                print(f"API Like Page: {res}")
                                success = res.get("success", False)
                            elif j_type in ["like", "love", "haha", "wow", "sad", "angry"]:
                                reaction = j_type.upper()
                                res = Fb.REACTION(reaction, uid)
                                print(f"API Reaction ({reaction}): {res}")
                                success = res.get("success", False)
                            else:
                                print(f"⚠️ Không hỗ trợ tương tác: {j_type}")
                        except Exception as e:
                            print(f"❌ Lỗi API: {e}")
                    else:
                        print("⚠️ Không trích xuất được UID.")

                    # XÁC NHẬN GOLIKE
                    need_skip = not success
                    print("Chờ 3.5s đồng bộ hệ thống...")
                    sleep(3.5)
                    
                    if success:
                        print("Đang ấn Hoàn thành...")
                        try:
                            ht = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//h6[contains(text(), 'Hoàn thành')]")))
                            driver.execute_script("arguments[0].click();", ht)
                            sleep(4)
                            try:
                                t_p = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "swal2-title"))).text
                                c_p = driver.find_element(By.ID, "swal2-content").text
                                print(f"GoLike báo: [{t_p}] {c_p}")
                                ok_c = driver.find_element(By.CSS_SELECTOR, ".swal2-confirm.swal2-styled")
                                driver.execute_script("arguments[0].click();", ok_c)
                                if "lỗi" in t_p.lower() or "thất bại" in t_p.lower() or "lỗi" in c_p.lower() or "thất bại" in c_p.lower():
                                    need_skip = True
                            except: pass
                        except Exception as e:
                            print(f"Lỗi ấn Hoàn thành: {e}")
                            need_skip = True
                            
                    if need_skip:
                        print("🚨 Bắt đầu Báo lỗi...")
                        try:
                            bl = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//h6[contains(text(), 'Báo lỗi')]/ancestor::div[contains(@class, 'row')]")))
                            driver.execute_script("arguments[0].click();", bl)
                            sleep(1.5)
                            
                            lydo = "Tôi không muốn làm Job này"
                            if not uid or uid == "0": lydo = "Không tìm thấy bài viết"
                            else: lydo = "Báo cáo hoàn thành thất bại"
                            
                            c_lydo = driver.find_element(By.XPATH, f"//h6[contains(text(), '{lydo}')]/ancestor::div[contains(@class, 'row')]")
                            driver.execute_script("arguments[0].click();", c_lydo)
                            sleep(1)
                            
                            gui = driver.find_element(By.XPATH, "//button[contains(text(), 'Gửi báo cáo')]")
                            driver.execute_script("arguments[0].click();", gui)
                            sleep(1.5)
                            try:
                                o_b = driver.find_element(By.CSS_SELECTOR, ".swal2-confirm.swal2-styled")
                                driver.execute_script("arguments[0].click();", o_b)
                            except: pass
                            print("Đã Báo lỗi thành công.")
                        except Exception as e:
                            print(f"Lỗi khi Báo lỗi: {e}")
                    
                    print("Đợi 10s trước khi tìm job tiếp theo...")
                    sleep(10)
                    
                except Exception as e:
                    print(f"Lỗi vòng lặp chạy (chờ 5s): {e}")
                    sleep(5)
        except Exception as e:
            print(f"Lỗi tương tác giao diện tài khoản: {e}")
    except KeyboardInterrupt:
        print("\n[!] Đã nhận Ctrl+C. Đang tắt...")
    finally:
        try: driver.quit()
        except: pass

# ======================================================================
# ==================== CHẾ ĐỘ 2: CHẠY SONG SONG (ĐA LUỒNG) =============
# ======================================================================
def log_thread(profile_name, message):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{profile_name}] {message}")

# PHASE 1: CÀI ĐẶT VÀ GIẢI CAPTCHA TUẦN TỰ TRÊN LUỒNG CHÍNH
def setup_bot_profile(profile_data, idx):
    p_name = profile_data.get("profile_name", f"Acc-{idx}")
    gl_user = profile_data.get("golike_username", "")
    gl_pass = profile_data.get("golike_password", "")
    fb_cookie = profile_data.get("facebook_cookie", "")
    target_fb = profile_data.get("target_fb_name", "")
    target_uid = profile_data.get("target_fb_uid", "")

    print(f"\n" + "="*60)
    print(f"🔷 KHỞI TẠO TÀI KHOẢN CHẠY SONG SONG: [{p_name}]")
    print("="*60)
    
    if not gl_user or not gl_pass or not fb_cookie:
        print(f"❌ Cấu hình [{p_name}] thiếu thông tin quan trọng. Bỏ qua!")
        return None, None

    try:
        Fb = FB_API(fb_cookie)
        kq = Fb.login()
        if isinstance(kq, dict) and 'err' in kq:
            print(f"❌ Cookie FB của [{p_name}] bị sai hoặc hết hạn: {kq['err']}")
            return None, None
        print(f"✅ FB API Kết nối thành công (UID: {Fb.session.user_id})")
    except Exception as e:
        print(f"❌ Lỗi API cho [{p_name}]: {e}")
        return None, None

    print(f"[*] Đang bật trình duyệt Chrome cho [{p_name}]...")
    options = Options()
    options.add_argument("--lang=en-US")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")
    
    driver = selenium_driver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    with drivers_lock:
        active_drivers.append(driver)
        
    w, h = 450, 750
    px = 20 + (idx * 470)
    py = 30
    if px > 1400:
        px = 20 + ((idx % 3) * 470)
        py = 450
    driver.set_window_position(px, py)
    driver.set_window_size(w, h)

    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', { get: () => undefined })"
    })

    try:
        driver.get("https://app.golike.net/login")
        sleep(2)
        
        driver.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/div/form/div[1]/input').send_keys(gl_user)
        driver.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/div/form/div[2]/div/input').send_keys(gl_pass)
        driver.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/div/form/div[3]/button').click()
        
        print(f"\n🔑 [BƯỚC BẮT BUỘC] Hãy nhìn vào màn hình trình duyệt của [{p_name}].")
        input("Vui lòng tự giải Captcha trên đó. Khi đã vào được màn hình chính, quay lại đây ấn [ENTER]...")
        
        nhiemvu = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[2]/div/div/div[2]')))
        driver.execute_script("arguments[0].click();", nhiemvu)
        
        fb_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[1]/div[2]/div[3]/div[1]/div')))
        driver.execute_script("arguments[0].click();", fb_btn)
        sleep(3)
        
        try:
            tb = WebDriverWait(driver, 4).until(EC.element_to_be_clickable((By.CLASS_NAME, 'swal2-title')))
            ok_btn = driver.find_element(By.CSS_SELECTOR, '.swal2-confirm.swal2-styled')
            driver.execute_script("arguments[0].click();", ok_btn)
        except: pass
        
        doiacc = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.select-account")))
        driver.execute_script("arguments[0].click();", doiacc)
        sleep(2.5)
        
        accounts = driver.find_elements(By.CSS_SELECTOR, "div.card.shadow-200.mt-1")
        selected = False
        
        for acc in accounts:
            try:
                nm = acc.find_element(By.CSS_SELECTOR, "div.col-8 span").text
                uid_acc = acc.get_attribute("id") or ""
                
                is_match = False
                if target_uid and str(target_uid).strip() == str(uid_acc).strip(): is_match = True
                elif target_fb and target_fb.lower().strip() in nm.lower().strip(): is_match = True
                
                if is_match:
                    driver.execute_script("arguments[0].click();", acc)
                    print(f"🚀 [OK] ĐÃ CHỌN XONG ACC: {nm} | UID: {uid_acc}")
                    selected = True
                    break
            except: pass
            
        if not selected:
            print(f"⚠️ Cảnh báo: Không tìm thấy UID/Tên khớp cho [{p_name}]. Chọn nick đầu tiên!")
            if len(accounts) > 0: 
                driver.execute_script("arguments[0].click();", accounts[0])
            else: 
                print("❌ Không tìm thấy nick FB nào liên kết!")
                return None, None
            
        sleep(3)
        print(f"✅ Đã thiết lập thành công tài khoản [{p_name}]!")
        return driver, Fb
        
    except Exception as e:
        print(f"❌ Lỗi trong quá trình Setup tài khoản [{p_name}]: {e}")
        try: driver.quit()
        except: pass
        return None, None


# PHASE 2: VÒNG LẶP CHẠY SONG SONG (DÀNH CHO LUỒNG PHỤ)
def run_bot_loop(driver, Fb, profile_data, idx):
    p_name = profile_data.get("profile_name", f"Acc-{idx}")
    
    log_thread(p_name, "🔥 BẮT ĐẦU CHẠY TỰ ĐỘNG!")
    failed_load_count = 0 # Thêm đếm số lần hụt Job liên tiếp
    try:
        while True:
            try:
                log_thread(p_name, "=== QUÉT JOB ===")
                try:
                    WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.card.hand, div.card.card-primary")))
                    failed_load_count = 0 # Đã thấy Job, reset bộ đếm
                except TimeoutException:
                    # Kiểm tra Popup Lỗi của GoLike khi không tải được danh sách
                    try:
                        popup = driver.find_element(By.ID, "swal2-content")
                        if popup.is_displayed():
                            txt = popup.text
                            if "danh sách Job" in txt or "Lỗi" in txt or "không tải được" in txt.lower():
                                log_thread(p_name, f"⚠️ GOLIKE BÁO LỖI TẢI JOB: [{txt}]")
                                try:
                                    ok_pop = driver.find_element(By.CSS_SELECTOR, ".swal2-confirm.swal2-styled")
                                    driver.execute_script("arguments[0].click();", ok_pop)
                                except: pass
                                sleep(2)
                                
                                log_thread(p_name, "🔄 Tự động Reset trang: Quay lại Nhiệm vụ -> Facebook...")
                                try:
                                    nv = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[2]/div/div/div[2]')))
                                    driver.execute_script("arguments[0].click();", nv)
                                    sleep(3.5)
                                    
                                    fb_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[1]/div[2]/div[3]/div[1]/div')))
                                    driver.execute_script("arguments[0].click();", fb_btn)
                                except Exception as err:
                                    log_thread(p_name, f"❌ Lỗi khi Reset: {err}")
                                
                                log_thread(p_name, "⏳ Bắt đầu nghỉ ngơi 30 giây nguội máy...")
                                failed_load_count = 0 # Reset bộ đếm
                                sleep(30)
                                continue
                    except: pass

                    failed_load_count += 1
                    if failed_load_count >= 10:
                        log_thread(p_name, f"🚨 ĐÃ HỤT JOB {failed_load_count} LẦN! Thực hiện Tự động Reset trang Nhiệm vụ -> Facebook...")
                        failed_load_count = 0
                        try:
                            nv = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[2]/div/div/div[2]')))
                            driver.execute_script("arguments[0].click();", nv)
                            sleep(3.5)
                            fb_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[1]/div[2]/div[3]/div[1]/div')))
                            driver.execute_script("arguments[0].click();", fb_btn)
                            log_thread(p_name, "✅ Reset trang xong. Đang chờ 30s nguội hệ thống...")
                        except Exception as e:
                            log_thread(p_name, f"❌ Lỗi khi tự động Reset: {e}")
                        sleep(30)
                        continue

                    log_thread(p_name, f"Không thấy Job nào (Lần {failed_load_count}/10). Đang ấn Tải lại...")
                    try:
                        reload = driver.find_element(By.CSS_SELECTOR, "button.loader-new")
                        driver.execute_script("arguments[0].click();", reload)
                        sleep(12)
                    except: pass
                    continue

                jobs = driver.find_elements(By.CSS_SELECTOR, "div.card.hand, div.card.card-primary")
                if not jobs: continue
                first_j = jobs[0]
                
                try:
                    j_id = first_j.find_element(By.CSS_SELECTOR, "h6.font-id b").text
                    j_raw = first_j.find_element(By.CSS_SELECTOR, "span.block-text-2").text
                    log_thread(p_name, f"Có Job: ID {j_id} | {j_raw}")
                except: j_raw = ""
                
                driver.execute_script("arguments[0].click();", first_j)
                sleep(1.5)
                
                orig_w = driver.current_window_handle
                try:
                    ch_b = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((By.XPATH, "//h6[text()='Trình duyệt']/ancestor::a")))
                    fb_url = ch_b.get_attribute("href")
                    ch_b.click()
                except TimeoutException:
                    driver.refresh()
                    sleep(3)
                    continue
                
                WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
                for hd in driver.window_handles:
                    if hd != orig_w:
                        driver.switch_to.window(hd)
                        break
                sleep(2)
                driver.close()
                driver.switch_to.window(orig_w)
                sleep(1)
                
                j_t = map_job_type(j_raw)
                uid = getidpost(fb_url)
                ok = False
                if uid and uid != "0":
                    sleep(1.5)
                    try:
                        if j_t == "follow":
                            res = Fb.FOLLOW(uid)
                            ok = res.get("success", False)
                            log_thread(p_name, f"API Follow: {res}")
                        elif j_t == "lik_page":
                            res = Fb.LIKE_PAGE(uid)
                            ok = res.get("success", False)
                            log_thread(p_name, f"API LikePage: {res}")
                        elif j_t in ["like", "love", "haha", "wow", "sad", "angry"]:
                            res = Fb.REACTION(j_t.upper(), uid)
                            ok = res.get("success", False)
                            log_thread(p_name, f"API Reaction ({j_t}): {res}")
                        else:
                            log_thread(p_name, f"⚠️ Loại tương tác chưa hỗ trợ: {j_t}")
                    except Exception as api_e:
                        log_thread(p_name, f"❌ Lỗi API tương tác: {api_e}")
                else:
                    log_thread(p_name, f"⚠️ Không trích xuất được UID từ Link: {fb_url}")
                
                need_skip = not ok
                sleep(3.5)
                if ok:
                    try:
                        ht = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//h6[contains(text(), 'Hoàn thành')]")))
                        driver.execute_script("arguments[0].click();", ht)
                        sleep(4)
                        try:
                            tp = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "swal2-title"))).text
                            cp = driver.find_element(By.ID, "swal2-content").text
                            log_thread(p_name, f"GoLike: [{tp}] {cp}")
                            ok_c = driver.find_element(By.CSS_SELECTOR, ".swal2-confirm.swal2-styled")
                            driver.execute_script("arguments[0].click();", ok_c)
                            if "lỗi" in tp.lower() or "thất bại" in tp.lower() or "lỗi" in cp.lower() or "thất bại" in cp.lower():
                                need_skip = True
                            else: need_skip = False
                        except: pass
                    except: need_skip = True
                    
                if need_skip:
                    try:
                        bl = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//h6[contains(text(), 'Báo lỗi')]/ancestor::div[contains(@class, 'row')]")))
                        driver.execute_script("arguments[0].click();", bl)
                        sleep(1.5)
                        ldo = "Báo cáo hoàn thành thất bại"
                        if not uid or uid == "0": ldo = "Không tìm thấy bài viết"
                        c_ldo = driver.find_element(By.XPATH, f"//h6[contains(text(), '{ldo}')]/ancestor::div[contains(@class, 'row')]")
                        driver.execute_script("arguments[0].click();", c_ldo)
                        sleep(1)
                        gui = driver.find_element(By.XPATH, "//button[contains(text(), 'Gửi báo cáo')]")
                        driver.execute_script("arguments[0].click();", gui)
                        sleep(1.5)
                        try:
                            o_b = driver.find_element(By.CSS_SELECTOR, ".swal2-confirm.swal2-styled")
                            driver.execute_script("arguments[0].click();", o_b)
                        except: pass
                        log_thread(p_name, "-> Đã báo lỗi job.")
                    except: pass
                
                log_thread(p_name, "Nghỉ 10 giây...")
                sleep(10)
            except Exception as ex:
                log_thread(p_name, f"Lỗi chu kỳ: {ex}")
                sleep(5)
    except Exception as fatal:
        log_thread(p_name, f"🚨 LUỒNG BỊ LỖI ĐỘT NGỘT: {fatal}")
    finally:
        try: driver.quit()
        except: pass

def run_parallel_mode():
    config_path = "config_parallel.json"
    if not os.path.exists(config_path):
        sample = [
            {
                "profile_name": "Nick Số 1",
                "golike_username": "Tên_Đăng_Nhập_GoLike",
                "golike_password": "Mật_Khẩu_GoLike",
                "facebook_cookie": "Cookie_Facebook_Tại_Đây",
                "target_fb_uid": "61554835667156",
                "target_fb_name": "Tên_Để_Dự_Phòng"
            },
            {
                "profile_name": "Nick Số 2",
                "golike_username": "Tên_Đăng_Nhập_GoLike",
                "golike_password": "Mật_Khẩu_GoLike",
                "facebook_cookie": "Cookie_Facebook_Tại_Đây",
                "target_fb_uid": "100093602988096",
                "target_fb_name": "Tên_Để_Dự_Phòng"
            }
        ]
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(sample, f, indent=4, ensure_ascii=False)
        print("\n" + "="*60)
        print("💥 CHƯA TÌM THẤY FILE CẤU HÌNH ĐA LUỒNG config_parallel.json!")
        print("Mình đã tự tạo file mẫu. Bạn hãy điền các tài khoản rồi chạy lại!")
        print(f"👉 Vị trí file: {os.path.abspath(config_path)}")
        print("="*60)
        input("\nẤn Enter để dừng...")
        return

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            profiles = json.load(f)
    except Exception as e:
        print(f"❌ Lỗi phân tích file cấu hình: {e}")
        return

    print(f"\n🚀 PHÁT HIỆN {len(profiles)} TÀI KHOẢN ĐĂNG KÝ CHẠY SONG SONG!")
    
    threads = []
    print("\n--- BẮT ĐẦU QUÁ TRÌNH THIẾT LẬP & GIẢI CAPTCHA LẦN LƯỢT ---")
    for idx, profile in enumerate(profiles):
        drv, fb_api = setup_bot_profile(profile, idx)
        if drv and fb_api:
            # KÍCH HOẠT LUỒNG CHẠY NGAY LẬP TỨC! CHẠY NGAY KHI ENTER XONG KHÔNG CẦN CHỜ!
            t = threading.Thread(target=run_bot_loop, args=(drv, fb_api, profile, idx))
            t.daemon = True
            t.start()
            threads.append(t)
            print(f"🚀 [LUỒNG PHỤ] Đã kích hoạt chạy ngầm thành công cho [{profile.get('profile_name')}].")
        else:
            print(f"⚠️ Không thể khởi tạo Acc [{profile.get('profile_name', idx)}]. Bỏ qua luồng này.")

    if not threads:
        print("\n❌ Không có tài khoản nào thiết lập thành công. Thoát!")
        return

    print(f"\n" + "*"*60)
    print(f"🔥 TẤT CẢ CÁC LUỒNG ĐANG HOẠT ĐỘNG! Đang theo dõi tiến trình chạy...")
    print("*"*60 + "\n")
    
    try:
        while any(t.is_alive() for t in threads):
            sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Kết thúc chế độ song song...")

# ======================================================================
# ==================== MENU KHỞI CHẠY HỆ THỐNG CHÍNH ==================
# ======================================================================
if __name__ == "__main__":
    print("\n" + "="*65)
    print("🔥        HỆ THỐNG AUTO CÀY COIN GOLIKE & FACEBOOK v" + CURRENT_VERSION + "        🔥")
    print("="*65)
    print("1. Chạy ĐƠN LẺ 1 tài khoản (Hỗ trợ cấu hình trực tiếp)")
    print("2. Chạy SONG SONG nhiều tài khoản (Đọc từ config_parallel.json)")
    print("-"*65)
    
    try:
        lua_chon = input("👉 Lựa chọn chế độ chạy (Nhập 1 hoặc 2, mặc định là 1): ").strip()
        if lua_chon == "2":
            run_parallel_mode()
        else:
            run_single_mode()
    except KeyboardInterrupt:
        print("\n[!] Đã nhận lệnh ngắt chương trình. Đang thoát hệ thống an toàn...")
    except Exception as e:
        print(f"\n🚨 Lỗi hệ thống khởi chạy: {e}")