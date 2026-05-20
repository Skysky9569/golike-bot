"""
Module quản lý tài khoản cho hệ thống GoLike
"""

import json
from typing import List, Dict

class AccountManager:
    """Module quản lý tài khoản"""

    def __init__(self):
        self.accounts = []
        self.current_account = None

    def load_accounts(self, filepath: str = "accounts.json") -> List[Dict]:
        """Tải danh sách tài khoản từ file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.accounts = json.load(f)
            return self.accounts
        except FileNotFoundError:
            print(f"Không tìm thấy file {filepath}")
            return []
        except Exception as e:
            print(f"Lỗi khi tải tài khoản: {e}")
            return []

    def save_accounts(self, filepath: str = "accounts.json"):
        """Lưu danh sách tài khoản vào file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.accounts, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Lỗi khi lưu tài khoản: {e}")

    def add_account(self, account_data: Dict):
        """Thêm tài khoản mới"""
        self.accounts.append(account_data)

    def get_account_by_id(self, account_id: str) -> Dict:
        """Lấy thông tin tài khoản theo ID"""
        for account in self.accounts:
            if account.get('id') == account_id:
                return account
        return None

    def get_all_accounts(self) -> List[Dict]:
        """Lấy tất cả tài khoản"""
        return self.accounts

    def remove_account(self, account_id: str):
        """Xóa tài khoản"""
        self.accounts = [acc for acc in self.accounts if acc.get('id') != account_id]