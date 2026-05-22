"""
Tool lọc API job comment từ GoLike

Tool này sẽ lặp tìm các job comment từ API GoLike bằng cách
lọc các job không phải follow và like.
"""

import requests
import time
import json
from typing import Optional, Dict, Any, List


class CommentJobFinder:
    """Tool tìm job comment từ GoLike API"""

    def __init__(self, auth_token: str, t_token: Optional[str] = None):
        """Khởi tạo CommentJobFinder

        Args:
            auth_token: Authorization token
            t_token: T token (optional)
        """
        self.auth_token = auth_token
        self.t_token = t_token
        self.base_url = "https://gateway.golike.net"
        self.session = requests.Session()

    def _build_headers(self) -> Dict[str, str]:
        """Build headers cho request

        Returns:
            Dict[str, str]: Headers dictionary
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

    def get_accounts(self) -> List[Dict[str, Any]]:
        """Lấy danh sách tài khoản TikTok

        Returns:
            List[Dict[str, Any]]: Danh sách tài khoản
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/tiktok-account",
                headers=self._build_headers(),
                timeout=10
            )
            data = response.json()
            if data.get("status") == 200:
                return data.get("data", [])
            return []
        except Exception as e:
            print(f"Lỗi lấy danh sách tài khoản: {e}")
            return []

    def get_job(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Lấy job cho một tài khoản

        Args:
            account_id: ID tài khoản

        Returns:
            Optional[Dict[str, Any]]: Job data hoặc None
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/advertising/publishers/tiktok/jobs",
                params={"account_id": account_id, "data": "null"},
                headers=self._build_headers(),
                timeout=10
            )
            data = response.json()
            if data.get("status") == 200 and data.get("data"):
                return data.get("data")
            return None
        except Exception as e:
            print(f"Lỗi lấy job cho account {account_id}: {e}")
            return None

    def find_comment_job(self, accounts: List[Dict[str, Any]], max_attempts: int = 100) -> Optional[Dict[str, Any]]:
        """Tìm job comment từ danh sách tài khoản

        Args:
            accounts: Danh sách tài khoản
            max_attempts: Số lần thử tối đa

        Returns:
            Optional[Dict[str, Any]]: Job comment hoặc None
        """
        print(f"🔍 Đang tìm job comment từ {len(accounts)} tài khoản...")
        print(f"🔄 Số lần thử tối đa: {max_attempts}")
        print("=" * 60)

        for attempt in range(1, max_attempts + 1):
            for acc in accounts:
                account_id = acc.get("id")
                username = acc.get("unique_username", "N/A")

                job = self.get_job(account_id)
                if not job:
                    continue

                job_type = job.get("type")
                job_id = job.get("id")
                link = job.get("link")

                # Lọc job không phải follow và like
                if job_type not in ["follow", "like"]:
                    print(f"✅ Tìm thấy job {job_type}!")
                    print(f"   Account: {username} (ID: {account_id})")
                    print(f"   Job ID: {job_id}")
                    print(f"   Link: {link}")
                    print(f"   Type: {job_type}")

                    # Hiển thị chi tiết nếu là comment
                    if job_type == "comment":
                        comment_run = job.get("comment_run", {})
                        if comment_run:
                            message = comment_run.get("message", "N/A")
                            print(f"   Comment: {message}")

                    print("=" * 60)
                    return job

            if attempt < max_attempts:
                print(f"⏳ Thử lần {attempt}/{max_attempts} - Không tìm thấy job comment...")
                time.sleep(18)

        print("❌ Không tìm thấy job comment sau {max_attempts} lần thử")
        return None

    def find_all_comment_jobs(self, accounts: List[Dict[str, Any]], max_attempts: int = 100) -> List[Dict[str, Any]]:
        """Tìm tất cả job comment từ danh sách tài khoản

        Args:
            accounts: Danh sách tài khoản
            max_attempts: Số lần thử tối đa

        Returns:
            List[Dict[str, Any]]: Danh sách job comment
        """
        print(f"🔍 Đang tìm tất cả job comment từ {len(accounts)} tài khoản...")
        print(f"🔄 Số lần thử tối đa: {max_attempts}")
        print("=" * 60)

        found_jobs = []

        for attempt in range(1, max_attempts + 1):
            for acc in accounts:
                account_id = acc.get("id")
                username = acc.get("unique_username", "N/A")

                job = self.get_job(account_id)
                if not job:
                    continue

                job_type = job.get("type")
                job_id = job.get("id")

                # Lọc job không phải follow và like
                if job_type not in ["follow", "like"]:
                    # Kiểm tra đã tìm thấy job này chưa
                    if not any(j.get("id") == job_id for j in found_jobs):
                        print(f"✅ Tìm thấy job {job_type}!")
                        print(f"   Account: {username} (ID: {account_id})")
                        print(f"   Job ID: {job_id}")
                        print(f"   Type: {job_type}")

                        # Hiển thị chi tiết nếu là comment
                        if job_type == "comment":
                            comment_run = job.get("comment_run", {})
                            if comment_run:
                                message = comment_run.get("message", "N/A")
                                print(f"   Comment: {message}")

                        found_jobs.append(job)
                        print("=" * 60)

            if attempt < max_attempts:
                print(f"⏳ Thử lần {attempt}/{max_attempts} - Đã tìm thấy {len(found_jobs)} job...")
                time.sleep(18)

        print(f"🎉 Tổng kết: Tìm thấy {len(found_jobs)} job comment")
        return found_jobs


def main():
    """Main function"""
    print("=" * 60)
    print("🔍 TOOL LỌC API JOB COMMENT - GOLIKE")
    print("=" * 60)

    # Nhập authorization token
    auth_token = input("📢 Nhập Authorization Token: ").strip()
    if not auth_token:
        print("❌ Token không được để trống!")
        return

    # Nhập T token (optional)
    t_token = input("📢 Nhập T Token (Enter để bỏ qua): ").strip() or None

    # Tạo finder
    finder = CommentJobFinder(auth_token, t_token)

    # Lấy danh sách tài khoản
    print("\n📱 Đang lấy danh sách tài khoản...")
    accounts = finder.get_accounts()

    if not accounts:
        print("❌ Không tìm thấy tài khoản nào!")
        return

    print(f"✅ Tìm thấy {len(accounts)} tài khoản:")
    for idx, acc in enumerate(accounts, 1):
        print(f"   [{idx}] {acc.get('unique_username', 'N/A')} (ID: {acc.get('id')})")

    # Chọn chế độ tìm
    print("\n" + "=" * 60)
    print("🎯 Chọn chế độ tìm:")
    print("   1. Tìm job comment đầu tiên")
    print("   2. Tìm tất cả job comment")
    print("=" * 60)

    choice = input("✅ Chọn (1/2): ").strip()

    # Nhập số lần thử
    max_attempts = input("🔄 Nhập số lần thử tối đa (mặc định 100): ").strip()
    max_attempts = int(max_attempts) if max_attempts.isdigit() else 100

    if choice == "1":
        # Tìm job comment đầu tiên
        job = finder.find_comment_job(accounts, max_attempts)

        if job:
            print("\n🎉 Tìm thấy job comment!")
            print(json.dumps(job, indent=2, ensure_ascii=False))
        else:
            print("\n❌ Không tìm thấy job comment")

    elif choice == "2":
        # Tìm tất cả job comment
        jobs = finder.find_all_comment_jobs(accounts, max_attempts)

        if jobs:
            print("\n🎉 Tìm thấy job comment!")
            print(json.dumps(jobs, indent=2, ensure_ascii=False))
        else:
            print("\n❌ Không tìm thấy job comment")

    else:
        print("❌ Lựa chọn không hợp lệ!")


if __name__ == "__main__":
    main()
