"""
Module quản lý cookie và xác thực cho Facebook
"""

import os
import json
from golike_core.security import CredentialManager

class CredentialManager:
    """Module quản lý xác thực và cookie"""

    def __init__(self):
        self.credentials = {}
        self.credential_file = "credentials.json"
        self.manager = CredentialManager()

    def save_facebook_cookie(self, cookie_data):
        """Lưu cookie Facebook"""
        try:
            # Mã hóa và lưu cookie
            encrypted_cookie = self.manager._encrypt(cookie_data)
            with open("facebook_cookie.enc", 'w', encoding='utf-8') as f:
                f.write(encrypted_cookie)
            return True
        except Exception as e:
            print(f"Lỗi khi lưu cookie: {e}")
            return False

    def load_facebook_cookie(self):
        """Tải cookie Facebook đã lưu"""
        try:
            if os.path.exists("facebook_cookie.enc"):
                with open("facebook_cookie.enc", 'r', encoding='utf-8') as f:
                    encrypted_data = f.read()
                decrypted_data = self.manager._decrypt(encrypted_data)
                return decrypted_data
            return None
        except Exception as e:
            print(f"Lỗi khi tải cookie: {e}")
            return None

    def validate_cookie(self, cookie):
        """Kiểm tra tính hợp lệ của cookie"""
        # Kiểm tra xem cookie có hợp lệ không
        return cookie and len(cookie) > 50  # Kiểm tra đơn giản

    def get_cookie_from_user(self):
        """Lấy cookie từ người dùng"""
        cookie = input("Nhập cookie Facebook: ")
        return cookie if self.validate_cookie(cookie) else None