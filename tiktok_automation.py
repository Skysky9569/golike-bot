"""
TikTok UI Automation Module

Module này cung cấp class TikTokUIAutomator để tự động hóa các tác vụ UI trên TikTok:
- Tìm và click nút Follow
- Tìm và click nút Like
- Verify trạng thái đã follow/like
- Tìm kiếm user qua thanh search

Sử dụng thư viện uiautomator2 để tương tác với UI.
"""

import time
import logging
import subprocess
import re
import xml.etree.ElementTree as ET
from typing import Optional, Tuple, List
from dataclasses import dataclass

# Try to import uiautomator2 globally
try:
    import uiautomator2 as u2
    HAS_U2 = True
except ImportError:
    HAS_U2 = False
    u2 = None

logger = logging.getLogger("golikebydom")


@dataclass
class ElementInfo:
    """Thông tin về element tìm thấy"""
    exists: bool
    text: Optional[str] = None
    resource_id: Optional[str] = None
    content_desc: Optional[str] = None
    bounds: Optional[Tuple[int, int, int, int]] = None  # (left, top, right, bottom)
    is_selected: bool = False


class PureADBAutomator:
    """UI Automator sử dụng thuần ADB (không cần thư viện uiautomator2)
    Dùng xml dump để tìm tọa độ và input tap để click.
    """

    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id
        from golike_core.adb_manager import ADBManager
        self.adb_mgr = ADBManager()
        self.adb_path = self.adb_mgr.adb_path
        self._connected = False

    def connect(self) -> bool:
        """Kiểm tra kết nối ADB"""
        try:
            cmd = [self.adb_path]
            if self.device_id:
                cmd.extend(["-s", self.device_id])
            cmd.extend(["shell", "getprop", "ro.product.model"])
            result = subprocess.run(cmd, capture_output=True, text=True,
                                   encoding='utf-8', errors='replace', timeout=5)
            if result.returncode == 0:
                self._connected = True
                logger.info(f"Pure ADB connected to: {result.stdout.strip()}")
                return True
        except Exception as e:
            logger.error(f"Pure ADB connection error: {e}")
        return False

    def disconnect(self) -> None:
        self._connected = False

    def _run_adb(self, args: List[str]) -> subprocess.CompletedProcess:
        cmd = [self.adb_path]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)
        return subprocess.run(cmd, capture_output=True, text=True,
                             encoding='utf-8', errors='replace', timeout=15)

    def _dump_ui(self) -> Optional[str]:
        """Xuất UI XML từ thiết bị và đọc nội dung (binary-safe, Windows-friendly)"""
        try:
            # Xuất ra file trên thiết bị
            self._run_adb(["shell", "uiautomator", "dump", "/sdcard/view.xml"])
            # Đọc nội dung file dưới dạng bytes để tránh UnicodeDecodeError trên Windows (cp1252)
            cmd = [self.adb_path]
            if self.device_id:
                cmd.extend(["-s", self.device_id])
            cmd.extend(["shell", "cat", "/sdcard/view.xml"])
            raw = subprocess.run(cmd, capture_output=True, timeout=15)
            if raw.returncode == 0 and raw.stdout:
                # Decode bytes dùng utf-8, thay thế ký tự lỗi thay vì crash
                xml_text = raw.stdout.decode('utf-8', errors='replace')
                if "<?xml" in xml_text:
                    return xml_text
        except Exception as e:
            logger.error(f"Lỗi khi xuất UI: {e}")
        finally:
            # Luôn đảm bảo dọn dẹp file tạm trên thiết bị
            try:
                self._run_adb(["shell", "rm", "-f", "/sdcard/view.xml"])
            except Exception:
                pass
        return None

    def _parse_bounds(self, bounds_str: str) -> Optional[Tuple[int, int, int, int]]:
        """Parse bounds string '[left,top][right,bottom]' thành tuple"""
        try:
            # Format: [76,542][308,630]
            match = re.findall(r"(\d+)", bounds_str)
            if len(match) == 4:
                return tuple(map(int, match))
        except Exception:
            pass
        return None

    def find_element(self, text_pattern: str = None, resource_id: str = None, content_desc: str = None) -> Optional[ElementInfo]:
        xml_data = self._dump_ui()
        if not xml_data:
            return None

        try:
            # Fix potential encoding issues in output
            xml_data = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\x80-\xFF]', '', xml_data)
            root = ET.fromstring(xml_data)
            
            for node in root.iter('node'):
                match = True
                if text_pattern and not re.search(text_pattern, node.get('text', ''), re.I):
                    match = False
                if resource_id and resource_id not in node.get('resource-id', ''):
                    match = False
                if content_desc and content_desc not in node.get('content-desc', ''):
                    match = False
                
                if match:
                    bounds = self._parse_bounds(node.get('bounds', ''))
                    if bounds:
                        return ElementInfo(
                            exists=True,
                            text=node.get('text'),
                            resource_id=node.get('resource-id'),
                            content_desc=node.get('content-desc'),
                            bounds=bounds,
                            is_selected=node.get('selected') == 'true'
                        )
        except Exception as e:
            logger.error(f"Error parsing UI XML: {e}")
        return None

    def click_at(self, bounds: Tuple[int, int, int, int]):
        left, top, right, bottom = bounds
        import random
        x = random.randint(left + 5, right - 5)
        y = random.randint(top + 5, bottom - 5)
        self._run_adb(["shell", "input", "tap", str(x), str(y)])

    def process_job(self, job_type: str) -> Tuple[bool, str, bool]:
        if not self._connected:
            if not self.connect():
                return False, "Không thể kết nối đến thiết bị qua ADB", False

        if job_type == "follow":
            # Tìm nút Follow hoặc Theo dõi
            el = self.find_element(text_pattern="^(Follow|Theo dõi)$")
            if not el:
                # Try resource ID as backup
                el = self.find_element(resource_id="follow_button")
            
            if el:
                # Check if already followed
                text = (el.text or "").lower()
                if "followed" in text or "đã theo dõi" in text or "following" in text:
                    return False, "Đã follow rồi", False
                
                self.click_at(el.bounds)
                return True, "Đã click nút Follow (Pure ADB)", False
            return False, "Không tìm thấy nút Follow", True

        elif job_type == "like":
            # Like button is tricky, usually an ImageView with content-desc or resource-id
            el = self.find_element(resource_id="like_icon")
            if not el:
                el = self.find_element(content_desc="Like")
            if not el:
                el = self.find_element(content_desc="Thích")
            
            if el:
                if el.is_selected or "unlike" in (el.content_desc or "").lower():
                    return False, "Đã like rồi", False
                
                self.click_at(el.bounds)
                return True, "Đã click nút Like (Pure ADB)", False
            
            # Double tap fallback for like
            try:
                # Need screen size for double tap center
                self._run_adb(["shell", "input", "tap", "360", "700"])
                time.sleep(0.15)
                self._run_adb(["shell", "input", "tap", "360", "700"])
                return True, "Đã thả tim bằng Double Tap (Pure ADB)", False
            except:
                pass
            
            return False, "Không tìm thấy nút Like", True
            
        return False, f"Loại job không hỗ trợ: {job_type}", False

    def scroll_down_only(self) -> None:
        self._run_adb(["shell", "input", "swipe", "360", "1000", "360", "300", "300"])

    def clear_search_text(self) -> bool:
        # Simple back press for pure adb search clearing
        for _ in range(2):
            self._run_adb(["shell", "input", "keyevent", "4"]) # BACK
            time.sleep(1)
        return True


class TikTokUIAutomator:
    """UI Automator cho TikTok app (Sử dụng uiautomator2)
    """

    # Selectors for search icon (more comprehensive)
    SEARCH_ICON_SELECTORS = [
        {"resourceId": "com.ss.android.ugc.trill:id/jhs"},
        {"resourceId": "com.zhiliaoapp.musically:id/search_icon"},
        {"description": "Tìm kiếm"},
        {"description": "Search"},
        {"contentDescription": "Search"},
        {"contentDescription": "Tìm kiếm"},
    ]

    SEARCH_INPUT_SELECTORS = [
        {"resourceId": "com.ss.android.ugc.trill:id/h5p"},
        {"resourceId": "com.ss.android.ugc.trill:id/search_input"},
        {"className": "android.widget.EditText"}
    ]

    SEARCH_BUTTON_SELECTORS = [
        {"resourceId": "com.ss.android.ugc.trill:id/zpp", "text": "Tìm kiếm"},
        {"resourceId": "com.ss.android.ugc.trill:id/search_btn"},
        {"resourceId": "com.zhiliaoapp.musically:id/search_button"},
        {"resourceId": "com.ss.android.ugc.trill:id/action_search"}
    ]

    # Selectors for user tab
    USERS_TAB_SELECTORS = [
        {"description": "Người dùng"},
        {"text": "Người dùng"},
        {"description": "Users"},
        {"text": "Users"},
        {"description": "Người dùng", "className": "android.widget.TextView"},
        {"description": "Users", "className": "android.widget.TextView"},
        {"text": "Người dùng", "className": "android.widget.TextView"},
        {"text": "Users", "className": "android.widget.TextView"},
    ]

    # Selectors cho nút Follow
    FOLLOW_SELECTORS = [
        # Text chính xác - ưu tiên textMatches để tránh nhầm
        {"textMatches": "^Follow$"},
        {"textMatches": "^Theo dõi$"},
        {"text": "Follow"},
        {"text": "Theo dõi"},
        # Resource-id selectors (nút Follow thường có resource-id đặc biệt)
        {"resourceId": "com.zhiliaoapp.musically:id/follow_button"},
        {"resourceId": "com.zhiliaoapp.musically:id/follow_btn"},
        {"resourceId": "com.zhiliaoapp.musically:id/follow"},
        {"resourceId": "com.ss.android.ugc.trill:id/follow_button"},
        {"resourceId": "com.ss.android.ugc.trill:id/follow_btn"},
        {"resourceId": "com.ss.android.ugc.trill:id/follow"},
        # Content-description selectors
        {"description": "Follow"},
        {"description": "Theo dõi"},
    ]

    # Selectors cho nút Like
    LIKE_SELECTORS = [
        # Resource-id selectors (nút like thường có resource-id đặc biệt)
        {"resourceId": "com.zhiliaoapp.musically:id/like_container"},
        {"resourceId": "com.zhiliaoapp.musically:id/like_icon"},
        {"resourceId": "com.zhiliaoapp.musically:id/like_btn"},
        {"resourceId": "com.ss.android.ugc.trill:id/like_container"},
        {"resourceId": "com.ss.android.ugc.trill:id/like_icon"},
        {"resourceId": "com.ss.android.ugc.trill:id/like_btn"},
        # Content-description selectors
        {"description": "Like"},
        {"description": "Thích"},
        {"description": "Unlike"},
        {"description": "Bỏ thích"},
        # Class name selectors
        {"className": "android.widget.ImageView"},
    ]

    def __init__(self, device_id: Optional[str] = None):
        """Khởi tạo TikTokUIAutomator

        Args:
            device_id: ID thiết bị ADB (nếu None dùng thiết bị mặc định)
        """
        self.device_id = device_id
        self._u2 = None
        self._connected = False

    def connect(self) -> bool:
        """Kết nối đến thiết bị

        Returns:
            bool: True nếu kết nối thành công, False nếu không
        """
        if not HAS_U2:
            logger.error("uiautomator2 chưa được cài đặt. Hãy chạy: pip install uiautomator2")
            return False

        try:
            if self.device_id:
                # Nếu device_id có dạng IP/WiFi (chứa '.' hoặc ':'), tự động chạy adb connect trước
                if "." in self.device_id or ":" in self.device_id:
                    try:
                        import subprocess
                        from golike_core.adb_manager import ADBManager
                        adb_mgr = ADBManager()
                        adb_path = adb_mgr.adb_path
                        logger.info(f"Đang tự động kết nối ADB qua Wifi đến {self.device_id}...")
                        subprocess.run([adb_path, "connect", self.device_id], capture_output=True, timeout=5)
                    except Exception as e:
                        logger.debug(f"Không thể chạy adb connect tự động: {e}")

                self._u2 = u2.connect(self.device_id)
            else:
                self._u2 = u2.connect()

            # Test kết nối bằng cách lấy thông tin thiết bị (info)
            self._u2.info
            self._connected = True
            logger.info(f"Đã kết nối đến thiết bị: {self.device_id or 'mặc định'}")
            return True
        except Exception as e:
            logger.error(f"Lỗi kết nối uiautomator2: {e}")
            return False

    def disconnect(self) -> None:
        """Ngắt kết nối"""
        self._u2 = None
        self._connected = False
        logger.info("Đã ngắt kết nối uiautomator2")

    def _is_follower_element(self, element_info: dict) -> bool:
        """Kiểm tra element có phải là Follower không

        Args:
            element_info: Thông tin element từ uiautomator2

        Returns:
            bool: True nếu là Follower, False nếu không
        """
        text = (element_info.get("text") or "").lower()
        content_desc = (element_info.get("contentDescription") or "").lower()

        # Check text
        for follower_text in ["follower", "người theo dõi", "followers"]:
            if follower_text in text:
                return True
            if follower_text in content_desc:
                return True

        return False

    def _find_element(self, selectors: List[dict], timeout: float = 2.0, exclude_follower: bool = False, exclude_imageview: bool = False) -> Optional[ElementInfo]:
        """Tìm element theo danh sách selectors

        Args:
            selectors: Danh sách selectors để tìm
            timeout: Timeout tối đa (giây)
            exclude_follower: Loại trừ element Follower (cho nút Follow)
            exclude_imageview: Loại trừ element ImageView (tránh nhầm với avatar)

        Returns:
            Optional[ElementInfo]: Thông tin element tìm thấy hoặc None
        """
        if not self._connected or not self._u2:
            logger.warning("Chưa kết nối đến thiết bị")
            return None

        start_time = time.time()
        while time.time() - start_time < timeout:
            for selector in selectors:
                try:
                    element = self._u2(**selector)
                    if element.exists:
                        info = element.info

                        # Loại trừ element Follower nếu cần
                        if exclude_follower and self._is_follower_element(info):
                            logger.debug(f"Bỏ qua element Follower: {info.get('text')}")
                            continue

                        # Loại trừ ImageView để tránh click nhầm vào avatar/profile picture
                        if exclude_imageview and info.get("className") == "android.widget.ImageView":
                            logger.debug(f"Bỏ qua ImageView (tránh click nhầm avatar): resourceId={info.get('resourceId')}, desc={info.get('contentDescription')}")
                            continue

                        bounds = info.get("bounds")
                        # Đảm bảo bounds là dictionary hợp lệ
                        if isinstance(bounds, dict):
                            # Chuyển đổi các giá trị bounds sang số nguyên
                            left = int(bounds.get("left", 0)) if bounds.get("left") is not None else 0
                            top = int(bounds.get("top", 0)) if bounds.get("top") is not None else 0
                            right = int(bounds.get("right", 0)) if bounds.get("right") is not None else 0
                            bottom = int(bounds.get("bottom", 0)) if bounds.get("bottom") is not None else 0

                            return ElementInfo(
                                exists=True,
                                text=info.get("text"),
                                resource_id=info.get("resourceId"),
                                content_desc=info.get("contentDescription"),
                                bounds=(left, top, right, bottom),
                                is_selected=info.get("selected", False)
                            )
                        else:
                            # Nếu bounds không phải là dictionary, sử dụng giá trị mặc định
                            logger.debug(f"Bounds không hợp lệ: {bounds}")
                            return ElementInfo(
                                exists=True,
                                text=info.get("text"),
                                resource_id=info.get("resourceId"),
                                content_desc=info.get("contentDescription"),
                                bounds=(0, 0, 0, 0),  # Giá trị mặc định
                                is_selected=info.get("selected", False)
                            )
                except Exception as e:
                    logger.debug(f"Lỗi tìm element với selector {selector}: {e}")
                    continue
            time.sleep(0.2)

        return None

    def find_follow_button(self, timeout: float = 2.0) -> Optional[ElementInfo]:
        """Tìm nút Follow (loại trừ Follower và ImageView/Avatar)

        Args:
            timeout: Timeout tối đa (giây)

        Returns:
            Optional[ElementInfo]: Thông tin nút Follow hoặc None
        """
        logger.debug("Đang tìm nút Follow...")
        return self._find_element(self.FOLLOW_SELECTORS, timeout, exclude_follower=True, exclude_imageview=True)

    def debug_find_follow_elements(self) -> List[dict]:
        """Debug: Tìm tất cả element có chứa "Follow" để xem có bao nhiêu

        Returns:
            List[dict]: Danh sách thông tin các element tìm thấy
        """
        if not self._connected or not self._u2:
            logger.warning("Chưa kết nối đến thiết bị")
            return []

        results = []
        try:
            # Tìm tất cả element có text chứa "Follow"
            elements = self._u2(textMatches=".*Follow.*")
            for element in elements:
                info = element.info
                results.append({
                    "text": info.get("text"),
                    "resource_id": info.get("resourceId"),
                    "content_desc": info.get("contentDescription"),
                    "bounds": info.get("bounds"),
                    "class": info.get("className")
                })

            logger.info(f"Tìm thấy {len(results)} element chứa 'Follow':")
            for i, r in enumerate(results, 1):
                logger.info(f"  [{i}] text='{r['text']}', resource_id='{r['resource_id']}', bounds={r['bounds']}")
        except Exception as e:
            logger.error(f"Lỗi debug: {e}")

        return results

    def find_like_button(self, timeout: float = 2.0) -> Optional[ElementInfo]:
        """Tìm nút Like

        Args:
            timeout: Timeout tối đa (giây)

        Returns:
            Optional[ElementInfo]: Thông tin nút Like hoặc None
        """
        logger.debug("Đang tìm nút Like...")
        return self._find_element(self.LIKE_SELECTORS, timeout)

    def is_already_followed(self, element: ElementInfo) -> bool:
        """Kiểm tra đã follow chưa

        Args:
            element: Thông tin element nút Follow

        Returns:
            bool: True nếu đã follow, False nếu chưa
        """
        if not element.exists:
            return False

        # Check text
        if element.text:
            text_lower = element.text.lower()
            if "followed" in text_lower or "đã theo dõi" in text_lower or "following" in text_lower:
                return True

        # Check selected state
        if element.is_selected:
            return True

        return False

    def is_already_liked(self, element: ElementInfo) -> bool:
        """Kiểm tra đã like chưa

        Args:
            element: Thông tin element nút Like

        Returns:
            bool: True nếu đã like, False nếu chưa
        """
        if not element.exists:
            return False

        # Check selected state (nút like thường selected khi đã like)
        if element.is_selected:
            return True

        # Check content description
        if element.content_desc:
            desc_lower = element.content_desc.lower()
            if "unlike" in desc_lower or "bỏ thích" in desc_lower or "liked" in desc_lower:
                return True

        return False

    def click_element(self, element: ElementInfo) -> bool:
        """Click vào element

        Args:
            element: Thông tin element cần click

        Returns:
            bool: True nếu click thành công, False nếu không
        """
        if not element.exists or not element.bounds:
            logger.warning("Element không tồn tại hoặc không có bounds")
            return False

        try:
            left, top, right, bottom = element.bounds
            # Kiểm tra xem các giá trị bounds có phải là số nguyên không
            if isinstance(left, str) or isinstance(top, str) or isinstance(right, str) or isinstance(bottom, str):
                logger.warning("Bounds không hợp lệ - chứa giá trị chuỗi")
                return False

            # Tinh toan toa do random trong pham vi cua nut de tranh click cung 1 diem
            import random
            
            # Tao ra mot vung an toan (padding) de tranh click vao mep nut
            width = right - left
            height = bottom - top
            safe_margin_x = int(width * 0.2)
            safe_margin_y = int(height * 0.2)
            
            # Neu nut qua nho, van click o giua, nguoc lai thi random
            if safe_margin_x > 0 and safe_margin_y > 0:
                click_x = random.randint(left + safe_margin_x, right - safe_margin_x)
                click_y = random.randint(top + safe_margin_y, bottom - safe_margin_y)
            else:
                click_x = (left + right) // 2
                click_y = (top + bottom) // 2

            logger.debug(f"Click random vao toa do ({click_x}, {click_y}) thuoc vung [{left},{top},{right},{bottom}]")
            self._u2.click(click_x, click_y)
            return True
        except Exception as e:
            logger.error(f"Loi click element: {e}")
            return False

    def random_swipe(self) -> None:
        """Vuốt ngẫu nhiên lên hoặc xuống để giả lập người dùng thật"""
        if not self._connected or not self._u2:
            return
            
        try:
            import random
            w, h = self._u2.window_size()
            
            # Xac suat 70% vuot xuong, 30% vuot len, kem theo Do Lech random tren truc Y
            # Giam bien do vuot de tranh lam mat nut Follow khoi man hinh
            if random.random() < 0.7:
                # Vuot xuong mot xiu
                start_y = int(h * random.uniform(0.55, 0.65))
                end_y = int(h * random.uniform(0.40, 0.45))
            else:
                # Vuot len mot xiu
                start_y = int(h * random.uniform(0.40, 0.45))
                end_y = int(h * random.uniform(0.55, 0.65))
                
            # Do lech random tren truc X de duong vuot khong bi thang tăp
            start_x = w // 2 + random.randint(-40, 40)
            end_x = start_x + random.randint(-20, 20)
            
            logger.debug(f"Thuc hien vuot ngau nhien (tu {start_y} den {end_y})")
            self._u2.swipe(start_x, start_y, end_x, end_y, duration=random.uniform(0.1, 0.3))
            
            # Vuot nguoc lai de tra ve vi tri cu (dam bao khong bi mat nut Follow/Like)
            time.sleep(random.uniform(0.2, 0.5))
            self._u2.swipe(end_x, end_y, start_x, start_y, duration=random.uniform(0.1, 0.3))
            
            time.sleep(random.uniform(0.5, 1.0))
        except Exception as e:
            logger.debug(f"Loi vuot ngau nhien: {e}")

    def scroll_down_only(self) -> None:
        """Chi vuot xuong de chuyen sang video khac (xem them) trong thoi gian cho."""
        try:
            w, h = self._u2.window_size()
            start_y = int(h * random.uniform(0.70, 0.85))
            end_y = int(h * random.uniform(0.15, 0.30))
            start_x = w // 2 + random.randint(-40, 40)
            end_x = start_x + random.randint(-20, 20)
            
            logger.debug("Dang vuot xem video khac...")
            self._u2.swipe(start_x, start_y, end_x, end_y, duration=random.uniform(0.15, 0.4))
        except Exception as e:
            logger.debug(f"Loi vuot video: {e}")

    def find_and_click_follow(self, retry_count: int = 2, retry_delay: float = 2.0) -> Tuple[bool, str, bool]:
        """Tìm và click nút Follow

        Args:
            retry_count: Số lần retry (mặc định 2)
            retry_delay: Delay giữa các lần retry (giây)

        Returns:
            Tuple[bool, str, bool]: (success, message, not_found)
                - success: True nếu click thành công
                - message: Mô tả kết quả
                - not_found: True nếu không tìm thấy nút (cần skip job)
        """
        for attempt in range(1, retry_count + 1):
            logger.info(f"Tìm nút Follow (lần {attempt}/{retry_count})...")

            element = self.find_follow_button(timeout=retry_delay)

            if not element:
                logger.warning(f"Không tìm thấy nút Follow (lần {attempt})")
                if attempt < retry_count:
                    time.sleep(retry_delay)
                    continue
                # Hết retry vẫn không thấy → báo not_found để skip job
                return False, "Không tìm thấy nút Follow", True

            # Check đã follow chưa
            if self.is_already_followed(element):
                logger.info("Đã follow rồi")
                return False, "Đã follow rồi", False

            # Click
            if self.click_element(element):
                logger.info("Đã click nút Follow")
                return True, "Đã click nút Follow", False
            else:
                logger.warning(f"Click thất bại (lần {attempt})")
                if attempt < retry_count:
                    time.sleep(retry_delay)

        return False, "Follow thất bại sau nhiều lần thử", False

    def find_and_click_like(self, retry_count: int = 2, retry_delay: float = 2.0) -> Tuple[bool, str, bool]:
        """Tìm và click nút Like

        Args:
            retry_count: Số lần retry (mặc định 2)
            retry_delay: Delay giữa các lần retry (giây)

        Returns:
            Tuple[bool, str, bool]: (success, message, not_found)
                - success: True nếu click thành công
                - message: Mô tả kết quả
                - not_found: True nếu không tìm thấy nút (cần skip job)
        """
        import random
        # Xem video 5-12s trươc khi tha tim
        watch_time = random.randint(5, 12)
        logger.info(f"Giả lập xem video: Đợi {watch_time}s trước khi thả tim...")
        for t in range(watch_time, -1, -1):
            print(f"\r\033[36m👀 Đang xem video: Doi {t}s ...\033[0m", end="")
            time.sleep(1)
        print("\r" + " " * 50 + "\r", end="") # Clear line

        not_found_count = 0
        for attempt in range(1, retry_count + 1):
            logger.info(f"Tìm nút Like (lần {attempt}/{retry_count})...")

            element = self.find_like_button(timeout=retry_delay)

            if not element:
                not_found_count += 1
                logger.warning(f"Không tìm thấy nút Like (lần {attempt}). Thử DOUBLE TAP giữa màn hình để thả tim...")
                try:
                    # Lấy kích thước màn hình hiện tại
                    w, h = self._u2.window_size()
                    # Random 1 diem vung trung tam de tha tim
                    import random
                    cx = (w // 2) + random.randint(-100, 100)
                    cy = (h // 2) + random.randint(-150, 150)

                    # Thực hiện click 2 lần rất nhanh để kích hoạt double tap thả tim
                    self._u2.click(cx, cy)
                    time.sleep(random.uniform(0.1, 0.18))
                    self._u2.click(cx, cy)

                    logger.info("Đã kích hoạt thả tim bằng Double Tap thành công")
                    return True, "Đã thả tim thành công bằng Double Tap", False
                except Exception as e:
                    logger.error(f"Lỗi khi thực hiện double tap dự phòng: {e}")

                if attempt < retry_count:
                    time.sleep(retry_delay)
                    continue
                # Hết retry vẫn không thấy → báo not_found để skip job
                return False, "Không tìm thấy nút Like", True

            # Check đã like chưa
            if self.is_already_liked(element):
                logger.info("Đã like rồi")
                return False, "Đã like rồi", False

            # Click
            if self.click_element(element):
                logger.info("Đã click nút Like")
                return True, "Đã click nút Like", False
            else:
                logger.warning(f"Click thất bại (lần {attempt})")
                if attempt < retry_count:
                    time.sleep(retry_delay)

        return False, "Like thất bại sau nhiều lần thử", False

    def process_job(self, job_type: str) -> Tuple[bool, str, bool]:
        """Xử lý job theo type

        Args:
            job_type: Loại job ("follow" hoặc "like")

        Returns:
            Tuple[bool, str, bool]: (success, message, not_found)
                - not_found: True nếu không tìm thấy nút sau 2 lần → caller nên skip job
        """
        if not self._connected:
            if not self.connect():
                return False, "Không thể kết nối đến thiết bị", False

        # Thuc hien vuot ngau nhien truoc khi tuong tac
        logger.info("Thuc hien thao tac vuot ngau nhien (Human-like behavior)")
        self.random_swipe()

        if job_type == "follow":
            return self.find_and_click_follow()
        elif job_type == "like":
            return self.find_and_click_like()
        else:
            return False, f"Loại job không hợp lệ: {job_type}", False

    def search_user(self, username: str, timeout: float = 5.0, retry_count: int = 3) -> Tuple[bool, str]:
        """Tim kiem user TikTok qua thanh search va vao profile

        Flow:
        1. Tap search icon tren main screen
        2. Clear text + go username
        3. Tap nut Tim kiem hoac Enter
        4. Doi ket qua load
        5. Tap tab Nguoi dung
        6. Tap user dau tien
        7. Doi profile load

        Args:
            username: TikTok username can tim (co hoac khong co @)
            retry_count: So lan thu lai neu that bai

        Returns:
            Tuple[bool, str]: (success, message)
        """
        if not self._connected:
            if not self.connect():
                return False, "Không thể kết nối đến thiết bị"

        clean_username = username.lstrip('@')

        for attempt in range(1, retry_count + 1):
            logger.info(f"Tim kiem user '{clean_username}' (lan {attempt}/{retry_count})...")

            try:
                # Buoc 1: Mo man hinh search
                search_icon = self._find_element(self.SEARCH_ICON_SELECTORS, timeout=2.0)
                if search_icon:
                    self.click_element(search_icon)
                    time.sleep(0.5)
                else:
                    # Co the da o man hinh search roi, thu tim search input truc tiep
                    logger.debug("Khong tim thay search icon, thu tim search input truc tiep")

                # Buoc 2: Tim o nhap search
                search_input = self._find_element(self.SEARCH_INPUT_SELECTORS, timeout=2.0)
                if not search_input:
                    logger.warning(f"Khong tim thay o nhap search (lan {attempt})")
                    if attempt < retry_count:
                        time.sleep(1)
                        continue
                    # Try alternative search with different resource IDs
                    logger.info("Thu tim voi resource ID thay the...")
                    # Try common search input resource IDs
                    alt_search_selectors = [
                        {"resourceId": "com.zhiliaoapp.musically:id/search_input"},
                        {"resourceId": "com.ss.android.ugc.trill:id/search_input"},
                        {"resourceId": "com.zhiliaoapp.musically:id/edit_text"},
                        {"resourceId": "com.ss.android.ugc.trill:id/edit_text"},
                        {"className": "android.widget.EditText"}
                    ]
                    for selector in alt_search_selectors:
                        alt_element = self._find_element([selector], timeout=1.0)
                        if alt_element:
                            logger.info("Tim thay resource ID thay the")
                            search_input = alt_element
                            break
                    if not search_input:
                        return False, "Khong tim thay o nhap search"

                # Clear text cu
                self.click_element(search_input)
                time.sleep(0.3)
                try:
                    # Try multiple ways to clear text
                    self._u2.clear_text()
                    self._u2.press("del")
                except Exception:
                    pass
                time.sleep(0.3)

                # Buoc 3: Go username
                self._u2.send_keys(clean_username)
                time.sleep(0.5)

                # Buoc 4: Tap nut Tim kiem hoac Enter
                search_btn = self._find_element(self.SEARCH_BUTTON_SELECTORS, timeout=1.0)
                if search_btn:
                    self.click_element(search_btn)
                else:
                    self._u2.press("enter")
                time.sleep(2.0)

                # Buoc 5: Tap tab Nguoi dung
                users_tab = self._find_element(self.USERS_TAB_SELECTORS, timeout=timeout)
                if not users_tab:
                    logger.warning(f"Khong tim thay tab Nguoi dung (lan {attempt})")
                    if attempt < retry_count:
                        time.sleep(1)
                        continue
                    # Try alternative user tab selectors
                    logger.info("Thu tim tab Nguoi dung voi selector thay the...")
                    alt_user_selectors = [
                        {"text": "Users"},
                        {"text": "Người dùng"},
                        {"description": "Users"},
                        {"description": "Người dùng"}
                    ]
                    alt_users_tab = self._find_element(alt_user_selectors, timeout=1.0)
                    if alt_users_tab:
                        self.click_element(alt_users_tab)
                        users_tab = alt_users_tab
                    else:
                        return False, "Khong tim thay tab Nguoi dung"

                if users_tab:
                    self.click_element(users_tab)
                    time.sleep(1.0)

                # Buoc 6: Tap user dau tien trong danh sach
                first_user_clicked = False
                try:
                    # Cach 1: Tim element chinh xac bang ten username tren man hinh
                    user_obj = self._u2(text=clean_username)
                    if not user_obj.exists:
                        # Thu tim chua username
                        user_obj = self._u2(textContains=clean_username)
                        
                    if user_obj.exists:
                        # Tap vao element dau tien tim duoc
                        info = user_obj[0].info
                        bounds = info.get('bounds')
                        if bounds:
                            left = int(bounds.get("left", 0))
                            top = int(bounds.get("top", 0))
                            right = int(bounds.get("right", 0))
                            bottom = int(bounds.get("bottom", 0))
                            self._u2.click((left + right) // 2, (top + bottom) // 2)
                            first_user_clicked = True
                            logger.info(f"Da tap vao user chua text '{clean_username}'")
                except Exception as e:
                    logger.warning(f"Loi khi tim user theo ten: {e}")

                if not first_user_clicked:
                    # Fallback: tap vao toa do duoi tab Nguoi dung
                    try:
                        w, h = self._u2.window_size()
                        click_x = w // 2
                        click_y = 400  # Default fallback
                        
                        # Neu co bounds cua tab Nguoi dung, tap xuong duoi 150px
                        if users_tab and users_tab.bounds:
                            _, _, _, tab_bottom = users_tab.bounds
                            click_y = tab_bottom + 150
                            
                        if click_y > h: 
                            click_y = h // 2
                            
                        self._u2.click(click_x, click_y)
                        first_user_clicked = True
                        logger.info(f"Da tap user dau tien (fallback toa do: {click_x}, {click_y})")
                    except Exception as e:
                        logger.warning(f"Loi fallback tap user: {e}")

                if not first_user_clicked and attempt >= retry_count:
                    return False, "Khong tim thay user nao trong ket qua"

                # Buoc 7: Doi profile load
                time.sleep(2.0)
                logger.info(f"Da vao profile user '{clean_username}' thanh cong")
                return True, f"Da vao profile '{clean_username}'"

            except Exception as e:
                logger.error(f"Loi search_user (lan {attempt}): {e}")
                if attempt < retry_count:
                    time.sleep(1)
                continue

        return False, f"Tìm kiếm '{clean_username}' thất bại sau {retry_count} lần thử"

    def clear_search_text(self) -> bool:
        """Xóa text trong ô search về trạng thái trống

        Returns:
            bool: True nếu xóa thành công
        """
        if not self._connected:
            return False

        try:
            # Vòng lặp tối đa 3 lần để quay lại màn hình thích hợp nếu chưa thấy ô/nút tìm kiếm
            for i in range(3):
                # 1. Kiểm tra xem có ô nhập search không (đang ở màn hình kết quả hoặc nhập liệu)
                search_input = self._find_element(self.SEARCH_INPUT_SELECTORS, timeout=0.8)
                if search_input:
                    logger.debug("Tìm thấy ô nhập search, tiến hành click và xóa text.")
                    self.click_element(search_input)
                    time.sleep(0.3)
                    self._u2.clear_text()
                    return True

                # 2. Kiểm tra xem có nút tìm kiếm không (đang ở màn hình chính/feed)
                search_icon = self._find_element(self.SEARCH_ICON_SELECTORS, timeout=0.5)
                if search_icon:
                    logger.debug("Tìm thấy icon search (màn hình chính), click để mở ô nhập.")
                    self.click_element(search_icon)
                    time.sleep(0.5)
                    # Sau khi mở, kiểm tra lại ô nhập search
                    search_input = self._find_element(self.SEARCH_INPUT_SELECTORS, timeout=1.0)
                    if search_input:
                        self.click_element(search_input)
                        time.sleep(0.3)
                        self._u2.clear_text()
                        return True

                # 3. Nếu chưa thấy gì (đang ở trang cá nhân hoặc trang con khác), tiến hành back
                logger.info(f"Chưa thấy ô search hoặc icon search, đang nhấn quay lại (lần {i+1}/3)...")
                self._u2.press("back")
                time.sleep(1.0)
        except Exception as e:
            logger.debug(f"Lỗi clear search text: {e}")

        return False
