"""
API Client for Golike application
Supports both TikTok and Facebook platforms
"""
import requests
from typing import Optional, Dict, Any, List
from .config import CONFIG
from .error_handling import APIError, NetworkError, SessionExpiredError, RateLimitError, retry_on_error
from .logging import logger


class GolikeAPIClient:
    """Client cho API Golike

    Xử lý tất cả các request đến API server với
    proper error handling và retry logic.
    Hỗ trợ cả TikTok và Facebook.
    """

    # Endpoint mapping cho từng platform
    ENDPOINTS = {
        'tiktok': {
            'accounts': '/api/tiktok-account',
            'jobs': '/api/advertising/publishers/tiktok/jobs',
            'complete': '/api/advertising/publishers/tiktok/complete-jobs',
            'skip': '/api/advertising/publishers/tiktok/skip-jobs',
        },
        'facebook': {
            'accounts': '/api/fb-account',
            'jobs': '/api/advertising/publishers/get-jobs-2026',
            'complete': '/api/advertising/publishers/complete-jobs-2026',
            'skip': '/api/report/send',
        }
    }

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 30,  # Tăng từ 10s → 30s
        connect_timeout: int = 5  # Tách connect timeout
    ):
        """Khởi tạo GolikeAPIClient

        Args:
            base_url: URL cơ sở cho API (mặc định từ CONFIG)
            timeout: Timeout mặc định cho requests (default: 30s)
            connect_timeout: Connect timeout (default: 5s)
        """
        self.base_url = base_url or CONFIG.api_base_url
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self._auth_token: Optional[str] = None
        self._t_token = 'VFZSak0wOUVWWGRQUkZrd1QxRTlQUT09'
        # Session với timeout cấu hình
        self.session = requests.Session()
        self.session.timeout = (connect_timeout, timeout)

    def set_auth(self, auth_token: str) -> None:
        """Set authorization token

        Args:
            auth_token: Authorization token
        """
        self._auth_token = auth_token

    def _build_headers(self) -> Dict[str, str]:
        """Build headers cho request

        Returns:
            Dict[str, str]: Headers dictionary
        """
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8,fr-FR;q=0.7,fr;q=0.6',
            'Origin': 'https://app.golike.net',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Content-Type': 'application/json;charset=utf-8'
        }
        if self._auth_token:
            # Truyền thẳng token, không thêm 'Bearer ' prefix
            # vì user có thể đã nhập sẵn format đầy đủ
            headers['Authorization'] = self._auth_token
        if self._t_token:
            headers['T'] = self._t_token
        return headers

    @retry_on_error(max_retries=3, exceptions=(requests.RequestException,), logger_instance=logger)
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET request với retry

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Dict[str, Any]: Response data

        Raises:
            APIError: Nếu request thất bại
        """
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(
                url,
                params=params,
                headers=self._build_headers(),
                timeout=(self.connect_timeout, self.timeout)
            )
            # Check for rate limit and session expired
            if response.status_code == 429:
                raise RateLimitError("Rate limit exceeded", status_code=429)
            if response.status_code in (401, 403):
                raise SessionExpiredError("Session expired or forbidden", status_code=response.status_code)
            return response.json()
        except (RateLimitError, SessionExpiredError):
            raise  # Không retry các lỗi này
        except requests.RequestException as e:
            raise NetworkError(f"GET request failed: {e}")

    @retry_on_error(max_retries=3, exceptions=(requests.RequestException,), logger_instance=logger)
    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """POST request với retry

        Args:
            endpoint: API endpoint
            data: Request body data

        Returns:
            Dict[str, Any]: Response data

        Raises:
            APIError: Nếu request thất bại
        """
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.post(
                url,
                json=data,
                headers=self._build_headers(),
                timeout=(self.connect_timeout, self.timeout)
            )
            # Check for rate limit and session expired
            if response.status_code == 429:
                raise RateLimitError("Rate limit exceeded", status_code=429)
            if response.status_code in (401, 403):
                raise SessionExpiredError("Session expired or forbidden", status_code=response.status_code)
            return response.json()
        except (RateLimitError, SessionExpiredError):
            raise  # Không retry các lỗi này
        except requests.RequestException as e:
            raise NetworkError(f"POST request failed: {e}")

    def get_accounts(self, provider: str = 'tiktok', limit: int = 200) -> Dict[str, Any]:
        """Lấy danh sách account theo provider

        Args:
            provider: 'tiktok' hoặc 'facebook'
            limit: Số lượng account tối đa

        Returns:
            Dict[str, Any]: Response data với danh sách account

        Raises:
            APIError: Nếu request thất bại
            ValueError: Nếu provider không hợp lệ
        """
        if provider not in self.ENDPOINTS:
            raise ValueError(f"Invalid provider: {provider}. Must be 'tiktok' or 'facebook'")

        endpoint = self.ENDPOINTS[provider]['accounts']
        params = {'limit': limit} if provider == 'facebook' else None
        return self.get(endpoint, params)

    def get_jobs(self, provider: str, account_id: str, **params) -> Dict[str, Any]:
        """Lấy job theo provider

        Args:
            provider: 'tiktok' hoặc 'facebook'
            account_id: ID của account
            **params: Các tham số bổ sung (server, low_job, etc.)

        Returns:
            Dict[str, Any]: Response data với danh sách job

        Raises:
            APIError: Nếu request thất bại
            ValueError: Nếu provider không hợp lệ
        """
        if provider not in self.ENDPOINTS:
            raise ValueError(f"Invalid provider: {provider}. Must be 'tiktok' or 'facebook'")

        endpoint = self.ENDPOINTS[provider]['jobs']

        # Build params theo provider
        if provider == 'tiktok':
            job_params = {'account_id': account_id, 'data': None}
        else:  # facebook
            job_params = {
                'fb_id': account_id,
                'server': params.get('server', 'sv2'),
                'low_job': params.get('low_job', '1')
            }

        return self.get(endpoint, job_params)

    def complete_job(self, provider: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Hoàn thành job

        Args:
            provider: 'tiktok' hoặc 'facebook'
            job_data: Dữ liệu job cần hoàn thành

        Returns:
            Dict[str, Any]: Response data

        Raises:
            APIError: Nếu request thất bại
            ValueError: Nếu provider không hợp lệ
        """
        if provider not in self.ENDPOINTS:
            raise ValueError(f"Invalid provider: {provider}. Must be 'tiktok' or 'facebook'")

        endpoint = self.ENDPOINTS[provider]['complete']

        # Build data theo provider
        if provider == 'tiktok':
            complete_data = {
                'ads_id': job_data.get('id'),
                'account_id': job_data.get('account_id'),
                'async': True,
                'data': None
            }
        else:  # facebook
            complete_data = {
                'object_id': job_data.get('object_id'),
                'job_id': job_data.get('id'),
                'type': job_data.get('type'),
                'uid': job_data.get('account_id'),
                'users_fb_account_id': job_data.get('users_fb_account_id'),
                'users_advertising_id': job_data.get('id'),
                'message': None
            }

        return self.post(endpoint, complete_data)

    def report_job(self, provider: str, job_data: Dict[str, Any], error_type: int = 6) -> Dict[str, Any]:
        """Báo cáo job thất bại

        Args:
            provider: 'tiktok' hoặc 'facebook'
            job_data: Dữ liệu job cần báo cáo
            error_type: Loại lỗi (mặc định 6)

        Returns:
            Dict[str, Any]: Response data

        Raises:
            APIError: Nếu request thất bại
            ValueError: Nếu provider không hợp lệ
        """
        if provider not in self.ENDPOINTS:
            raise ValueError(f"Invalid provider: {provider}. Must be 'tiktok' or 'facebook'")

        endpoint = self.ENDPOINTS[provider]['skip']

        # Build data theo provider
        if provider == 'tiktok':
            report_data = {
                'description': 'Báo cáo hoàn thành thất bại',
                'users_advertising_id': job_data.get('id'),
                'type': 'ads',
                'provider': 'tiktok',
                'fb_id': job_data.get('account_id'),
                'error_type': error_type
            }
        else:  # facebook
            report_data = {
                'description': 'Báo cáo hoàn thành thất bại',
                'users_advertising_id': job_data.get('id'),
                'type': 'ads',
                'fb_id': job_data.get('account_id'),
                'error_type': error_type,
                'provider': 'facebook',
                'comment': None
            }

        return self.post(endpoint, report_data)

    def skip_job(self, provider: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Skip job (chỉ cho TikTok)

        Args:
            provider: 'tiktok' hoặc 'facebook'
            job_data: Dữ liệu job cần skip

        Returns:
            Dict[str, Any]: Response data

        Raises:
            APIError: Nếu request thất bại
            ValueError: Nếu provider không hợp lệ
        """
        if provider not in self.ENDPOINTS:
            raise ValueError(f"Invalid provider: {provider}. Must be 'tiktok' or 'facebook'")

        if provider == 'facebook':
            # Facebook dùng report để skip
            return self.report_job(provider, job_data)

        endpoint = self.ENDPOINTS[provider]['skip']
        skip_data = {
            'ads_id': job_data.get('id'),
            'object_id': job_data.get('object_id'),
            'account_id': job_data.get('account_id'),
            'type': job_data.get('type')
        }

        return self.post(endpoint, skip_data)

    def health_check(self) -> Dict[str, Any]:
        """
        Kiểm tra API server health.

        Returns:
            Dict với status, latency_ms, message
        """
        import time
        start = time.time()
        try:
            # Test endpoint cơ bản
            response = self.get('/health', timeout=5)
            latency = int((time.time() - start) * 1000)
            if response.get('status') == 200:
                return {
                    'status': 'ok',
                    'latency_ms': latency,
                    'message': 'Healthy'
                }
            else:
                return {
                    'status': 'error',
                    'latency_ms': latency,
                    'message': 'Unhealthy response'
                }
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return {
                'status': 'error',
                'latency_ms': latency,
                'message': str(e)
            }
