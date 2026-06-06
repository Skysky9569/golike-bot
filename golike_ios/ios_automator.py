"""
iOS Automation module using facebook-wda.
This provides a lighter, faster, Python-only alternative to Appium.
"""
from golike_core.logging import logger
from golike_core.adb_manager import colored
import time

try:
    import wda
    WDA_AVAILABLE = True
except ImportError:
    WDA_AVAILABLE = False
    logger.warning("facebook-wda not installed. iOS automation will not work.")

class TikTokIOSAutomator:
    def __init__(self, platform_version="16.4", device_name="iPhone", udid=None, bundle_id="com.zhiliaoapp.musically"):
        """Khởi tạo kết nối với WebDriverAgent"""
        self.platform_version = platform_version
        self.device_name = device_name
        self.udid = udid
        self.bundle_id = bundle_id
        self.client = None

    def connect(self) -> bool:
        """Kết nối tới thiết bị iOS thông qua facebook-wda."""
        if not WDA_AVAILABLE:
            logger.error("Vui lòng cài đặt: pip install facebook-wda tidevice")
            return False

        import socket
        def is_port_open(port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(('localhost', port)) == 0

        if not is_port_open(8100):
            logger.warning("Cổng 8100 đang đóng. Đang kiểm tra tidevice...")
            try:
                import subprocess
                # Thử tìm bundle ID của WDA nếu chưa có hoặc dùng mặc định
                result = subprocess.run(['tidevice', 'applist'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    wda_bundles = [line.split()[0] for line in result.stdout.split('\n') if 'WebDriverAgentRunner' in line]
                    if wda_bundles:
                        logger.info(f"Tìm thấy WDA Bundle: {wda_bundles[0]}")
                        logger.warning(f"Gợi ý: Hãy mở Terminal mới và chạy lệnh sau:")
                        logger.warning(colored(f"tidevice wdaproxy -B {wda_bundles[0]} -p 8100", "cyan"))
                    else:
                        logger.error("Không tìm thấy WebDriverAgent trên thiết bị!")
                else:
                    logger.error("Không thể liệt kê app bằng tidevice. Vui lòng kiểm tra kết nối USB.")
            except Exception as te:
                logger.debug(f"Lỗi khi dùng tidevice: {te}")

            logger.error("❌ Lỗi: WebDriverAgent chưa được khởi động trên điện thoại.")
            return False

        try:
            logger.info("Đang kết nối với WebDriverAgent (http://localhost:8100)...")
            self.client = wda.Client('http://localhost:8100')

            logger.info(f"Đang mở App: {self.bundle_id}...")
            # Sử dụng app_start thay vì session để không reset app
            self.client.app_start(self.bundle_id)

            logger.info(f"✅ Kết nối WDA thành công với {self.bundle_id}.")
            return True
        except Exception as e:
            logger.error(f"Lỗi kết nối WDA: {e}")
            logger.warning("Vui lòng đảm bảo WebDriverAgent đang chạy ở cổng 8100.")
            return False
    def open_url(self, url: str):
        """Mở link TikTok trực tiếp (Deep Link)"""
        if not self.client: return
        try:
            logger.info(f"Đang mở link: {url}")
            # Cách 1: Thử dùng lệnh open_url trực tiếp của WDA (Nhanh và chuẩn deep link)
            try:
                self.client.open_url(url)
                time.sleep(2)
                
                # Xử lý Alert "Open in TikTok?" hoặc "Mở trong TikTok?"
                # Thường xuất hiện lần đầu hoặc tùy version iOS
                for _ in range(3):
                    if self.client.alert.exists:
                        buttons = self.client.alert.buttons()
                        # Tìm nút "Open", "Mở", "Allow", "Cho phép"
                        for btn in ["Open", "Mở", "Allow", "Cho phép"]:
                            if btn in buttons:
                                self.client.alert.click(btn)
                                logger.info(f"✅ Đã xác nhận mở App: {btn}")
                                break
                        break
                    time.sleep(1)
                
                time.sleep(3) # Chờ app chuyển hướng
                return
            except Exception as e:
                logger.debug(f"Lệnh open_url trực tiếp không thành công: {e}")

            # Cách 2: Fallback qua Safari nếu open_url trực tiếp bị lỗi
            logger.info(f"Mở link qua Safari: {url}")
            self.client.app_start("com.apple.mobilesafari")
            time.sleep(1.5)
            
            try:
                # Tìm thanh địa chỉ
                url_bar = self.client(nameContains="URL")
                if not url_bar.exists: url_bar = self.client(nameContains="Address")
                if not url_bar.exists: url_bar = self.client(nameContains="Địa chỉ")
                    
                url_bar.click()
                time.sleep(0.5)
                self.client.send_keys(url + "\n")
                
                # Đợi Safari hỏi có mở app không
                time.sleep(2)
                if self.client.alert.exists:
                    self.client.alert.click("Open")
            except Exception as inner_e:
                logger.error(f"Không thể gõ URL vào Safari: {inner_e}")
                
            time.sleep(5) # Chờ app load
        except Exception as e:
            logger.error(f"Lỗi mở link iOS: {e}")

    def close(self):
        if self.client:
            logger.info("Đã ngắt kết nối WDA.")
            self.client = None

    def click_follow(self) -> bool:
        """Thực hiện click Follow trên TikTok iOS."""
        if not self.client:
            return False
            
        selectors = ["Follow", "Theo dõi"]
        
        for name in selectors:
            try:
                el = self.client(name=name, visible=True)
                if el.exists:
                    el.click()
                    logger.info("✅ Đã click Follow (iOS).")
                    time.sleep(2)
                    return True
            except:
                continue
                
        # Dùng XPath nếu Name không được
        xpaths = [
            "//XCUIElementTypeButton[@name='Follow']",
            "//XCUIElementTypeButton[@label='Theo dõi']"
        ]
        for xp in xpaths:
            try:
                el = self.client(xpath=xp)
                if el.exists:
                    el.click()
                    logger.info("✅ Đã click Follow (iOS XPath).")
                    time.sleep(2)
                    return True
            except:
                continue
                
        logger.error("Không tìm thấy nút Follow trên iOS.")
        return False
            
    def click_like(self) -> bool:
        """Thực hiện click Like trên TikTok iOS."""
        if not self.client:
            return False
            
        selectors = ["Like", "Thích"]
        
        for name in selectors:
            try:
                el = self.client(name=name, visible=True)
                if el.exists:
                    # wda trả về selected qua value hoặc thuộc tính
                    if el.value == "1": 
                         logger.info("Đã like từ trước.")
                         return True
                    el.click()
                    logger.info("✅ Đã click Like (iOS).")
                    time.sleep(1)
                    return True
            except:
                continue
                
        try:
            logger.warning("Không tìm thấy nút Like, thử Double Tap vào giữa màn hình...")
            w, h = self.client.window_size()
            x = w // 2
            y = h // 2
            self.client.double_tap(x, y)
            time.sleep(1)
            return True
        except:
            pass
            
        return False

