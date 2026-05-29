"""
GoLike Facebook Desktop Selenium Bot
- Desktop Chrome (no mobile UA)
- F12 DevTools friendly
- Cookie injection for FB login
- API-driven job fetch from GoLike
- Browser executes actions on facebook.com/xxx directly
"""
import os
import sys
import time
import re
import json
import random
import uuid
import base64
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

# Selenium imports - optional (not available on Termux/Android)
HAS_SELENIUM = False
try:
    from selenium import webdriver as selenium_driver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import (
        TimeoutException, StaleElementReferenceException,
        NoSuchElementException, ElementClickInterceptedException
    )
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_SELENIUM = True
except ImportError:
    pass

from golike_core.security import CredentialManager
from golike_core.api_client import GolikeAPIClient
from golike_core.logging import logger
from golike_core.adb_manager import colored
from golike_core.error_handling import SessionExpiredError, RateLimitError

# ============================================================
# CONSTANTS
# ============================================================
COOKIE_FILE = "facebook_cookie.enc"
DEFAULT_DELAY = 2.0
MAX_CONSECUTIVE_FAILURES = 10
DEVICE_ID_FILE = ".golike_device_id"


def generate_t_token() -> str:
    """Generate dynamic 't' token: timestamp base64 encoded 3x"""
    t = str(int(time.time()))
    for _ in range(3):
        t = base64.b64encode(t.encode('utf-8')).decode('utf-8')
    return t


def get_device_id() -> str:
    """Get or create persistent device ID (g-device-id header)"""
    if os.path.exists(DEVICE_ID_FILE):
        with open(DEVICE_ID_FILE, 'r') as f:
            return f.read().strip()
    did = str(uuid.uuid4())
    with open(DEVICE_ID_FILE, 'w') as f:
        f.write(did)
    return did


def patch_api_client_headers(client: GolikeAPIClient) -> None:
    """Override _build_headers on api_client to add dynamic headers (t, g-device-id)"""
    orig_build = client._build_headers
    device_id = get_device_id()

    def patched_build():
        headers = orig_build()
        headers['t'] = generate_t_token()
        headers['g-device-id'] = device_id
        return headers

    client._build_headers = patched_build


# ============================================================
# FB Reaction ID map (for URL-based reaction triggers)
# ============================================================
REACTION_MAP = {
    "like": "1", "love": "2", "care": "3",
    "haha": "4", "wow": "5", "sad": "6", "angry": "7",
}

# ============================================================
# SELECTORS for facebook.com (desktop)
# ============================================================
SELECTORS = {
    "like_button": [
        'div[data-testid="like_button"]',
        'div[aria-label="Like"]',
        'span[data-testid="UFI2ReactionLink"]',
        'div[data-testid="fb-ufi-likelink"]',
        'a[href*="/ufi/reaction/"]',
        '//div[@aria-label="Like" and @role="button"]',
        '//span[contains(text(), "Like")]/parent::*',
    ],
    "reaction_picker": [
        'div[data-testid="fb-ufi-reactions-menu"]',
        'div[data-testid="reactions-picker"]',
        'div[aria-label="Reactions"]',
    ],
    "follow_button": [
        'div[aria-label="Follow"]',
        'div[aria-label="Theo dõi"]',
        'button[aria-label*="Follow"]',
        '//div[@role="button" and contains(@aria-label, "Follow")]',
        '//span[contains(text(), "Follow")]/parent::*',
    ],
    "like_page_button": [
        'div[aria-label="Like Page"]',
        'div[aria-label="Thích Trang"]',
        'button[aria-label*="Like Page"]',
        '//div[@role="button" and contains(@aria-label, "Like")]',
    ],
    "share_button": [
        'div[aria-label="Share"]',
        'div[data-testid="fb-ufi-sharebutton"]',
    ],
}

# ============================================================
# COOKIE MANAGEMENT
# ============================================================

def parse_cookie_string(cookie_str: str) -> List[Dict[str, Any]]:
    """Parse cookie string into list of dicts for Selenium add_cookie()"""
    cookies = []
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            key, value = item.split("=", 1)
            cookies.append({
                "name": key.strip(),
                "value": value.strip(),
                "domain": ".facebook.com",
                "path": "/",
            })
    return cookies


def load_facebook_cookie() -> Optional[str]:
    """Load decrypted Facebook cookie from encrypted file"""
    if not os.path.exists(COOKIE_FILE):
        return None
    try:
        cred_manager = CredentialManager()
        with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
            encrypted = f.read().strip()
        return cred_manager._decrypt(encrypted) or None
    except Exception as e:
        logger.error(f"Failed to load cookie: {e}")
        return None


def save_facebook_cookie(cookie_str: str) -> bool:
    """Encrypt and save Facebook cookie"""
    try:
        cred_manager = CredentialManager()
        encrypted = cred_manager._encrypt(cookie_str)
        with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
            f.write(encrypted)
        return True
    except Exception as e:
        logger.error(f"Failed to save cookie: {e}")
        return False


def get_cookie_interactive() -> str:
    """Interactive cookie input from user"""
    print(colored("\n════════════════════════════════════════════════", "cyan"))
    print(colored("🍪 NHẬP COOKIE FACEBOOK", "yellow"))
    print(colored("════════════════════════════════════════════════", "cyan"))
    print(colored("Cách lấy cookie:", "white"))
    print(colored("  1. Mở Chrome, đăng nhập facebook.com", "white"))
    print(colored("  2. F12 → Application → Cookies → facebook.com", "white"))
    print(colored("  3. Copy toàn bộ cookie string", "white"))

    while True:
        cookie = input(colored("\nNhập cookie Facebook (hoặc 'exit'): ", "green")).strip()
        if cookie.lower() == "exit":
            sys.exit(0)
        if not cookie or len(cookie) < 50:
            print(colored("❌ Cookie quá ngắn! Cần ít nhất 50 ký tự.", "red"))
            continue

        save_facebook_cookie(cookie)
        print(colored("✅ Đã lưu cookie thành công!", "green"))
        return cookie


# ============================================================
# BROWSER SETUP
# ============================================================

def create_desktop_driver(proxy: Optional[str] = None) -> selenium_driver.Chrome:
    """Create desktop Chrome driver - no mobile UA, no emulation.
    User can open F12 DevTools freely."""
    options = Options()

    # Desktop flags - no mobile emulation
    options.add_argument("--lang=en-US")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Allow DevTools (F12) to work
    options.add_argument("--auto-open-devtools-for-tabs")
    options.add_argument("--window-size=1280,900")

    if proxy:
        options.add_argument(f"--proxy-server={proxy}")

    driver = selenium_driver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    return driver


def inject_anti_detection(driver: selenium_driver.Chrome) -> None:
    """Minimal anti-detection - still allows DevTools usage"""
    script = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', {
        get: () => {
            const p = [{name:'Chrome PDF Plugin'},{name:'Chrome PDF Viewer'},{name:'Native Client'}];
            p.item = i => p[i];
            p.namedItem = n => p.find(x => x.name === n);
            p.refresh = () => {};
            Object.setPrototypeOf(p, PluginArray.prototype);
            return p;
        }
    });
    Object.defineProperty(navigator, 'languages', { get: () => ['vi-VN', 'vi', 'en-US', 'en'] });
    """
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": script
    })


def inject_cookies_to_driver(driver: selenium_driver.Chrome, cookie_str: str) -> None:
    """Inject Facebook cookies into browser via Selenium + CDP"""
    cookies = parse_cookie_string(cookie_str)
    domains = [".facebook.com", ".www.facebook.com"]

    # Wait a moment for page to load
    time.sleep(1)

    for domain in domains:
        for c in cookies:
            try:
                driver.add_cookie({
                    "name": c["name"],
                    "value": c["value"],
                    "domain": domain,
                    "path": "/",
                })
            except Exception:
                pass

    # CDP injection for reliability (per-cookie error handling)
    for c in cookies:
        try:
            driver.execute_cdp_cmd("Network.setCookie", {
                "name": c["name"],
                "value": c["value"],
                "domain": ".facebook.com",
                "path": "/",
            })
        except Exception:
            pass


def verify_fb_login(driver: selenium_driver.Chrome) -> bool:
    """Verify Facebook login by checking page content"""
    try:
        driver.get("https://www.facebook.com/")
        # Wait for page to actually render before checking
        WebDriverWait(driver, 10).until(
            lambda d: len(d.find_element(By.TAG_NAME, "body").text) > 100
        )
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        login_indicators = ["create new account", "email or phone", "log in", "sign up"]
        return not any(indicator in body for indicator in login_indicators)
    except Exception:
        return False


# ============================================================
# HUMAN-LIKE INTERACTION
# ============================================================

def human_delay(min_s: float = 0.5, max_s: float = 1.5) -> None:
    """Random delay simulating human timing"""
    t = min_s + (max_s - min_s) * random.betavariate(2, 5)
    time.sleep(round(t, 3))


def scroll_to_element(driver, element) -> None:
    """Smooth scroll element into center view"""
    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            element
        )
        time.sleep(0.5)
    except Exception:
        pass


def click_human(driver, element, pre_delay: bool = True, post_delay: bool = True) -> bool:
    """Human-like click with mouse events"""
    if pre_delay:
        human_delay()
    try:
        scroll_to_element(driver, element)
        driver.execute_script("""
            var el = arguments[0];
            var box = el.getBoundingClientRect();
            var x = box.left + box.width * (0.3 + Math.random() * 0.4);
            var y = box.top + box.height * (0.3 + Math.random() * 0.4);
            function fire(type) {
                el.dispatchEvent(new MouseEvent(type, {
                    bubbles: true, cancelable: true,
                    clientX: x, clientY: y,
                    buttons: 1, button: 0,
                }));
            }
            fire('mouseover');
            fire('mousedown');
            fire('mouseup');
            fire('click');
        """, element)
        if post_delay:
            human_delay(0.3, 0.8)
        return True
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", element)
            return True
        except Exception:
            return False


def find_element_multi(driver, selectors: List[str], timeout: float = 8) -> Any:
    """Find element with multiple fallback selectors"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for sel in selectors:
            try:
                if sel.startswith("//"):
                    el = driver.find_element(By.XPATH, sel)
                else:
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                if el and el.is_displayed():
                    return el
            except Exception:
                pass
        time.sleep(0.3)
    return None


# ============================================================
# JOB TYPE MAPPING
# ============================================================

def map_job_action(job_type: str) -> Tuple[str, str]:
    """Map job type string to (action, reaction_type)
    Returns: ('like'|'follow'|'like_page'|'reaction', specific_type)
    """
    jt = job_type.lower()
    if "reaction" in jt:
        for react in ["love", "haha", "wow", "sad", "angry", "care"]:
            if react in jt:
                return ("reaction", react.upper())
        return ("reaction", "LIKE")
    if "like_page" in jt or "like-page" in jt:
        return ("like_page", "")
    if "follow" in jt:
        return ("follow", "")
    if "comment" in jt:
        return ("comment", "")
    # Default to like
    return ("like", "")


def detect_reaction_type(job_type: str) -> Optional[str]:
    """Detect specific reaction from job type string"""
    jt = job_type.lower()
    for react in ["love", "haha", "wow", "sad", "angry", "care"]:
        if react in jt:
            return react.upper()
    return None


# ============================================================
# FACEBOOK ACTION EXECUTORS (DOM-based, on facebook.com)
# ============================================================

def do_like(driver: selenium_driver.Chrome, object_id: str) -> bool:
    """Like a post on facebook.com by navigating to it and clicking Like"""
    try:
        url = f"https://www.facebook.com/{object_id}"
        print(colored(f"  📄 Navigating to: {url}", "cyan"))
        driver.get(url)
        time.sleep(3)

        # Look for Like button
        like_btn = find_element_multi(driver, SELECTORS["like_button"], timeout=8)
        if like_btn:
            print(colored("  👍 Clicking Like button...", "yellow"))
            ok = click_human(driver, like_btn)
            time.sleep(1.5)
            return ok

        print(colored("  ⚠ Like button not found", "yellow"))
        return False
    except Exception as e:
        logger.error(f"do_like error: {e}")
        return False


def do_reaction(driver: selenium_driver.Chrome, object_id: str, reaction_type: str = "LIKE") -> bool:
    """React to a post with specific reaction type on facebook.com"""
    try:
        url = f"https://www.facebook.com/{object_id}"
        print(colored(f"  📄 Navigating to: {url}", "cyan"))
        driver.get(url)
        time.sleep(3)

        # Hover on Like button to open reaction picker
        like_btn = find_element_multi(driver, SELECTORS["like_button"], timeout=8)
        if not like_btn:
            print(colored("  ⚠ Like button not found for reaction", "yellow"))
            return False

        # Hover to open reaction picker
        print(colored(f"  🎭 Opening reaction picker for {reaction_type}...", "yellow"))
        action = ActionChains(driver)
        action.move_to_element(like_btn).perform()
        time.sleep(1)

        # Now click the specific reaction
        reaction_label = reaction_type.capitalize()
        try:
            react_btn = driver.find_element(
                By.XPATH, f'//div[@aria-label="{reaction_label}"]'
            )
            ok = click_human(driver, react_btn)
            time.sleep(1.5)
            return ok
        except Exception:
            # Fallback: open reaction via URL
            react_id = REACTION_MAP.get(reaction_type.lower(), "1")
            react_url = f"https://www.facebook.com/{object_id}/reactions/?type={react_id}"
            driver.get(react_url)
            time.sleep(2)
            return True
    except Exception as e:
        logger.error(f"do_reaction error: {e}")
        return False


def do_follow(driver: selenium_driver.Chrome, object_id: str) -> bool:
    """Follow a user/page on facebook.com"""
    try:
        url = f"https://www.facebook.com/{object_id}"
        print(colored(f"  📄 Navigating to: {url}", "cyan"))
        driver.get(url)
        time.sleep(3)

        fb_btn = find_element_multi(driver, SELECTORS["follow_button"], timeout=8)
        if fb_btn:
            print(colored("  ➕ Clicking Follow button...", "yellow"))
            ok = click_human(driver, fb_btn)
            time.sleep(1.5)
            return ok

        print(colored("  ⚠ Follow button not found", "yellow"))
        return False
    except Exception as e:
        logger.error(f"do_follow error: {e}")
        return False


def do_like_page(driver: selenium_driver.Chrome, object_id: str) -> bool:
    """Like a Facebook Page"""
    try:
        url = f"https://www.facebook.com/{object_id}"
        print(colored(f"  📄 Navigating to: {url}", "cyan"))
        driver.get(url)
        time.sleep(3)

        lp_btn = find_element_multi(driver, SELECTORS["like_page_button"], timeout=8)
        if lp_btn:
            print(colored("  👍 Clicking Like Page button...", "yellow"))
            ok = click_human(driver, lp_btn)
            time.sleep(1.5)
            return ok

        print(colored("  ⚠ Like Page button not found", "yellow"))
        return False
    except Exception as e:
        logger.error(f"do_like_page error: {e}")
        return False


ACTION_HANDLERS = {
    "like": do_like,
    "reaction": do_reaction,
    "follow": do_follow,
    "like_page": do_like_page,
}


# ============================================================
# MAIN BOT LOGIC
# ============================================================

class FacebookDesktopBot:
    """Facebook Desktop Bot - API-driven jobs, browser execution"""

    def __init__(self, auth_token: str, cookie: str):
        self.auth_token = auth_token
        self.cookie = cookie
        self.api_client = GolikeAPIClient()
        self.api_client.set_auth(auth_token)
        patch_api_client_headers(self.api_client)
        self.driver: Optional[selenium_driver.Chrome] = None
        self.stats = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "earned": 0,
        }

    def start_browser(self) -> bool:
        """Start desktop Chrome and inject FB cookie"""
        print(colored("\n🚀 Khởi động Chrome Desktop...", "cyan"))
        try:
            self.driver = create_desktop_driver()
            inject_anti_detection(self.driver)

            print(colored("🍪 Đang bơm cookie Facebook...", "yellow"))
            self.driver.get("https://www.facebook.com/")
            time.sleep(2)
            inject_cookies_to_driver(self.driver, self.cookie)

            if verify_fb_login(self.driver):
                print(colored("✅ Đăng nhập Facebook thành công!", "green"))
                # Open Facebook home to show login state
                self.driver.get("https://www.facebook.com/")
                time.sleep(2)
                return True
            else:
                print(colored("❌ Cookie Facebook không hợp lệ hoặc đã hết hạn!", "red"))
                return False
        except Exception as e:
            logger.error(f"Browser start failed: {e}")
            return False

    def close_browser(self) -> None:
        """Close browser"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def fetch_facebook_accounts(self) -> List[Dict[str, Any]]:
        """Fetch Facebook accounts from GoLike API.
        Response structure: {status:200, data: {data: [{account objects...}]}}
        """
        try:
            resp = self.api_client.get_accounts(provider='facebook', limit=200)
            if resp.get("status") == 200:
                inner = resp.get("data", {})
                if isinstance(inner, dict):
                    raw = inner.get("data", [])
                else:
                    raw = inner if isinstance(inner, list) else []
                accounts = [item for item in raw if isinstance(item, dict)]
                print(colored(f"📋 Found {len(accounts)} Facebook accounts", "cyan"))
                return accounts
            else:
                print(colored(f"⚠ API response: {resp}", "yellow"))
                return []
        except Exception as e:
            logger.error(f"Failed to fetch accounts: {e}")
            return []

    def get_job(self, fb_id: str, server: str = "sv2", low_job: str = "1") -> Optional[Dict[str, Any]]:
        """Fetch one job from GoLike API"""
        try:
            resp = self.api_client.get_jobs(
                provider='facebook',
                account_id=fb_id,
                server=server,
                low_job=low_job
            )
            status = resp.get("status") if resp else None
            if status == 200:
                jobs = resp.get("data", [])
                if jobs and isinstance(jobs, list):
                    return jobs[0]
            elif status in (401, 403):
                print(colored("⚠ Session expired!", "red"))
            elif status == 429:
                print(colored("⚠ Rate limited! Waiting...", "yellow"))
                time.sleep(10)
            return None
        except Exception as e:
            logger.error(f"Failed to get job: {e}")
            return None

    def complete_job(self, job_data: Dict[str, Any]) -> bool:
        """Complete job via GoLike API"""
        try:
            resp = self.api_client.complete_job(provider='facebook', job_data=job_data)
            if resp.get("status") == 200:
                reward = resp.get("data", {}).get("prices", 0)
                self.stats["earned"] += reward
                print(colored(f"  ✅ Hoàn thành! +{reward} xu", "green"))
                return True
            print(colored(f"  ⚠ Complete failed: {resp}", "yellow"))
            return False
        except Exception as e:
            logger.error(f"Complete job error: {e}")
            return False

    def report_job(self, job_data: Dict[str, Any]) -> bool:
        """Report job failure via GoLike API"""
        try:
            self.api_client.report_job(provider='facebook', job_data=job_data)
            print(colored("  📝 Đã báo cáo job thất bại", "yellow"))
            return True
        except Exception as e:
            logger.error(f"Report job error: {e}")
            return False

    def execute_action(self, action: str, object_id: str, reaction_type: Optional[str] = None) -> bool:
        """Execute Facebook action in browser"""
        handler = ACTION_HANDLERS.get(action)
        if not handler:
            logger.warning(f"No handler for action: {action}")
            return False

        if action == "reaction":
            rt = reaction_type or "LIKE"
            return handler(self.driver, object_id, rt)
        return handler(self.driver, object_id)

    def process_single_job(self, job_data: Dict[str, Any], fb_id: str) -> bool:
        """Process a single Facebook job"""
        raw_object_id = job_data.get("object_id")
        job_type = job_data.get("type", "unknown")

        if not raw_object_id:
            print(colored("  ⚠ Job missing object_id, reporting...", "yellow"))
            self.report_job(job_data)
            return False

        object_id = str(raw_object_id)
        action, reaction_type = map_job_action(job_type)

        print(colored(f"\n{'─'*50}", "white"))
        print(colored(f"  📌 Job: {job_type}", "cyan"))
        print(colored(f"  🆔 Object: {object_id}", "cyan"))
        print(colored(f"  🎯 Action: {action}", "cyan"))
        if reaction_type:
            print(colored(f"  🎭 Reaction: {reaction_type}", "cyan"))

        # Execute the action in browser
        success = self.execute_action(action, object_id, reaction_type)

        if success:
            # Prepare complete payload
            complete_data = job_data.copy()
            complete_data["account_id"] = fb_id
            ok = self.complete_job(complete_data)
            if ok:
                self.stats["success"] += 1
                return True
            else:
                self.stats["failed"] += 1
                self.report_job(job_data)
                return False
        else:
            print(colored("  ❌ Action failed, reporting...", "red"))
            self.stats["failed"] += 1
            self.report_job(job_data)
            return False

    def run_loop(
        self,
        fb_id: str,
        server: str = "sv2",
        low_job: str = "1",
        max_jobs: int = 0,
    ) -> None:
        """Main job processing loop"""
        consecutive_fails = 0

        print(colored(f"\n{'='*60}", "cyan"))
        print(colored(f"🤖 BẮT ĐẦU CHẠY JOB - FB ID: {fb_id}", "yellow"))
        print(colored(f"{'='*60}", "cyan"))

        job_count = 0
        while True:
            if max_jobs > 0 and job_count >= max_jobs:
                print(colored(f"\n✅ Đã đạt giới hạn {max_jobs} jobs. Dừng lại.", "green"))
                break

            print(colored(f"\n{'─'*40}", "white"))
            print(colored(f"  🔄 Đang lấy job... (đã làm: {job_count})", "white"))

            job = self.get_job(fb_id, server, low_job)
            if not job:
                consecutive_fails += 1
                if consecutive_fails >= 5:
                    print(colored("\n⏸ Không có job sau 5 lần thử. Nghỉ 30s...", "yellow"))
                    time.sleep(30)
                    consecutive_fails = 0
                else:
                    delay = random.randint(3, 7)
                    print(colored(f"  ⏳ Thử lại sau {delay}s...", "yellow"))
                    time.sleep(delay)
                continue

            consecutive_fails = 0
            job_count += 1

            ok = self.process_single_job(job, fb_id)
            if not ok:
                consecutive_fails += 1

            # Random delay between jobs
            delay = round(random.uniform(1.5, 4.0), 1)
            print(colored(f"  ⏳ Chờ {delay}s trước job tiếp theo...", "white"))
            time.sleep(delay)

            # Show stats periodically
            if job_count % 5 == 0:
                self.show_stats()

        self.show_stats()

    def show_stats(self) -> None:
        """Display current stats"""
        print(colored(f"\n{'='*50}", "cyan"))
        print(colored(f"📊 THỐNG KÊ:", "yellow"))
        print(colored(f"   ✅ Thành công: {self.stats['success']}", "green"))
        print(colored(f"   ❌ Thất bại: {self.stats['failed']}", "red"))
        print(colored(f"   🪙 Tổng xu: {self.stats['earned']}", "cyan"))
        print(colored(f"{'='*50}", "cyan"))


# ============================================================
# INTERACTIVE MENU
# ============================================================

def sele_desktop_menu() -> None:
    """Main menu for Facebook Desktop Selenium Bot"""
    if not HAS_SELENIUM:
        print(colored("\n❌ Facebook Desktop Selenium không khả dụng!", "red"))
        print(colored("💡 Tính năng này yêu cầu: pip install selenium webdriver-manager", "yellow"))
        print(colored("💡 Chỉ hỗ trợ trên Windows/Linux có Chrome Desktop.", "yellow"))
        input(colored("Nhấn Enter để quay lại...", "white"))
        return

    cred_manager = CredentialManager()
    cookie = load_facebook_cookie()

    print(colored("\n" + "█" * 60, "blue"))
    print(colored("█" + " " * 58 + "█", "blue"))
    print(colored("█     🤖 GOLIKE FACEBOOK DESKTOP SELENIUM BOT     █", "blue"))
    print(colored("█" + " " * 58 + "█", "blue"))
    print(colored("█" * 60, "blue"))

    # Cookie handling
    if cookie:
        masked = cookie[:30] + "..." + cookie[-10:] if len(cookie) > 45 else "***"
        print(colored(f"\n🍪 Cookie: {masked}", "green"))
        choice = input(colored("📌 Dùng cookie này? (y/n, Enter=y): ", "white")).strip().lower()
        if choice == "n":
            cookie = get_cookie_interactive()
    else:
        print(colored("\n⚠ Chưa có cookie Facebook!", "yellow"))
        cookie = get_cookie_interactive()

    # Auth token
    tokens = cred_manager.get_auth_labels()
    if not tokens:
        print(colored("\n⚠ Chưa có authorization token!", "red"))
        input(colored("Nhấn Enter để quay lại...", "white"))
        return

    auth_token = None
    if len(tokens) == 1:
        auth_token = cred_manager.get_auth_by_label(tokens[0])
    else:
        print(colored("\n🔑 Chọn authorization token:", "cyan"))
        for i, label in enumerate(tokens, 1):
            token = cred_manager.get_auth_by_label(label)
            masked = token[:10] + "..." + token[-4:] if token and len(token) > 14 else "***"
            print(f"  [{i}] {label} ({masked})")
        try:
            idx = int(input(colored("Nhập số thứ tự: ", "white")).strip())
            if 1 <= idx <= len(tokens):
                auth_token = cred_manager.get_auth_by_label(tokens[idx - 1])
        except ValueError:
            print(colored("Lựa chọn không hợp lệ!", "red"))
            return

    if not auth_token:
        print(colored("❌ Không có token!", "red"))
        return

    # Mode selection
    print(colored("\n" + "─" * 50, "white"))
    print(colored("CHỌN CHẾ ĐỘ:", "yellow"))
    print(colored("  [1] 🏃 Chạy tự động (lấy job từ API, làm trên browser)", "green"))
    print(colored("  [2] 🔧 Chạy thủ công (nhập link FB, làm trên browser)", "cyan"))
    print(colored("   [0] 🔙 Quay lại", "white"))

    mode = input(colored("Nhập lựa chọn: ", "white")).strip()

    if mode == "0":
        return
    elif mode == "1":
        run_auto_mode(auth_token, cookie)
    elif mode == "2":
        run_manual_mode(auth_token, cookie)
    else:
        print(colored("Lựa chọn không hợp lệ!", "red"))


def run_auto_mode(auth_token: str, cookie: str) -> None:
    """Automatic mode: fetch jobs from API, execute in browser"""
    bot = FacebookDesktopBot(auth_token, cookie)

    # Start browser
    if not bot.start_browser():
        input(colored("\nNhấn Enter để quay lại...", "white"))
        return

    try:
        # Fetch accounts
        print(colored("\n📋 Đang lấy danh sách tài khoản Facebook từ API...", "cyan"))
        accounts = bot.fetch_facebook_accounts()
        if not accounts:
            print(colored("❌ Không tìm thấy tài khoản Facebook nào!", "red"))
            return

        # Let user choose account
        print(colored("\nChọn tài khoản Facebook:", "yellow"))
        for i, acc in enumerate(accounts, 1):
            fb_id = acc.get("fb_id", acc.get("id", "N/A"))
            name = acc.get("name", acc.get("username", ""))
            print(f"  [{i}] {name} (ID: {fb_id})")
        print(f"  [{len(accounts) + 1}] Tất cả (tự động chuyển)")

        try:
            choice = int(input(colored("Nhập số thứ tự: ", "white")).strip())
            if 1 <= choice <= len(accounts):
                selected = [accounts[choice - 1]]
            else:
                selected = accounts
        except ValueError:
            selected = [accounts[0]]

        # Settings
        print(colored("\n⚙ CÀI ĐẶT:", "yellow"))
        server = input(colored("Server (sv1/sv2, Enter=mặc định sv2): ", "white")).strip() or "sv2"
        max_jobs_str = input(colored("Số job tối đa (Enter=không giới hạn): ", "white")).strip()
        max_jobs = int(max_jobs_str) if max_jobs_str.isdigit() else 0

        for acc in selected:
            fb_id = acc.get("fb_id") or acc.get("id") or ""
            fb_id = str(fb_id) if fb_id else ""

            if not fb_id:
                print(colored("  ⚠ Bỏ qua account thiếu fb_id", "yellow"))
                continue

            bot.run_loop(
                fb_id=fb_id,
                server=server,
                max_jobs=max_jobs,
            )

            if max_jobs > 0:
                break

    except KeyboardInterrupt:
        print(colored("\n\n👋 Đã dừng bởi người dùng.", "yellow"))
        bot.show_stats()
    except Exception as e:
        logger.error(f"Auto mode error: {e}")
        print(colored(f"\n❌ Lỗi: {e}", "red"))
    finally:
        bot.close_browser()

    input(colored("\nNhấn Enter để quay lại menu...", "white"))


def run_manual_mode(auth_token: str, cookie: str) -> None:
    """Manual mode: user enters FB link, bot does action"""
    bot = FacebookDesktopBot(auth_token, cookie)

    if not bot.start_browser():
        input(colored("\nNhấn Enter để quay lại...", "white"))
        return

    print(colored("\n📝 CHẾ ĐỘ THỦ CÔNG", "yellow"))
    print(colored("Nhập link Facebook để bot thực hiện action.", "cyan"))
    print(colored("Nhập 'exit' để thoát.", "white"))

    try:
        while True:
            print(colored("\n" + "─" * 50, "white"))
            fb_link = input(colored("🔗 Nhập link Facebook: ", "green")).strip()
            if fb_link.lower() == "exit":
                break

            # Extract object ID from URL
            object_id = None
            patterns = [
                r'facebook\.com/(\d+)',
                r'facebook\.com/([a-zA-Z0-9\.]+)/posts/(\d+)',
                r'facebook\.com/photo/\?fbid=(\d+)',
                r'fb\.com/(\d+)',
            ]
            for p in patterns:
                m = re.search(p, fb_link)
                if m:
                    object_id = m.group(1)
                    break

            if not object_id:
                # Use URL as-is (could be a page username)
                object_id = fb_link.split("facebook.com/")[-1].split("?")[0]

            print(colored(f"\n🆔 Object ID: {object_id}", "cyan"))
            print(colored("Chọn action:", "yellow"))
            print(colored("  [1] 👍 Like", "white"))
            print(colored("  [2] ❤️ Reaction (Love/Haha/Wow/Sad/Angry/Care)", "white"))
            print(colored("  [3] ➕ Follow", "white"))
            print(colored("  [4] 👍 Like Page", "white"))
            print(colored("   [0] 🔙 Quay lại", "white"))

            act = input(colored("Chọn: ", "white")).strip()
            if act == "0":
                break
            elif act == "1":
                do_like(bot.driver, object_id)
            elif act == "2":
                print(colored("Chọn reaction:", "yellow"))
                print(colored("  [1] LIKE  [2] LOVE  [3] HAHA  [4] WOW", "white"))
                print(colored("  [5] SAD  [6] ANGRY  [7] CARE", "white"))
                r_choice = input(colored("Chọn (1-7): ", "white")).strip()
                r_map = {"1": "LIKE", "2": "LOVE", "3": "HAHA", "4": "WOW",
                         "5": "SAD", "6": "ANGRY", "7": "CARE"}
                rt = r_map.get(r_choice, "LIKE")
                do_reaction(bot.driver, object_id, rt)
            elif act == "3":
                do_follow(bot.driver, object_id)
            elif act == "4":
                do_like_page(bot.driver, object_id)
            else:
                print(colored("Lựa chọn không hợp lệ!", "red"))

    except KeyboardInterrupt:
        print(colored("\n\n👋 Đã dừng.", "yellow"))
    finally:
        bot.close_browser()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    try:
        sele_desktop_menu()
    except KeyboardInterrupt:
        print(colored("\n\n👋 Tạm biệt!", "green"))
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(colored(f"\n❌ Lỗi nghiêm trọng: {e}", "red"))