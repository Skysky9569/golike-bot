"""
Facebook Job Processor
Xử lý các job Facebook từ API Golike
"""
import os
import time
from typing import Optional, Dict, Any
from golike_core.api_client import GolikeAPIClient
from golike_core.logging import logger
from golike_core.error_handling import SessionExpiredError, RateLimitError
from .fb_web_api import FB_API


class FacebookJobProcessor:
    """Processor cho Facebook jobs

    Xử lý việc lấy job, thực hiện job và hoàn thành job
    với proper error handling và retry logic.
    """

    def __init__(self, api_client: GolikeAPIClient, fb_id: str, cookie: Optional[str] = None, internal_id: Optional[int] = None):
        """Khởi tạo FacebookJobProcessor

        Args:
            api_client: GolikeAPIClient instance
            fb_id: ID của account Facebook (UID)
            cookie: Facebook cookie (để thực hiện job)
            internal_id: ID nội bộ của account trong DB (users_fb_account_id)
        """
        self.api_client = api_client
        self.fb_id = fb_id
        self.internal_id = internal_id
        self.cookie = cookie
        self.fb_api = None

    def _clear_session_files(self) -> None:
        """Xóa các file session local khi phát hiện session expired"""
        session_files = [
            'session_fb.pkl',
            '.facebook_session',
            'facebook_cookie.enc',
            f'fb_session_{self.fb_id}.pkl' if self.fb_id else None
        ]
        for f in session_files:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                    logger.info(f"Removed expired session file: {f}")
                except Exception as e:
                    logger.warning(f"Failed to remove session file {f}: {e}")

    def _init_fb_api(self) -> bool:
        """Khởi tạo FB API nếu chưa có

        Returns:
            bool: True nếu thành công, False nếu không
        """
        if self.fb_api is None and self.cookie:
            try:
                self.fb_api = FB_API(self.cookie)
                return True
            except Exception as e:
                logger.error(f"Lỗi khởi tạo FB API: {e}")
                return False
        return self.fb_api is not None

    def _like_post(self, object_id: str) -> Dict[str, Any]:
        """Like bài viết

        Args:
            object_id: ID của bài viết

        Returns:
            Dict[str, Any]: Kết quả
        """
        if not self._init_fb_api():
            return {"success": False, "error": "fb_api_not_initialized"}

        try:
            result = self.fb_api.REACTION("LIKE", object_id)
            return result
        except Exception as e:
            logger.error(f"Lỗi like post: {e}")
            return {"success": False, "error": str(e)}

    def _like_page(self, object_id: str) -> Dict[str, Any]:
        """Like page

        Args:
            object_id: ID của page

        Returns:
            Dict[str, Any]: Kết quả
        """
        if not self._init_fb_api():
            return {"success": False, "error": "fb_api_not_initialized"}

        try:
            result = self.fb_api.FOLLOW(object_id)
            return result
        except Exception as e:
            logger.error(f"Lỗi like page: {e}")
            return {"success": False, "error": str(e)}

    def _comment(self, object_id: str, content: str) -> Dict[str, Any]:
        """Comment bài viết

        Args:
            object_id: ID của bài viết
            content: Nội dung comment

        Returns:
            Dict[str, Any]: Kết quả
        """
        if not self._init_fb_api():
            return {"success": False, "error": "fb_api_not_initialized"}

        try:
            result = self.fb_api.CMT(content, object_id, 'null')
            return result
        except Exception as e:
            logger.error(f"Lỗi comment: {e}")
            return {"success": False, "error": str(e)}

    def _follow(self, object_id: str) -> Dict[str, Any]:
        """Follow người dùng

        Args:
            object_id: ID của người dùng

        Returns:
            Dict[str, Any]: Kết quả
        """
        if not self._init_fb_api():
            return {"success": False, "error": "fb_api_not_initialized"}

        try:
            result = self.fb_api.FOLLOW(object_id)
            return result
        except Exception as e:
            logger.error(f"Lỗi follow: {e}")
            return {"success": False, "error": str(e)}

    def _reaction(self, object_id: str, reaction_type: str = "LIKE") -> Dict[str, Any]:
        """Reaction bài viết

        Args:
            object_id: ID của bài viết
            reaction_type: Loại reaction (LIKE, LOVE, HAHA, WOW, SAD, ANGRY, CARE)

        Returns:
            Dict[str, Any]: Kết quả
        """
        if not self._init_fb_api():
            return {"success": False, "error": "fb_api_not_initialized"}

        try:
            result = self.fb_api.REACTION(reaction_type, object_id)
            return result
        except Exception as e:
            logger.error(f"Lỗi reaction: {e}")
            return {"success": False, "error": str(e)}

    def process_job(
        self,
        job_type: str,
        retry_on_fail: bool = False,
        max_retries: int = 2,
        filter_by_type: bool = False,
        server: str = "sv2",
        low_job: str = "1"
    ) -> Dict[str, Any]:
        """Xử lý một job Facebook

        Args:
            job_type: Loại job ('like', 'like_page', 'comment', 'follow', 'reaction')
            retry_on_fail: Có retry khi thất bại không
            max_retries: Số lần retry tối đa
            filter_by_type: Có filter job theo type không
            server: Server parameter cho API
            low_job: Low job parameter cho API

        Returns:
            Dict[str, Any]: Kết quả xử lý
                - success: bool - Thành công hay không
                - reward: int - Số xu nhận được
                - reason: str - Lý do thất bại (nếu có)
        """
        # Kiểm tra cookie trước
        if not self.cookie:
            return {"success": False, "reason": "no_cookie"}

        # Lấy job từ API
        try:
            job_response = self.api_client.get_jobs(
                provider='facebook',
                account_id=self.fb_id,
                server=server,
                low_job=low_job
            )
        except SessionExpiredError as e:
            logger.warning("Session expired khi lấy job")
            self._clear_session_files()
            return {"success": False, "reason": "session_expired"}
        except RateLimitError as e:
            logger.warning("Rate limit khi lấy job")
            return {"success": False, "reason": "rate_limited"}
        except Exception as e:
            logger.error(f"Lỗi lấy job: {e}")
            return {"success": False, "reason": "api_error"}

        # Kiểm tra có job không
        status = job_response.get("status") if job_response else None
        if status == 401 or status == 403:
            logger.warning("Session expired (HTTP 401/403)")
            self._clear_session_files()
            return {"success": False, "reason": "session_expired"}
        if status == 429:
            return {"success": False, "reason": "rate_limited"}
        if status != 200:
            return {"success": False, "reason": "api_error"}

        job_list = job_response.get("data")
        if not job_list or not isinstance(job_list, list):
            return {"success": False, "reason": "no_jobs"}

        # Tìm job phù hợp
        job_data = None
        
        # 1. Tìm job khớp chính xác type (nếu filter_by_type = True)
        if filter_by_type:
            for j in job_list:
                if j.get("type") == job_type:
                    job_data = j
                    break
            if not job_data:
                return {"success": False, "reason": "type_mismatch"}
        else:
            # 2. Ưu tiên lấy job có type trùng với job_type yêu cầu
            for j in job_list:
                # Kiểm tra tương đối, vd 'like' có thể nằm trong 'facebook_like_v1'
                if job_type in str(j.get("type", "")):
                    job_data = j
                    break
            
            # 3. Nếu ko thấy cái nào giống thì lấy cái đầu tiên (cũ) hoặc báo fail
            if not job_data:
                 # Nếu ko match type nào giống, lấy luôn cái đầu tiên cho an toàn
                 job_data = job_list[0]

        if not job_data:
             return {"success": False, "reason": "no_jobs"}

        # Thực hiện job theo type
        raw_object_id = job_data.get("object_id")
        if not raw_object_id:
            return {"success": False, "reason": "no_object_id"}
            
        # ÉP KIỂU STRING BẮT BUỘC: API FB_WEB_API bắt buộc ID phải là string
        object_id = str(raw_object_id)
        
        # Cập nhật lại job_type thực tế từ job để map handler đúng
        real_job_type = job_data.get("type", job_type)
        
        # Map handler support multiple strings
        def get_handler(jtype):
            # Kiểm tra reaction chi tiết trước
            reaction_keywords = ["reaction", "love", "haha", "wow", "sad", "angry", "care"]
            if any(kw in jtype for kw in reaction_keywords):
                return self._reaction
            elif "like_page" in jtype or "like-page" in jtype:
                return self._like_page
            elif "like" in jtype:
                return self._like_post
            elif "comment" in jtype:
                return self._comment
            elif "follow" in jtype:
                return self._follow
            return None

        handler = get_handler(real_job_type)
        if not handler:
            logger.warning(f"Unsupported real job type found: {real_job_type}, falling back to base handler for {job_type}")
            handler = get_handler(job_type)
            
        if not handler:
            return {"success": False, "reason": f"unsupported_job_type ({real_job_type})"}

        # Xác định tham số reaction tối ưu
        reaction_verb = "LIKE"
        if handler == self._reaction:
            verbs = ["LOVE", "HAHA", "WOW", "SAD", "ANGRY", "CARE"]
            for v in verbs:
                if v.lower() in real_job_type.lower():
                    reaction_verb = v
                    break



        # Thực hiện job với retry
        attempt = 0
        rate_limit_count = 0
        rate_limit_delays = [3, 8, 15]

        while attempt < max_retries:
            attempt += 1
            try:
                if handler == self._comment:
                    # Comment cần content
                    result = handler(object_id, "Nice post!")
                elif handler == self._reaction:
                    # Dùng reaction_verb đã xác định ở trên
                    result = handler(object_id, reaction_verb)
                else:
                    result = handler(object_id)

                if result.get("success"):
                    # Đính kèm metadata cần thiết cho complete API
                    # job_data cần có account_id (UID) và users_fb_account_id (DB Internal ID)
                    job_complete_payload = job_data.copy()
                    job_complete_payload["account_id"] = self.fb_id  # map to `uid` in complete API
                    if self.internal_id:
                         job_complete_payload["users_fb_account_id"] = self.internal_id

                    # Hoàn thành job với API Golike
                    complete_response = self.api_client.complete_job(
                        provider='facebook',
                        job_data=job_complete_payload
                    )

                    if complete_response.get("status") == 200:
                        data = complete_response.get("data", {})
                        return {
                            "success": True,
                            "reward": data.get("prices", 0),
                            "type": data.get("type", job_type)
                        }
                    elif attempt < max_retries and retry_on_fail:
                        logger.warning(f"Complete job thất bại lần {attempt}, retrying...")
                        time.sleep(1)
                    else:
                        break
                elif result.get("rate_limited"):
                    rate_limit_count += 1
                    if rate_limit_count >= 3:
                        logger.error("Rate limit exceeded after 3 attempts with exponential backoff. Stopping.")
                        break
                    delay = rate_limit_delays[rate_limit_count - 1]
                    logger.warning(f"Rate limited, waiting {delay}s (retry {rate_limit_count}/3)...")
                    time.sleep(delay)
                    attempt -= 1
                elif attempt < max_retries and retry_on_fail:
                    logger.warning(f"Thực hiện job thất bại lần {attempt}, retrying...")
                    time.sleep(1)
                else:
                    break
            except Exception as e:
                logger.error(f"Lỗi thực hiện job lần {attempt}: {e}")
                if attempt < max_retries and retry_on_fail:
                    time.sleep(1)
                else:
                    break

        # Report job sau khi fail hết retry
        try:
            # Đính kèm metadata để skip/report job nhận biết account
            report_payload = job_data.copy()
            report_payload["account_id"] = self.fb_id
            
            self.api_client.report_job(
                provider='facebook',
                job_data=report_payload
            )
        except Exception as e:
            logger.error(f"Lỗi report job: {e}")

        return {"success": False, "reason": "max_retries_exceeded"}
