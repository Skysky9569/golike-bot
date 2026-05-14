"""
TikTok Automation Bot - Refactored Version
Bot tự động thực hiện jobs từ Golike.net trên TikTok
"""

from selenium import webdriver as selenium_driver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager
import time
import cv2
import numpy as np
import subprocess
import sys
import os
import re
import requests
import json
from datetime import datetime
from typing import Optional, Tuple, List
from dataclasses import dataclass, field
from enum import Enum
import logging
import io

# Set console encoding to UTF-8 for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ],
    force=True
)
logger = logging.getLogger(__name__)


class JobType(Enum):
    """Enum for job types"""
    FOLLOW = "FOLLOW"
    LIKE = "LIKE"
    COMMENT = "CMT"
    UNKNOWN = "UNKNOWN"


class AccountStatus(Enum):
    """Enum for TikTok account status"""
    VALID = "sky"
    BANNED = "jack"
    UNKNOWN = "unknown"


@dataclass
class AccountConfig:
    """Configuration for account settings"""
    username: str
    password: str
    screen_name: str
    window_x: int


@dataclass
class JobResult:
    """Result of a job execution"""
    job_id: Optional[str] = None
    money: Optional[str] = None
    url: Optional[str] = None
    status: AccountStatus = AccountStatus.VALID
    job_type: JobType = JobType.UNKNOWN
    device: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))


@dataclass
class BotState:
    """State tracking for the bot"""
    jobs_completed: int = 0
    jobs_skipped: int = 0
    total_money: int = 0
    current_account: Optional[str] = None

    def save(self, file_path: str = "bot_state.json"):
        """Save state to file"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump({
                    "jobs_completed": self.jobs_completed,
                    "jobs_skipped": self.jobs_skipped,
                    "total_money": self.total_money,
                    "current_account": self.current_account
                }, f, indent=2)
            logger.info(f"Đã lưu state vào {file_path}")
        except Exception as e:
            logger.error(f"Lỗi lưu state: {e}")

    @classmethod
    def load(cls, file_path: str = "bot_state.json") -> Optional["BotState"]:
        """Load state from file"""
        try:
            if not os.path.exists(file_path):
                return None
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return cls(
                    jobs_completed=data.get("jobs_completed", 0),
                    jobs_skipped=data.get("jobs_skipped", 0),
                    total_money=data.get("total_money", 0),
                    current_account=data.get("current_account")
                )
        except Exception as e:
            logger.error(f"Lỗi load state: {e}")
            return None


# Account configurations
ACCOUNT_CONFIGS = {
    1: AccountConfig(
        username="DOM",
        password="DOM",
        screen_name="screen1.png",
        window_x=100
    ),
    2: AccountConfig(
        username="DOM",
        password="DOM",
        screen_name="screen2.png",
        window_x=600
    )
}

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN", "DOM")
TELEGRAM_CHAT_ID = os.getenv("CHAT_ID", "DOM")

# Constants
IMAGE_MATCH_THRESHOLD = 0.5
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT = 10
ADB_TIMEOUT = 10

# Wait time constants
WAIT_FOR_PAGE_LOAD = 2
WAIT_FOR_TIKTOK_LOAD = 10
WAIT_FOR_TAB_SWITCH = 2
WAIT_FOR_JOB_RECEIVE = 3
WAIT_FOR_ACTION_DELAY = 3
WAIT_FOR_COMPLETE_DELAY = 4
WAIT_FOR_NEXT_JOB = 3
WAIT_FOR_RETRY_DELAY = 7


class ChromeDriver:
    """Chrome browser driver with anti-detection setup"""

    def __init__(self, headless: bool = False):
        self.driver = self._create_driver(headless)

    def _create_driver(self, headless: bool) -> selenium_driver.Chrome:
        """Create Chrome driver with anti-detection options"""
        options = Options()
        options.add_argument("--lang=en-US")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--log-level=3")

        if headless:
            options.add_argument("--headless=new")

        driver = selenium_driver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        # Hide webdriver property
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined })
            """
        })

        return driver

    def set_window_position(self, x: int, y: int, width: int = 500, height: int = 700):
        """Set window position and size"""
        self.driver.set_window_size(width, height)
        self.driver.set_window_position(x, y)


class ADBManager:
    """Manager for ADB device operations"""

    def __init__(self):
        self.selected_device: Optional[str] = None
        self.adb_path = self._find_adb_path()

    def _find_adb_path(self) -> str:
        """Find adb executable path, prioritizing local project ADB folder"""
        # 1. Try local project ADB folder relative to current working dir
        local_path = os.path.join(os.getcwd(), "ADB", "adb.exe")
        if os.path.exists(local_path):
            logger.info(f"Sử dụng local ADB: {local_path}")
            return local_path
            
        # 2. Try common absolute paths used in this workspace
        common_path = r"D:\pythonadb\ADB\adb.exe"
        if os.path.exists(common_path):
            logger.info(f"Sử dụng ADB path: {common_path}")
            return common_path

        # 3. Default to system "adb" (requires system PATH configuration)
        logger.warning("Không tìm thấy local adb.exe, sử dụng system adb...")
        return "adb"

    def check_connected_devices(self) -> List[str]:
        """Check and return list of connected ADB devices"""
        try:
            result = subprocess.run(
                [self.adb_path, "devices"],
                capture_output=True,
                text=True,
                timeout=ADB_TIMEOUT
            )
            output = result.stdout.strip().splitlines()
            devices = [line.split()[0] for line in output[1:] if line.strip() and "device" in line]
            return devices
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.error(f"ADB error: {e}")
            return []

    def select_device(self) -> Optional[str]:
        """Interactive device selection"""
        devices = self.check_connected_devices()

        if not devices:
            logger.error("Không có thiết bị ADB nào được kết nối.")
            return None

        logger.info("Thiết bị ADB đang kết nối:")
        for i, device in enumerate(devices, start=1):
            logger.info(f"{i}. {device}")

        while True:
            try:
                choice = int(input("👉 Chọn số thiết bị để kết nối: "))
                if 1 <= choice <= len(devices):
                    self.selected_device = devices[choice - 1]
                    logger.info(f"🔌 Đã chọn thiết bị: {self.selected_device}")
                    return self.selected_device
                else:
                    logger.warning("⚠️ Lựa chọn không hợp lệ, thử lại.")
            except ValueError:
                logger.warning("⚠️ Vui lòng nhập số hợp lệ.")
            except KeyboardInterrupt:
                logger.info("Đã hủy chọn thiết bị.")
                return None

    def open_url(self, url: str) -> bool:
        """Open URL on Android device"""
        if not self.selected_device:
            logger.error("Chưa chọn thiết bị.")
            return False

        try:
            result = subprocess.run(
                [self.adb_path, "-s", self.selected_device, "shell", "am", "start", "-a",
                 "android.intent.action.VIEW", "-d", url],
                capture_output=True,
                text=True,
                timeout=ADB_TIMEOUT
            )

            if result.returncode == 0:
                logger.info(f"✅ Đã mở link trên điện thoại: {url}")
                return True
            else:
                logger.error(f"❌ ADB lỗi: {result.stderr.strip()}")
                return False
        except subprocess.TimeoutExpired:
            logger.error("❌ Timeout khi mở link.")
            return False
        except Exception as e:
            logger.error(f"❌ Lỗi khi gửi link: {e}")
            return False

    def take_screenshot(self, output_path: str) -> bool:
        """Take screenshot from Android device"""
        if not self.selected_device:
            logger.error("Chưa chọn thiết bị.")
            return False

        try:
            subprocess.run(
                [self.adb_path, "-s", self.selected_device, "shell", "screencap", "-p", f"/sdcard/{output_path}"],
                check=True,
                timeout=ADB_TIMEOUT
            )
            subprocess.run(
                [self.adb_path, "-s", self.selected_device, "pull", f"/sdcard/{output_path}", output_path],
                check=True,
                timeout=ADB_TIMEOUT
            )
            logger.info(f"📸 Đã chụp màn hình: {output_path}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Lỗi chụp màn hình: {e}")
            return False
        except subprocess.TimeoutExpired:
            logger.error("❌ Timeout khi chụp màn hình.")
            return False

    def tap(self, x: int, y: int) -> bool:
        """Tap at coordinates on Android device"""
        if not self.selected_device:
            logger.error("Chưa chọn thiết bị.")
            return False

        try:
            subprocess.run(
                [self.adb_path, "-s", self.selected_device, "shell", "input", "tap", str(x), str(y)],
                check=True,
                timeout=5
            )
            logger.info(f"✅ Đã tap tại ({x}, {y})")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Lỗi tap: {e}")
            return False


class ImageMatcher:
    """Image matching for UI element detection"""

    @staticmethod
    def match_and_click(
        needle_path: str,
        haystack_path: str,
        label: str,
        adb_manager: ADBManager,
        threshold: float = IMAGE_MATCH_THRESHOLD
    ) -> bool:
        """Match template image and click on matched position"""
        try:
            needle = cv2.imread(needle_path)
            haystack = cv2.imread(haystack_path)

            if needle is None:
                logger.error(f"❌ Không đọc được file mẫu: {needle_path}")
                return False
            if haystack is None:
                logger.error(f"❌ Không đọc được màn hình: {haystack_path}")
                return False

            h, w = needle.shape[:2]
            result = cv2.matchTemplate(haystack, needle, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            logger.info(f"🔍 Độ khớp với {label}: {max_val:.2f}")

            if max_val >= threshold:
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                adb_manager.tap(center_x, center_y)
                logger.info(f"✅ Đã click vào nút {label} tại ({center_x}, {center_y})")
                return True
            else:
                logger.warning(f"⚠️ Không đủ độ khớp với {label} (chỉ {max_val:.2f})")
                return False

        except Exception as e:
            logger.error(f"❌ Lỗi matching ảnh: {e}")
            return False


class TelegramNotifier:
    """Telegram notification handler"""

    @staticmethod
    def send_message(message: str) -> bool:
        """Send message via Telegram bot"""
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }

        try:
            resp = requests.post(url, data=payload, timeout=15)
            resp.raise_for_status()
            logger.info("Đã gửi thông báo Telegram")
            return True
        except requests.RequestException as e:
            logger.error(f"❌ Lỗi gửi Telegram: {e}")
            return False


class GolikeBot:
    """Main bot for Golike automation"""

    def __init__(self, account_config: AccountConfig):
        self.config = account_config
        self.chrome = ChromeDriver()
        self.adb = ADBManager()
        self.state = BotState()
        self.image_matcher = ImageMatcher()
        self.telegram = TelegramNotifier()

    def login(self) -> bool:
        """Login to Golike"""
        try:
            logger.info("Đang đăng nhập...")
            self.chrome.driver.get("https://app.golike.net/login")

            # Wait for form to load
            WebDriverWait(self.chrome.driver, DEFAULT_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "form"))
            )

            # Fill username
            username_input = self.chrome.driver.find_element(
                By.XPATH,
                "/html/body/div[1]/div/div[1]/div/form/div[1]/input"
            )
            username_input.click()
            username_input.send_keys(self.config.username)

            # Fill password
            password_input = self.chrome.driver.find_element(
                By.XPATH,
                "/html/body/div[1]/div/div[1]/div/form/div[2]/div/input"
            )
            password_input.click()
            password_input.send_keys(self.config.password)

            # Click login button
            login_button = self.chrome.driver.find_element(
                By.XPATH,
                "/html/body/div[1]/div/div[1]/div/form/div[3]/button"
            )
            login_button.click()

            logger.info("Đã click nút đăng nhập")
            input("Nhấn Enter sau khi giải captcha xong: ")
            logger.info("Đã đăng nhập thành công")
            return True

        except TimeoutException:
            logger.error("Timeout khi tải trang đăng nhập")
            return False
        except NoSuchElementException as e:
            logger.error(f"Không tìm thấy element: {e}")
            return False
        except Exception as e:
            logger.error(f"Lỗi đăng nhập: {e}")
            return False

    def get_account_balance(self) -> Optional[Tuple[str, str, str]]:
        """Get account balance information"""
        try:
            so_du = WebDriverWait(self.chrome.driver, DEFAULT_TIMEOUT).until(
                EC.presence_of_element_located((By.CLASS_NAME, "current_coin"))
            ).text.strip()

            cho_duyet = self.chrome.driver.find_element(By.CLASS_NAME, "pending_coin").text.strip()
            can_lam_lai = self.chrome.driver.find_element(By.CLASS_NAME, "hold_coin").text.strip()

            logger.info("=== Thông tin tài khoản ===")
            logger.info(f"💰 Số dư      : {so_du}")
            logger.info(f"⏳ Chờ duyệt  : {cho_duyet}")
            logger.info(f"🔄 Cần làm lại: {can_lam_lai}")
            logger.info("========================")

            return so_du, cho_duyet, can_lam_lai

        except TimeoutException:
            logger.error("Timeout khi lấy thông tin tài khoản")
            return None
        except NoSuchElementException as e:
            logger.error(f"Không tìm thấy element: {e}")
            return None

    def select_account(self) -> bool:
        """Select TikTok account to work with"""
        try:
            try:
                WebDriverWait(self.chrome.driver, DEFAULT_TIMEOUT).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#cheatModal > div > div > div > div > div > button"))
                ).click()
                logger.info("Đã ấn đã hiểu....")
            except (NoSuchElementException, TimeoutException):
                logger.info("Ko có nút đã hiểu...")
                pass
            
            logger.info("Đang chọn tài khoản...")
            # Click to open account selection
            WebDriverWait(self.chrome.driver, DEFAULT_TIMEOUT).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div/div[2]/div/div/div[2]"))
            ).click()

            time.sleep(WAIT_FOR_PAGE_LOAD)

            # Navigate to account selection
            WebDriverWait(self.chrome.driver, DEFAULT_TIMEOUT).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#app > div > div:nth-child(1) > div.page-container > div.job-grid > div:nth-child(3) > div > h6"))
            ).click()

            time.sleep(WAIT_FOR_PAGE_LOAD)

            # Click account dropdown
            WebDriverWait(self.chrome.driver, DEFAULT_TIMEOUT).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#app > div > div:nth-child(1) > div.page-container > div.card.mt-2 > div > div > div.col-5.pr-0 > h6"))
            ).click()

            time.sleep(WAIT_FOR_PAGE_LOAD)


            # Get list of accounts
            usernames = self.chrome.driver.find_elements(By.CSS_SELECTOR, "div.col-8.pl-3.pr-0 > span")

            logger.info("🔍 Danh sách tài khoản:")
            for i, u in enumerate(usernames):
                logger.info(f"{i + 1}. {u.text.strip()}")

            try:
                choice = int(input("👉 Nhập số tài khoản để chạy: ")) - 1
                if 0 <= choice < len(usernames):
                    usernames[choice].click()
                    self.state.current_account = usernames[choice].text
                    logger.info(f"✅ Đã chọn: {self.state.current_account}")
                    return True
                else:
                    logger.error("❌ Số không hợp lệ.")
                    return False
            except ValueError:
                logger.error("❌ Vui lòng nhập số.")
                return False

        except TimeoutException:
            logger.error("Timeout khi chọn tài khoản")
            return False
        except Exception as e:
            logger.error(f"Lỗi chọn tài khoản: {e}")
            return False

    def receive_job(self) -> bool:
        """Receive job from platform"""
        try:
            logger.info("Đang nhận job...")

            # Click receive job button
            receive_btn = WebDriverWait(self.chrome.driver, DEFAULT_TIMEOUT).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div/div[1]/div[2]/div[2]/div[2]/div/div/div/div[2]/div"))
            )
            receive_btn.click()

            time.sleep(WAIT_FOR_JOB_RECEIVE)

            # Handle load job popup if present
            self._handle_load_job_popup()

            # Try to skip caution if present
            self._skip_caution()

            # Wait for toast message
            try:
                toast = WebDriverWait(self.chrome.driver, 20).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, ".toast-message"))
                ).text
                logger.info(f"📢 {toast}")
            except TimeoutException:
                logger.info("Không có thông báo toast")

            return True

        except TimeoutException:
            logger.error("Timeout khi nhận job")
            return False
        except Exception as e:
            logger.error(f"Lỗi nhận job: {e}")
            return False

    def _handle_load_job_popup(self) -> None:
        """Handle load job popup if present"""
        try:
            content_elements = self.chrome.driver.find_elements(By.ID, "swal2-content")
            for el in content_elements:
                if "Hệ thống đang tính toán jobs dành cho bạn" in el.text:
                    logger.info("Phát hiện popup load job")
                    try:
                        ok_btn = self.chrome.driver.find_element(By.CLASS_NAME, "swal2-confirm")
                        ok_btn.click()
                        logger.info("Đã click OK popup")
                        time.sleep(WAIT_FOR_PAGE_LOAD)

                        # Click receive job again
                        receive_btn = self.chrome.driver.find_element(
                            By.XPATH, "/html/body/div[1]/div/div[1]/div[2]/div[2]/div[2]/div/div/div/div[2]/div"
                        )
                        receive_btn.click()
                    except NoSuchElementException:
                        logger.warning("Không tìm thấy nút OK")
        except Exception as e:
            logger.debug(f"Không có popup load job: {e}")

    def _skip_caution(self) -> None:
        """Skip caution popup if present"""
        try:
            skip_checkbox = self.chrome.driver.find_element(
                By.XPATH, "/html/body/div[1]/div/div[1]/div[2]/div[2]/div[4]/div/div/div[2]/label/input"
            )
            skip_checkbox.click()

            skip_button = self.chrome.driver.find_element(
                By.XPATH, "/html/body/div[1]/div/div[1]/div[2]/div[2]/div[4]/div/div/div[3]/button[2]"
            )
            skip_button.click()
            logger.info("Đã skip caution")
        except NoSuchElementException:
            logger.debug("Không có caution popup")

    def get_job_type(self) -> JobType:
        """Get current job type"""
        try:
            job_text = WebDriverWait(self.chrome.driver, DEFAULT_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.ml-1.d400.font-weight-bold"))
            ).text.strip()

            if "TĂNG LƯỢT THEO DÕI" in job_text:
                logger.info(f"Loại job: FOLLOW")
                return JobType.FOLLOW
            elif "TĂNG LƯỢT COMMENT" in job_text:
                logger.info(f"Loại job: COMMENT")
                # Send Telegram notification for comment job
                message = f"📝 Phát hiện job COMMENT | Acc: {self.state.current_account}"
                self.telegram.send_message(message)
                input("Job comment - Nhấn Enter sau khi comment xong: ")
                return JobType.COMMENT
            elif "TĂNG LIKE CHO BÀI VIẾT" in job_text:
                logger.info(f"Loại job: LIKE")
                return JobType.LIKE
            else:
                logger.warning(f"Loại job không xác định: {job_text}")
                return JobType.UNKNOWN

        except TimeoutException:
            logger.error("Timeout khi lấy loại job")
            return JobType.UNKNOWN
        except Exception as e:
            logger.error(f"Lỗi lấy loại job: {e}")
            return JobType.UNKNOWN

    def get_job_id(self) -> Optional[str]:
        """Get current job ID"""
        try:
            job_id_element = self.chrome.driver.find_element(
                By.XPATH, "//div[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'job id')]/b"
            )
            job_id = job_id_element.text.strip()
            logger.info(f"Job ID: {job_id}")
            return job_id
        except NoSuchElementException:
            logger.warning("Không tìm thấy Job ID")
            return None

    def get_job_money(self) -> Optional[str]:
        """Get money reward for current job"""
        try:
            money_element = self.chrome.driver.find_element(
                By.XPATH, "//span[@class='money-return']//span[@class='font-bold']"
            )
            money_text = money_element.text
            logger.info(f"Đớp được: {money_text}")

            # Extract number and update total
            money_match = re.search(r'\d+', money_text)
            if money_match:
                money_value = int(money_match.group())
                self.state.total_money += money_value
                logger.info(f"💰 Tổng đã đớp: {self.state.total_money}VND")

            return money_text
        except NoSuchElementException:
            logger.warning("Không tìm thấy tiền thưởng")
            return None

    def check_tiktok_account(self, url: str) -> AccountStatus:
        """Check if TikTok account is valid"""
        try:
            logger.info(f"Đang check link: {url}")

            # Open in new tab
            original_window = self.chrome.driver.current_window_handle
            self.chrome.driver.execute_script("window.open('');")
            new_tab = [tab for tab in self.chrome.driver.window_handles if tab != original_window][0]
            self.chrome.driver.switch_to.window(new_tab)

            self.chrome.driver.get(url)
            time.sleep(WAIT_FOR_TIKTOK_LOAD)

            # Check for account status
            try:
                status_element = self.chrome.driver.find_element(By.XPATH, '//p[contains(text(), "account")]')
                status_text = status_element.text.lower()

                if "this account" in status_text:
                    logger.warning("⚠️ Acc bị jack")
                    return AccountStatus.BANNED
                else:
                    logger.info("✅ Acc bình thường")
                    return AccountStatus.VALID
            except NoSuchElementException:
                logger.info("✅ Acc bình thường (không có thông báo)")
                return AccountStatus.VALID

        except Exception as e:
            logger.error(f"Lỗi check TikTok account: {e}")
            return AccountStatus.UNKNOWN
        finally:
            # Close new tab and switch back
            try:
                if len(self.chrome.driver.window_handles) > 1:
                    self.chrome.driver.close()
                    self.chrome.driver.switch_to.window(original_window)
            except Exception as e:
                logger.warning(f"Lỗi đóng tab: {e}")

    def perform_action(self, url: str, job_type: JobType) -> bool:
        """Perform action on Android device"""
        try:
            # Send link to device
            if not self.adb.open_url(url):
                logger.error("Không thể mở link trên thiết bị")
                return False

            time.sleep(WAIT_FOR_TIKTOK_LOAD)

            # Take screenshot
            if not self.adb.take_screenshot(self.config.screen_name):
                logger.error("Không thể chụp màn hình")
                return False

            # Match and click buttons
            found = (
                self.image_matcher.match_and_click("screen.png", self.config.screen_name, "Follow", self.adb)
                or self.image_matcher.match_and_click("tim.png", self.config.screen_name, "Tim", self.adb)
            )

            if not found:
                logger.warning("⚠️ Không tìm thấy nút Follow hoặc Tim")
                return False

            return True

        except Exception as e:
            logger.error(f"Lỗi thực hiện action: {e}")
            return False

    def click_menu_button(self, choice: int) -> bool:
        """Click menu button by keyword or index"""
        try:
            js_get_buttons = """
            const buttons = document.querySelectorAll('a.btn, button.btn');
            let data = [];
            buttons.forEach((btn, index) => {
                data.push({index: index, text: btn.innerText.trim()});
            });
            return data;
            """
            buttons = self.chrome.driver.execute_script(js_get_buttons)

            logger.info("=== MENU ===")
            for i, btn in enumerate(buttons):
                logger.info(f"{i + 1}. {btn['text']}")

            keyword_map = {
                1: "tiktok",
                2: "hoàn thành",
                3: "báo lỗi",
                4: "gửi báo cáo"
            }

            if choice in keyword_map:
                keyword = keyword_map[choice].lower()
                matched = next((btn for btn in buttons if keyword in btn["text"].lower()), None)
                if matched:
                    self.chrome.driver.execute_script(
                        f"document.querySelectorAll('a.btn, button.btn')[{matched['index']}].click();"
                    )
                    logger.info(f"✅ Đã click vào: {matched['text']}")
                    return True
                else:
                    logger.warning(f"❌ Không tìm thấy nút chứa: '{keyword}'")
                    return False
            else:
                idx = choice - 1
                if 0 <= idx < len(buttons):
                    self.chrome.driver.execute_script(
                        f"document.querySelectorAll('a.btn, button.btn')[{idx}].click();"
                    )
                    logger.info(f"✅ Đã click vào mục số {choice}. ({buttons[idx]['text']})")
                    return True
                else:
                    logger.warning(f"❌ Không có nút tương ứng vị trí {choice}")
                    return False

        except Exception as e:
            logger.error(f"Lỗi click menu: {e}")
            return False

    def complete_job(self) -> bool:
        """Complete job and handle result"""
        retry = 0

        while retry < MAX_RETRY_ATTEMPTS:
            try:
                time.sleep(4)

                title_elements = self.chrome.driver.find_elements(By.ID, "swal2-title")
                content_elements = self.chrome.driver.find_elements(By.ID, "swal2-content")

                if not title_elements:
                    logger.info("Không thấy popup")
                    return False

                for title, content in zip(title_elements, content_elements):
                    title_text = title.text.strip()
                    content_text = content.text.strip()

                    logger.info(f"Popup: {title_text}")

                    # Handle error popup
                    if "Lỗi" in title_text:
                        retry += 1
                        logger.warning(f"Lỗi lần thứ {retry} / {MAX_RETRY_ATTEMPTS}")

                        # Click OK
                        self._click_ok_button()

                        time.sleep(1)

                        # Click complete again
                        self.click_menu_button(2)
                        logger.info("Đã click lại Hoàn thành")
                        time.sleep(WAIT_FOR_RETRY_DELAY)
                        break

                    # Handle success popup
                    elif "Báo cáo thành công" in content_text:
                        match = re.search(r"Số jobs đã làm trong ngày\s+(\d+)", content_text)
                        if match:
                            jobs_count = int(match.group(1))
                            logger.info(f"Số jobs trong ngày: {jobs_count}")

                        # Click OK
                        self._click_ok_button()
                        logger.info("Đã click OK sau báo cáo thành công")

                        return True

                else:
                    logger.info("Hoàn thành thành công ✅ (popup khác)")
                    return True

            except Exception as e:
                logger.error(f"Lỗi xử lý popup: {e}")
                return False

        # Max retries reached
        logger.warning("Thử 3 lần vẫn thất bại ❌")
        self.click_menu_button(3)  # Báo lỗi
        self.click_menu_button(4)  # Gửi báo cáo
        self.state.jobs_skipped += 1
        self._click_ok_button()
        return False

    def _click_ok_button(self) -> None:
        """Click OK button in popup"""
        try:
            ok_btn = self.chrome.driver.find_element(By.CLASS_NAME, "swal2-confirm")
            ok_btn.click()
            logger.info("Đã click OK popup")
        except NoSuchElementException:
            try:
                self.chrome.driver.execute_script(
                    "document.querySelector('button.swal2-confirm.swal2-styled').click();"
                )
            except Exception:
                logger.warning("Không thể click OK")

    def log_job_result(self, result: JobResult) -> None:
        """Log job result to file"""
        try:
            with open("id.txt", "a", encoding="utf-8") as f:
                f.write(
                    f"{result.timestamp} | ID:{result.job_id} | {result.money} | "
                    f"{result.url} | {result.status.value} | {result.job_type.value} | "
                    f"{result.device}\n"
                )
            logger.info("Đã ghi log job")
        except Exception as e:
            logger.error(f"Lỗi ghi log: {e}")

    def _get_tiktok_url_and_check(self) -> Optional[str]:
        """Click TikTok button and get the TikTok URL"""
        original_window = self.chrome.driver.current_window_handle

        try:
            # Click TikTok button
            tiktok_btn = WebDriverWait(self.chrome.driver, DEFAULT_TIMEOUT).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'TikTok')]"))
            )
            tiktok_btn.click()
            logger.info("Đã click vào TikTok")

            # Wait for new tab to open
            time.sleep(WAIT_FOR_TAB_SWITCH)

            # Switch to new tab
            WebDriverWait(self.chrome.driver, 10).until(lambda d: len(d.window_handles) > 1)
            new_tab = [tab for tab in self.chrome.driver.window_handles if tab != original_window][0]
            self.chrome.driver.switch_to.window(new_tab)

            # Wait for TikTok to load
            time.sleep(WAIT_FOR_PAGE_LOAD)

            # Get TikTok URL
            tiktok_url = self.chrome.driver.current_url

            # Check if it's a valid TikTok URL
            if "tiktok.com" not in tiktok_url.lower():
                logger.warning(f"URL không phải TikTok: {tiktok_url}")
                time.sleep(WAIT_FOR_PAGE_LOAD)  # Wait a bit more
                tiktok_url = self.chrome.driver.current_url

            # Close new tab and switch back
            self.chrome.driver.close()
            self.chrome.driver.switch_to.window(original_window)

            return tiktok_url

        except TimeoutException:
            logger.warning("Timeout khi mở TikTok")
            return None
        except Exception as e:
            logger.error(f"Lỗi lấy TikTok URL: {e}")
            # Try to switch back to original window
            try:
                if len(self.chrome.driver.window_handles) > 1:
                    self.chrome.driver.close()
                self.chrome.driver.switch_to.window(original_window)
            except (NoSuchElementException, TimeoutException):
                pass
            return None

    def run_job_loop(self) -> None:
        """Main job execution loop"""
        logger.info("=== BẮT ĐẦU VÒNG LẶP JOB ===")

        while True:
            try:
                # Receive job
                if not self.receive_job():
                    logger.error("Không thể nhận job, thử lại sau...")
                    time.sleep(5)
                    continue

                logger.info("Đã nhận job")

                # Get job type
                job_type = self.get_job_type()

                if job_type == JobType.COMMENT:
                    logger.info("Job type: COMMENT - đã xử lý thủ công")

                # Get TikTok URL and check account
                current_url = self._get_tiktok_url_and_check()

                if not current_url:
                    logger.error("Không thể lấy link TikTok")
                    time.sleep(5)
                    continue

                logger.info(f"TikTok URL: {current_url}")

                # Check account status
                account_status = self.check_tiktok_account(current_url)

                # Create job result
                result = JobResult(
                    url=current_url,
                    status=account_status,
                    job_type=job_type,
                    device=self.adb.selected_device
                )

                if account_status == AccountStatus.VALID:
                    # Perform action
                    if self.perform_action(current_url, job_type):
                        # Get job details
                        result.job_id = self.get_job_id()
                        result.money = self.get_job_money()

                        # Complete job
                        time.sleep(WAIT_FOR_ACTION_DELAY)
                        self.click_menu_button(2)  # Hoàn thành
                        time.sleep(WAIT_FOR_COMPLETE_DELAY)

                        if self.complete_job():
                            self.state.jobs_completed += 1
                            logger.info(
                                f"✅ Job hoàn thành | Tổng: {self.state.jobs_completed} | "
                                f"Skip: {self.state.jobs_skipped}"
                            )
                        else:
                            logger.warning("❌ Job không hoàn thành")
                else:
                    # Account is banned, skip job
                    logger.warning("⚠️ Skip job do account bị jack")
                    self.click_menu_button(3)  # Báo lỗi
                    self.click_menu_button(4)  # Gửi báo cáo
                    self.state.jobs_skipped += 1

                    time.sleep(5)
                    self._click_ok_button()

                # Log result
                self.log_job_result(result)

                # Small delay before next job
                time.sleep(WAIT_FOR_NEXT_JOB)

            except KeyboardInterrupt:
                logger.info("Đã dừng bot bởi người dùng")
                break
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp: {e}")
                time.sleep(5)

    def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            # Save state before cleanup
            self.state.save()
            if hasattr(self, 'chrome') and self.chrome.driver:
                self.chrome.driver.quit()
                logger.info("Đã đóng Chrome driver")
        except Exception as e:
            logger.error(f"Lỗi cleanup: {e}")


def main() -> None:
    """Main entry point"""
    try:
        # Clear screen
        os.system('cls' if os.name == 'nt' else 'clear')

        # Load previous state
        previous_state = BotState.load()
        if previous_state:
            print("=== THÔNG TIN LẦN CHẠY TRƯỚC ===")
            print(f"💰 Tổng tiền đã đớp: {previous_state.total_money}VND")
            print(f"✅ Jobs đã làm: {previous_state.jobs_completed}")
            print(f"⏭️ Jobs skip: {previous_state.jobs_skipped}")
            print(f"👤 Tài khoản: {previous_state.current_account or 'N/A'}")
            print("============================")

            while True:
                choice = input("Tiếp tục từ lần chạy trước? (y/n): ").strip().lower()
                if choice in ['y', 'yes', 'có']:
                    use_previous_state = True
                    break
                elif choice in ['n', 'no', 'không']:
                    use_previous_state = False
                    break
                else:
                    print("⚠️ Vui lòng nhập y hoặc n")
        else:
            use_previous_state = False
            print("Không tìm thấy state lần chạy trước, bắt đầu mới.")

        # Select account configuration
        print("\n=== TIKTOK AUTOMATION BOT ===")
        print("Chọn cấu hình tài khoản:")
        print("1. Tài khoản 1")
        print("2. Tài khoản 2")

        while True:
            try:
                choice = int(input("Chọn setting 1 hay 2: "))
                if choice in ACCOUNT_CONFIGS:
                    config = ACCOUNT_CONFIGS[choice]
                    logger.info(f"Đã chọn: {config.username} | {config.screen_name} | x={config.window_x}")
                    break
                else:
                    print("⚠️ Lựa chọn không hợp lệ")
            except ValueError:
                print("⚠️ Vui lòng nhập số")

        # Select ADB device
        adb_manager = ADBManager()
        if not adb_manager.select_device():
            logger.error("Không thể chọn thiết bị ADB")
            return

        # Initialize bot
        bot = GolikeBot(config)
        bot.adb = adb_manager  # Share ADB manager

        # Load previous state if user chose to continue
        if use_previous_state and previous_state:
            bot.state = previous_state
            logger.info(f"Đã load state: {bot.state.total_money}VND, {bot.state.jobs_completed} jobs")

        # Setup window position
        bot.chrome.set_window_position(config.window_x, 40)

        # Login
        if not bot.login():
            logger.error("Đăng nhập thất bại")
            return

        # Get account balance
        bot.get_account_balance()

        # Select account
        if not bot.select_account():
            logger.error("Chọn tài khoản thất bại")
            return

        # Run job loop
        bot.run_job_loop()

    except KeyboardInterrupt:
        logger.info("Đã dừng bởi người dùng")
    except Exception as e:
        logger.error(f"Lỗi chính: {e}")
    finally:
        if 'bot' in locals():
            bot.cleanup()


if __name__ == "__main__":
    main()
