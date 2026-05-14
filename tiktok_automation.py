"""
TikTok UI Automation Module

Module này cung cấp class TikTokUIAutomator để tự động hóa các tác vụ UI trên TikTok:
- Tìm và click nút Follow
- Tìm và click nút Like
- Verify trạng thái đã follow/like

Sử dụng thư viện uiautomator2 để tương tác với UI.
"""

import time
import logging
from typing import Optional, Tuple, List
from dataclasses import dataclass

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


class TikTokUIAutomator:
    """UI Automator cho TikTok app

    Cung cấp các method để tìm và tương tác với các element trên TikTok:
    - Nút Follow/Followed
    - Nút Like (trái tim)
    """

    # Selectors cho nút Follow (chính xác hơn để tránh nhầm với Follower)
    FOLLOW_SELECTORS = [
        # Text chính xác - ưu tiên textMatches để tránh nhầm
        {"textMatches": "^Follow$"},
        {"textMatches": "^Theo dõi$"},
        {"text": "Follow"},
        {"text": "Theo dõi"},
        # Resource-id selectors (nút Follow thường có resource-id đặc biệt)
        {"resourceId": "com.zhiliaoapp.musically:id/title"},
        {"resourceId": "com.zhiliaoapp.musically:id/follow_button"},
        {"resourceId": "com.zhiliaoapp.musically:id/follow_btn"},
        {"resourceId": "com.zhiliaoapp.musically:id/follow"},
        # Content-description selectors
        {"description": "Follow"},
        {"description": "Theo dõi"},
    ]

    # Selectors cho nút Follower (để loại trừ)
    FOLLOWER_SELECTORS = [
        {"textMatches": ".*Follower.*"},
        {"textMatches": ".*Người theo dõi.*"},
        {"text": "Followers"},
        {"text": "Người theo dõi"},
    ]

    # Selectors cho nút Like
    LIKE_SELECTORS = [
        # Resource-id selectors (nút like thường có resource-id đặc biệt)
        {"resourceId": "com.zhiliaoapp.musically:id/like_container"},
        {"resourceId": "com.zhiliaoapp.musically:id/like_icon"},
        {"resourceId": "com.zhiliaoapp.musically:id/like_btn"},
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
        try:
            import uiautomator2 as u2
        except ImportError:
            logger.error("uiautomator2 chưa được cài đặt. Hãy chạy: pip install uiautomator2")
            return False

        try:
            if self.device_id:
                self._u2 = u2.connect(self.device_id)
            else:
                self._u2 = u2.connect()

            # Test kết nối
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

    def _find_element(self, selectors: List[dict], timeout: float = 2.0, exclude_follower: bool = False) -> Optional[ElementInfo]:
        """Tìm element theo danh sách selectors

        Args:
            selectors: Danh sách selectors để tìm
            timeout: Timeout tối đa (giây)
            exclude_follower: Loại trừ element Follower (cho nút Follow)

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

                        bounds = info.get("bounds")
                        return ElementInfo(
                            exists=True,
                            text=info.get("text"),
                            resource_id=info.get("resourceId"),
                            content_desc=info.get("contentDescription"),
                            bounds=(bounds.get("left", 0), bounds.get("top", 0),
                                   bounds.get("right", 0), bounds.get("bottom", 0)),
                            is_selected=info.get("selected", False)
                        )
                except Exception as e:
                    logger.debug(f"Lỗi tìm element với selector {selector}: {e}")
                    continue
            time.sleep(0.2)

        return None

    def find_follow_button(self, timeout: float = 2.0) -> Optional[ElementInfo]:
        """Tìm nút Follow (loại trừ Follower)

        Args:
            timeout: Timeout tối đa (giây)

        Returns:
            Optional[ElementInfo]: Thông tin nút Follow hoặc None
        """
        logger.debug("Đang tìm nút Follow...")
        return self._find_element(self.FOLLOW_SELECTORS, timeout, exclude_follower=True)

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
            center_x = (left + right) // 2
            center_y = (top + bottom) // 2

            logger.debug(f"Click vào tọa độ ({center_x}, {center_y})")
            self._u2.click(center_x, center_y)
            return True
        except Exception as e:
            logger.error(f"Lỗi click element: {e}")
            return False

    def find_and_click_follow(self, retry_count: int = 3, retry_delay: float = 2.0) -> Tuple[bool, str]:
        """Tìm và click nút Follow

        Args:
            retry_count: Số lần retry
            retry_delay: Delay giữa các lần retry (giây)

        Returns:
            Tuple[bool, str]: (success, message)
                - success: True nếu thành công, False nếu không
                - message: Mô tả kết quả
        """
        for attempt in range(1, retry_count + 1):
            logger.info(f"Tìm nút Follow (lần {attempt}/{retry_count})...")

            element = self.find_follow_button(timeout=retry_delay)

            if not element:
                logger.warning(f"Không tìm thấy nút Follow (lần {attempt})")
                if attempt < retry_count:
                    time.sleep(retry_delay)
                    continue
                return False, "Không tìm thấy nút Follow"

            # Check đã follow chưa
            if self.is_already_followed(element):
                logger.info("Đã follow rồi")
                return False, "Đã follow rồi"

            # Click
            if self.click_element(element):
                logger.info("Đã click nút Follow")
                return True, "Đã click nút Follow"
            else:
                logger.warning(f"Click thất bại (lần {attempt})")
                if attempt < retry_count:
                    time.sleep(retry_delay)

        return False, "Follow thất bại sau nhiều lần thử"

    def find_and_click_like(self, retry_count: int = 3, retry_delay: float = 2.0) -> Tuple[bool, str]:
        """Tìm và click nút Like

        Args:
            retry_count: Số lần retry
            retry_delay: Delay giữa các lần retry (giây)

        Returns:
            Tuple[bool, str]: (success, message)
                - success: True nếu thành công, False nếu không
                - message: Mô tả kết quả
        """
        for attempt in range(1, retry_count + 1):
            logger.info(f"Tìm nút Like (lần {attempt}/{retry_count})...")

            element = self.find_like_button(timeout=retry_delay)

            if not element:
                logger.warning(f"Không tìm thấy nút Like (lần {attempt}). Thử DOUBLE TAP giữa màn hình để thả tim...")
                try:
                    # Lấy kích thước màn hình hiện tại
                    w, h = self._u2.window_size()
                    cx, cy = w // 2, h // 2
                    
                    # Thực hiện click 2 lần rất nhanh để kích hoạt double tap thả tim
                    self._u2.click(cx, cy)
                    time.sleep(0.15)
                    self._u2.click(cx, cy)
                    
                    logger.info("Đã kích hoạt thả tim bằng Double Tap thành công")
                    return True, "Đã thả tim thành công bằng Double Tap"
                except Exception as e:
                    logger.error(f"Lỗi khi thực hiện double tap dự phòng: {e}")

                if attempt < retry_count:
                    time.sleep(retry_delay)
                    continue
                return False, "Không tìm thấy nút Like"

            # Check đã like chưa
            if self.is_already_liked(element):
                logger.info("Đã like rồi")
                return False, "Đã like rồi"

            # Click
            if self.click_element(element):
                logger.info("Đã click nút Like")
                return True, "Đã click nút Like"
            else:
                logger.warning(f"Click thất bại (lần {attempt})")
                if attempt < retry_count:
                    time.sleep(retry_delay)

        return False, "Like thất bại sau nhiều lần thử"

    def process_job(self, job_type: str) -> Tuple[bool, str]:
        """Xử lý job theo type

        Args:
            job_type: Loại job ("follow" hoặc "like")

        Returns:
            Tuple[bool, str]: (success, message)
        """
        if not self._connected:
            if not self.connect():
                return False, "Không thể kết nối đến thiết bị"

        if job_type == "follow":
            return self.find_and_click_follow()
        elif job_type == "like":
            return self.find_and_click_like()
        else:
            return False, f"Loại job không hợp lệ: {job_type}"
