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
import os
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from golike_core.config import CONFIG

# ================= ANTI-DETECTION STEALTH SCRIPT =================
# Script để conceal selenium automation và randomize fingerprint
STEALTH_INJECTION_SCRIPT = """
// Landmark: randomize device fingerprint on every run
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
Object.defineProperty(navigator, 'platform', { get: () => { const plats = ['Win32','MacIntel','Linux x86_64']; return plats[Math.floor(Math.random()*plats.length)]; } });
// Per-run resolution randomization
const XRES = Math.floor(1280 + Math.random()*800);
const YRES = Math.floor(720 + Math.random()*480);
Object.defineProperty(Screen.prototype, 'width', { get: () => XRES });
Object.defineProperty(Screen.prototype, 'height', { get: () => YRES });
Object.defineProperty(Screen.prototype, 'availWidth', { get: () => XRES - 16 });
Object.defineProperty(Screen.prototype, 'availHeight', { get: () => YRES - 64 });
"""

# ================= RANDOMIZATION UTILS =================
def smart_random_delay(base_delay: float, variance: float = 0.3) -> float:
    """
    Tạo delay với randomization Gaussian để mô phỏng timing con người.

    Args:
        base_delay: Delay cơ bản (giây)
        variance: Method sai số tương đối (default 0.3 = ±30%)

    Returns:
        Actual delay với randomization (luôn >= 0.1s)
    """
    multiplier = random.gauss(1.0, variance / 2)
    # Clamp để tránh delay quá ngắn hoặc quá dài (0.5x - 1.5x)
    multiplier = max(0.5, min(1.5, multiplier))
    actual = base_delay * multiplier
    return max(0.1, actual)  # Đảm bảo tối thiểu 0.1s


# ================= MEMORY CIRCUIT BREAKER =================
MEMORY_LIMIT_PERCENT = 90  # Ngưỡng RAM % tối đa
MEMORY_AVAILABLE_MIN = 1000  # RAM tối thiểu cần giữ (MB)


def check_system_memory():
    """
    Kiểm tra RAM hệ thống hiện tại.

    Returns:
        tuple: (used_percent, available_mb)
    """
    try:
        import psutil
        mem = psutil.virtual_memory()
        return mem.percent, mem.available / (1024 * 1024)
    except ImportError:
        # psutil không có - skip memory check
        return 0, float('inf')
    except Exception:
        # Lỗi khi đọc memory - giả định OK để không block bot
        return 0, float('inf')


def wait_for_memory(frequency: float = 5.0):
    """
    Chờ RAM giải phóng khi vượt ngưỡng.

    Args:
        frequency: Tần số kiểm tra lại (giây)
    """
    while True:
        used_percent, available_mb = check_system_memory()

        if used_percent < MEMORY_LIMIT_PERCENT and available_mb > MEMORY_AVAILABLE_MIN:
            # RAM đã đủ thấp - thoát
            print(f"[✓] RAM ổn: {used_percent:.1f}% used, {available_mb:.0f}MB available")
            return

        # Vẫn quá cao - tiếp tục chờ
        print(f"⏳ Chờ RAM giải phóng... ({used_percent:.1f}% used, {available_mb:.0f}MB available)")
        time.sleep(frequency)


def smart_sleep(seconds: int):
    """Sleep for *seconds* seconds.
    If the duration is longer than 20 seconds, prints a countdown to the console.
    """
    try:
        secs = int(seconds)
    except Exception:
        secs = int(seconds)
    if secs > 20:
        for remaining in range(secs, 0, -1):
            print(f"⏳ Waiting {remaining}s...", end="\r", flush=True)
            time.sleep(1)
        print(" " * 30, end="\r")  # clear line
    else:
        time.sleep(secs)
import sys
import os
import re
import requests
import json
from datetime import datetime
from time import sleep
import threading

# ================= API RATE LIMIT SEMAPHORE =================
# Giới hạn tối đa N API calls đồng thời giữa tất cả threads
MAX_CONCURRENT_API_CALLS = 3
GLOBAL_API_SEMAPHORE = threading.Semaphore(MAX_CONCURRENT_API_CALLS)


def throttled_api_call(api_obj, method_name, *args, **kwargs):
    """
    Gọi Facebook API với rate limiting semaphore.

    Args:
        api_obj: Đối tượng FB_API
        method_name: Tên method (REACTION, FOLLOW, LIKE_PAGE)
        *args, **kwargs: Tham số cho method

    Returns:
        Kết quả từ API call
    """
    with GLOBAL_API_SEMAPHORE:
        # Small random delay trước khi call để tránh synchronized timing
        time.sleep(random.uniform(0.3, 1.0))

        # Gọi API
        method = getattr(api_obj, method_name, None)
        if method:
            return method(*args, **kwargs)
        else:
            print(f"[!] Không tìm thấy method {method_name} trong FB_API")
            return {"success": False}


# ================= USER-AGENT POOL =================
# Pool các User-Agent mobile để tránh fingerprint trùng giữa các acc
MOBILE_UA_POOL = [
    {
        "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "platform": "iPhone",
        "width": 390,
        "height": 844,
    },
    {
        "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
        "platform": "iPhone",
        "width": 390,
        "height": 844,
    },
    {
        "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "platform": "iPhone",
        "width": 390,
        "height": 844,
    },
    {
        "ua": "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "platform": "iPad",
        "width": 768,
        "height": 1024,
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
        "platform": "Android",
        "width": 360,
        "height": 800,
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36",
        "platform": "Android",
        "width": 360,
        "height": 800,
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
        "platform": "Android",
        "width": 393,
        "height": 851,
    },
]


def get_random_device_profile():
    """Random toàn bộ device profile (UA + platform + viewport)."""
    profile = random.choice(MOBILE_UA_POOL)
    # Thêm slight variation vào viewport
    width_var = random.randint(-10, 10)
    height_var = random.randint(-20, 20)
    return {
        "user_agent": profile["ua"],
        "platform": profile["platform"],
        "viewport_width": max(320, profile["width"] + width_var),
        "viewport_height": max(500, profile["height"] + height_var),
    }


# Helper to detect the "job limit" toast
def job_limit_reached(driver):
    """Return True if a toast or popup appears indicating the max jobs limit."""
    try:
        # 1. Check Toast messages with fresh lookup each time
        toast_elems = driver.find_elements(By.CSS_SELECTOR, "div.toast-message")
        for i, _ in enumerate(toast_elems):
            try:
                # Re-find element fresh each iteration to avoid stale reference
                elem = driver.find_elements(By.CSS_SELECTOR, "div.toast-message")[i]
                msg = elem.get_attribute("textContent").lower()
                if "100 job" in msg or ("tối đa" in msg and "job" in msg) or ("giới hạn" in msg and "job" in msg) or "đã làm quá" in msg or "max job" in msg:
                    print(f"🚨 Phát hiện giới hạn Job: {elem.get_attribute('textContent').strip()}")
                    return True
            except Exception as e:
                # Skip stale element silently - this is expected in parallel mode
                # only log if we can't access any elements
                continue

        # 2. Check SweetAlert popups
        popup_titles = driver.find_elements(By.CSS_SELECTOR, "h2#swal2-title")
        popup_contents = driver.find_elements(By.CSS_SELECTOR, "div#swal2-content")
        
        full_text = ""
        for t in popup_titles:
            if t.is_displayed(): full_text += t.text.lower() + " "
        for c in popup_contents:
            if c.is_displayed(): full_text += c.text.lower() + " "

        # Check SV2 pattern: số job hôm này X
        job_match = re.search(r"số job hôm này\s*(\d+)", full_text)
        max_job_limit = CONFIG_DELAY.get("max_job_limit", 100)
        try:
            max_job_limit = int(max_job_limit) if max_job_limit is not None else 100
        except (ValueError, TypeError):
            max_job_limit = 100  # Fallback an toàn
        is_sv2_max = job_match and int(job_match.group(1)) >= max_job_limit

        if "100 job" in full_text or ("tối đa" in full_text and "job" in full_text) or ("giới hạn" in full_text and "job" in full_text) or "đã làm quá" in full_text or "max job" in full_text or is_sv2_max:
            print(f"🚨 Phát hiện giới hạn Job từ Popup: {full_text.strip()}")
            # Tự động đóng popup nếu có
            try:
                ok_btn = driver.find_element(By.CSS_SELECTOR, ".swal2-confirm.swal2-styled")
                if ok_btn.is_displayed():
                    driver.execute_script("arguments[0].click();", ok_btn)
            except Exception as e:
                print(f'[!] Không đóng được popup: {type(e).__name__}: {e}')
            return True

    except Exception as e:
        print(f'[ERROR] Lỗi kiểm tra job limit: {type(e).__name__}: {e}')

    return False


# ======== TÌM NÚT "TRÌNH DUYỆT" (BROWSER BUTTON) ========

_BROWSER_BTN_SELECTORS = [
    # XPATH dựa theo text h6 bên trong thẻ <a>
    ("xpath", "//a[.//h6[normalize-space()='Trình duyệt']]"),
    ("xpath", "//a[.//h6[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'trình duyệt')]]"),
    # Text trực tiếp trên thẻ <a>
    ("xpath", "//a[normalize-space()='Trình duyệt']"),
    ("xpath", "//a[contains(normalize-space(), 'Trình duyệt')]"),
    # Có thể Golike dùng button thay vì <a>
    ("xpath", "//button[contains(normalize-space(), 'Trình duyệt')]"),
    # CSS fallback - link chứa text 'trinh-duyet' hoặc href chứa 'facebook'
    ("css", "a[href*='facebook.com']"),
    ("css", "a[href*='fb.com']"),
    # Nếu Golike dùng 'Browser' tiếng Anh
    ("xpath", "//a[.//h6[contains(normalize-space(), 'Browser')]]"),
    ("xpath", "//a[contains(normalize-space(), 'Browser')]"),
]

def find_browser_button(driver, timeout=8):
    """Tìm nút 'Trình duyệt' trong giao diện GoLike job detail.
    Thử nhiều selector khác nhau để xử lý khi Golike thay đổi UI.
    Trả về element nếu tìm thấy, raise TimeoutException nếu không.
    """
    import time as _time
    deadline = _time.time() + timeout
    last_err = None
    while _time.time() < deadline:
        for sel_type, sel_val in _BROWSER_BTN_SELECTORS:
            try:
                if sel_type == "xpath":
                    elems = driver.find_elements(By.XPATH, sel_val)
                else:
                    elems = driver.find_elements(By.CSS_SELECTOR, sel_val)
                for el in elems:
                    try:
                        if el.is_displayed() and el.is_enabled():
                            return el
                    except Exception:
                        pass
            except Exception as e:
                last_err = e
        _time.sleep(0.5)
    # Không tìm thấy — in HTML debug để giúp chẩn đoán
    try:
        body_html = driver.find_element(By.TAG_NAME, "body").get_attribute("innerHTML")
        snippet = body_html[:3000]
        print("[DEBUG] Không tìm thấy nút Trình duyệt. HTML snippet (3000 chars):")
        print(snippet)
    except Exception:
        pass
    raise TimeoutException("Không tìm thấy nút Trình duyệt sau khi thử tất cả selectors")


# ======== PHÁT HIỆN & XỬ LÝ RATE LIMIT ("quá nhanh") ========

RATE_LIMIT_KEYWORDS = [
    "thao tác quá nhanh", "quá nhanh", "rate limit",
    "thử lại sau", "vui lòng chờ", "too fast",
    "slow down", "try again later", "please wait",
]

def check_rate_limit_on_page(driver):
    """Kiểm tra page hiện tại có thông báo rate limit không.
    Kiểm tra: Swal2 popup, toast message, và page source.
    Returns: True nếu phát hiện rate limit.
    """
    page_text = ""
    try:
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    except Exception:
        pass
    for kw in RATE_LIMIT_KEYWORDS:
        if kw in page_text:
            print(f"\n⚠️ PHÁT HIỆN RATE LIMIT: '{kw}' trong nội dung trang")
            return True
    # Kiểm tra Swal2 popup và toast - với xử lý StaleElement cho song song
    for selector, label in [
        ("#swal2-title", "Swal2 title"),
        ("#swal2-content", "Swal2 content"),
        ("div.toast-message", "toast message"),
    ]:
        try:
            # Dùng find_elements + loop để tránh StaleElement khi chạy song song
            elems = driver.find_elements(By.CSS_SELECTOR, selector)
            for elem in elems:
                try:
                    elem_text = elem.text.lower()
                    for kw in RATE_LIMIT_KEYWORDS:
                        if kw in elem_text:
                            print(f"\n⚠️ PHÁT HIỆN RATE LIMIT: '{kw}' trong {label}")
                            return True
                except Exception:
                    # Stale element - bỏ qua và chuyển element tiếp theo
                    continue
        except Exception:
            pass
    return False


def handle_rate_limit(driver, context_name="tool"):
    """Xử lý khi phát hiện rate limit: về home -> chờ delay -> kiếm xu -> facebook -> tiếp tục.
    Returns: True nếu đã xử lý, False nếu không cần.
    """
    if not check_rate_limit_on_page(driver):
        return False

    print(f"[{context_name}] ⏳ Phát hiện 'thao tác quá nhanh' — đang về Home...")

    # Bước 1: Về Home (nút Trang chủ)
    try:
        home_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[2]/div/div/div[1]'))
        )
        driver.execute_script("arguments[0].click();", home_btn)
        sleep(smart_random_delay(2, variance=0.2))
        print(f"[{context_name}] ✅ Đã về Home")
    except Exception as e:
        print(f"[{context_name}] ❌ Không thể về Home: {e}")
        driver.refresh()
        sleep(smart_random_delay(3, variance=0.2))

    # Bước 2: Chờ delay config
    delay = CONFIG_DELAY.get("sleep_on_reset", 30)
    print(f"[{context_name}] ⏳ Nghỉ ngơi {delay} giây...")
    wait_for_memory()  # Check memory trước khi chờ dài
    smart_sleep(smart_random_delay(delay, variance=0.15))

    # Bước 3: Ấn Kiếm xu
    try:
        kiem_xu_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[2]/div/div/div[2]'))
        )
        driver.execute_script("arguments[0].click();", kiem_xu_btn)
        sleep(smart_random_delay(1, variance=0.2))
        print(f"[{context_name}] ✅ Đã ấn Kiếm xu")
    except Exception as e:
        print(f"[{context_name}] ❌ Không thể ấn Kiếm xu: {e}")

    # Bước 4: Ấn Facebook
    try:
        fb_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[1]/div[2]/div[3]/div[1]/div'))
        )
        driver.execute_script("arguments[0].click();", fb_btn)
        sleep(smart_random_delay(2, variance=0.2))
        print(f"[{context_name}] ✅ Đã ấn Facebook - sẵn sàng quét job")
    except Exception as e:
        print(f"[{context_name}] ❌ Không thể ấn Facebook: {e}")

    return True

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

try:
    from golike_facebook.selenium_fb import FacebookSeleniumBot
    HAS_SELENIUM_DOM_BOT = True
except ImportError as e:
    HAS_SELENIUM_DOM_BOT = False
    class FacebookSeleniumBot:
        pass

# Fix encoding cho Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Quản lý bộ trình duyệt đang chạy
active_drivers = []
drivers_lock = threading.Lock()
_cleanup_done = False

def cleanup():
    """Đóng tất cả trình duyệt Selenium và dọn dẹp tiến trình Chrome."""
    global _cleanup_done
    if _cleanup_done:
        return
    _cleanup_done = True

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
            # Chỉ diệt chrome.exe được spawn bởi chromedriver.exe hoặc có --remote-debugging-port
            # -> TUYỆT ĐỐI không đụng vào Chrome cá nhân của user
            ps_cmd = (
                "$cdPids = (Get-CimInstance Win32_Process -Filter \"Name='chromedriver.exe'\" | "
                "ForEach-Object { $_.ProcessId }); "
                "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
                "Where-Object { "
                "($_.CommandLine -like '*--remote-debugging-port*') -or "
                "($cdPids -contains $_.ParentProcessId) "
                "} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
            )
            subprocess.run(["powershell", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        # Tắt driver
        os.system("taskkill /f /im chromedriver.exe /T >nul 2>&1")

# Global flag để kiểm soát việc dừng tool
STOP_FLAG = False

def handle_exit_signal(signum, frame):
    """Xử lý Ctrl+C - Tạm dừng, hỏi người dùng muốn làm gì"""
    global STOP_FLAG

    print("\n[🛑] Đã nhận Ctrl+C. Tạm dừng tool, trình duyệt Selenium vẫn đang mở...")
    print("[💡] Gõ 'm' để VỀ MENU chính (Chrome sẽ bị đóng).")
    print("[💡] Gõ 'exit' để THOÁT hoàn toàn và ĐÓNG tool.")

    # Đợi user nhập lựa chọn
    try:
        user_input = input("👉 Lựa chọn (m/exit): ").strip().lower()
        if user_input == 'exit':
            print("[✅] Đang đóng trình duyệt và thoát chương trình...")
            cleanup()
            sys.exit(0)
        else:  # 'm' hoặc bất kỳ phím nào khác
            print("[🔴] Đang đóng trình duyệt...")
            cleanup()
            print("[✓] Đang trở về menu chính...")
    except (EOFError, KeyboardInterrupt):
        cleanup()
        sys.exit(0)

    STOP_FLAG = True
    raise KeyboardInterrupt

import signal

def setup_lifecycle():
    """Đăng ký signal handler cho Ctrl+C và SIGTERM."""
    try:
        signal.signal(signal.SIGINT, handle_exit_signal)
        signal.signal(signal.SIGTERM, handle_exit_signal)
    except ValueError:
        pass

# ================== HỆ THỐNG TỰ ĐỘNG CẬP NHẬT ==================
def _load_sele_version() -> str:
    """Đọc version từ version.json cùng thư mục."""
    try:
        _vf = os.path.join(SCRIPT_DIR, "version.json")
        with open(_vf, "r", encoding="utf-8") as _f:
            return json.load(_f).get("version", "1.8.11")
    except (json.JSONDecodeError, IOError):
        return "1.8.11"

CURRENT_VERSION = _load_sele_version()

def kiem_tra_cap_nhat():
    # Sử dụng hệ thống cập nhật tập trung từ updater.py
    try:
        import updater
        updater.run_version_check(CURRENT_VERSION)
    except Exception as e:
        print(f"[!] Không thể kiểm tra cập nhật: {e}")

# ================= PROXY PARSING =================

def parse_proxy_url(raw: str):
    """
    Parse proxy string thanh cac thanh phan cho Selenium Chrome + requests library.
    Ho tro cac dinh dang:
      - IP:PORT                     -> HTTP proxy khong auth
      - IP:PORT:USER:PASS           -> HTTP proxy co auth
      - socks5://IP:PORT            -> SOCKS5 proxy khong auth
      - socks5://IP:PORT:USER:PASS  -> SOCKS5 proxy co auth
      - http://IP:PORT              -> HTTP proxy (tuong minh)

    Returns dict with chrome_arg, requests_proxies, has_auth, etc. or None if empty.
    """
    if not raw or not raw.strip():
        return None

    raw = raw.strip()

    proto = "http"
    remainder = raw
    if "://" in raw:
        proto, remainder = raw.split("://", 1)

    parts = remainder.split(":")
    if len(parts) < 2:
        print("[!] Dinh dang proxy khong hop le: %s. Dung IP:PORT" % raw)
        return None

    host = parts[0]
    port = parts[1]
    username = None
    password = None
    has_auth = False

    if len(parts) >= 4:
        username = parts[2]
        password = parts[3]
        has_auth = True
    elif len(parts) == 3:
        print("[!] Proxy auth thieu password: %s. Su dung khong auth." % raw)

    chrome_arg = "%s://%s:%s" % (proto, host, port)

    if has_auth:
        requests_proxies = {
            "http": "%s://%s:%s@%s:%s" % (proto, username, password, host, port),
            "https": "%s://%s:%s@%s:%s" % (proto, username, password, host, port),
        }
    else:
        requests_proxies = {
            "http": "%s://%s:%s" % (proto, host, port),
            "https": "%s://%s:%s" % (proto, host, port),
        }

    return {
        "chrome_arg": chrome_arg,
        "requests_proxies": requests_proxies,
        "has_auth": has_auth,
        "username": username,
        "password": password,
        "host": host,
        "port": port,
    }


def _build_proxy_auth_extension(proxy_info: dict) -> str:
    """Tao Chrome extension tam thoi de handle proxy authentication."""
    import tempfile

    host = proxy_info["host"]
    port = proxy_info["port"]
    username = proxy_info["username"]
    password = proxy_info["password"]

    ext_dir = tempfile.mkdtemp(prefix="chrome_proxy_auth_")

    manifest = {
        "version": "1.0.0",
        "manifest_version": 3,
        "name": "Proxy Auth",
        "permissions": ["proxy", "webRequest", "webRequestAuthProvider"],
        "background": {"service_worker": "background.js"}
    }

    with open(os.path.join(ext_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f)

    bg_js = """
    chrome.webRequest.onAuthRequired.addListener(
        function(details) {
            return {
                authCredentials: {
                    username: "%s",
                    password: "%s"
                }
            };
        },
        {urls: ["<all_urls>"]},
        ['blocking']
    );
    """ % (username, password)

    with open(os.path.join(ext_dir, "background.js"), "w") as f:
        f.write(bg_js)

    return ext_dir


def get_proxy_from_config(profile_proxy: str = None) -> dict:
    """
    Lay proxy info tu profile hoac default_proxy.
    profile_proxy: proxy rieng cua profile (tu config_parallel.json)
    Returns parse_proxy_url result hoac None.
    """
    raw = (profile_proxy or "").strip()
    if raw:
        return parse_proxy_url(raw)

    default_raw = CONFIG_DELAY.get("default_proxy", "")
    if default_raw and default_raw.strip():
        return parse_proxy_url(default_raw)

    return None


# ================= CẤU HÌNH DELAY =================
CONFIG_DELAY = {}

def load_delay_config(filepath: str = "config_golike_sele.json"):
    """Load delay config từ file JSON"""
    global CONFIG_DELAY

    default_config = {
        "delay_between_jobs": 10,
        "delay_after_api_call": 3.5,
        "delay_after_complete": 4,
        "delay_after_report_error": 1.5,
        "delay_on_job_hunt_retry": 12,
        "delay_between_accounts": 60,
        "timeout_driver_load": 10,
        "timeout_wait_element": 8,
        "sleep_on_reset": 30,
        "sleep_on_cool_down": 300,
        "delay_after_reset_click": 3.5,
        "sleep_on_hunt_retry": 10,
        "switch_server_minutes": 0,
        "default_proxy": ""
    }

    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                CONFIG_DELAY = json.load(f)
            # Merge với default cho các key thiếu
            for k, v in default_config.items():
                if k not in CONFIG_DELAY:
                    CONFIG_DELAY[k] = v
            print(f"[✓] Đã load config từ {filepath}")
            return
        except Exception as e:
            print(f"[!] Lỗi load config: {e} - Dùng默认")

    CONFIG_DELAY = default_config
    print(f"[!] Không tìm thấy config, dùng mặc định")


def send_tg_notify(message: str):
    """Gửi thông báo Telegram nếu đã cấu hình trong .env hoặc config."""
    # Ưu tiên enviroment variables, fallback vào config
    if not os.getenv('TELEGRAM_ENABLED', '').lower() in ('true', '1', 'yes'):
        if not CONFIG_DELAY.get("telegram_enabled", False):
            return

    # Lấy token từ env var, fallback vào config (sau khi resolve placeholder)
    token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    if not token:
        cfg_token = CONFIG_DELAY.get("telegram_bot_token", "")
        # Nếu là placeholder ${VAR}, lấy từ env
        if cfg_token.startswith('${') and cfg_token.endswith('}'):
            token = os.getenv(cfg_token[2:-1], "")
        else:
            token = cfg_token

    if not token:
        return

    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
    if not chat_id:
        chat_id = CONFIG_DELAY.get("telegram_chat_id", "")

    if not chat_id:
        return

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=10)
    except Exception:
        pass


def setup_telegram_notify():
    """Hỏi user có muốn nhận thông báo Telegram không, và cấu hình chat_id."""
    config_path = os.path.join(SCRIPT_DIR, "config_golike_sele.json")

    # Ưu tiên env var, fallback vào config
    token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    if not token:
        cfg_token = CONFIG_DELAY.get("telegram_bot_token", "")
        if cfg_token.startswith('${') and cfg_token.endswith('}'):
            token = os.getenv(cfg_token[2:-1], '')
        else:
            token = cfg_token

    if not token:
        # Hướng dẫn user cách setup
        print("\n[!] Chua co bot token. Day phil set trong .env file:")
        print("    TELEGRAM_BOT_TOKEN=your_bot_token")
        print("    TELEGRAM_CHAT_ID=your_chat_id")
        return  # Không có bot token thì bỏ qua

    # Lấy chat_id từ env hoặc config
    saved_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
    if not saved_chat_id:
        saved_chat_id = CONFIG_DELAY.get("telegram_chat_id", "").strip()

    was_enabled   = os.getenv('TELEGRAM_ENABLED', '').lower() in ('true', '1', 'yes')
    if not was_enabled:
        was_enabled = CONFIG_DELAY.get("telegram_enabled", False)

    print("\n" + "─"*55)
    print("🔔  CẤU HÌNH THÔNG BÁO TELEGRAM")
    print("─"*55)
    ans = input("Bạn có muốn nhận thông báo từ Telegram bot không? (y/n): ").strip().lower()

    if ans not in ["y", "yes", ""]:
        CONFIG_DELAY["telegram_enabled"] = False
        print("[✓] Đã tắt thông báo Telegram.")
        _save_tg_config(config_path)
        return

    # Hỏi dùng chat_id cũ hay nhập mới
    if saved_chat_id:
        print(f"[*] Chat ID đã lưu: {saved_chat_id}")
        reuse = input("Dùng ID cũ (Enter/y) hay nhập ID mới (n)? ").strip().lower()
        if reuse in ["n", "no"]:
            saved_chat_id = input("👉 Nhập Chat ID mới: ").strip()
    else:
        print("[*] Chưa có Chat ID nào được lưu.")
        saved_chat_id = input("👉 Nhập Chat ID của bạn: ").strip()

    if not saved_chat_id:
        print("[!] Không nhập Chat ID, bỏ qua cấu hình Telegram.")
        return

    # Gửi tin nhắn test
    print("[*] Đang gửi tin nhắn kiểm tra...")
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={
            "chat_id": saved_chat_id,
            "text": "✅ <b>GoLike Bot đã kết nối!</b>\nBạn sẽ nhận thông báo khi acc đạt giới hạn job.",
            "parse_mode": "HTML"
        }, timeout=10)
        if r.status_code == 200:
            print("[✅] Gửi thành công! Bot Telegram đã hoạt động.")
            # Lưu config (không lưu token vì đã dùng env var)
            CONFIG_DELAY["telegram_enabled"] = True
            CONFIG_DELAY["telegram_chat_id"] = saved_chat_id
            _save_tg_config(config_path)
        else:
            print(f"[❌] Gửi thất bại (HTTP {r.status_code}). Kiểm tra lại Chat ID.")
            CONFIG_DELAY["telegram_enabled"] = False
    except Exception as ex:
        print(f"[❌] Lỗi kết nối: {ex}")
        CONFIG_DELAY["telegram_enabled"] = False
        print(f"[❌] Lỗi kết nối Telegram: {ex}")
        CONFIG_DELAY["telegram_enabled"] = False


def _save_tg_config(config_path: str):
    """Lưu lại config_golike_sele.json sau khi cập nhật telegram settings."""
    try:
        # Xóa sensitive data trước khi lưu để tránh commit
        config_to_save = CONFIG_DELAY.copy()
        config_to_save.pop('telegram_bot_token', None)
        config_to_save.pop('telegram_chat_id', None)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_to_save, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

# ── ANSI color helpers ──────────────────────────────────────────────
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_YELLOW = "\033[93m"
C_CYAN = "\033[96m"
C_BLUE = "\033[94m"
C_MAGENTA = "\033[95m"
LABEL_COLORS = [C_CYAN, C_BLUE, C_MAGENTA]


def show_config_summary():
    """Hiển thị tóm tắt config đã cài và hỏi user có muốn thay đổi không."""
    print("\n" + "─" * 55)
    print(f"{C_BOLD}📋 CONFIG HIỆN TẠI (config_golike_sele.json){C_RESET}")
    print("─" * 55)

    # ── Nhóm Delay & Timeout ──────────────────────────────────────
    print(f"\n  {C_BOLD}⏱ DELAY & TIMEOUT{C_RESET}")
    delay_keys = [
        ("delay_between_jobs",       "Delay giữa các job"),
        ("delay_after_api_call",     "Delay sau API call"),
        ("delay_after_complete",     "Delay sau khi hoàn thành"),
        ("delay_after_report_error", "Delay sau khi báo lỗi"),
        ("delay_on_job_hunt_retry",  "Delay khi tải lại job"),
        ("delay_between_accounts",   "Delay khi đổi acc"),
        ("timeout_driver_load",      "Timeout tải driver"),
        ("timeout_wait_element",     "Timeout chờ element"),
        ("sleep_on_reset",           "Sleep khi reset trang"),
        ("sleep_on_cool_down",       "Sleep khi nguội hệ thống"),
        ("delay_after_reset_click",  "Delay click khi reset"),
        ("sleep_on_hunt_retry",      "Sleep khi retry hunt job"),
        ("switch_server_minutes",    "Tự động đổi server"),
    ]

    for i, (key, label) in enumerate(delay_keys):
        val = CONFIG_DELAY.get(key, "?")
        color = LABEL_COLORS[i % len(LABEL_COLORS)]

        if key == "sleep_on_cool_down" and val:
            suffix = f"  ({round(val / 60, 1)} phút)"
        elif key == "switch_server_minutes":
            suffix = "  (tắt)" if val == 0 else ""
        else:
            suffix = ""

        unit = " phút" if key == "switch_server_minutes" else "s"
        print(f"    {color}{label + ' ':.<40s}{C_RESET} {C_YELLOW}{val}{unit}{suffix}{C_RESET}")

    # ── Nhóm Proxy ────────────────────────────────────────────────
    print(f"\n  {C_BOLD}🌐 PROXY{C_RESET}")
    proxy_val = CONFIG_DELAY.get("default_proxy", "")
    proxy_display = proxy_val if proxy_val else "(không đặt)"
    print(f"    {C_MAGENTA}{'Default proxy':.<40s}{C_RESET} {C_YELLOW}{proxy_display}{C_RESET}")
    print("─" * 55)

    ans = input("\n👉 Bạn có muốn thay đổi config không? (Enter để bỏ qua): ").strip().lower()
    if ans in ("y", "yes"):
        setup_delay_config()


def setup_delay_config():
    """Menu setup delay lần đầu"""
    config_path = os.path.join(SCRIPT_DIR, "config_golike_sele.json")

    print("\n" + "="*60)
    print("CẤU HÌNH DELAY CHO GOLIKE FACEBOOK SELENIUM")
    print("="*60)
    print(f"[File lưu tại: {os.path.abspath(config_path)}]\n")

    key_names = {
        "delay_between_jobs": "Delay giữa các job (giây)",
        "delay_after_api_call": "Delay sau API call (giây)",
        "delay_after_complete": "Delay sau khi nhấn Hoàn thành (giây)",
        "delay_after_report_error": "Delay sau khi báo lỗi (giây)",
        "delay_on_job_hunt_retry": "Delay khi tải lại job (giây)",
        "delay_between_accounts": "Delay khi đổi acc (giây)",
        "timeout_driver_load": "Timeout tải driver (giây)",
        "timeout_wait_element": "Timeout chờ element (giây)",
        "sleep_on_reset": "Sleep khi reset trang (giây)",
        "sleep_on_cool_down": "Sleep khi nguội hệ thống (giây)",
        "delay_after_reset_click": "Delay click khi reset (giây)",
        "sleep_on_hunt_retry": "Sleep khi retry hunt job (giây)",
        "switch_server_minutes": "Thời gian tự động đổi Server (phút, 0 để tắt)"
    }

    config = CONFIG_DELAY.copy() if CONFIG_DELAY else {}

    for key, label in key_names.items():
        default = config.get(key, 10)
        user_input = input(f"{label} [mặc định: {default}]: ").strip()
        if user_input:
            try:
                config[key] = float(user_input)
            except ValueError:
                print(f"[!] Giá trị không hợp lệ, giữ mặc định: {default}")

    # Lưu file
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"\n[✅] Đã lưu config vào {config_path}")
    except Exception as e:
        print(f"[!] Lỗi lưu config: {e}")

    input("\nNhấn Enter để tiếp tục...")
    load_delay_config(config_path)  # Reload config

# ================= CHIA SẺ HÀM LOGIC CHUNG =================
def map_job_type(job_text):
    job_text = job_text.lower()
    if "like cho fanpage" in job_text: return "lik_page"
    if "like cho bài viết" in job_text or "like cho bài" in job_text: return "like"
    if "theo dõi" in job_text: return "follow"
    if "love" in job_text or "tim" in job_text: return "love"
    if "haha" in job_text: return "haha"
    if "wow" in job_text: return "wow"
    if "sad" in job_text or "buồn" in job_text: return "sad"
    if "angry" in job_text or "phẫn nộ" in job_text: return "angry"
    if "care" in job_text or "thương thương" in job_text: return "care"
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

def click_home_navigation(driver):
    try:
        home = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[2]/div/div/div[1]')))
        driver.execute_script("arguments[0].click();", home)
    except Exception as e:
        print(f"Lỗi click Trang chủ: {e}")

def click_kiem_xu_navigation(driver):
    try:
        nhiemvu = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[2]/div/div/div[2]')))
        driver.execute_script("arguments[0].click();", nhiemvu)
    except Exception as e:
        print(f"Lỗi click Kiếm xu: {e}")

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


def setup_multi_accounts():
    import os, json
    file_path = "multi_accounts.json"
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                accounts = json.load(f)
            if accounts and isinstance(accounts, list):
                print("\n--- TÌM THẤY DANH SÁCH TÀI KHOẢN ĐÃ LƯU ---")
                for i, acc in enumerate(accounts, 1):
                    print(f"{i}. UID: {acc.get('uid', 'N/A')}")
                ans = input("Bạn có muốn chạy danh sách này không? (y/n): ").strip().lower()
                if ans in ['y', 'yes', '']:
                    return accounts
        except: pass
        
    print("\n--- NHẬP DANH SÁCH TÀI KHOẢN MỚI ---")
    print("Nhấn Enter để trống tại phần nhập Cookie khi bạn muốn kết thúc.")
    accounts = []
    idx = 1
    while True:
        c = input(f"Nhập Cookie cho Acc {idx}: ").strip()
        if not c:
            break
        u = input(f"Nhập UID cho Acc {idx}: ").strip()
        accounts.append({"cookie": c, "uid": u})
        idx += 1
        
    if accounts:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(accounts, f, indent=4)
        except: pass
            
    return accounts

def run_single_mode():
    global STOP_FLAG
    STOP_FLAG = False
    print("\n🚀 Bắt đầu thiết lập chế độ Chạy đơn lẻ...")
    target_server_raw = input("👉 Bạn muốn cày ở Server nào? (Nhập 1 hoặc 2, hoặc Enter để tự động chuyển): ").strip()
    target_server = ""
    if target_server_raw == "1":
        target_server = "SV1"
    elif target_server_raw == "2":
        target_server = "SV2"
    elif target_server_raw.upper() in ["SV1", "SV2"]:
        target_server = target_server_raw.upper()
    is_seq = input("Bạn có muốn chạy lần lượt nhiều tài khoản (Sequential Single Mode)? (y/n): ").strip().lower()
    accounts_list = []
    if is_seq in ['y', 'yes']:
        accounts_list = setup_multi_accounts()
        if not accounts_list:
            print("❌ Không có tài khoản nào được nhập. Thoát.")
            return
    else:
        cookie_fb = load_cookie()
        accounts_list = [{"cookie": cookie_fb, "uid": None}]

    # Hoi proxy
    default_proxy = CONFIG_DELAY.get("default_proxy", "")
    proxy_prompt = "🌐 Nhập proxy (IP:PORT hoặc IP:PORT:USER:PASS) hoặc Enter để bỏ qua"
    if default_proxy:
        proxy_prompt += " [mặc định: %s]" % default_proxy
    proxy_input = input(proxy_prompt + ": ").strip()
    if not proxy_input:
        proxy_input = default_proxy
    proxy_info = parse_proxy_url(proxy_input)

    proxy_auth_ext = None
    Fb = None
    fb_proxies = proxy_info["requests_proxies"] if proxy_info else None

    golike_user, golike_pass = get_golike_credentials()

    print("\nĐang khởi động Chrome...", flush=True)
    options = Options()

    # ================= RANDOMIZE ALL FINGERPRINTS =================
    # Lấy device profile ngẫu nhiên (UA + platform + viewport)
    device_profile = get_random_device_profile()

    options.add_argument("--lang=en-US")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--no-sandbox")
    options.add_argument(f"user-agent={device_profile['user_agent']}")
    options.add_argument(f"--window-size={device_profile['viewport_width']},{device_profile['viewport_height']}")
    print(f"[+] Fingerprint random:")
    print(f"     • UA: {device_profile['user_agent'][:50]}...")
    print(f"     • Platform: {device_profile['platform']}")
    print(f"     • Viewport: {device_profile['viewport_width']}x{device_profile['viewport_height']}")

    if proxy_info:
        options.add_argument("--proxy-server=%s" % proxy_info["chrome_arg"])
        if proxy_info["has_auth"]:
            proxy_auth_ext = _build_proxy_auth_extension(proxy_info)
            options.add_argument("--load-extension=%s" % proxy_auth_ext)
            print("[*] Proxy co auth: da cai extension tu dong")

    driver = selenium_driver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    with drivers_lock:
        active_drivers.append(driver)
    driver.set_window_position(100, 100)
    driver.set_window_size(500, 750)

    # Inject stealth script để conceal automation và randomize navigator properties
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": STEALTH_INJECTION_SCRIPT
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

        prev_max_job = False  # Flag: acc trước bị MAX_JOB
        for acc_idx, acc_info in enumerate(accounts_list):
            if STOP_FLAG: break
            
            current_cookie = acc_info.get("cookie")
            current_uid = acc_info.get("uid")  # Facebook UID (dùng cho API)
            current_golike_uid = acc_info.get("golike_uid") or current_uid  # GoLike UID (dùng để chọn nick trong dropdown)
            
            if current_cookie:
                Fb = FB_API(current_cookie, proxies=fb_proxies)
                Fb.login()
            else:
                Fb = None
                
            if acc_idx > 0:
                print(f"\n🔄 Chuyển sang tài khoản tiếp theo (FB UID: {current_uid} | GoLike UID: {current_golike_uid})...")
                click_home_navigation(driver)
                sleep(2)
                try:
                    btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Đã hiểu')]")
                    driver.execute_script("arguments[0].click();", btn)
                    sleep(1)
                except: pass
                click_kiem_xu_navigation(driver)
                sleep(1)
                try:
                    fb_b = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[1]/div[2]/div[3]/div[1]/div')))
                    driver.execute_script("arguments[0].click();", fb_b)
                except: pass
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
            
                if current_golike_uid:
                    chon_acc = None
                    for i, (acc, name, acc_id) in enumerate(valid_accounts, start=1):
                        if str(current_golike_uid).strip() == str(acc_id).strip():
                            chon_acc = i
                            break
                    if not chon_acc:
                        print(f"❌ Không tìm thấy nick GoLike với UID: {current_golike_uid}. Bỏ qua!")
                        continue
                else:
                    chon_acc = int(input("👉 Nhập số để chọn nick chạy: "))
            
                selected_node, name_run, uid_run = valid_accounts[chon_acc-1]
                driver.execute_script("arguments[0].click();", selected_node)
                print(f"🚀 ✅ ĐANG CHẠY ACC: {name_run} | UID: {uid_run}")
                sleep(3)
                if prev_max_job:
                    print("⏳ Chờ 60s để thông báo cũ biến mất...")
                    smart_sleep(60)
                    prev_max_job = False
            
                # VÒNG LẶP CHẠY CHÍNH
                failed_load_count = 0 # Bộ đếm số lần không tìm thấy Job liên tiếp
                last_server_switch_time = time.time()
                while not STOP_FLAG:
                    try:
                        # ---- Kiểm tra rate limit ----
                        handle_rate_limit(driver, name_run)

                        # ---- Kiểm tra RAM (Memory Circuit Breaker) ----
                        used_percent, available_mb = check_system_memory()
                        if used_percent >= MEMORY_LIMIT_PERCENT or available_mb <= MEMORY_AVAILABLE_MIN:
                            print(f"[⚠️] RAM cao: {used_percent:.1f}% used, {available_mb:.0f}MB available - đang chờ...")
                            wait_for_memory()

                        # ---- Kiểm tra đổi server ----
                        if target_server:
                            try:
                                current_sv_elem = driver.find_element(By.CSS_SELECTOR, "small.d300 span.font-bold")
                                current_sv = current_sv_elem.text.strip().upper()
                                if current_sv != target_server:
                                    print(f"🔄 Đang chuyển sang {target_server} theo yêu cầu...")
                                    switch_btn = driver.find_element(By.XPATH, "//button[normalize-space(.)='Đổi server']")
                                    driver.execute_script("arguments[0].click();", switch_btn)
                                    sleep(1)
                                    sv_cards = driver.find_elements(By.CSS_SELECTOR, "div.card.hand")
                                    for card in sv_cards:
                                        try:
                                            sv_name = card.find_element(By.CSS_SELECTOR, "span.font-bold").text.strip().upper()
                                            if sv_name == target_server:
                                                driver.execute_script("arguments[0].click();", card)
                                                sleep(2)
                                                print(f"✅ Đã chọn xong {target_server}!")
                                                break
                                        except: pass
                            except: pass
                        else:
                            switch_mins = CONFIG_DELAY.get("switch_server_minutes", 0)
                            if switch_mins > 0 and (time.time() - last_server_switch_time) > switch_mins * 60:
                                try:
                                    switch_btn = driver.find_element(By.XPATH, "//button[normalize-space(.)='Đổi server']")
                                    driver.execute_script("arguments[0].click();", switch_btn)
                                    # Wait for success toast and display its message
                                    try:
                                        toast_msg = WebDriverWait(driver, 5).until(
                                            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.toast.toast-success div.toast-message"))
                                        ).text
                                        print("🔔 %s" % toast_msg)
                                    except Exception:
                                        pass
                                    print("🔄 Đã tự động ấn Đổi Server lấy job!")
                                    last_server_switch_time = time.time()
                                    sleep(2)
                                except:
                                    pass
                        # ----------------------------

                        print("\n================== TÌM JOB MỚI ==================")
                        try:
                            # 1. Quét thông báo max job trong 3s
                            for _ in range(3):
                                if job_limit_reached(driver):
                                    raise Exception("MAX_JOB")
                                sleep(1)

                            # 2. Quét job (chờ 15s)
                            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.card.hand, div.card.card-primary")))
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
                                            sleep(smart_random_delay(CONFIG_DELAY.get("delay_after_reset_click", 3.5), variance=0.2))
                                        
                                            fb_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[1]/div[2]/div[3]/div[1]/div')))
                                            driver.execute_script("arguments[0].click();", fb_btn)
                                        except Exception as err:
                                            print(f"❌ Lỗi thao tác Reset: {err}")
                                    
                                        print("⏳ Nghỉ ngơi 30 giây trước khi thử quét tiếp...")
                                        smart_sleep(smart_random_delay(CONFIG_DELAY.get("sleep_on_reset", 30), variance=0.15))
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
                                    sleep(smart_random_delay(CONFIG_DELAY.get("delay_after_reset_click", 3.5), variance=0.2))
                                    # Click lại Facebook để tải lại trang Job sạch sẽ
                                    fb_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[1]/div[2]/div[3]/div[1]/div')))
                                    driver.execute_script("arguments[0].click();", fb_btn)
                                    print(f"✅ Đã làm mới xong trang. Đang nghỉ {round(CONFIG_DELAY.get("sleep_on_cool_down", 300)/60,2)} phút nguội hệ thống...")
                                except Exception as e:
                                    print(f"❌ Lỗi trong lúc tự động Reset: {e}")
                                smart_sleep(smart_random_delay(CONFIG_DELAY.get("sleep_on_cool_down", 300), variance=0.1))
                                continue

                            try:
                                current_sv_elem = driver.find_element(By.CSS_SELECTOR, "small.d300 span.font-bold")
                                current_sv = current_sv_elem.text.strip().upper()
                            except: current_sv = "SV1"

                            if current_sv == "SV2":
                                print(f"Không thấy Job nào (SV2 - Lần {failed_load_count}/10). Đang ấn Tải lại...")
                                try:
                                    reload_btn = driver.find_element(By.CSS_SELECTOR, "button.loader-new")
                                    driver.execute_script("arguments[0].click();", reload_btn)
                                    sleep(smart_random_delay(CONFIG_DELAY.get("delay_on_job_hunt_retry", 12), variance=0.2))
                                except: pass
                            else:
                                print(f"Không thấy Job nào ({current_sv} - Lần {failed_load_count}/10). Đứng chờ auto-push...")
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
                        sleep(CONFIG_DELAY.get("delay_after_report_error", 1.5))
                    
                        orig_window = driver.current_window_handle
                        try:
                            chrome_btn = find_browser_button(driver, timeout=8)
                            fb_job_url = chrome_btn.get_attribute("href")
                            driver.execute_script("arguments[0].click();", chrome_btn)
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
                        sleep(CONFIG_DELAY.get("delay_after_report_error", 1))
                    
                        # GỌI API
                        j_type = map_job_type(job_type_raw)
                        uid = getidpost(fb_job_url)
                        success = False
                    
                        if uid and uid and uid != "0":
                            print(f"=> Phân tích UID thành công: {uid}. Đang gọi API...")
                            sleep(smart_random_delay(CONFIG_DELAY.get("delay_after_api_call", 1.5), variance=0.2))
                            try:
                                if j_type == "follow":
                                    res = throttled_api_call(Fb, "FOLLOW", uid)
                                    print(f"API Follow: {res}")
                                    success = res.get("success", False)
                                elif j_type == "lik_page":
                                    res = throttled_api_call(Fb, "LIKE_PAGE", uid)
                                    print(f"API Like Page: {res}")
                                    success = res.get("success", False)
                                elif j_type in ["like", "love", "haha", "wow", "sad", "angry", "care"]:
                                    reaction = j_type.upper()
                                    res = throttled_api_call(Fb, "REACTION", reaction, uid)
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
                        delay_sync = CONFIG_DELAY.get("delay_after_complete", 3.5)
                        print(f"Chờ {delay_sync}s đồng bộ hệ thống...")
                        sleep(delay_sync)
                    
                        if success:
                            print("Đang ấn Hoàn thành...")
                            try:
                                ht = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//h6[contains(text(), 'Hoàn thành')]")))
                                driver.execute_script("arguments[0].click();", ht)
                                sleep(smart_random_delay(CONFIG_DELAY.get("delay_after_complete", 4), variance=0.2))
                                try:
                                    t_p = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "swal2-title"))).text
                                    c_p = driver.find_element(By.ID, "swal2-content").text
                                    print(f"GoLike báo: [{t_p}] {c_p}")
                                    # Kiểm tra rate limit từ popup
                                    popup_text = f"{t_p} {c_p}".lower()
                                    rate_limit_detected = False
                                    for kw in RATE_LIMIT_KEYWORDS:
                                        if kw in popup_text:
                                            print(f"⚠️ GoLike báo rate limit: '{kw}' — đang xử lý...")
                                            rate_limit_detected = True
                                            break

                                    if rate_limit_detected:
                                        ok_c = driver.find_element(By.CSS_SELECTOR, ".swal2-confirm.swal2-styled")
                                        driver.execute_script("arguments[0].click();", ok_c)
                                        sleep(1)
                                        handle_rate_limit(driver, name_run)
                                        # After handling rate limit, continue to next job scan
                                        need_skip = True
                                    else:
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
                                bl = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'row')][.//h6[contains(text(), 'Báo lỗi')]]")))
                                driver.execute_script("arguments[0].click();", bl)
                                sleep(CONFIG_DELAY.get("delay_after_report_error", 1.5))
                            
                                lydo = "Tôi không muốn làm Job này"
                                if not uid or uid == "0": lydo = "Không tìm thấy bài viết"
                                else: lydo = "Báo cáo hoàn thành thất bại"
                            
                                c_lydo = driver.find_element(By.XPATH, f"//div[contains(@class, 'row')][.//h6[contains(text(), '{lydo}')]]")
                                driver.execute_script("arguments[0].click();", c_lydo)
                                sleep(CONFIG_DELAY.get("delay_after_report_error", 1))
                            
                                gui = driver.find_element(By.XPATH, "//button[contains(text(), 'Gửi báo cáo')]")
                                driver.execute_script("arguments[0].click();", gui)
                                sleep(CONFIG_DELAY.get("delay_after_report_error", 1.5))
                                try:
                                    o_b = driver.find_element(By.CSS_SELECTOR, ".swal2-confirm.swal2-styled")
                                    driver.execute_script("arguments[0].click();", o_b)
                                except: pass
                                print("Đã Báo lỗi thành công.")
                            except Exception as e:
                                print(f"Lỗi khi Báo lỗi: {e}")
                    
                        print(f"Đợi {CONFIG_DELAY.get('delay_between_jobs', 10)}s trước khi tìm job tiếp theo...")
                        if job_limit_reached(driver):
                            acc_name = locals().get('name_run') or str(current_uid)
                            now_str = datetime.now().strftime('%H:%M:%S %d/%m/%Y')
                            tg_msg = (
                                f"🚨 <b>GoLike MAX JOB</b>\n"
                                f"👤 Acc: <b>{acc_name}</b>\n"
                                f"⏰ Lúc: {now_str}\n"
                                f"✅ Đã đủ 100 jobs/ngày. Đang chuyển sang acc tiếp theo..."
                            )
                            send_tg_notify(tg_msg)
                            print("[⚠️] Đã đạt giới hạn 100 jobs/ngày. Tự động chuyển acc tiếp theo...")
                            prev_max_job = True
                            break
                        smart_sleep(smart_random_delay(CONFIG_DELAY.get("delay_between_jobs", 10)))

                    except Exception as e:
                        if str(e) == "MAX_JOB":
                            acc_name = locals().get('name_run') or str(current_uid)
                            now_str = datetime.now().strftime('%H:%M:%S %d/%m/%Y')
                            tg_msg = (
                                f"🚨 <b>GoLike MAX JOB</b>\n"
                                f"👤 Acc: <b>{acc_name}</b>\n"
                                f"⏰ Lúc: {now_str}\n"
                                f"✅ Đã đủ 100 jobs/ngày. Đang chuyển sang acc tiếp theo..."
                            )
                            send_tg_notify(tg_msg)
                            print("[⚠️] Đã đạt giới hạn 100 jobs/ngày.")
                            prev_max_job = True
                            break  # Thoát while -> for loop xử lý chuyển acc
                        print(f"Lỗi vòng lặp chạy (chờ 5s): {e}")
                        sleep(5)  # Keep as error retry - not configurable
            except Exception as e:
                print(f"Lỗi tương tác giao diện tài khoản: {e}")
    except KeyboardInterrupt:
        pass
    finally:
        pass # Giữ trình duyệt mở theo yêu cầu

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
    profile_proxy = profile_data.get("proxy", "")

    proxy_info = get_proxy_from_config(profile_proxy)

    print(f"\n" + "="*60)
    print(f"🔷 KHỞI TẠO TÀI KHOẢN CHẠY SONG SONG: [{p_name}]")
    print("="*60)
    if proxy_info:
        print(f"🌐 Proxy: {proxy_info['chrome_arg']}")

    if not gl_user or not gl_pass or not fb_cookie:
        print(f"❌ Cấu hình [{p_name}] thiếu thông tin quan trọng. Bỏ qua!")
        return None, None

    try:
        fb_proxies = proxy_info["requests_proxies"] if proxy_info else None
        Fb = FB_API(fb_cookie, proxies=fb_proxies)
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

    # ================= RANDOMIZE ALL FINGERPRINTS =================
    # Lấy device profile ngẫu nhiên (UA + platform + viewport) per account
    device_profile = get_random_device_profile()

    options.add_argument("--lang=en-US")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument(f"user-agent={device_profile['user_agent']}")
    options.add_argument(f"--window-size={device_profile['viewport_width']},{device_profile['viewport_height']}")
    print(f"[+] [{p_name}] Fingerprint random:")
    print(f"     • UA: {device_profile['user_agent'][:50]}...")
    print(f"     • Platform: {device_profile['platform']}")
    print(f"     • Viewport: {device_profile['viewport_width']}x{device_profile['viewport_height']}")

    if proxy_info:
        options.add_argument("--proxy-server=%s" % proxy_info["chrome_arg"])
        if proxy_info["has_auth"]:
            proxy_auth_ext = _build_proxy_auth_extension(proxy_info)
            options.add_argument("--load-extension=%s" % proxy_auth_ext)

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

    # Inject stealth script để conceal automation và randomize navigator properties
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": STEALTH_INJECTION_SCRIPT
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

        # ── Thử nhiều selector để tìm danh sách acc ──────────────────────
        ACC_CARD_SELECTORS = [
            "div.card.shadow-200.mt-1",
            "div.card.mt-1",
            "div.card.shadow",
            "div.account-item",
            "div.select-account div.card",
            "div.list-account div.card",
        ]
        accounts = []
        for sel in ACC_CARD_SELECTORS:
            accounts = driver.find_elements(By.CSS_SELECTOR, sel)
            if accounts:
                log_thread(p_name, f"[DEBUG] Tìm thấy {len(accounts)} acc với selector: {sel}")
                break

        if not accounts:
            # Fallback: lấy tất cả card trong vùng dropdown
            try:
                dropdown = driver.find_element(By.CSS_SELECTOR, "div.select-account")
                accounts = dropdown.find_elements(By.CSS_SELECTOR, "div.card")
                log_thread(p_name, f"[DEBUG] Fallback: tìm thấy {len(accounts)} card trong select-account")
            except Exception:
                pass

        # ── Lấy golike_uid để ưu tiên match chính xác ────────────────────
        golike_uid = str(profile_data.get("golike_uid", profile_data.get("target_fb_uid", ""))).strip()
        target_uid = str(profile_data.get("target_fb_uid", "")).strip()
        target_name = str(profile_data.get("target_fb_name", "")).strip().lower()

        # ── Name extractors: thử nhiều selector con khác nhau ────────────
        NAME_SELECTORS = ["div.col-8 span", "span.name", "div.name", "p.name", "span", "div.info span"]
        UID_ATTRS      = ["id", "data-id", "data-uid", "data-user-id"]

        def extract_acc_info(card):
            """Trả về (name, uid_str) từ card element."""
            name = ""
            uid_str = ""
            for ns in NAME_SELECTORS:
                try:
                    name = card.find_element(By.CSS_SELECTOR, ns).text.strip()
                    if name:
                        break
                except Exception:
                    pass
            for ua in UID_ATTRS:
                try:
                    uid_str = (card.get_attribute(ua) or "").strip()
                    if uid_str:
                        break
                except Exception:
                    pass
            return name, uid_str

        # ── In danh sách acc tìm được để debug ───────────────────────────
        log_thread(p_name, f"[ACC LIST] golike_uid='{golike_uid}' | target_uid='{target_uid}' | target_name='{target_name}'")
        for i, acc in enumerate(accounts):
            try:
                nm, uid_acc = extract_acc_info(acc)
                log_thread(p_name, f"  [{i}] name='{nm}' | uid='{uid_acc}'")
            except Exception:
                pass

        # ── Match theo thứ tự ưu tiên: golike_uid > target_uid > name ────
        selected = False
        for acc in accounts:
            try:
                nm, uid_acc = extract_acc_info(acc)

                match_uid   = golike_uid and uid_acc and golike_uid == uid_acc
                match_tuid  = target_uid and uid_acc and target_uid == uid_acc
                match_name  = target_name and nm and target_name in nm.lower()

                if match_uid or match_tuid or match_name:
                    driver.execute_script("arguments[0].click();", acc)
                    reason = "golike_uid" if match_uid else ("target_uid" if match_tuid else "target_name")
                    log_thread(p_name, f"✅ Đã chọn acc: '{nm}' (uid='{uid_acc}') — match by {reason}")
                    selected = True
                    break
            except Exception:
                pass

        if not selected:
            log_thread(p_name, f"⚠️ Không tìm thấy acc khớp cho [{p_name}]!")
            log_thread(p_name, f"   Hãy kiểm tra 'golike_uid'/'target_fb_uid'/'target_fb_name' trong config.")
            if accounts:
                nm0, uid0 = extract_acc_info(accounts[0])
                driver.execute_script("arguments[0].click();", accounts[0])
                log_thread(p_name, f"⚠️ Tạm thời chọn acc đầu tiên: '{nm0}' (uid='{uid0}')")
            else:
                log_thread(p_name, "❌ Không tìm thấy acc FB nào liên kết!")
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
    last_server_switch_time = time.time()
    try:
        while not STOP_FLAG:
            try:
                # ---- Kiểm tra rate limit ----
                handle_rate_limit(driver, p_name)

                # ---- Kiểm tra RAM (Memory Circuit Breaker) ----
                used_percent, available_mb = check_system_memory()
                if used_percent >= MEMORY_LIMIT_PERCENT or available_mb <= MEMORY_AVAILABLE_MIN:
                    log_thread(p_name, f"[⚠️] RAM cao: {used_percent:.1f}% used, {available_mb:.0f}MB available - đang chờ...")
                    wait_for_memory()

                # ---- Kiểm tra đổi server ----
                switch_mins = CONFIG_DELAY.get("switch_server_minutes", 0)
                if switch_mins > 0 and (time.time() - last_server_switch_time) > switch_mins * 60:
                    try:
                        switch_btn = driver.find_element(By.XPATH, "//button[normalize-space(.)='Đổi server']")
                        driver.execute_script("arguments[0].click();", switch_btn)
                        # Wait for success toast and display its message
                        try:
                            toast_msg = WebDriverWait(driver, 5).until(
                                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.toast.toast-success div.toast-message"))
                            ).text
                            print("🔔 %s" % toast_msg)
                        except Exception:
                            pass
                        log_thread(p_name, "🔄 Đã tự động ấn Đổi Server!")
                        last_server_switch_time = time.time()
                        sleep(2)
                    except:
                        pass
                # ----------------------------

                log_thread(p_name, "=== QUÉT JOB ===")
                try:
                    # 1. Quét thông báo max job trong 3s
                    for _ in range(3):
                        if job_limit_reached(driver):
                            raise Exception("MAX_JOB")
                        sleep(1)

                    # 2. Quét job (chờ 15s)
                    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.card.hand, div.card.card-primary")))
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
                                    sleep(smart_random_delay(CONFIG_DELAY.get("delay_after_reset_click", 3.5), variance=0.2))
                                    
                                    fb_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[1]/div[2]/div[3]/div[1]/div')))
                                    driver.execute_script("arguments[0].click();", fb_btn)
                                except Exception as err:
                                    log_thread(p_name, f"❌ Lỗi khi Reset: {err}")
                                
                                log_thread(p_name, "⏳ Bắt đầu nghỉ ngơi 30 giây nguội máy...")
                                failed_load_count = 0 # Reset bộ đếm
                                smart_sleep(smart_random_delay(CONFIG_DELAY.get("sleep_on_reset", 30), variance=0.15))
                                continue
                    except: pass

                    failed_load_count += 1
                    if failed_load_count >= 10:
                        log_thread(p_name, f"🚨 ĐÃ HỤT JOB {failed_load_count} LẦN! Thực hiện Tự động Reset trang Nhiệm vụ -> Facebook...")
                        failed_load_count = 0
                        try:
                            nv = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[2]/div/div/div[2]')))
                            driver.execute_script("arguments[0].click();", nv)
                            sleep(smart_random_delay(CONFIG_DELAY.get("delay_after_reset_click", 3.5), variance=0.2))
                            fb_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[1]/div[2]/div[3]/div[1]/div')))
                            driver.execute_script("arguments[0].click();", fb_btn)
                            log_thread(p_name, "✅ Reset trang xong. Đang chờ 5 phút nguội hệ thống...")
                        except Exception as e:
                            log_thread(p_name, f"❌ Lỗi khi tự động Reset: {e}")
                        smart_sleep(smart_random_delay(CONFIG_DELAY.get("sleep_on_cool_down", 300), variance=0.1))
                        continue

                    log_thread(p_name, f"Không thấy Job nào (Lần {failed_load_count}/10). Đang ấn Tải lại...")
                    try:
                        reload = driver.find_element(By.CSS_SELECTOR, "button.loader-new")
                        driver.execute_script("arguments[0].click();", reload)
                        sleep(smart_random_delay(CONFIG_DELAY.get("delay_on_job_hunt_retry", 12), variance=0.2))
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
                sleep(CONFIG_DELAY.get("delay_after_report_error", 1.5))
                
                orig_w = driver.current_window_handle
                try:
                    ch_b = find_browser_button(driver, timeout=8)
                    fb_url = ch_b.get_attribute("href")
                    driver.execute_script("arguments[0].click();", ch_b)
                except TimeoutException:
                    log_thread(p_name, "Lỗi: Không tìm thấy lựa chọn trình duyệt. Bỏ qua.")
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
                sleep(CONFIG_DELAY.get("delay_after_report_error", 1))
                
                j_t = map_job_type(j_raw)
                uid = getidpost(fb_url)
                ok = False
                if uid and uid != "0":
                    sleep(smart_random_delay(CONFIG_DELAY.get("delay_after_report_error", 1.5), variance=0.2))
                    try:
                        if j_t == "follow":
                            res = throttled_api_call(Fb, "FOLLOW", uid)
                            ok = res.get("success", False)
                            log_thread(p_name, f"API Follow: {res}")
                        elif j_t == "lik_page":
                            res = throttled_api_call(Fb, "LIKE_PAGE", uid)
                            ok = res.get("success", False)
                            log_thread(p_name, f"API LikePage: {res}")
                        elif j_t in ["like", "love", "haha", "wow", "sad", "angry", "care"]:
                            res = throttled_api_call(Fb, "REACTION", j_t.upper(), uid)
                            ok = res.get("success", False)
                            log_thread(p_name, f"API Reaction ({j_t}): {res}")
                        else:
                            log_thread(p_name, f"⚠️ Loại tương tác chưa hỗ trợ: {j_t}")
                    except Exception as api_e:
                        log_thread(p_name, f"❌ Lỗi API tương tác: {api_e}")
                else:
                    log_thread(p_name, f"⚠️ Không trích xuất được UID từ Link: {fb_url}")

                need_skip = not ok
                sleep(smart_random_delay(CONFIG_DELAY.get("delay_after_api_call", 3.5), variance=0.2))
                if ok:
                    try:
                        ht = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//h6[contains(text(), 'Hoàn thành')]")))
                        driver.execute_script("arguments[0].click();", ht)
                        sleep(smart_random_delay(CONFIG_DELAY.get("delay_after_complete", 4), variance=0.2))
                        try:
                            tp = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "swal2-title"))).text
                            cp = driver.find_element(By.ID, "swal2-content").text
                            log_thread(p_name, f"GoLike: [{tp}] {cp}")
                            # Kiểm tra rate limit từ popup
                            popup_text = f"{tp} {cp}".lower()
                            rate_limit_detected = False
                            for kw in RATE_LIMIT_KEYWORDS:
                                if kw in popup_text:
                                    log_thread(p_name, f"⚠️ Rate limit: '{kw}' — đang xử lý...")
                                    rate_limit_detected = True
                                    break

                            if rate_limit_detected:
                                ok_c = driver.find_element(By.CSS_SELECTOR, ".swal2-confirm.swal2-styled")
                                driver.execute_script("arguments[0].click();", ok_c)
                                sleep(1)
                                handle_rate_limit(driver, p_name)
                                # After handling rate limit, continue to next job scan
                                need_skip = True
                            else:
                                ok_c = driver.find_element(By.CSS_SELECTOR, ".swal2-confirm.swal2-styled")
                                driver.execute_script("arguments[0].click();", ok_c)
                                if "lỗi" in tp.lower() or "thất bại" in tp.lower() or "lỗi" in cp.lower() or "thất bại" in cp.lower():
                                    need_skip = True
                                else: need_skip = False
                        except: pass
                    except: need_skip = True

                if need_skip:
                    try:
                        bl = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'row')][.//h6[contains(text(), 'Báo lỗi')]]")))
                        driver.execute_script("arguments[0].click();", bl)
                        sleep(CONFIG_DELAY.get("delay_after_report_error", 1.5))
                        ldo = "Báo cáo hoàn thành thất bại"
                        if not uid or uid == "0": ldo = "Không tìm thấy bài viết"
                        c_ldo = driver.find_element(By.XPATH, f"//div[contains(@class, 'row')][.//h6[contains(text(), '{ldo}')]]")
                        driver.execute_script("arguments[0].click();", c_ldo)
                        sleep(CONFIG_DELAY.get("delay_after_report_error", 1))
                        gui = driver.find_element(By.XPATH, "//button[contains(text(), 'Gửi báo cáo')]")
                        driver.execute_script("arguments[0].click();", gui)
                        sleep(CONFIG_DELAY.get("delay_after_report_error", 1.5))
                        try:
                            o_b = driver.find_element(By.CSS_SELECTOR, ".swal2-confirm.swal2-styled")
                            driver.execute_script("arguments[0].click();", o_b)
                        except: pass
                        log_thread(p_name, "-> Đã báo lỗi job.")
                    except: pass
                
                log_thread(p_name, "Nghỉ 10 giây...")
                if job_limit_reached(driver):
                    now_str = datetime.now().strftime('%H:%M:%S %d/%m/%Y')
                    tg_msg = (
                        f"🚨 <b>GoLike MAX JOB</b>\n"
                        f"👤 Acc: <b>{p_name}</b>\n"
                        f"⏰ Lúc: {now_str}\n"
                        f"✅ Đã đủ 100 jobs/ngày. Luồng [{p_name}] dừng lại."
                    )
                    send_tg_notify(tg_msg)
                    log_thread(p_name, "[⚠️] Đã đạt giới hạn 100 jobs/ngày. Dừng luồng.")
                    break
                smart_sleep(smart_random_delay(CONFIG_DELAY.get("delay_between_jobs", 10)))
            except Exception as ex:
                log_thread(p_name, f"Lỗi chu kỳ: {ex}")
                sleep(5)
    except Exception as fatal:
        log_thread(p_name, f"🚨 LUỒNG BỊ LỖI ĐỘT NGỘT: {fatal}")
    finally:
        pass # Giữ trình duyệt mở theo yêu cầu

def run_parallel_mode():
    global STOP_FLAG
    STOP_FLAG = False
    config_path = "config_parallel.json"
    if not os.path.exists(config_path):
        sample = [
            {
                "profile_name": "Nick Số 1",
                "golike_username": "Tên_Đăng_Nhập_GoLike",
                "golike_password": "Mật_Khẩu_GoLike",
                "facebook_cookie": "Cookie_Facebook_Tại_Đây",
                "target_fb_uid": "61554835667156",
                "target_fb_name": "Tên_Để_Dự_Phòng",
                "proxy": ""
            },
            {
                "profile_name": "Nick Số 2",
                "golike_username": "Tên_Đăng_Nhập_GoLike",
                "golike_password": "Mật_Khẩu_GoLike",
                "facebook_cookie": "Cookie_Facebook_Tại_Đây",
                "target_fb_uid": "100093602988096",
                "target_fb_name": "Tên_Để_Dự_Phòng",
                "proxy": ""
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
            raw = json.load(f)
    except Exception as e:
        print(f"❌ Lỗi phân tích file cấu hình: {e}")
        return

    # Hỗ trợ 2 format:
    # Format 1 (list): [{profile1}, {profile2}, ...]
    # Format 2 (dict): {"parallel_accounts": [...], "delay_between_jobs": ..., ...}
    if isinstance(raw, list):
        profiles = raw
    elif isinstance(raw, dict):
        profiles = raw.get("parallel_accounts", [])
        # Nếu dict có delay config -> load vào CONFIG_DELAY
        delay_keys = ["delay_between_jobs", "delay_after_api_call", "delay_after_complete",
                      "delay_after_report_error", "delay_on_job_hunt_retry", "delay_between_accounts",
                      "timeout_driver_load", "timeout_wait_element", "sleep_on_reset",
                      "sleep_on_cool_down", "delay_after_reset_click", "sleep_on_hunt_retry",
                      "switch_server_minutes", "default_proxy"]
        for k in delay_keys:
            if k in raw:
                CONFIG_DELAY[k] = raw[k]
        if any(k in raw for k in delay_keys):
            print(f"[✓] Đã load delay config từ config_parallel.json")
    else:
        print(f"❌ config_parallel.json có định dạng không hợp lệ (cần list hoặc dict).")
        return

    if not profiles:
        print("❌ Không tìm thấy tài khoản nào trong config_parallel.json!")
        print("   Hãy thêm danh sách vào key 'parallel_accounts' hoặc dùng format list.")
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
            if STOP_FLAG:
                break
            sleep(CONFIG_DELAY.get("delay_after_report_error", 1))
    except KeyboardInterrupt:
        pass

# ======================================================================
# ==================== CHẾ ĐỘ 3: SELENIUM DOM (KHÔNG DÙNG API) =========
# ======================================================================

def load_multi_cookies():
    """Hoi user co muon nhap nhieu cookie de auto-rotate khong.

    Returns:
        list[str] | None: Danh sach cookie, hoac None neu user khong muon rotate
    """
    print("\n🔄 AUTO-ROTATE ACC: Khi acc dat gioi han job, tool se tu dong chuyen sang cookie tiep theo.")
    choice = input("👉 Ban co muon nhap nhieu cookie de tu dong chuyen acc khong? (y/N): ").strip().lower()
    if choice not in ('y', 'yes'):
        return None

    print("\n📋 Nhap danh sach cookie Facebook (moi dong 1 cookie):")
    print("   (Nhap cookie va an Enter. De trong va an Enter de ket thuc.)")
    cookies = []
    idx = 1
    while True:
        c = input(f"   Cookie #{idx}: ").strip()
        if not c:
            break
        cookies.append(c)
        idx += 1

    if not cookies:
        print("[!] Khong co cookie nao duoc nhap. Se chay che do don le.")
        return None

    print(f"✅ Da nhan {len(cookies)} cookie. Tool se tu dong chuyen khi dat gioi han job.")
    return cookies


def _select_golike_account(driver):
    """Chon tai khoan trong giao dien Golike bang Selenium.

    Returns:
        tuple: (selected_name, selected_uid) hoac (None, None) neu that bai
    """
    try:
        doiacc = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.select-account"))
        )
        driver.execute_script("arguments[0].click();", doiacc)
        sleep(2)

        accounts = driver.find_elements(By.CSS_SELECTOR, "div.card.shadow-200.mt-1")
        valid_accounts = []
        for acc in accounts:
            try:
                name = acc.find_element(By.CSS_SELECTOR, "div.col-8 span").text
                acc_id = acc.get_attribute("id") or ""
                valid_accounts.append((acc, name, acc_id))
            except Exception:
                pass

        if not valid_accounts:
            print("[LOI] Khong tim thay tai khoan nao!")
            return None, None

        print("\n--- CHON TAI KHOAN CAY ---")
        for i, (acc, name, acc_id) in enumerate(valid_accounts, start=1):
            print(f"{i}. {name} | UID: {acc_id}")

        chon_acc = int(input("👉 Nhap so de chon nick chay: "))
        selected_node, name_run, uid_run = valid_accounts[chon_acc - 1]
        driver.execute_script("arguments[0].click();", selected_node)
        print(f"🚀 ✅ DANG CHAY ACC: {name_run} | UID: {uid_run}")
        sleep(3)
        return name_run, uid_run
    except Exception as e:
        print(f"[LOI] Khong the chon account: {e}")
        return None, None


def _switch_to_next_account(driver, bot, cookie_list, current_idx, proxy_arg, save_prof, proxy_auth_ext, golike_user, golike_pass):
    """Chuyen sang cookie tiep theo khi acc hien tai dat gioi han job.

    Args:
        driver: Selenium WebDriver hien tai
        bot: FacebookSeleniumBot instance hien tai
        cookie_list: Danh sach tat ca cookie
        current_idx: Index cua cookie hien tai trong list
        proxy_arg: Proxy argument (giu nguyen)
        save_prof: Save profile flag (giu nguyen)
        proxy_auth_ext: Proxy auth extension (giu nguyen)
        golike_user: GoLike username
        golike_pass: GoLike password

    Returns:
        tuple: (bot_moi, driver_moi, new_idx, name_run, uid_run)
               hoac (None, None, -1, None, None) neu khong con cookie
    """
    next_idx = current_idx + 1
    if next_idx >= len(cookie_list):
        print("\n[⚠️] Da het danh sach cookie! Tat ca acc deu dat gioi han.")
        return None, None, -1, None, None

    print(f"\n{'='*60}")
    print(f"🔄 CHUYEN SANG ACC #{next_idx + 1}/{len(cookie_list)}")
    print(f"{'='*60}")

    new_cookie = cookie_list[next_idx]
    print(f"🔍 Dang kiem tra cookie #{next_idx + 1}...")

    try:
        from FB_WEB_API_FIXED import FB_API
        test_fb = FB_API(new_cookie)
        test_result = test_fb.login()
        if isinstance(test_result, dict) and 'err' in test_result:
            print(f"❌ Cookie #{next_idx + 1} khong hop le: {test_result['err']}")
            print("   Bo qua cookie nay, thu cookie tiep theo...")
            return _switch_to_next_account(driver, bot, cookie_list, next_idx, proxy_arg, save_prof, proxy_auth_ext, golike_user, golike_pass)
    except Exception as e:
        print(f"⚠️ Khong the kiem tra cookie #{next_idx + 1}: {e}")

    print(f"✅ Cookie #{next_idx + 1} hop le!")

    # Stop bot cu
    try:
        if bot and hasattr(bot, 'stop'):
            bot.stop()
    except Exception as e:
        print(f"[Canh bao] Loi khi dung bot cu: {e}")

    # Tao bot moi voi cookie moi
    bot_moi = FacebookSeleniumBot(
        cookie_str=new_cookie,
        profile_name=f"rotate_{next_idx}",
        proxy=proxy_arg,
        save_profile=save_prof,
        proxy_auth_ext=proxy_auth_ext,
    )

    print("[*] Khoi dong Chrome voi cookie moi...")
    if not bot_moi.start():
        print("[LOI] Khong the dang nhap Facebook voi cookie moi!")
        return _switch_to_next_account(driver, bot, cookie_list, next_idx, proxy_arg, save_prof, proxy_auth_ext, golike_user, golike_pass)

    driver_moi = bot_moi.driver

    # Mo lai GoLike + login
    driver_moi.get("https://app.golike.net/login")
    time.sleep(2)

    try:
        tk = driver_moi.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/div/form/div[1]/input')
        tk.clear()
        tk.send_keys(golike_user)

        mk = driver_moi.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/div/form/div[2]/div/input')
        mk.clear()
        mk.send_keys(golike_pass)

        dn = driver_moi.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/div/form/div[3]/button')
        dn.click()

        input("\n👉 Vui long tu giai Captcha (neu co).\nSau khi giai xong, an [ENTER] de tiep tuc...")

        nhiemvu = WebDriverWait(driver_moi, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[2]/div/div/div[2]'))
        )
        driver_moi.execute_script("arguments[0].click();", nhiemvu)

        fb_btn = WebDriverWait(driver_moi, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[1]/div[2]/div[3]/div[1]/div'))
        )
        driver_moi.execute_script("arguments[0].click();", fb_btn)
        sleep(3)

        try:
            tb = WebDriverWait(driver_moi, 3).until(EC.element_to_be_clickable((By.CLASS_NAME, 'swal2-title')))
            print(f"Thong bao tu GoLike: {tb.text}")
            ok_btn = driver_moi.find_element(By.CSS_SELECTOR, '.swal2-confirm.swal2-styled')
            driver_moi.execute_script("arguments[0].click();", ok_btn)
        except TimeoutException:
            pass
    except Exception as e:
        print(f"[LOI] Khong the login GoLike cho acc moi: {e}")
        return bot_moi, driver_moi, next_idx, None, None

    # Chon account
    name_run, uid_run = _select_golike_account(driver_moi)
    if not name_run:
        print("[!] Khong the chon account trong Golike!")

    return bot_moi, driver_moi, next_idx, name_run, uid_run


# ======================================================================
# ==================== MENU KHỞI CHẠY HỆ THỐNG CHÍNH ==================
# ======================================================================
def sele_menu():
    """Menu chinh cua golikefb_sele. Duoc goi tu main.py hoac chay doc lap."""
    global STOP_FLAG

    setup_lifecycle()
    kiem_tra_cap_nhat()
    load_delay_config()
    setup_telegram_notify()
    show_config_summary()

    while True:
        STOP_FLAG = False

        print("\n" + "="*65)
        print("🔥        HỆ THỐNG AUTO CÀY COIN GOLIKE & FACEBOOK v" + CURRENT_VERSION + "        🔥")
        print("="*65)
        print("1. Chạy ĐƠN LẺ 1 tài khoản (API - FB_WEB_API_FIXED)")
        print("2. Chạy SONG SONG nhiều tài khoản (API - FB_WEB_API_FIXED)")
        print("3. Setup Delay Config")
        print("0. Thoát chương trình")
        print("-" * 65)

        try:
            lua_chon = input("👉 Lựa chọn (1/2/3/0): ").strip()

            if lua_chon == "0":
                print("\n[✅] Tạm biệt!")
                cleanup()
                break
            elif lua_chon == "3":
                setup_delay_config()
                load_delay_config()
                continue
            elif lua_chon == "2":
                run_parallel_mode()
            else:
                run_single_mode()

            if STOP_FLAG:
                return
        except KeyboardInterrupt:
            print("\n[!] Đã nhận Ctrl+C. Không thoát, vui lòng chọn menu...")
        except Exception as e:
            print(f"\n🚨 Lỗi hệ thống khởi chạy: {e}")


if __name__ == "__main__":
    sele_menu()