"""
Security module for credential management and input validation
"""
import os
import hashlib
import base64
import re
from typing import Optional

# Removed cryptography dependency for Termux compatibility
# Always use simple XOR encryption
HAS_CRYPTO = False
Fernet = None
hashes = None
PBKDF2HMAC = None


class CredentialManager:
    """Quản lý credential với mã hóa

    Sử dụng XOR encryption với Base64 encoding để bảo vệ
    authorization token và cookie.
    """

    def __init__(self, key: Optional[str] = None):
        """Khởi tạo CredentialManager

        Args:
            key: Khóa mã hóa (nếu None sẽ dùng key mặc định)
        """
        self.key = key or self._generate_key()
        self.credential_file = "secure_credentials.enc"

    @staticmethod
    def _generate_key() -> str:
        """Tạo khóa mã hóa từ machine ID

        Returns:
            str: Khóa mã hóa 32 ký tự
        """
        import platform
        machine_id = platform.node() + platform.machine()
        return hashlib.sha256(machine_id.encode()).hexdigest()[:32]

    def _encrypt(self, data: str) -> str:
        """Mã hóa dữ liệu (XOR + Base64)

        Args:
            data: Dữ liệu cần mã hóa

        Returns:
            str: Dữ liệu đã mã hóa (Base64)
        """
        key_bytes = self.key.encode()
        data_bytes = data.encode()
        encrypted = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data_bytes)])
        return base64.b64encode(encrypted).decode()

    def _decrypt(self, encrypted: str) -> str:
        """Giải mã dữ liệu

        Args:
            encrypted: Dữ liệu đã mã hóa

        Returns:
            str: Dữ liệu gốc hoặc chuỗi rỗng nếu thất bại
        """
        try:
            key_bytes = self.key.encode()
            encrypted_bytes = base64.b64decode(encrypted)
            decrypted = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(encrypted_bytes)])
            return decrypted.decode()
        except Exception:
            return ""

    def save_auth(self, auth_token: str) -> bool:
        """Lưu authorization token đã mã hóa

        Args:
            auth_token: Authorization token cần lưu

        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            encrypted = self._encrypt(auth_token)
            with open(self.credential_file, 'w', encoding='utf-8') as f:
                f.write(encrypted)
            return True
        except Exception as e:
            print(f"[!] Lỗi lưu credential: {e}")
            return False

    def get_auth(self) -> Optional[str]:
        """Lấy authorization token

        Returns:
            Optional[str]: Token hoặc None nếu không tồn tại
        """
        if not os.path.exists(self.credential_file):
            return None
        try:
            with open(self.credential_file, 'r', encoding='utf-8') as f:
                encrypted = f.read().strip()
            decrypted = self._decrypt(encrypted)
            return decrypted if decrypted else None
        except Exception:
            return None

    def clear_auth(self) -> bool:
        """Xóa authorization token

        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            if os.path.exists(self.credential_file):
                os.remove(self.credential_file)
            return True
        except Exception as e:
            print(f"[!] Lỗi xóa credential: {e}")
            return False


class ValidationError(Exception):
    """Exception cho validation error"""
    pass


class InputValidator:
    """Validator cho input người dùng

    Cung cấp các method để validate và sanitize input
    từ người dùng.
    """

    @staticmethod
    def validate_ip(ip: str) -> bool:
        """Validate địa chỉ IP

        Args:
            ip: Địa chỉ IP cần validate

        Returns:
            bool: True nếu hợp lệ, False nếu không
        """
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        parts = ip.split('.')
        return all(0 <= int(part) <= 255 for part in parts)

    @staticmethod
    def validate_port(port: int) -> bool:
        """Validate port number

        Args:
            port: Port number cần validate

        Returns:
            bool: True nếu hợp lệ (1-65535), False nếu không
        """
        return 1 <= port <= 65535

    @staticmethod
    def validate_auth_token(token: str) -> bool:
        """Validate authorization token format

        Args:
            token: Token cần validate

        Returns:
            bool: True nếu hợp lệ, False nếu không
        """
        if not token or not token.strip():
            return False
        if len(token) < 10 or len(token) > 500:
            return False
        return True

    @staticmethod
    def validate_cookie(cookie: str) -> bool:
        """Validate Facebook cookie format

        Args:
            cookie: Cookie cần validate

        Returns:
            bool: True nếu hợp lệ, False nếu không
        """
        if not cookie or not cookie.strip():
            return False
        # Cookie phải có ít nhất một cặp key=value
        if '=' not in cookie:
            return False
        # Cookie thường có c_user hoặc datr
        if 'c_user=' not in cookie and 'datr=' not in cookie:
            return False
        return True

    @staticmethod
    def sanitize_string(input_str: str, max_length: int = 100) -> str:
        """Sanitize string input

        Args:
            input_str: Chuỗi cần sanitize
            max_length: Độ dài tối đa

        Returns:
            str: Chuỗi đã được sanitize
        """
        if not input_str:
            return ""
        sanitized = input_str.strip()[:max_length]
        dangerous_chars = ['\0', '\r', '\n']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        return sanitized

    @staticmethod
    def validate_account_id(account_id: str) -> bool:
        """Validate account ID

        Args:
            account_id: Account ID cần validate

        Returns:
            bool: True nếu hợp lệ, False nếu không
        """
        if not account_id or not account_id.strip():
            return False
        return account_id.replace('_', '').replace('-', '').isalnum()


class SecureHeaderBuilder:
    """Builder cho HTTP headers với security considerations"""

    def __init__(self, auth_token: str, t_token: Optional[str] = None):
        """Khởi tạo SecureHeaderBuilder

        Args:
            auth_token: Authorization token
            t_token: T token (optional)
        """
        self.auth_token = auth_token
        self.t_token = t_token

    def build(self) -> dict:
        """Build headers với security defaults

        Returns:
            dict: Headers dictionary
        """
        headers = {
            'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8',
            'Referer': 'https://app.golike.net/',
            'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': "Windows",
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
            'Authorization': self.auth_token,
            'Content-Type': 'application/json;charset=utf-8'
        }
        if self.t_token:
            headers['T'] = self.t_token
        return headers
