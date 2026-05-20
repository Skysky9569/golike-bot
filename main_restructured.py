"""
Hệ thống GoLike - Tự động hóa Facebook
Phiên bản tái cấu trúc
"""

import sys
import os

# Kiểm tra và thiết lập encoding UTF-8 cho Windows
if sys.platform == "win32":
    import codecs
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("GoLike Bot - Hệ thống tự động hóa Facebook")
    print("=" * 50)
    print("Đang khởi tạo hệ thống...")

    # Ở đây ta có thể tích hợp các module đã tái cấu trúc
    # Ví dụ: từ golike_core.modules import GoLikeSystem
    # system = GoLikeSystem()
    # system.run()

if __name__ == "__main__":
    main()