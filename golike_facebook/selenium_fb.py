"""
Facebook Selenium DOM Bot
Tương tác trực tiếp trên giao diện m.facebook.com qua Selenium
Thay thế FB_WEB_API_FIXED.py cho việc thực hiện job
"""
import time
import os
import re
import urllib.request
import ssl
from typing import Optional, Dict, Any, List

from selenium import webdriver as selenium_driver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException,
    ElementClickInterceptedException, StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager

from golike_core.logging import logger
from golike_core.adb_manager import colored

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
    
    function fire(type) {
        var ev = new MouseEvent(type, {
            bubbles: true, cancelable: true, view: window, buttons: 1
        });
        el.dispatchEvent(ev);
    }
    
    fire('mousedown');
    setTimeout(function() {
        fire('mouseup');
        fire('click');
        if (typeof el.click === 'function') el.click();
    }, 100);
    return true;
}
return false;
"""


def build_anti_detect_options(
    user_data_dir: Optional[str] = None,
    proxy: Optional[str] = None,
    proxy_auth_ext: Optional[str] = None,
    use_desktop: bool = False,
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

    if use_desktop:
        # User agent cho Desktop (Windows/Chrome)
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    else:
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


def inject_anti_detection_scripts(driver: selenium_driver.Chrome, use_desktop: bool = False) -> None:
    """
    Bơm JavaScript chống detect vào browser (chạy trước mọi trang).
    Thêm CDP emulation để giả lập thiết bị iPhone nhất quán.
    """
    # Bơm JS vào mọi document mới (kể cả iframe)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": PRELOAD_JS
    })

    if use_desktop:
        # Emulate Windows platform
        try:
            driver.execute_cdp_cmd("Network.setUserAgentOverride", {
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "platform": "Win32"
            })
        except: pass
        return

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
        # User confirmed XPaths
        "//div[@role='dialog']//div[@role='button'][.//div[@data-ad-rendering-role='like_button']]",
        "//div[@role='button'][.//div[@data-ad-rendering-role='like_button']]",
        "//div[@role='dialog']//div[@role='button' and (.//span[text()='Thích'] or .//span[text()='Like'])]",
        "//div[@role='button' and (.//span[text()='Thích'] or .//span[text()='Like'])]",
        "//div[@role='button' and (@aria-label='Thích' or @aria-label='Like')]",

        # Siêu chính xác: div chứa icon like đặc trưng của FB Desktop (Comet)
        'div[data-ad-rendering-role="like_button"]',
        '//div[@data-ad-rendering-role="like_button"]/ancestor::div[@role="button"]',
        
        # XPath cực kỳ chính xác dựa trên SVG path (Thumb icon)
        '//*[local-name()="path" and starts-with(@d, "M10.999.5a2.5")]/ancestor::div[@role="button"]',
        '//*[local-name()="path" and starts-with(@d, "M10.999.5a2.5")]/ancestor::span/ancestor::div[@role="button"]',
        
        # Nút dựa trên text "Thích" lồng trong cấu trúc div/span của Comet
        '//div[@role="button"]//span[text()="Thích"]',
        '//div[@role="button"]//span[text()="Like"]',
        
        # Desktop (Comet) - Aria labels
        'div[aria-label="Thích"][role="button"]',
        'div[aria-label="Like"][role="button"]',
        'div[aria-label="Thích bài viết"]',
        'div[aria-label="Like post"]',
        
        # Mobile/mbasic
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
        # Desktop
        'div[aria-label="Theo dõi"]',
        'div[aria-label="Follow"]',
        '//span[text()="Theo dõi"]',
        '//span[text()="Follow"]',
    ],
    "like_page_button": [
        # Ưu tiên các nút Theo dõi (Follow) cho job like_page
        '//div[@role="button"]//span[text()="Theo dõi"]',
        '//div[@role="button"]//span[text()="Follow"]',
        '//span[text()="Theo dõi"]/ancestor::div[@role="button"]',
        '//span[text()="Follow"]/ancestor::div[@role="button"]',

        # Nút Thích trang truyền thống
        'a[href*="/a/like.php"]',
        'a[ajaxify*="like"]',
        'button[name="like"]',
        # Desktop
        'div[aria-label="Thích"][role="button"]',
        'div[aria-label="Like"][role="button"]',
    ],

    "reaction_options": [
        "//div[@aria-label='{reaction_type}']", # User confirmed
        'div[data-store*="reaction"] a',
        'a[href*="reaction_type="]',
        # Desktop (Comet) - Vietnamese labels
        'div[role="dialog"] div[aria-label="Yêu thích"][role="button"]',
        'div[role="dialog"] div[aria-label="Thương thương"][role="button"]',
        'div[role="dialog"] div[aria-label="Haha"][role="button"]',
        'div[role="dialog"] div[aria-label="Wow"][role="button"]',
        'div[role="dialog"] div[aria-label="Buồn"][role="button"]',
        'div[role="dialog"] div[aria-label="Phẫn nộ"][role="button"]',
        # Desktop (Comet) - General / English labels
        'div[aria-label*="Love"]',
        'div[aria-label*="Care"]',
        'div[aria-label*="Haha"]',
        'div[aria-label*="Wow"]',
        'div[aria-label*="Sad"]',
        'div[aria-label*="Angry"]',
    ],
    "action_bar_anchors": [
        '//div[@role="button"]//span[text()="Bình luận"]',
        '//div[@role="button"]//span[text()="Chia sẻ"]',
        '//div[@role="button"]//span[text()="Comment"]',
        '//div[@role="button"]//span[text()="Share"]',
        # Mobile
        'a[href*="/comment/"]',
        'a[href*="/share/"]',
    ],
    "liked_state": [
        '//div[@role="button"]//span[text()="Bỏ thích"]',
        '//div[@role="button"]//span[text()="Unlike"]',
        '//div[@aria-pressed="true"]',
        'a[href*="/unlike/"]',
    ],
    "not_found": [
        '//h2[contains(text(), "không xem được nội dung")]',
        '//h2[contains(text(), "not found")]',
        '//span[contains(text(), "không hiển thị")]',
        '//span[contains(text(), "không tìm thấy trang")]',
        '//span[contains(text(), "đã xóa nội dung")]',
        '//div[contains(text(), "không xem được nội dung")]',
        '//h2[contains(text(), "không khả dụng")]',
    ]
}

# Facebook internal reaction IDs dung khi goi API/URL
# 1=Like, 2=Love, 3=Care, 4=Haha, 5=Wow, 6=Sad, 7=Angry
REACTION_MAP = {
    "like": "1", "love": "2", "care": "3",
    "haha": "4", "wow": "5", "sad": "6", "angry": "7",
}

# Nhãn tiếng Việt cho Facebook Desktop (Comet)
REACTION_LABELS = {
    "like": "Thích",
    "love": "Yêu thích",
    "care": "Thương thương",
    "haha": "Haha",
    "wow": "Wow",
    "sad": "Buồn",
    "angry": "Phẫn nộ",
}


def find_element_safe(driver, selectors: List[str], timeout: float = 5) -> Any:
    """Tìm element với ưu tiên vùng Main/Article để tránh click nhầm"""
    end = time.time() + timeout
    while time.time() < end:
        # THỬ 1: Tìm trong vùng Main/Article trước (CHÍNH XÁC NHẤT)
        for sel in selectors:
            try:
                # Nếu selector chưa có tiền tố, thử thêm tiền tố article
                if not sel.startswith("//") and not sel.startswith("("):
                    scoped_sel = f"article {sel}, [role='main'] {sel}"
                    elems = driver.find_elements(By.CSS_SELECTOR, scoped_sel)
                    for el in elems:
                        if el.is_displayed(): return el
                
                # Nếu là XPath, nó thường đã được scoped trong SELECTORS
                if sel.startswith("//"):
                    el = driver.find_element(By.XPATH, sel)
                    if el.is_displayed(): return el
            except: pass

        # THỬ 2: Tìm toàn trang (DỰ PHÒNG)
        for sel in selectors:
            try:
                if sel.startswith("/") or sel.startswith("("):
                    el = driver.find_element(By.XPATH, sel)
                else:
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                
                if el and el.is_displayed():
                    return el
            except Exception:
                pass
        time.sleep(0.4)
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


def click_js(driver, element, label: str = "nút") -> bool:
    """Click an toàn bằng JavaScript có scroll và thông báo"""
    try:
        driver.execute_script(
            """
            var el = arguments[0];
            if (el) {
                el.scrollIntoView({behavior: 'smooth', block: 'center'});
                el.style.border = '3px solid red'; // Highlight đậm hơn
                el.style.backgroundColor = 'rgba(255, 0, 0, 0.2)'; 
            }
            """,
            element
        )
        time.sleep(1.0) # Chờ quan sát
        driver.execute_script(CLICK_SAFE_JS, element)
        print(f"   [✓] Đã click {label}")
        return True
    except Exception as e:
        print(f"   [✗] Lỗi khi click {label}: {e}")
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
        use_desktop: bool = False,
    ):
        self.cookie_str = cookie_str
        self.profile_name = profile_name
        self.proxy = proxy
        self.proxy_auth_ext = proxy_auth_ext
        self.use_desktop = use_desktop

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
                use_desktop=self.use_desktop,
            )
            self.driver = selenium_driver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options,
            )
            
            if self.use_desktop:
                self.driver.set_window_size(1366, 768)
            else:
                self.driver.set_window_size(500, 750)
                
            inject_anti_detection_scripts(self.driver, use_desktop=self.use_desktop)

            logger.info("[%s] Đang bơm cookie vào browser..." % self.profile_name)
            target_url = "https://www.facebook.com/" if self.use_desktop else "https://mbasic.facebook.com/"
            self.driver.get(target_url)
            time.sleep(1)
            self._inject_cookies()

            time.sleep(1)
            # Không cần force_reload vì _inject_cookies đã refresh() rồi
            if not self._verify_login(force_reload=False):
                logger.error("[%s] Cookie không hợp lệ hoặc hết hạn" % self.profile_name)
                return False

            logger.info("[%s] Đăng nhập Facebook thành công" % self.profile_name)
            return True

        except Exception as e:
            logger.error("[%s] Lỗi khởi động bot: %s" % (self.profile_name, str(e)))
            return False

    def stop(self) -> None:
        """Đóng browser và dọn dẹp tiến trình"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
        
        # Dọn dẹp triệt để tiến trình chạy ngầm
        import sys
        if sys.platform == 'win32':
            import subprocess
            try:
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
                os.system("taskkill /f /im chromedriver.exe /T >nul 2>&1")
            except Exception:
                pass
        elif sys.platform == 'darwin':
            import subprocess
            try:
                cmd = "ps aux | grep -E 'Google Chrome.*--remote-debugging-port' | grep -v grep | awk '{print $2}' | xargs kill -9"
                subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["pkill", "-f", "chromedriver"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

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

    def _verify_login(self, force_reload: bool = True) -> bool:
        """Kiểm tra đã đăng nhập Facebook chưa"""
        try:
            if force_reload:
                target_url = "https://www.facebook.com/" if self.use_desktop else "https://mbasic.facebook.com/"
                self.driver.get(target_url)
                time.sleep(2)
            
            page = self.driver.page_source.lower()
            if 'name="email"' in page or 'name="pass"' in page or 'login_form' in page:
                return False
            return True
        except Exception:
            return False

    # ---- Tab helpers ----

    def _open_job_tab(self, link: str, current_tab_only: bool = False) -> Optional[str]:
        """Mở link Facebook job trong tab mới, trả về main tab handle"""
        if not self.driver:
            return None

        # Resolve naked IDs
        if re.match(r'^https?://(www\.|m\.|mbasic\.)?facebook\.com/\d+/?$', link.split('?')[0]):
            try:
                ctx = ssl._create_unverified_context()
                r = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                resp = urllib.request.urlopen(r, timeout=5, context=ctx)
                final_url = resp.geturl()
                if 'login' not in final_url and 'facebook.com/' in final_url and re.search(r'/(videos|reel|posts|photos)/', final_url):
                    link = final_url
                else:
                    html = resp.read().decode('utf-8', errors='ignore')
                    canonical = re.search(r'canonical.*?href=[\x22\x27](.*?)[\x22\x27]', html)
                    if canonical: link = canonical.group(1)
            except Exception as e:
                logger.warning("[%s] Lỗi resolve link ID trần: %s" % (self.profile_name, str(e)))

        # Chuyển link sang mbasic (nếu không dùng desktop mode)
        if not self.use_desktop:
            match_reel = re.search(r'/reel/(\d+)', link)
            if match_reel:
                link = f"https://mbasic.facebook.com/video.php?v={match_reel.group(1)}"
            else:
                link = link.replace("www.facebook.com", "mbasic.facebook.com")
                link = link.replace("m.facebook.com", "mbasic.facebook.com")
                link = link.replace("://facebook.com", "://mbasic.facebook.com")
        else:
            # Nếu dùng desktop mode, đảm bảo link là www.facebook.com
            link = link.replace("mbasic.facebook.com", "www.facebook.com")
            link = link.replace("m.facebook.com", "www.facebook.com")

        if current_tab_only:
            print(f"[*] Đang tải trang: {link[:60]}...")
            try:
                current_url = self.driver.current_url.lower()
                target_url = link.lower()
                
                # Hàm trích xuất path chính (bỏ domain và query) để so sánh nội dung
                def get_clean_path(u):
                    if "facebook.com" not in u: return u
                    return u.split('facebook.com')[-1].split('?')[0].strip('/')

                # Chỉ tải nếu URL hiện tại không khớp với ID bài viết mục tiêu
                if get_clean_path(current_url) != get_clean_path(target_url) or "facebook.com" not in current_url:
                    self.driver.get(link)
                
                # Đợi trang load xong (ready state)
                WebDriverWait(self.driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
                time.sleep(1)
            except Exception:
                pass
            return "current"

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
        print(f"[*] Đang tải trang: {link[:60]}...")
        self.driver.get(link)
        # Đợi trang load xong
        try:
            WebDriverWait(self.driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            time.sleep(2)
        except: pass
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

    def _check_content_available(self) -> Dict[str, Any]:
        """Kiểm tra bài viết/trang có tồn tại hay bị lỗi không"""
        try:
            # 1. Kiểm tra selector "not found"
            found_err = find_element_safe(self.driver, SELECTORS["not_found"], timeout=3)
            if found_err:
                err_text = found_err.text.strip() or "Nội dung không khả dụng"
                return {"success": False, "error": f"Facebook báo lỗi: {err_text}", "is_not_found": True}
            
            # 2. Kiểm tra text trong body nếu selector hụt
            page_text = self.driver.page_source.lower()
            err_keywords = [
                "bạn hiện không xem được nội dung này",
                "nội dung này hiện không hiển thị",
                "trang này không hiển thị",
                "không tìm thấy trang",
                "đã xóa nội dung",
                "content not found",
                "page not found"
            ]
            for kw in err_keywords:
                if kw in page_text:
                    return {"success": False, "error": f"Nội dung bị lỗi hoặc đã xóa ({kw})", "is_not_found": True}
            
            return {"success": True}
        except Exception:
            return {"success": True} # Giả định OK nếu lỗi check

    # ---- DOM Actions ----

    def do_like(self, link: str, current_tab_only: bool = False) -> Dict[str, Any]:
        """Like bài viết"""
        main_tab = self._open_job_tab(link, current_tab_only=current_tab_only)
        if not main_tab:
            return {"success": False, "error": "Không thể mở tab"}

        # KIỂM TRA BÀI VIẾT CÓ TỒN TẠI KHÔNG
        check = self._check_content_available()
        if not check.get("success"):
            if not current_tab_only: self._close_job_tab(main_tab)
            return check

        try:
            print("[*] Đang tìm nút LIKE...")
            btn = find_element_safe(self.driver, SELECTORS["like_button"], timeout=6)
            if not btn:
                if not current_tab_only: self._close_job_tab(main_tab)
                return {"success": False, "error": "Không tìm thấy nút like"}

            ok = click_js(self.driver, btn, label="nút LIKE")
            time.sleep(1)
            if not current_tab_only: self._close_job_tab(main_tab)
            return {"success": ok}

        except Exception as e:
            if not current_tab_only: self._close_job_tab(main_tab)
            return {"success": False, "error": str(e)}

    def do_reaction(self, link: str, reaction_type: str = "LIKE", current_tab_only: bool = False) -> Dict[str, Any]:
        """Thả reaction (like, love, haha, wow, sad, angry, care)"""
        reaction_num = REACTION_MAP.get(reaction_type.lower(), "1")
        main_tab = self._open_job_tab(link, current_tab_only=current_tab_only)
        if not main_tab:
            return {"success": False, "error": "Không thể mở tab"}

        # KIỂM TRA BÀI VIẾT CÓ TỒN TẠI KHÔNG
        check = self._check_content_available()
        if not check.get("success"):
            if not current_tab_only: self._close_job_tab(main_tab)
            return check

        try:
            # 1. TÌM NÚT LIKE/THÍCH CHÍNH
            print(f"[*] Đang thực hiện thả cảm xúc: {reaction_type.upper()}...")
            btn = find_element_safe(self.driver, SELECTORS["like_button"], timeout=10)
            if not btn:
                if not current_tab_only: self._close_job_tab(main_tab)
                return {"success": False, "error": "Không tìm thấy nút like/thích"}

            # Cuộn tới nút
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", btn)
            time.sleep(2)

            # Nếu chỉ là Like thì click luôn
            if reaction_type.lower() == "like":
                print("[+] Đang click: LIKE")
                ok = click_js(self.driver, btn, label="nút LIKE")
                time.sleep(1)
                if not current_tab_only: self._close_job_tab(main_tab)
                return {"success": ok}

            # 2. MỞ MENU CẢM XÚC (Hover trên Desktop, Long-press trên Mobile)
            if self.use_desktop:
                print("[*] Đang di chuột vào nút Thích để mở menu cảm xúc (Desktop Mode)...")
                actions = ActionChains(self.driver)
                actions.move_to_element(btn).perform()
                time.sleep(2)
            else:
                print("[*] Đang nhấn giữ nút Thích để mở menu cảm xúc (Mobile Mode)...")
                self.driver.execute_script("""
                    var el = arguments[0];
                    var rect = el.getBoundingClientRect();
                    var x = rect.left + rect.width / 2;
                    var y = rect.top + rect.height / 2;
                    function fire(type) {
                        el.dispatchEvent(new MouseEvent(type, {
                            bubbles: true, cancelable: true, view: window, 
                            buttons: 1, clientX: x, clientY: y
                        }));
                    }
                    fire('mousedown');
                    setTimeout(function() { fire('mouseup'); }, 1500);
                """, btn)
                time.sleep(2.5)

            # 3. CHỌN CẢM XÚC CỤ THỂ
            vn_label = REACTION_LABELS.get(reaction_type.lower(), reaction_type.capitalize())
            en_label = reaction_type.capitalize()
            
            print(f"[*] Đang tìm cảm xúc: {vn_label} ({en_label})...")
            
            # Thử click bằng Selenium XPath (theo logic user đã test)
            reaction_xpaths = [
                f"//div[@aria-label='{vn_label}']",
                f"//div[@aria-label='{en_label}']",
                f"//div[@role='button' and @aria-label='{vn_label}']",
                f"//div[@role='button' and @aria-label='{en_label}']"
            ]
            
            for rxpath in reaction_xpaths:
                try:
                    r_btns = self.driver.find_elements(By.XPATH, rxpath)
                    for rb in r_btns:
                        if rb.is_displayed():
                            print(f"   [✓] Tìm thấy nút {vn_label} qua XPath. Đang click...")
                            rb.click()
                            time.sleep(1.5)
                            if not current_tab_only: self._close_job_tab(main_tab)
                            return {"success": True}
                except: continue

            # Fallback dùng JS (logic cũ nhưng cải tiến)
            print("[!] XPath không click được, thử lại bằng JavaScript...")
            click_result = self.driver.execute_script("""
                var vn = arguments[0].toLowerCase();
                var en = arguments[1].toLowerCase();
                var rid = arguments[2];
                var containers = document.querySelectorAll('div[role="dialog"], div[role="toolbar"], div[role="tooltip"], [role="presentation"]');
                var foundBtn = null;
                for (var i = 0; i < containers.length; i++) {
                    var buttons = containers[i].querySelectorAll('div[role="button"], a[role="button"], [aria-label]');
                    for (var j = 0; j < buttons.length; j++) {
                        var b = buttons[j];
                        var label = (b.getAttribute('aria-label') || "").toLowerCase();
                        var text = (b.innerText || "").toLowerCase();
                        if ((vn && label.includes(vn)) || (en && label.includes(en)) || (vn && text.includes(vn))) {
                            foundBtn = b; break;
                        }
                    }
                    if (foundBtn) break;
                }
                if (foundBtn) {
                    ['mousedown', 'mouseup', 'click'].forEach(type => {
                        foundBtn.dispatchEvent(new MouseEvent(type, {bubbles: true, cancelable: true, view: window}));
                    });
                    if (typeof foundBtn.click === 'function') foundBtn.click();
                    return true;
                }
                return false;
            """, vn_label, en_label, reaction_num)

            if click_result:
                print(colored(f"   [✓] Đã thả {reaction_type.upper()} thành công!", "green"))
                time.sleep(1.5)
                if not current_tab_only: self._close_job_tab(main_tab)
                return {"success": True}
            
            if not current_tab_only: self._close_job_tab(main_tab)
            return {"success": False, "error": f"Không thể click cảm xúc {reaction_type.upper()}"}

        except Exception as e:
            if not current_tab_only: self._close_job_tab(main_tab)
            return {"success": False, "error": str(e)}

    def do_follow(self, link: str, current_tab_only: bool = False) -> Dict[str, Any]:
        """Follow người dùng"""
        main_tab = self._open_job_tab(link, current_tab_only=current_tab_only)
        if not main_tab:
            return {"success": False, "error": "Không thể mở tab"}

        # KIỂM TRA TRANG CÓ TỒN TẠI KHÔNG
        check = self._check_content_available()
        if not check.get("success"):
            if not current_tab_only: self._close_job_tab(main_tab)
            return check

        try:
            print("[*] Đang tìm nút FOLLOW...")
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
                if not current_tab_only: self._close_job_tab(main_tab)
                return {"success": False, "error": "Không tìm thấy nút follow"}

            ok = click_js(self.driver, btn, label="nút FOLLOW")
            time.sleep(1.5)
            page = self.driver.page_source.lower()
            verified = "đang theo dõi" in page or "following" in page or "hủy theo dõi" in page
            if not current_tab_only: self._close_job_tab(main_tab)
            return {"success": verified or ok}

        except Exception as e:
            if not current_tab_only: self._close_job_tab(main_tab)
            return {"success": False, "error": str(e)}

    def do_like_page(self, link: str, current_tab_only: bool = False) -> Dict[str, Any]:
        """Like fanpage"""
        main_tab = self._open_job_tab(link, current_tab_only=current_tab_only)
        if not main_tab:
            return {"success": False, "error": "Không thể mở tab"}

        # KIỂM TRA TRANG CÓ TỒN TẠI KHÔNG
        check = self._check_content_available()
        if not check.get("success"):
            if not current_tab_only: self._close_job_tab(main_tab)
            return check

        try:
            print("[*] Đang tìm nút LIKE hoặc FOLLOW PAGE...")
            btn = find_element_safe(self.driver, SELECTORS["like_page_button"], timeout=8)
            if not btn:
                try:
                    links = self.driver.find_elements(By.TAG_NAME, "a")
                    for a in links:
                        txt = (a.text or "").lower().strip()
                        if txt in ("thích", "like", "thich", "theo dõi", "follow"):
                            btn = a
                            break
                except Exception:
                    pass

            if not btn:
                if not current_tab_only: self._close_job_tab(main_tab)
                return {"success": False, "error": "Không tìm thấy nút like/follow page"}

            ok = click_js(self.driver, btn, label="nút LIKE/FOLLOW PAGE")
            time.sleep(1.5)
            if not current_tab_only: self._close_job_tab(main_tab)
            return {"success": ok}

        except Exception as e:
            if not current_tab_only: self._close_job_tab(main_tab)
            return {"success": False, "error": str(e)}

    # ---- Job Dispatcher ----

    def process_job(self, job_type: str, link: str, current_tab_only: bool = False) -> Dict[str, Any]:
        """Dispatch job đến đúng handler"""
        jt = job_type.lower()

        if jt in ("like", "love", "haha", "wow", "sad", "angry", "care"):
            return self.do_reaction(link, jt, current_tab_only=current_tab_only)
        elif jt == "follow":
            return self.do_follow(link, current_tab_only=current_tab_only)
        elif jt in ("lik_page", "like_page"):
            return self.do_like_page(link, current_tab_only=current_tab_only)
        else:
            return {"success": False, "error": "Loại job không hỗ trợ: " + jt}