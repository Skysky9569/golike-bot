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

# ======== NHẬP API CỦA TOOL ========
from FB_WEB_API_FIXED import FB_API
from curl_cffi import requests as cffi_requests

# Fix encoding cho Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Quản lý danh sách driver đang chạy để cleanup
active_drivers = []
drivers_lock = threading.Lock()

def cleanup_all():
    print("\n[!] Đang đóng toàn bộ trình duyệt và dọn dẹp chạy nền...")
    with drivers_lock:
        for drv in active_drivers:
            try:
                drv.quit()
            except:
                pass
    if sys.platform == 'win32':
        os.system("taskkill /f /im chromedriver.exe /T >nul 2>&1")

atexit.register(cleanup_all)

# --- Hàm in log phân biệt theo luồng ---
def log(profile_name, message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{profile_name}] {message}")

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
    import re
    m = re.search(r'facebook\.com/(?:profile\.php\?id=)?(\d+)', lk)
    if m: return m.group(1)
    m = re.search(r'fbid=(\d+)', lk)
    if m: return m.group(1)
        
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
            return str(uid) if uid else "0"
    except Exception:
        pass
    return "0"

# ================= LUỒNG CHẠY CHÍNH CỦA TỪNG TÀI KHOẢN =================
def run_bot_profile(profile_data, idx):
    p_name = profile_data.get("profile_name", f"Profile {idx}")
    gl_user = profile_data.get("golike_username", "")
    gl_pass = profile_data.get("golike_password", "")
    fb_cookie = profile_data.get("facebook_cookie", "")
    target_fb = profile_data.get("target_fb_name", "")
    target_uid = profile_data.get("target_fb_uid", "")

    log(p_name, "Khởi chạy luồng.")
    
    if not gl_user or not gl_pass or not fb_cookie:
        log(p_name, "Lỗi: Thiếu cấu hình thông tin đăng nhập. Dừng luồng.")
        return

    # Khởi tạo FB API
    log(p_name, "Đang kết nối Facebook API...")
    try:
        Fb = FB_API(fb_cookie)
        kq_login = Fb.login()
        if isinstance(kq_login, dict) and 'err' in kq_login:
            log(p_name, f"❌ Cookie Facebook không hợp lệ: {kq_login['err']}. Dừng luồng.")
            return
        log(p_name, f"✅ FB API Đăng nhập thành công (UID: {Fb.session.user_id}).")
    except Exception as e:
        log(p_name, f"❌ Lỗi khởi tạo FB API: {e}")
        return

    # Khởi tạo Chrome
    log(p_name, "Đang khởi động Chrome...")
    options = Options()
    options.add_argument("--lang=en-US")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    options.add_argument("user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")

    # Tải driver
    driver = selenium_driver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    
    # Lưu vào danh sách quản lý driver
    with drivers_lock:
        active_drivers.append(driver)

    # Bố trí vị trí cửa sổ cạnh nhau cho gọn
    width, height = 450, 750
    pos_x = 20 + (idx * 470)
    pos_y = 30
    # Nếu tràn màn hình ngang thì xuống hàng
    if pos_x > 1400:
        pos_x = 20 + ((idx % 3) * 470)
        pos_y = 450
    driver.set_window_position(pos_x, pos_y)
    driver.set_window_size(width, height)
    
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', { get: () => undefined })"
    })

    try:
        # Đăng nhập GoLike
        log(p_name, "Đang truy cập GoLike...")
        driver.get("https://app.golike.net/login")
        
        tk = driver.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/div/form/div[1]/input')
        tk.clear()
        tk.send_keys(gl_user)
        
        mk = driver.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/div/form/div[2]/div/input')
        mk.clear()
        mk.send_keys(gl_pass)
        
        dn = driver.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/div/form/div[3]/button')
        dn.click()
        log(p_name, "Đã gửi thông tin đăng nhập. Vui lòng tự giải CAPTCHA trên trình duyệt nếu có!")
        
        # Đợi đăng nhập thành công (chờ xuất hiện logo/menu nhiệm vụ)
        # Không thể dùng input() vì nó sẽ kẹt luồng, ta sẽ đợi đến khi thấy phần tử "Nhiệm vụ"
        log(p_name, "Đang theo dõi trạng thái đăng nhập... (Chờ tối đa 120 giây để vượt Captcha)")
        
        nhiemvu = WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="app"]/div/div[2]/div/div/div[2]'))
        )
        log(p_name, "✅ Đăng nhập GoLike thành công!")
        nhiemvu.click()
        
        fb_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[1]/div[2]/div[3]/div[1]/div'))
        )
        fb_btn.click()
        sleep(3)
        
        # Check popup cảnh báo lỗi tài khoản nếu có
        try:
            tb = WebDriverWait(driver, 4).until(EC.element_to_be_clickable((By.CLASS_NAME, 'swal2-title')))
            log(p_name, f"Nhận thông báo hệ thống: {tb.text}")
            ok_btn = driver.find_element(By.CSS_SELECTOR, '.swal2-confirm.swal2-styled')
            ok_btn.click()
            sleep(1)
        except:
            pass
            
        # Chọn tài khoản Facebook cấu hình
        log(p_name, "Đang mở bảng Chọn tài khoản Facebook...")
        doiacc = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.select-account"))
        )
        doiacc.click()
        sleep(2.5)
        
        accounts = driver.find_elements(By.CSS_SELECTOR, "div.card.shadow-200.mt-1")
        acc_selected = False
        
        search_desc = f"UID: '{target_uid}'" if target_uid else f"Tên: '{target_fb}'"
        log(p_name, f"Tìm thấy {len(accounts)} tài khoản liên kết. Đang so khớp {search_desc}...")
        
        for acc in accounts:
            try:
                name = acc.find_element(By.CSS_SELECTOR, "div.col-8 span").text
                acc_uid = acc.get_attribute("id") or ""
                
                # Khớp theo UID (nếu có) HOẶC Khớp theo tên
                is_match = False
                if target_uid and str(target_uid).strip() == str(acc_uid).strip():
                    is_match = True
                elif target_fb and target_fb.lower().strip() in name.lower().strip():
                    is_match = True
                
                if is_match:
                    acc.click()
                    log(p_name, f"🚀 ✅ ĐANG CHẠY ACC: {name} | UID: {acc_uid}")
                    acc_selected = True
                    break
            except:
                pass
                
        if not acc_selected:
            log(p_name, f"⚠️ Không tìm thấy nick '{target_fb}'. Mặc định click chọn tài khoản đầu tiên!")
            if len(accounts) > 0:
                accounts[0].click()
            else:
                log(p_name, "❌ Không tìm thấy tài khoản FB nào trong danh sách. Dừng luồng!")
                return
                
        sleep(3)
        
        # ================= BẮT ĐẦU VÒNG LẶP CHẠY JOB =================
        while True:
            try:
                log(p_name, "=== ĐANG QUÉT JOB MỚI ===")
                
                # Đợi danh sách job load
                try:
                    WebDriverWait(driver, 8).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.card.card-primary.mb-3"))
                    )
                except TimeoutException:
                    log(p_name, "Không thấy Job nào. Đang click Tải lại...")
                    try:
                        reload_btn = driver.find_element(By.CSS_SELECTOR, "button.loader-new")
                        reload_btn.click()
                        sleep(12)
                    except:
                        pass
                    continue

                jobs = driver.find_elements(By.CSS_SELECTOR, "div.card.card-primary.mb-3")
                if not jobs:
                    continue
                
                first_job = jobs[0]
                
                # Đọc thông tin Job
                try:
                    job_id = first_job.find_element(By.CSS_SELECTOR, "h6.font-id b").text
                    job_type_raw = first_job.find_element(By.CSS_SELECTOR, "span.block-text-2").text
                    log(p_name, f"Phát hiện Job ID: {job_id} | Loại: {job_type_raw}")
                except:
                    job_type_raw = ""
                
                first_job.click()
                sleep(1.5)
                
                orig_window = driver.current_window_handle
                
                # Click Trình duyệt
                try:
                    chrome_btn = WebDriverWait(driver, 8).until(
                        EC.element_to_be_clickable((By.XPATH, "//h6[text()='Trình duyệt']/ancestor::a"))
                    )
                    fb_job_url = chrome_btn.get_attribute("href")
                    chrome_btn.click()
                except TimeoutException:
                    log(p_name, "❌ Lỗi: Không thấy tùy chọn trình duyệt. Bỏ qua.")
                    driver.refresh()
                    sleep(3)
                    continue
                
                # Mở tab rồi đóng lại
                WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
                for handle in driver.window_handles:
                    if handle != orig_window:
                        driver.switch_to.window(handle)
                        break
                sleep(2)
                driver.close()
                driver.switch_to.window(orig_window)
                sleep(1)
                
                # --- XỬ LÝ API FACEBOOK ---
                j_type = map_job_type(job_type_raw)
                log(p_name, f"Đang phân tích link: {fb_job_url}")
                uid = getidpost(fb_job_url)
                
                success = False
                if uid and uid != "0":
                    log(p_name, f"=> Lấy UID thành công: {uid}. Bắt đầu chạy tương tác qua API...")
                    sleep(1.5)
                    
                    try:
                        if j_type == "follow":
                            res = Fb.FOLLOW(uid)
                            log(p_name, f"API Follow trả về: {res}")
                            success = res.get("success", False)
                        elif j_type == "lik_page":
                            res = Fb.LIKE_PAGE(uid)
                            log(p_name, f"API LikePage trả về: {res}")
                            success = res.get("success", False)
                        elif j_type in ["like", "love", "haha", "wow", "sad", "angry"]:
                            reaction = j_type.upper()
                            res = Fb.REACTION(reaction, uid)
                            log(p_name, f"API Reaction ({reaction}) trả về: {res}")
                            success = res.get("success", False)
                        else:
                            log(p_name, f"⚠️ Loại tương tác không hỗ trợ: {j_type}")
                    except Exception as e:
                        log(p_name, f"❌ Lỗi thực thi API: {e}")
                else:
                    log(p_name, "⚠️ Không trích xuất được UID.")
                
                # --- XÁC NHẬN HOÀN THÀNH TRÊN GOLIKE ---
                need_skip = not success
                
                log(p_name, "Chờ 3.5s hệ thống đồng bộ...")
                sleep(3.5)
                
                if success:
                    log(p_name, "Bấm 'Hoàn thành'...")
                    try:
                        ht_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//h6[contains(text(), 'Hoàn thành')]"))
                        )
                        driver.execute_script("arguments[0].click();", ht_btn)
                        
                        sleep(4) # Đợi popup render
                        try:
                            title = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "swal2-title"))).text
                            content = driver.find_element(By.ID, "swal2-content").text
                            log(p_name, f"GoLike báo: [{title}] {content}")
                            
                            ok_pop = driver.find_element(By.CSS_SELECTOR, ".swal2-confirm.swal2-styled")
                            ok_pop.click()
                            
                            if "lỗi" in title.lower() or "thất bại" in title.lower() or "lỗi" in content.lower() or "thất bại" in content.lower():
                                need_skip = True
                            else:
                                need_skip = False
                        except:
                            pass
                    except Exception as e:
                        log(p_name, f"❌ Lỗi click Hoàn thành: {e}")
                        need_skip = True
                        
                if need_skip:
                    log(p_name, "🚨 Bắt đầu Báo lỗi & Bỏ qua job...")
                    try:
                        bao_loi = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//h6[contains(text(), 'Báo lỗi')]/ancestor::div[contains(@class, 'row')]"))
                        )
                        driver.execute_script("arguments[0].click();", bao_loi)
                        sleep(1.5)
                        
                        ly_do_text = "Tôi không muốn làm Job này"
                        if not uid or uid == "0":
                            ly_do_text = "Không tìm thấy bài viết"
                        else:
                            ly_do_text = "Báo cáo hoàn thành thất bại"
                            
                        ly_do = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, f"//h6[contains(text(), '{ly_do_text}')]/ancestor::div[contains(@class, 'row')]"))
                        )
                        driver.execute_script("arguments[0].click();", ly_do)
                        sleep(1)
                        
                        gui_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Gửi báo cáo')]")
                        driver.execute_script("arguments[0].click();", gui_btn)
                        sleep(1.5)
                        
                        try:
                            ok_bl = driver.find_element(By.CSS_SELECTOR, ".swal2-confirm.swal2-styled")
                            driver.execute_script("arguments[0].click();", ok_bl)
                        except:
                            pass
                        log(p_name, "Đã gửi Báo cáo lỗi.")
                    except Exception as e:
                        log(p_name, f"Lỗi khi báo lỗi: {e}")
                
                log(p_name, "Nghỉ ngơi 10 giây...")
                sleep(10)
                
            except Exception as loop_err:
                log(p_name, f"Lỗi xảy ra trong chu kỳ chạy: {loop_err}")
                sleep(5)
                
    except Exception as fatal:
        log(p_name, f"💥 LỖI HỆ THỐNG (Luồng Dừng!): {fatal}")
    finally:
        log(p_name, "Kết thúc luồng. Đóng trình duyệt.")
        try:
            driver.quit()
        except:
            pass

# ================== KHỞI CHẠY CHƯƠNG TRÌNH ==================
def main():
    config_path = "config_parallel.json"
    
    if not os.path.exists(config_path):
        # Tạo file mẫu nếu chưa tồn tại
        sample = [
            {
                "profile_name": "Acc Facebook 1",
                "golike_username": "Tài_Khoản_GoLike_1",
                "golike_password": "Mật_Khẩu_GoLike_1",
                "facebook_cookie": "Paste_Cookie_FB_1_Vào_Đây",
                "target_fb_uid": "61554835667156",
                "target_fb_name": "Tên Dự Phòng Nếu Không Có UID (Ví dụ: Trần Duy)"
            },
            {
                "profile_name": "Acc Facebook 2",
                "golike_username": "Tài_Khoản_GoLike_2",
                "golike_password": "Mật_Khẩu_GoLike_2",
                "facebook_cookie": "Paste_Cookie_FB_2_Vào_Đây",
                "target_fb_uid": "100093602988096",
                "target_fb_name": "Tên Dự Phòng 2 (Ví dụ: Trần Kiên)"
            }
        ]
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(sample, f, indent=4, ensure_ascii=False)
        
        print("\n" + "="*60)
        print("💥 CHƯA TÌM THẤY FILE CẤU HÌNH config_parallel.json!")
        print("Mình đã tự động tạo 1 file cấu hình MẪU tại:")
        print(f"👉 {os.path.abspath(config_path)}")
        print("Hãy mở file đó lên, điền thông tin các nick muốn cày rồi chạy lại nhé!")
        print("="*60)
        input("\nẤn Enter để thoát...")
        return

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            profiles = json.load(f)
    except Exception as e:
        print(f"❌ Lỗi đọc file config_parallel.json: {e}")
        return

    if not isinstance(profiles, list) or len(profiles) == 0:
        print("❌ Lỗi: File config_parallel.json rỗng hoặc sai định dạng list [].")
        return

    print(f"\n🚀 PHÁT HIỆN {len(profiles)} TÀI KHOẢN ĐĂNG KÝ CHẠY SONG SONG!")
    print("Bắt đầu phân tách các luồng trình duyệt...\n")

    threads = []
    for i, profile in enumerate(profiles):
        t = threading.Thread(
            target=run_bot_profile,
            args=(profile, i),
            name=f"Thread-{i}"
        )
        t.daemon = True # Đảm bảo luồng phụ tự ngắt khi luồng chính thoát
        threads.append(t)
        t.start()
        sleep(5) # Delay 5s giữa các lần mở Chrome để tránh nghẽn RAM lúc đầu
    
    # Giữ luồng chính sống để theo dõi luồng phụ
    try:
        while any(t.is_alive() for t in threads):
            sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Bạn đã ấn Ctrl+C để ngắt toàn bộ hệ thống!")
        
if __name__ == "__main__":
    main()
