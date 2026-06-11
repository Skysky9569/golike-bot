"""
Security module for credential management and input validation
"""
import os
import json
import hashlib
import base64
import re
from typing import Optional, Dict, List

# Cryptography support with fallback to XOR for Termux compatibility
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes  # noqa: F401 - imported for type checking
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC  # noqa: F401 - imported for type checking
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    Fernet = None
    hashes = None
    PBKDF2HMAC = None


class CredentialManager:
    """Quản lý credential với mã hóa Fernet (hoặc XOR fallback)

    Sử dụng Fernet encryption để bảo vệ authorization token và cookie.
    Lưu trữ nhiều token trong file JSON: {label: encrypted_token}
    """

    def __init__(self, key: Optional[str] = None):
        """Khởi tạo CredentialManager

        Args:
            key: Khóa mã hóa (nếu None sẽ dùng key mặc định)
        """
        self.key = key or self._generate_key()
        self.credential_file = "auth_tokens.json"
        self.old_credential_file = "secure_credentials.enc"
        self._migrate_old_credential()

    def _generate_key(self) -> str:
        """Tạo khóa mã hóa từ machine ID

        Returns:
            str: Khóa mã hóa 32 ký tự
        """
        import platform
        machine_id = platform.node() + platform.machine()
        return hashlib.sha256(machine_id.encode()).hexdigest()[:32]

    def _get_fernet_key(self, key: str) -> bytes:
        """Tạo Fernet key từ password string

        Args:
            key: Key string

        Returns:
            bytes: Fernet-compatible 32-byte key
        """
        # Pad to 32 bytes for Fernet
        key_bytes = key.encode()
        if len(key_bytes) < 32:
            key_bytes = key_bytes + (b'\x00' * (32 - len(key_bytes)))
        return base64.urlsafe_b64encode(key_bytes[:32])

    def _encrypt(self, data: str) -> str:
        """Mã hóa dữ liệu bằng Fernet (ưu tiên) hoặc XOR fallback

        Args:
            data: Dữ liệu cần mã hóa

        Returns:
            str: Dữ liệu đã mã hóa
        """
        if HAS_CRYPTO:
            try:
                fernet_key = self._get_fernet_key(self.key)
                f = Fernet(fernet_key)
                return f.encrypt(data.encode()).decode()
            except Exception:
                pass

        # Fallback to XOR encryption
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
        # Try Fernet first if available
        if HAS_CRYPTO:
            try:
                fernet_key = self._get_fernet_key(self.key)
                f = Fernet(fernet_key)
                return f.decrypt(encrypted.encode()).decode()
            except Exception:
                pass

        # Fallback to XOR decryption
        try:
            key_bytes = self.key.encode()
            encrypted_bytes = base64.b64decode(encrypted)
            decrypted = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(encrypted_bytes)])
            return decrypted.decode()
        except Exception:
            return ""

    def _load_tokens(self) -> Dict[str, str]:
        """Load token dictionary from JSON file

        Returns:
            Dict[str, str]: Dictionary of label to encrypted token
        """
        if not os.path.exists(self.credential_file):
            return {}
        try:
            with open(self.credential_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                # Ensure all values are strings
                return {k: str(v) for k, v in data.items()}
            else:
                return {}
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_tokens(self, tokens: Dict[str, str]) -> None:
        """Save token dictionary to JSON file

        Args:
            tokens: Dictionary of label to encrypted token
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(self.credential_file)), exist_ok=True)
            with open(self.credential_file, 'w', encoding='utf-8') as f:
                json.dump(tokens, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[!] Lỗi lưu file token: {e}")

    def _migrate_old_credential(self) -> None:
        """Migrate old single token file to new JSON format if needed"""
        if os.path.exists(self.old_credential_file) and not os.path.exists(self.credential_file):
            try:
                with open(self.old_credential_file, 'r') as f:
                    old_encrypted = f.read().strip()
                old_decrypted = self._decrypt(old_encrypted)
                if old_decrypted:
                    # Save as label "default" in new format
                    tokens = {"default": self._encrypt(old_decrypted)}
                    self._save_tokens(tokens)
                # Remove old file after migration (whether successful or not)
                os.remove(self.old_credential_file)
            except Exception:
                # If migration fails, we still remove the old file to avoid infinite retry
                try:
                    os.remove(self.old_credential_file)
                except:
                    pass

    def save_auth(self, label: str, auth_token: str, g_auth: Optional[str] = None, g_device_id: Optional[str] = None, t_token: Optional[str] = None) -> bool:
        """Lưu authorization token đã mã hóa với nhãn cụ thể

        Args:
            label: Nhãn để xác định token
            auth_token: Authorization token cần lưu
            g_auth: GoLike g-auth header
            g_device_id: GoLike g-device-id header
            t_token: GoLike t header (version token)

        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        if not label or not auth_token:
            return False
        try:
            tokens = self._load_tokens()
            if g_auth:
                import json
                save_data = {
                    "authorization": auth_token,
                    "g-auth": g_auth,
                    "g-device-id": g_device_id,
                    "t": t_token
                }
                save_val = json.dumps(save_data)
            else:
                save_val = auth_token

            tokens[label] = self._encrypt(save_val)
            self._save_tokens(tokens)
            return True
        except Exception as e:
            print(f"[!] Lỗi lưu credential: {e}")
            return False

    def get_auth_by_label(self, label: str) -> Optional[str]:
        """Lấy authorization token theo nhãn

        Args:
            label: Nhãn của token cần lấy

        Returns:
            Optional[str]: Token hoặc None nếu không tồn tại
        """
        tokens = self._load_tokens()
        if label in tokens:
            return self._decrypt(tokens[label])
        return None

    def get_auth_labels(self) -> List[str]:
        """Lấy danh sách tất cả các nhãn token

        Returns:
            List[str]: Danh sách các nhãn
        """
        return list(self._load_tokens().keys())

    def clear_auth(self) -> bool:
        """Xóa tất cả authorization tokens

        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            self._save_tokens({})
            return True
        except Exception as e:
            print(f"[!] Lỗi xóa credential: {e}")
            return False

    def delete_auth(self, label: str) -> bool:
        """Xóa authorization token theo nhãn

        Args:
            label: Nhãn của token cần xóa

        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            tokens = self._load_tokens()
            if label in tokens:
                del tokens[label]
                self._save_tokens(tokens)
                return True
            else:
                return False
        except Exception as e:
            print(f"[!] Lỗi xóa token: {e}")
            return False

    def has_any_token(self) -> bool:
        """Kiểm tra xem có token nào được lưu trữ không

        Returns:
            bool: True nếu có ít nhất một token, False nếu không
        """
        return len(self._load_tokens()) > 0


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
            'Sec-Ch-Ua': '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
            'Authorization': self.auth_token,
            'Content-Type': 'application/json;charset=utf-8'
        }
        if self.t_token:
            headers['T'] = self.t_token
        return headers
