"""
Mô-đun chống phát hiện (Anti-detection) cho trình duyệt Selenium.
Chứa các script JavaScript để giả lập vân tay trình duyệt (browser fingerprint).
"""

# Script cơ bản để che giấu thuộc tính webdriver và một số thông số hệ thống
BASIC_STEALTH_SCRIPT = """
// Ẩn navigator.webdriver
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// Giả lập plugins
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });

// Đặt ngôn ngữ
Object.defineProperty(navigator, 'languages', { get: () => ['vi-VN', 'vi', 'en-US', 'en'] });

// Ngẫu nhiên hóa platform
const plats = ['Win32', 'MacIntel', 'Linux x86_64'];
const plat = plats[Math.floor(Math.random() * plats.length)];
Object.defineProperty(navigator, 'platform', { get: () => plat });
"""

# Script nâng cao giả lập thiết bị di động (thường dùng cho Facebook m-site)
MOBILE_STEALTH_SCRIPT = """
// 1. Ẩn navigator.webdriver
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 2. Fake plugins (giống Chrome mobile thật)
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

// 3. Ngôn ngữ + platform + vendor + maxTouchPoints
Object.defineProperty(navigator, 'languages', { get: () => ['vi-VN', 'vi', 'en-US', 'en'] });
Object.defineProperty(navigator, 'platform',  { get: () => 'iPhone' });
Object.defineProperty(navigator, 'vendor',    { get: () => 'Apple Computer, Inc.' });
Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 5 });

// 4. Hardware (giữ nhất quán)
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 6 });
Object.defineProperty(navigator, 'deviceMemory',        { get: () => 4 });

// 5. Chrome runtime
window.chrome = {
    runtime: { id: undefined },
    loadTimes: function() {},
    csi: function() {},
    app: {}
};

// 6. WebGL & Canvas Spoofing
try {
  const getParameter = WebGLRenderingContext.prototype.getParameter;
  WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter(parameter);
  };
  const originalFillText = CanvasRenderingContext2D.prototype.fillText;
  CanvasRenderingContext2D.prototype.fillText = function(text, x, y, maxWidth) {
    return originalFillText.call(this, text, x + (Math.random() * 0.2 - 0.1), y + (Math.random() * 0.2 - 0.1), maxWidth);
  };
} catch(e) {}
"""

# Script dùng trong golikefb_sele.py và selenium_fb.py (tổng hợp)
FB_STEALTH_SCRIPT = """
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
            osc.start = function(when = 0) {
                return _origStart(when + (Math.random() * 0.0001));
            };
            return osc;
        };
    } catch(e) {}
})();
"""

