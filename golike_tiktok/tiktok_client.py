"""
TikTok Job Processor
Xử lý các job TikTok từ API Golike với direct API calls
"""
import time
from typing import Optional, Dict, Any, List
from golike_core.api_client import GolikeAPIClient
from golike_core.logging import logger

# Import UI automation module
try:
    from tiktok_automation import TikTokUIAutomator
    UI_AUTOMATION_AVAILABLE = True
except ImportError:
    UI_AUTOMATION_AVAILABLE = False
    logger.warning("tiktok_automation module không khả dụng. UI automation sẽ bị tắt.")


class TikTokJobProcessor:
    """Processor cho TikTok jobs

    Xử lý việc lấy job, thực hiện job và hoàn thành job
    với proper error handling và retry logic.
    """

    def __init__(self, api_client: GolikeAPIClient, account_id: str, device_id: Optional[str] = None):
        """Khởi tạo TikTokJobProcessor

        Args:
            api_client: GolikeAPIClient instance
            account_id: ID của account TikTok
            device_id: ID thiết bị ADB (nếu có)
        """
        self.api_client = api_client
        self.account_id = account_id
        self.device_id = device_id
        self.prev_job: Optional[Dict[str, Any]] = None

        # Tạo UI automator nếu có sẵn
        self.ui_automator = None
        if UI_AUTOMATION_AVAILABLE and device_id:
            try:
                self.ui_automator = TikTokUIAutomator(device_id=device_id)
                logger.info("UI Automation đã sẵn sàng")
            except Exception as e:
                logger.warning(f"Không thể tạo UI automator: {e}")

    def get_accounts(self) -> List[Dict[str, Any]]:
        """Lấy danh sách account TikTok

        Returns:
            List[Dict[str, Any]]: Danh sách account
        """
        try:
            response = self.api_client.get('/api/tiktok-account')
            if response and response.get("status") == 200:
                return response.get("data", [])
            return []
        except Exception as e:
            logger.error(f"Lỗi lấy danh sách account: {e}")
            return []

    def get_job(self) -> Optional[Dict[str, Any]]:
        """Lấy job từ API

        Returns:
            Optional[Dict[str, Any]]: Job data hoặc None nếu không có job
        """
        try:
            response = self.api_client.get(
                f'/api/advertising/publishers/tiktok/jobs?account_id={self.account_id}&data=null'
            )
            if response and response.get("status") == 200 and response.get("data"):
                return response
            return None
        except Exception as e:
            logger.error(f"Lỗi lấy job: {e}")
            return None

    def is_duplicate_job(self, job_data: Dict[str, Any]) -> bool:
        """Kiểm tra job có trùng lặp không

        Args:
            job_data: Dữ liệu job cần kiểm tra

        Returns:
            bool: True nếu trùng lặp, False nếu không
        """
        if not self.prev_job:
            return False

        prev_data = self.prev_job.get("data", {})
        current_data = job_data.get("data", {})

        return (
            prev_data.get("link") == current_data.get("link") and
            prev_data.get("type") == current_data.get("type")
        )

    def is_valid_job(self, job_data: Dict[str, Any]) -> bool:
        """Kiểm tra job có hợp lệ không

        Args:
            job_data: Dữ liệu job cần kiểm tra

        Returns:
            bool: True nếu hợp lệ, False nếu không
        """
        data = job_data.get("data", {})
        return bool(data.get("link"))

    def report_job(self, job_data: Dict[str, Any], description: str = "Báo cáo hoàn thành thất bại") -> bool:
        """Report job thất bại

        Args:
            job_data: Dữ liệu job
            description: Mô tả lỗi

        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            data = job_data.get("data", {})
            self.api_client.post('/api/report/send', {
                "description": description,
                "users_advertising_id": data.get("id"),
                "type": "ads",
                "provider": "tiktok",
                "fb_id": self.account_id,
                "error_type": 6
            })
            return True
        except Exception as e:
            logger.error(f"Lỗi report job: {e}")
            return False

    def skip_job(self, job_data: Dict[str, Any]) -> bool:
        """Skip job

        Args:
            job_data: Dữ liệu job

        Returns:
            bool: True nếu thành công, False nếu không
        """
        try:
            data = job_data.get("data", {})
            self.api_client.post('/api/advertising/publishers/tiktok/skip-jobs', {
                "ads_id": data.get("id"),
                "object_id": data.get("object_id"),
                "account_id": self.account_id,
                "type": data.get("type")
            })
            return True
        except Exception as e:
            logger.error(f"Lỗi skip job: {e}")
            return False

    def complete_job(self, job_data: Dict[str, Any], retry_on_fail: bool = False) -> Dict[str, Any]:
        """Hoàn thành job

        Args:
            job_data: Dữ liệu job
            retry_on_fail: Có retry khi thất bại không

        Returns:
            Dict[str, Any]: Kết quả hoàn thành job
        """
        data = job_data.get("data", {})
        ads_id = data.get("id")

        max_retries = 2 if retry_on_fail else 1

        for attempt in range(1, max_retries + 1):
            try:
                response = self.api_client.post('/api/advertising/publishers/tiktok/complete-jobs', {
                    "ads_id": ads_id,
                    "account_id": self.account_id,
                    "async": True,
                    "data": None
                })

                if response and response.get("status") == 200:
                    msg = response.get("message", "Báo cáo thành công!")
                    logger.info(f"Golike báo: {msg}")
                    return {
                        "success": True,
                        "reward": response.get("data", {}).get("prices", 0),
                        "type": response.get("data", {}).get("type", ""),
                        "message": msg,
                        "data": response.get("data", {})
                    }
                elif attempt < max_retries:
                    logger.warning(f"Complete job thất bại lần {attempt}, retrying...")
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Lỗi complete job lần {attempt}: {e}")
                if attempt < max_retries:
                    time.sleep(1)

        return {"success": False, "reason": "max_retries_exceeded"}

    def process_ui_automation(self, job_type: str) -> tuple[bool, str]:
        """Thực hiện UI automation cho job

        Args:
            job_type: Loại job (follow/like)

        Returns:
            tuple[bool, str]: (success, message)
        """
        if not self.ui_automator or job_type not in ["follow", "like"]:
            return False, "UI automation không khả dụng"

        try:
            return self.ui_automator.process_job(job_type)
        except Exception as e:
            logger.error(f"Lỗi UI automation: {e}")
            return False, str(e)

    def process_job(
        self,
        job_types: List[str],
        retry_on_fail: bool = False,
        delay: int = 5
    ) -> Dict[str, Any]:
        """Xử lý một job TikTok

        Args:
            job_types: Danh sách loại job được phép (['follow'], ['like'], hoặc ['follow', 'like'])
            retry_on_fail: Có retry khi thất bại không
            delay: Thời gian đợi sau khi mở link (giây)

        Returns:
            Dict[str, Any]: Kết quả xử lý
                - success: bool - Thành công hay không
                - reward: int - Số xu nhận được
                - reason: str - Lý do thất bại (nếu có)
                - job_data: dict - Dữ liệu job
                - is_duplicate: bool - Job có trùng lặp không
                - is_invalid: bool - Job có hợp lệ không
                - ui_success: bool - UI automation thành công không
                - ui_message: str - Thông báo từ UI automation
        """
        # Lấy job từ API
        job_response = self.get_job()
        if not job_response:
            return {"success": False, "reason": "no_jobs"}

        job_data = job_response.get("data", {})
        if not job_data:
            return {"success": False, "reason": "no_job_data"}

        # Lưu job trước để kiểm tra trùng lặp
        is_duplicate = self.is_duplicate_job(job_response)
        if is_duplicate:
            logger.warning("Job trùng lặp, bỏ qua")
            self.prev_job = job_response
            return {
                "success": False,
                "reason": "duplicate_job",
                "job_data": job_data,
                "is_duplicate": True
            }

        # Kiểm tra job hợp lệ
        is_valid = self.is_valid_job(job_response)
        if not is_valid:
            logger.warning("Job không hợp lệ (không có link)")
            self.prev_job = job_response
            return {
                "success": False,
                "reason": "invalid_job",
                "job_data": job_data,
                "is_invalid": True
            }

        # Lưu job hiện tại
        self.prev_job = job_response

        # Lấy thông tin job
        job_type = job_data.get("type", "")
        link = job_data.get("link", "")
        object_id = job_data.get("object_id", "")
        ads_id = job_data.get("id", "")

        # Kiểm tra job type có trong danh sách cho phép không
        if job_type not in job_types:
            logger.warning(f"Job type {job_type} không trong danh sách cho phép: {job_types}")
            return {
                "success": False,
                "reason": "invalid_job_type",
                "job_data": job_data,
                "job_type": job_type
            }

        # UI Automation
        ui_success = False
        ui_message = ""
        if self.ui_automator and job_type in ["follow", "like"]:
            ui_success, ui_message = self.process_ui_automation(job_type)

        # Đợi theo delay
        for t in range(delay, -1, -1):
            time.sleep(1)

        # Hoàn thành job
        result = self.complete_job(job_response, retry_on_fail=retry_on_fail)

        result.update({
            "job_data": job_data,
            "job_type": job_type,
            "link": link,
            "ui_success": ui_success,
            "ui_message": ui_message
        })

        return result
