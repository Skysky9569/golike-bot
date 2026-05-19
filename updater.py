"""
Golike Bot - Dedicated Updater & Self-Healing Engine
Manages file integrity, directory recovery, and automatic updates
Sử dụng version.json để kiểm tra phiên bản nhẹ hơn (thay vì tải toàn bộ main.py)
"""
import os
import sys
import re
import json
from typing import Optional

# Auto-detect internet module (preferred requests, fallback native urllib)
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    HAS_REQUESTS = False

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/skysky9569/golike-bot/main/"
UPDATE_URL = f"{GITHUB_RAW_BASE}main.py"
VERSION_URL = f"{GITHUB_RAW_BASE}version.json"

# Core system files to protect and recover
ESSENTIAL_FILES = [
    "golikefb_sele.py",
    "tiktok_automation.py",
    "golike_core/__init__.py",
    "golike_core/api_client.py",
    "golike_core/config.py",
    "golike_core/error_handling.py",
    "golike_core/logging.py",
    "golike_core/security.py",
]

def _download_text(url: str, timeout: int = 20) -> Optional[str]:
    """Helper method supporting double fetch mechanism (requests or urllib)"""
    try:
        if HAS_REQUESTS:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200:
                return r.text
        else:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                if response.status == 200:
                    return response.read().decode('utf-8')
    except Exception:
        pass
    return None

def _compare_versions(local: str, remote: str) -> int:
    """
    So sánh 2 phiên bản theo Semantic Versioning (major.minor.patch).
    Returns:
        -1: local < remote (cần cập nhật)
         0: local == remote (đã mới nhất)
         1: local > remote (local mới hơn)
    """
    def parse_ver(v: str):
        # Loại bỏ ký tự 'v' ở đầu nếu có
        v = v.strip().lstrip('v')
        parts = v.split('.')
        result = []
        for p in parts:
            try:
                result.append(int(p))
            except ValueError:
                result.append(0)
        # Đảm bảo ít nhất 3 phần (major.minor.patch)
        while len(result) < 3:
            result.append(0)
        return tuple(result)

    local_tuple = parse_ver(local)
    remote_tuple = parse_ver(remote)

    if local_tuple < remote_tuple:
        return -1
    elif local_tuple > remote_tuple:
        return 1
    return 0

def _load_local_version() -> str:
    """Đọc phiên bản từ file version.json local"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    version_file = os.path.join(base_dir, "version.json")
    try:
        with open(version_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("version", "0.0.0")
    except Exception:
        return "0.0.0"

def _save_local_version(version: str, changelog: str = "") -> None:
    """Cập nhật file version.json local sau khi upgrade thành công"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    version_file = os.path.join(base_dir, "version.json")
    import datetime
    data = {
        "version": version,
        "release_date": datetime.date.today().isoformat(),
        "changelog": changelog
    }
    try:
        with open(version_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

def ensure_system_complete() -> bool:
    """Scan workspace and dynamically reconstruct all missing essential files"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    missing_files = []
    
    for rel_path in ESSENTIAL_FILES:
        full_path = os.path.join(base_dir, rel_path.replace('/', os.sep))
        if not os.path.exists(full_path):
            missing_files.append(rel_path)
            
    if not missing_files:
        return True  # Workspace is completely intact
        
    print("\033[1;33m\n[⚠️] PHÁT HIỆN HỆ THỐNG BỊ THIẾU CÁC TỆP TIN CỐT LÕI! \033[0m")
    print("\033[1;36m[*] Đang khởi động quy trình Tự Phục Hồi (Self-Healing Engine)... \033[0m")
    print(f"[*] Tiến hành tải khẩn cấp {len(missing_files)} file từ Github Server...\n")
    
    need_restart = False
    
    for rel_path in missing_files:
        full_path = os.path.join(base_dir, rel_path.replace('/', os.sep))
        print(f"📥 Đang khôi phục: \033[1;37m{rel_path}\033[0m ... ", end="", flush=True)
        
        # Auto-create missing parent directory structures (e.g. golike_core/)
        parent_dir = os.path.dirname(full_path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            
        # Connect and download
        content = _download_text(f"{GITHUB_RAW_BASE}{rel_path}", timeout=25)
        if content is not None:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            print("\033[1;32m[OK - THÀNH CÔNG]\033[0m")
            need_restart = True
        else:
            print("\033[1;31m[THẤT BẠI - LỖI TẢI DỮ LIỆU]\033[0m")
            
    if need_restart:
        print("\033[1;36m\n" + "═" * 60 + "\033[0m")
        print("\033[1;32m[✅] HỆ THỐNG ĐÃ ĐƯỢC TỰ ĐỘNG PHỤC HỒI HOÀN HẢO ĐẦY ĐỦ!\033[0m")
        print("\033[1;33m[👉] Vui lòng gõ lại lệnh \033[1;37m`python main.py`\033[1;33m để chạy tool!\033[0m")
        print("\033[1;36m" + "═" * 60 + "\n\033[0m")
        sys.exit(0)
    return False

def run_version_check(current_version: str):
    """
    Kiểm tra phiên bản mới bằng cách so sánh version.json local vs GitHub.
    Nhẹ hơn nhiều so với việc tải toàn bộ main.py (~74KB) chỉ để check version.
    
    Flow:
    1. Tải version.json (~100 bytes) từ GitHub
    2. So sánh phiên bản bằng Semantic Versioning  
    3. Nếu có bản mới → hỏi user có muốn cập nhật không
    4. Nếu đồng ý → tải main.py mới + cập nhật version.json local
    """
    if sys.platform == 'win32':
        os.system('color')
        
    print(f"\033[1;36m[*] Đang kiểm tra cập nhật hệ thống (Phiên bản: v{current_version})...\033[0m")
    
    # === Bước 1: Tải version.json từ GitHub (nhẹ, nhanh) ===
    version_data = _download_text(VERSION_URL, timeout=10)
    
    if not version_data:
        # Fallback: nếu version.json chưa có trên GitHub, thử cách cũ (tải main.py)
        print("\033[1;33m[!] Không tìm thấy version.json trên server, thử phương thức cũ...\033[0m")
        _fallback_version_check(current_version)
        return
    
    try:
        remote_info = json.loads(version_data)
        latest_ver = remote_info.get("version", "0.0.0")
        changelog = remote_info.get("changelog", "")
        release_date = remote_info.get("release_date", "N/A")
    except (json.JSONDecodeError, Exception):
        print("\033[1;33m[!] Lỗi đọc dữ liệu phiên bản từ server (bỏ qua).\033[0m")
        return
    
    # === Bước 2: So sánh phiên bản ===
    cmp = _compare_versions(current_version, latest_ver)
    
    if cmp == 0:
        print("\033[1;32m[✅] Tool đã ở phiên bản mới nhất.\033[0m")
        return
    
    if cmp == 1:
        print(f"\033[1;35m[🔬] Phiên bản local (v{current_version}) mới hơn server (v{latest_ver}). Dev mode?\033[0m")
        return
    
    # === Bước 3: Có bản mới → hiển thị thông tin ===
    print(f"\n\033[1;33m{'═' * 55}\033[0m")
    print(f"\033[1;33m  🔔 PHÁT HIỆN PHIÊN BẢN MỚI!\033[0m")
    print(f"\033[1;33m{'═' * 55}\033[0m")
    print(f"\033[1;37m  📌 Phiên bản hiện tại : v{current_version}\033[0m")
    print(f"\033[1;32m  🆕 Phiên bản mới nhất : v{latest_ver}\033[0m")
    print(f"\033[1;36m  📅 Ngày phát hành     : {release_date}\033[0m")
    if changelog:
        print(f"\033[1;36m  📝 Thay đổi           : {changelog}\033[0m")
    print(f"\033[1;33m{'═' * 55}\033[0m\n")
    
    chon = input("\033[1;32m📥 Bạn có muốn tự động tải và nâng cấp? (y/n, Enter là Có): \033[0m").strip().lower()
    
    if chon in ['y', 'yes', '']:
        _perform_upgrade(latest_ver, changelog)
    else:
        print(f"\033[1;37m[*] Đã từ chối. Tiếp tục chạy phiên bản hiện tại v{current_version}.\033[0m")

def _perform_upgrade(new_version: str, changelog: str = ""):
    """Tải lại toàn bộ file code từ GitHub (xóa cũ → tải mới).
    Giữ nguyên các file config: adb_config.json, *.enc, logs/, v.v.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Danh sách file code cần tải lại (không phải config)
    CODE_FILES = [
        "main.py",
        "updater.py",
        "tiktok_automation.py",
        "golikefb_sele.py",
        "FB_WEB_API_FIXED.py",
        "golike_core/__init__.py",
        "golike_core/api_client.py",
        "golike_core/config.py",
        "golike_core/error_handling.py",
        "golike_core/logging.py",
        "golike_core/security.py",
    ]

    # Thêm các file trong golike_facebook nếu folder tồn tại
    fb_dir = os.path.join(base_dir, "golike_facebook")
    if os.path.exists(fb_dir):
        for fname in os.listdir(fb_dir):
            if fname.endswith(".py"):
                CODE_FILES.append(f"golike_facebook/{fname}")

    print(f"\033[1;36m[*] Đang tải {len(CODE_FILES)} file code từ GitHub...\033[0m")

    ok_count = 0
    fail_count = 0
    for rel_path in CODE_FILES:
        full_path = os.path.join(base_dir, rel_path.replace("/", os.sep))
        url = f"{GITHUB_RAW_BASE}{rel_path}"
        print(f"  📥 {rel_path} ... ", end="", flush=True)

        content = _download_text(url, timeout=25)
        if content is not None:
            # Tạo thư mục nếu chưa có
            parent = os.path.dirname(full_path)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)
            # Xóa file cũ và ghi mới
            try:
                if os.path.exists(full_path):
                    os.remove(full_path)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print("\033[1;32m[OK]\033[0m")
                ok_count += 1
            except Exception as e:
                print(f"\033[1;31m[LỖI GHI: {e}]\033[0m")
                fail_count += 1
        else:
            print("\033[1;33m[BỎ QUA - không tải được]\033[0m")
            fail_count += 1

    # Cập nhật version.json local
    _save_local_version(new_version, changelog)

    print(f"\n\033[1;32m[✅] Cập nhật hoàn tất! {ok_count} file mới, {fail_count} lỗi.\033[0m")
    print("\033[1;33m[👉] Vui lòng gõ lại `python main.py` để khởi chạy phiên bản mới.\033[0m")
    sys.exit(0)

def _fallback_version_check(current_version: str):
    """
    Phương thức fallback: tải main.py từ GitHub và parse CURRENT_VERSION.
    Dùng khi version.json chưa được push lên GitHub.
    """
    server_code = _download_text(UPDATE_URL, timeout=15)
    if not server_code:
        print("\033[1;33m[!] Không thể kết nối máy chủ cập nhật (tự động bỏ qua).\033[0m")
        return
        
    match = re.search(r'CURRENT_VERSION\s*=\s*["\']([^"\']+)["\']', server_code)
    if match:
        latest_ver = match.group(1)
        cmp = _compare_versions(current_version, latest_ver)
        
        if cmp < 0:
            print(f"\n\033[1;33m[🔔] PHÁT HIỆN PHIÊN BẢN MỚI HƠN: v{latest_ver}!\033[0m")
            chon = input("\033[1;32m📥 Bạn có muốn tự động tải và ghi đè nâng cấp? (y/n, Enter là Có): \033[0m").strip().lower()
            if chon in ['y', 'yes', '']:
                print("\033[1;36m[*] Đang thực hiện nâng cấp main.py...\033[0m")
                
                main_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
                with open(main_file, "w", encoding="utf-8") as f:
                    f.write(server_code)
                
                # Cập nhật version.json local
                _save_local_version(latest_ver, "Cập nhật từ phương thức fallback")
                    
                print("\033[1;32m[✅] Cập nhật hoàn tất! Vui lòng gõ lại `python main.py` để khởi chạy.\033[0m")
                sys.exit(0)
            else:
                print(f"\033[1;37m[*] Đã từ chối. Tiếp tục chạy phiên bản hiện tại v{current_version}.\033[0m")
        else:
            print("\033[1;32m[✅] Tool đã ở phiên bản mới nhất.\033[0m")

if __name__ == "__main__":
    print("\033[1;35m\n=============================================\033[0m")
    print("\033[1;35m🔧  GOLIKE BOT - ĐỘC LẬP PHỤC HỒI & CẬP NHẬT\033[0m")
    print("\033[1;35m=============================================\033[0m")
    ensure_system_complete()
    print("\033[1;32m[✅] Tất cả các file cốt lõi đã đầy đủ!\033[0m\n")
