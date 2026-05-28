"""
Facebook Selenium DOM Bot
Tương tác trực tiếp trên giao diện m.facebook.com qua Selenium
Thay thế FB_WEB_API_FIXED.py cho việc thực hiện job
"""
import time
import os
import re
import urllib.request
from typing import Optional, Dict, Any, List

from selenium import webdriver as selenium_driver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException,
    ElementClickInterceptedException, StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager

from golike_core.logging import logger

# ============================================================
# ANTI-DETECTION JAVASCRIPT
# ============================================================

PRELOAD_JS = """
// ═══════════════════════════════════════════════
// 1. Ẩn navigator.webdriver
// ═══════════════════════════════════════════════
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// ═══════════════════════════════════════════════
// 2. Fake plugins (giống real Chrome mobile)
// ═══════════════════════════════════════════════
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const plugins = [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
            { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
        ];
        plugins.item = (i) => plugins[i];
        plugins.namedItem = (name) => plugins.find(p => p.name === name);
        plugins.refresh = () => {};
        Object.setPrototypeOf(plugins, PluginArray.prototype);
        return plugins;
    }
});

// ═══════════════════════════════════════════════
// 3. Ngôn ngữ + platform + vendor + maxTouchPoints
// ═══════════════════════════════════════════════
Object.defineProperty(navigator, 'languages', { get: () => ['vi-VN', 'vi', 'en-US', 'en'] });
Object.defineProperty(navigator, 'platform',  { get: () => 'iPhone' });
Object.defineProperty(navigator, 'vendor',    { get: () => 'Apple Computer, Inc.' });
Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 5 });

// ═══════════════════════════════════════════════
// 4. Hardware (giữ nhất quán)
// ═══════════════════════════════════════════════
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 6 });
Object.defineProperty(navigator, 'deviceMemory',        { get: () => 4 });

// ═══════════════════════════════════════════════
// 5. Chrome runtime (tránh bị detect qua window.chrome)
// ═══════════════════════════════════════════════
window.chrome = {
    runtime: { id: undefined },
    loadTimes: function() {},
    csi: function() {},
    app: {}
};

// ═══════════════════════════════════════════════
// 6. Permissions query
// ═══════════════════════════════════════════════
try {
    const _origPermQuery = window.navigator.permissions.query.bind(navigator.permissions);
    window.navigator.permissions.query = (params) => (
        params.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission, onchange: null })
            : _origPermQuery(params)
    );
} catch(e) {}

// ═══════════════════════════════════════════════
// 7. Canvas fingerprint noise (tinh tế hơn)
// ═══════════════════════════════════════════════
(function() {
    const _origGetCtx = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(type, ...args) {
        const ctx = _origGetCtx.apply(this, [type, ...args]);
        if (type === '2d' && ctx) {
            const _origFillText     = ctx.fillText.bind(ctx);
            const _origStrokeText   = ctx.strokeText.bind(ctx);
            const _origGetImageData = ctx.getImageData.bind(ctx);
            ctx.fillText   = function(t, x, y, ...r) { return _origFillText(t,   x + 0.05, y + 0.05, ...r); };
            ctx.strokeText = function(t, x, y, ...r) { return _origStrokeText(t, x + 0.05, y + 0.05, ...r); };
            ctx.getImageData = function(x, y, w, h) {
                const data = _origGetImageData(x, y, w, h);
                for (let i = 0; i < data.data.length; i += 199)
                    data.data[i] = data.data[i] ^ 1; // flip 1 bit mỗi ~200px
                return data;
            };
        }
        return ctx;
    };
})();

// ═══════════════════════════════════════════════
// 8. WebGL fingerprint spoof
// ═══════════════════════════════════════════════
(function() {
    const _origGetParam = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {
        if (param === 37445) return 'Apple Inc.';                      // UNMASKED_VENDOR_WEBGL
        if (param === 37446) return 'Apple GPU';                       // UNMASKED_RENDERER_WEBGL
        if (param === 7937)  return 'WebKit WebGL';                    // VENDOR
        if (param === 7936)  return 'WebKit';                          // RENDERER
        if (param === 7938)  return 'WebGL 1.0 (OpenGL ES 2.0)';      // VERSION
        return _origGetParam.call(this, param);
    };
    try {
        const _origGetParam2 = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(param) {
            if (param === 37445) return 'Apple Inc.';
            if (param === 37446) return 'Apple GPU';
            return _origGetParam2.call(this, param);
        };
    } catch(e) {}
})();

// ═══════════════════════════════════════════════
// 9. AudioContext fingerprint noise
// ═══════════════════════════════════════════════
(function() {
    try {
        const AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) return;
        const _origCreateOscillator = AC.prototype.createOscillator;
        AC.prototype.createOscillator = function() {
            const osc = _origCreateOscillator.apply(this, arguments);
            const _origStart = osc.start.bind(osc);
            osc.start = function(when) { return _origStart((when || 0) + 0.000001); };
            return osc;
        };
        const _origCreateBuffer = AC.prototype.createBuffer;
        AC.prototype.createBuffer = function(ch, len, sr) {
            const buf = _origCreateBuffer.apply(this, arguments);
            // Thêm noise cực nhỏ vào audio buffer
            for (let c = 0; c < buf.numberOfChannels; c++) {
                const data = buf.getChannelData(c);
                for (let i = 0; i < data.length; i++)
                    data[i] += (Math.random() - 0.5) * 0.0001;
            }
            return buf;
        };
    } catch(e) {}
})();

// ═══════════════════════════════════════════════
// 10. Screen/window size nhất quán với iPhone
// ═══════════════════════════════════════════════
try {
    Object.defineProperty(screen, 'width',       { get: () => 390 });
    Object.defineProperty(screen, 'height',      { get: () => 844 });
    Object.defineProperty(screen, 'availWidth',  { get: () => 390 });
    Object.defineProperty(screen, 'availHeight', { get: () => 844 });
    Object.defineProperty(screen, 'colorDepth',  { get: () => 30 });
    Object.defineProperty(screen, 'pixelDepth',  { get: () => 30 });
    Object.defineProperty(window, 'devicePixelRatio', { get: () => 3 });
} catch(e) {}

// ═══════════════════════════════════════════════
// 11. Ẩn Automation qua toString() (native fn check)
// ═══════════════════════════════════════════════
(function() {
    const nativeFn = Function.prototype.toString;
    const patches = new WeakSet();
    function patchToString(fn, str) {
        try {
            Object.defineProperty(fn, 'toString', {
                value: function() { return str; },
                writable: true, configurable: true,
            });
            patches.add(fn);
        } catch(e) {}
    }
    patchToString(navigator.permissions.query, 'function query() { [native code] }');
    patchToString(HTMLCanvasElement.prototype.getContext,  'function getContext() { [native code] }');
    patchToString(WebGLRenderingContext.prototype.getParameter, 'function getParameter() { [native code] }');
})();

// ═══════════════════════════════════════════════
// 12. Connection info giả (4G)
// ═══════════════════════════════════════════════
try {
    Object.defineProperty(navigator, 'connection', {
        get: () => ({
            effectiveType: '4g',
            downlink: 10,
            rtt: 50,
            saveData: false,
        })
    });
} catch(e) {}
"""

CLICK_SAFE_JS = """
var el = arguments[0];
if (el) {
    el.scrollIntoView({behavior: 'smooth', block: 'center'});
    el.style.visibility = 'visible';
    el.style.display = 'block';
    el.click();
    return true;
}
return false;
"""


def build_anti_detect_options(
    user_data_dir: Optional[str] = None,
    proxy: Optional[str] = None,
    proxy_auth_ext: Optional[str] = None,
) -> Options:
    """Tạo Chrome options chống detect nâng cao"""
    options = Options()

    # --- Ẩn automation flags ---
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=vi-VN")

    # Giảm footprint của Chrome automation
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins-discovery")
    options.add_argument("--disable-blink-features=MediaStream")
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    options.add_argument("--allow-running-insecure-content")

    # Fingerprint giảm thiểu
    options.add_argument("--disable-features=AudioServiceOutOfProcess")
    options.add_argument("--use-fake-ui-for-media-stream")
    options.add_argument("--use-fake-device-for-media-stream")

    options.add_experimental_option("excludeSwitches", [
        "enable-automation",
        "enable-logging",
        "ignore-certificate-errors",
    ])
    options.add_experimental_option("useAutomationExtension", False)

    # iPhone 14 Pro UA (khớp với platform/vendor trong PRELOAD_JS)
    options.add_argument(
        "user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    )

    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_setting_values.media_stream": 2,
        # Tắt popup lưu password / autofill
        "autofill.profile_enabled": False,
    }
    options.add_experimental_option("prefs", prefs)

    if user_data_dir:
        options.add_argument("--user-data-dir={}".format(user_data_dir))

    if proxy:
        options.add_argument("--proxy-server={}".format(proxy))

    if proxy_auth_ext:
        options.add_argument("--load-extension={}".format(proxy_auth_ext))

    return options


def inject_anti_detection_scripts(driver: selenium_driver.Chrome) -> None:
    """
    Bơm JavaScript chống detect vào browser (chạy trước mọi trang).
    Thêm CDP emulation để giả lập thiết bị iPhone nhất quán.
    """
    # Bơm JS vào mọi document mới (kể cả iframe)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": PRELOAD_JS
    })

    # Emulate iPhone 14 Pro qua CDP Network
    try:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {
            "headers": {
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                "sec-ch-ua": '"Not/A)Brand";v="99", "Safari";v="17"',
                "sec-ch-ua-mobile": "?1",
                "sec-ch-ua-platform": '"iOS"',
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "sec-fetch-user": "?1",
            }
        })
    except Exception:
        pass

    # Emulate kích thước màn hình iPhone 14 Pro (khớp với screen trong JS)
    try:
        driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
            "width": 390,
            "height": 844,
            "deviceScaleFactor": 3,
            "mobile": True,
        })
    except Exception:
        pass

    # Ẩn automation qua CDP
    try:
        driver.execute_cdp_cmd("Emulation.setAutomationOverride", {"enabled": False})
    except Exception:
        pass


def parse_cookie_string(cookie_str: str) -> List[Dict[str, Any]]:
    """Parse cookie string thành list các dict cho Selenium add_cookie()"""
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


# ============================================================
# SELECTORS cho m.facebook.com
# ============================================================

SELECTORS = {
    "like_button": [
        'a[href*="/reactions/picker/"]',
        'a[href*="/like/"]',
        'a[data-store*="reaction"]',
        'a[aria-label*="Thich"]',
        'a[aria-label*="Like"]',
        'span[data-store*="reaction"] a',
    ],
    "follow_button": [
        'a[href*="/a/subscribe.php"]',
        'a[href*="/subscribe.php"]',
        'a[ajaxify*="subscribe"]',
    ],
    "like_page_button": [
        'a[href*="/a/like.php"]',
        'a[ajaxify*="like"]',
        'button[name="like"]',
    ],
    "reaction_options": [
        'div[data-store*="reaction"] a',
        'a[href*="reaction_type="]',
    ],
}

# Facebook internal reaction IDs dung khi goi API/URL
# 1=Like, 2=Love, 3=Care, 4=Haha, 5=Wow, 6=Sad, 7=Angry
REACTION_MAP = {
    "like": "1", "love": "2", "care": "3",
    "haha": "4", "wow": "5", "sad": "6", "angry": "7",
}


def find_element_safe(driver, selectors: List[str], timeout: float = 5) -> Any:
    """Tìm element với nhiều selector dự phòng"""
    end = time.time() + timeout
    while time.time() < end:
        for sel in selectors:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                if el and el.is_displayed():
                    return el
            except Exception:
                pass
        time.sleep(0.3)
    return None


import random
import math


def human_delay(min_s: float = 0.5, max_s: float = 1.8) -> None:
    """
    Delay ngẫu nhiên kiểu người thật:
    - Phân phối beta để tập trung ở khoảng giữa (không đều hoàn toàn)
    """
    t = min_s + (max_s - min_s) * (random.betavariate(2, 5))
    time.sleep(round(t, 3))


def click_js(driver, element) -> bool:
    """Click an toàn bằng JavaScript (không simulate mouse)"""
    try:
        driver.execute_script(CLICK_SAFE_JS, element)
        return True
    except Exception:
        return False


def click_human(
    driver,
    element,
    pre_delay: bool = True,
    post_delay: bool = True,
) -> bool:
    """
    Click giống người thật:
      1. Scroll element vào giữa màn hình
      2. Di chuyển chuột dần về phía element (simulate qua JS mousemove)
      3. Dispatch mousedown + mouseup + click
      4. Delay trước/sau ngẫu nhiên
    """
    if pre_delay:
        human_delay(0.3, 1.0)
    try:
        driver.execute_script(
            """
            var el = arguments[0];
            el.scrollIntoView({behavior: 'smooth', block: 'center'});
            """,
            element
        )
        time.sleep(round(random.uniform(0.15, 0.4), 3))

        # Dispatch synthetic mouse events (trông như real user)
        driver.execute_script(
            """
            var el  = arguments[0];
            var box = el.getBoundingClientRect();
            // Chọn điểm click ngẫu nhiên trong bounds của element
            var x = box.left + box.width  * (0.3 + Math.random() * 0.4);
            var y = box.top  + box.height * (0.3 + Math.random() * 0.4);

            function fireEvent(type) {
                el.dispatchEvent(new MouseEvent(type, {
                    bubbles: true, cancelable: true,
                    clientX: x, clientY: y,
                    screenX: x + window.screenX,
                    screenY: y + window.screenY,
                    buttons: 1, button: 0,
                }));
            }
            fireEvent('mousemove');
            fireEvent('mouseover');
            fireEvent('mouseenter');
            fireEvent('mousedown');
            fireEvent('mouseup');
            fireEvent('click');
            """,
            element
        )
        if post_delay:
            human_delay(0.4, 1.2)
        return True
    except Exception:
        # Fallback về click JS đơn giản
        return click_js(driver, element)


# ============================================================
# FacebookSeleniumBot
# ============================================================

class FacebookSeleniumBot:
    """Bot tương tác Facebook qua Selenium DOM click trên m.facebook.com"""

    def __init__(
        self,
        cookie_str: str,
        profile_name: str = "default",
        user_data_dir: Optional[str] = None,
        proxy: Optional[str] = None,
        save_profile: bool = False,
        proxy_auth_ext: Optional[str] = None,
    ):
        self.cookie_str = cookie_str
        self.profile_name = profile_name
        self.proxy = proxy
        self.proxy_auth_ext = proxy_auth_ext

        if user_data_dir:
            self.user_data_dir = user_data_dir
        elif save_profile:
            base = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "chrome_profiles"
            )
            os.makedirs(base, exist_ok=True)
            safe_name = "".join(c for c in profile_name if c.isalnum() or c in "_-")
            self.user_data_dir = os.path.join(base, safe_name)
        else:
            self.user_data_dir = None

        self.driver: Optional[selenium_driver.Chrome] = None

    # ---- Browser lifecycle ----

    def start(self) -> bool:
        """Khởi động Chrome + bơm cookie + verify login"""
        try:
            options = build_anti_detect_options(
                user_data_dir=self.user_data_dir,
                proxy=self.proxy,
                proxy_auth_ext=self.proxy_auth_ext,
            )
            self.driver = selenium_driver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options,
            )
            self.driver.set_window_size(500, 750)
            inject_anti_detection_scripts(self.driver)

            logger.info("[%s] Đang bơm cookie vào browser..." % self.profile_name)
            self.driver.get("https://mbasic.facebook.com/")
            time.sleep(1)
            self._inject_cookies()

            time.sleep(2)
            if not self._verify_login():
                logger.error("[%s] Cookie không hợp lệ hoặc hết hạn" % self.profile_name)
                return False

            logger.info("[%s] Đăng nhập Facebook thành công" % self.profile_name)
            return True

        except Exception as e:
            logger.error("[%s] Lỗi khởi động bot: %s" % (self.profile_name, str(e)))
            return False

    def stop(self) -> None:
        """Đóng browser"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def _inject_cookies(self) -> None:
        """Bơm cookie Facebook vào browser"""
        cookies = parse_cookie_string(self.cookie_str)
        domains = [".facebook.com", ".m.facebook.com", ".mbasic.facebook.com"]

        for domain in domains:
            for c in cookies:
                cookie_data = {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": domain,
                    "path": "/",
                }
                try:
                    self.driver.add_cookie(cookie_data)
                except Exception:
                    pass

        # Them CDP set cookie cho .facebook.com
        try:
            for c in cookies:
                self.driver.execute_cdp_cmd("Network.setCookie", {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": ".facebook.com",
                    "path": "/",
                })
        except Exception:
            pass

        self.driver.refresh()
        time.sleep(2)

    def _verify_login(self) -> bool:
        """Kiểm tra đã đăng nhập Facebook chưa"""
        try:
            self.driver.get("https://mbasic.facebook.com/")
            time.sleep(2)
            page = self.driver.page_source.lower()
            if 'name="email"' in page or 'name="pass"' in page:
                return False
            return True
        except Exception:
            return False

    # ---- Tab helpers ----

    def _open_job_tab(self, link: str) -> Optional[str]:
        """Mở link Facebook job trong tab mới, trả về main tab handle"""
        if not self.driver:
            return None

        # Resolve naked IDs (e.g. facebook.com/123456) using Desktop User-Agent 
        # because mobile FB shows "content not found" for them
        if re.match(r'^https?://(www\.|m\.|mbasic\.)?facebook\.com/\d+/?$', link.split('?')[0]):
            try:
                r = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                resp = urllib.request.urlopen(r, timeout=5)
                final_url = resp.geturl()
                
                # Uu tien url redirect neu no la link post/reel cu the
                if 'login' not in final_url and 'facebook.com/' in final_url and re.search(r'/(videos|reel|posts|photos)/', final_url):
                    link = final_url
                else:
                    html = resp.read().decode('utf-8', errors='ignore')
                    canonical = re.search(r'canonical.*?href=[\x22\x27](.*?)[\x22\x27]', html)
                    if canonical:
                        link = canonical.group(1)
            except Exception as e:
                logger.warning("[%s] Lỗi resolve link ID trần: %s" % (self.profile_name, str(e)))

        # Nếu link là reel, mbasic không hỗ trợ đường dẫn /reel/, phải chuyển thành video.php
        match_reel = re.search(r'/reel/(\d+)', link)
        if match_reel:
            link = f"https://mbasic.facebook.com/video.php?v={match_reel.group(1)}"
        else:
            # Chuyển link sang mbasic để tương tác nhẹ hơn và tránh block
            link = link.replace("www.facebook.com", "mbasic.facebook.com")
            link = link.replace("m.facebook.com", "mbasic.facebook.com")
            link = link.replace("://facebook.com", "://mbasic.facebook.com")

        main_tab = self.driver.current_window_handle
        self.driver.execute_script("window.open('');")
        time.sleep(0.5)

        new_tab = None
        for h in self.driver.window_handles:
            if h != main_tab:
                new_tab = h
                break

        if not new_tab:
            logger.warning("[%s] Không thể mở tab mới cho job" % self.profile_name)
            return None

        self.driver.switch_to.window(new_tab)
        self.driver.get(link)
        time.sleep(2)
        return main_tab

    def _close_job_tab(self, main_tab: str) -> None:
        """Đóng job tab và quay lại main tab"""
        try:
            self.driver.close()
        except Exception:
            pass
        try:
            self.driver.switch_to.window(main_tab)
        except Exception:
            if self.driver.window_handles:
                self.driver.switch_to.window(self.driver.window_handles[0])

    # ---- DOM Actions ----

    def do_like(self, link: str) -> Dict[str, Any]:
        """Like bài viết"""
        main_tab = self._open_job_tab(link)
        if not main_tab:
            return {"success": False, "error": "Không thể mở tab"}

        try:
            btn = find_element_safe(self.driver, SELECTORS["like_button"], timeout=6)
            if not btn:
                self._close_job_tab(main_tab)
                return {"success": False, "error": "Không tìm thấy nút like"}

            ok = click_js(self.driver, btn)
            time.sleep(1)
            self._close_job_tab(main_tab)
            return {"success": ok}

        except Exception as e:
            self._close_job_tab(main_tab)
            return {"success": False, "error": str(e)}

    def do_reaction(self, link: str, reaction_type: str = "LIKE") -> Dict[str, Any]:
        """Thả reaction (like, love, haha, wow, sad, angry, care)"""
        reaction_num = REACTION_MAP.get(reaction_type.lower(), "1")
        main_tab = self._open_job_tab(link)
        if not main_tab:
            return {"success": False, "error": "Không thể mở tab"}

        try:
            if reaction_type.lower() == "like":
                btn = find_element_safe(self.driver, SELECTORS["like_button"], timeout=6)
                if btn:
                    ok = click_js(self.driver, btn)
                    time.sleep(1)
                    self._close_job_tab(main_tab)
                    return {"success": ok}
                self._close_job_tab(main_tab)
                return {"success": False, "error": "Không tìm thấy nút like"}

            # Reaction khác: long-press để mở menu
            btn = find_element_safe(self.driver, SELECTORS["like_button"], timeout=6)
            if not btn:
                self._close_job_tab(main_tab)
                return {"success": False, "error": "Không tìm thấy nút like"}

            self.driver.execute_script("""
                var el = arguments[0];
                var ev = new MouseEvent('mousedown', {bubbles: true});
                el.dispatchEvent(ev);
            """, btn)
            time.sleep(0.8)

            try:
                rbtn = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href*="reaction_type=' + reaction_num + '"]'))
                )
                ok = click_js(self.driver, rbtn)
                time.sleep(1)
                self._close_job_tab(main_tab)
                return {"success": ok}
            except TimeoutException:
                rbtn = find_element_safe(self.driver, SELECTORS["reaction_options"], timeout=2)
                if rbtn:
                    ok = click_js(self.driver, rbtn)
                    time.sleep(1)
                    self._close_job_tab(main_tab)
                    return {"success": ok}
                self._close_job_tab(main_tab)
                return {"success": False, "error": "Không tìm thấy nút reaction"}

        except Exception as e:
            self._close_job_tab(main_tab)
            return {"success": False, "error": str(e)}

    def do_follow(self, link: str) -> Dict[str, Any]:
        """Follow người dùng"""
        main_tab = self._open_job_tab(link)
        if not main_tab:
            return {"success": False, "error": "Không thể mở tab"}

        try:
            btn = find_element_safe(self.driver, SELECTORS["follow_button"], timeout=8)
            if not btn:
                try:
                    links = self.driver.find_elements(By.TAG_NAME, "a")
                    for a in links:
                        txt = (a.text or "").lower().strip()
                        href = (a.get_attribute("href") or "").lower()
                        if txt in ("theo dõi", "follow", "theo doi") or "subscribe" in href:
                            btn = a
                            break
                except Exception:
                    pass

            if not btn:
                self._close_job_tab(main_tab)
                return {"success": False, "error": "Không tìm thấy nút follow"}

            ok = click_js(self.driver, btn)
            time.sleep(1.5)
            page = self.driver.page_source.lower()
            verified = "đang theo dõi" in page or "following" in page or "hủy theo dõi" in page
            self._close_job_tab(main_tab)
            return {"success": verified or ok}

        except Exception as e:
            self._close_job_tab(main_tab)
            return {"success": False, "error": str(e)}

    def do_like_page(self, link: str) -> Dict[str, Any]:
        """Like fanpage"""
        main_tab = self._open_job_tab(link)
        if not main_tab:
            return {"success": False, "error": "Không thể mở tab"}

        try:
            btn = find_element_safe(self.driver, SELECTORS["like_page_button"], timeout=8)
            if not btn:
                try:
                    links = self.driver.find_elements(By.TAG_NAME, "a")
                    for a in links:
                        txt = (a.text or "").lower().strip()
                        if txt in ("thích", "like", "thich"):
                            btn = a
                            break
                except Exception:
                    pass

            if not btn:
                self._close_job_tab(main_tab)
                return {"success": False, "error": "Không tìm thấy nút like page"}

            ok = click_js(self.driver, btn)
            time.sleep(1.5)
            self._close_job_tab(main_tab)
            return {"success": ok}

        except Exception as e:
            self._close_job_tab(main_tab)
            return {"success": False, "error": str(e)}

    # ---- Job Dispatcher ----

    def process_job(self, job_type: str, link: str) -> Dict[str, Any]:
        """Dispatch job đến đúng handler"""
        jt = job_type.lower()

        if jt in ("like", "love", "haha", "wow", "sad", "angry", "care"):
            return self.do_reaction(link, jt)
        elif jt == "follow":
            return self.do_follow(link)
        elif jt in ("lik_page", "like_page"):
            return self.do_like_page(link)
        else:
            return {"success": False, "error": "Loại job không hỗ trợ: " + jt}