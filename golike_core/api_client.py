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
        self._auth_token = None
        self._g_auth = None
        self._g_device_id = None
        self._t_token = None
        # Session với timeout cấu hình
        self.session = requests.Session()
        self.session.timeout = (connect_timeout, timeout)

    def set_auth(self, auth_token: str, g_auth: Optional[str] = None, g_device_id: Optional[str] = None) -> None:
        """Set authorization token and g-auth info

        Args:
            auth_token: Authorization token or JSON string with headers
            g_auth: GoLike g-auth header
            g_device_id: GoLike g-device-id header
        """
        if not auth_token:
            return

        try:
            import json
            data = json.loads(auth_token)
            if isinstance(data, dict):
                self._auth_token = data.get("authorization")
                self._g_auth = data.get("g-auth") or data.get("g_auth")
                self._g_device_id = data.get("g-device-id") or data.get("g_device_id")
                # Load t token from stored credentials if available
                t_from_cred = data.get("t")
                if t_from_cred:
                    self._t_token = t_from_cred
                return
        except Exception:
            pass

        self._auth_token = auth_token
        self._g_auth = g_auth
        self._g_device_id = g_device_id
        # Extract t token if passed in JSON data (already handled above)

    def set_t_token(self, t_token: str) -> None:
        """Set t header token (version token from browser)

        Args:
            t_token: The t header value captured from browser DevTools
        """
        if t_token:
            self._t_token = t_token

    def _build_headers(self) -> Dict[str, str]:
        """Build headers cho request

        Returns:
            Dict[str, str]: Headers dictionary
        """
        import time
        import base64

        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8,fr-FR;q=0.7,fr;q=0.6',
            'Origin': 'https://app.golike.net',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Sec-Ch-Ua': '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
            'Content-Type': 'application/json;charset=utf-8'
        }
        if self._auth_token:
            headers['Authorization'] = self._auth_token
        if self._g_auth:
            headers['g-auth'] = self._g_auth
        if self._g_device_id:
            headers['g-device-id'] = self._g_device_id

        # Use stored t token from credentials (version token) if available
        # Otherwise fallback to triple-base64 encoded timestamp
        if self._t_token:
            headers['t'] = self._t_token
        else:
            t_val = str(int(time.time()))
            for _ in range(3):
                t_val = base64.b64encode(t_val.encode('utf-8')).decode('utf-8')
            headers['t'] = t_val

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
            headers = self._build_headers()
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=(self.connect_timeout, self.timeout)
            )
            # Log full API details on error
            if response.status_code != 200:
                headers_to_log = {k: (v[:15] + "..." if len(v) > 20 else v) for k, v in headers.items()}
                logger.error(f"\n[API GET ERROR] URL: {response.url}\n"
                             f"Headers: {headers_to_log}\n"
                             f"Status Code: {response.status_code}\n"
                             f"Response: {response.text}\n")
            
            # Check for rate limit and session expired
            if response.status_code == 429:
                raise RateLimitError("Rate limit exceeded", status_code=429)
            if response.status_code in (401, 403):
                raise SessionExpiredError(f"Session expired or forbidden (HTTP {response.status_code}) - Response: {response.text}", status_code=response.status_code)
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
            headers = self._build_headers()
            response = requests.post(
                url,
                json=data,
                headers=headers,
                timeout=(self.connect_timeout, self.timeout)
            )
            # Log full API details on error
            if response.status_code != 200:
                headers_to_log = {k: (v[:15] + "..." if len(v) > 20 else v) for k, v in headers.items()}
                logger.error(f"\n[API POST ERROR] URL: {response.url}\n"
                             f"Headers: {headers_to_log}\n"
                             f"Status Code: {response.status_code}\n"
                             f"Response: {response.text}\n")

            # Check for rate limit and session expired
            if response.status_code == 429:
                raise RateLimitError("Rate limit exceeded", status_code=429)
            if response.status_code in (401, 403):
                raise SessionExpiredError(f"Session expired or forbidden (HTTP {response.status_code}) - Response: {response.text}", status_code=response.status_code)
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
