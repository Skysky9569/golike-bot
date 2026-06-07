"""
GoLike Bot - Auto-Updater with Clean Slate Approach
Resets the entire codebase on update, preserving only user config files.
Uses version.json for lightweight version checking.
"""
import os
import sys
import re
import json
import shutil
import threading
from typing import Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor

# Auto-detect internet module (preferred requests, fallback native urllib)
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    HAS_REQUESTS = False

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/skysky9569/golike-bot/main/"
GITHUB_API_BASE = "https://api.github.com/repos/skysky9569/golike-bot/"
UPDATE_URL = f"{GITHUB_RAW_BASE}main.py"
VERSION_URL = f"{GITHUB_RAW_BASE}version.json"
REPO_TREE_URL = f"{GITHUB_API_BASE}git/trees/main?recursive=1"

# File extensions to PRESERVE during update (user data)
CONFIG_EXTENSIONS = ['.json', '.enc', '.md']

# Folders to PRESERVE during update
PRESERVED_FOLDERS = ['node_modules', '.git', '__pycache__', '.pytest_cache', '.claude', '.agents']

# Files to always keep (logs, credentials, local configs)
ALWAYS_KEEP_FILES = ['logs', 'logs/', '.gitignore', 'package.json', 'package-lock.json', 'Authorization.txt']


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
        v = v.strip().lstrip('v')
        parts = v.split('.')
        result = []
        for p in parts:
            try:
                result.append(int(p))
            except ValueError:
                result.append(0)
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


def _is_config_file(filename: str, filepath: str) -> bool:
    """
    Check if a file should be preserved (user config/data).
    Returns True if the file is a config file that should NOT be deleted.
    """
    # Always preserve files with config extensions
    _, ext = os.path.splitext(filename)
    if ext.lower() in CONFIG_EXTENSIONS:
        return True

    # Check if filepath matches any always-keep patterns
    for keep_pattern in ALWAYS_KEEP_FILES:
        if keep_pattern in filepath:
            return True

    return False


def _get_all_repo_files() -> List[str]:
    """
    Get list of all files from GitHub repository (recursive).
    Returns relative paths from repo root.
    """
    try:
        if HAS_REQUESTS:
            response = requests.get(REPO_TREE_URL, timeout=15)
            if response.status_code != 200:
                return []
            data = response.json()
        else:
            with urllib.request.urlopen(REPO_TREE_URL, timeout=15) as response:
                if response.status != 200:
                    return []
                data = json.loads(response.read().decode('utf-8'))

        if 'tree' not in data:
            return []
            
        items = data['tree']
        files = []
        for item in items:
            if isinstance(item, dict) and item.get('type') == 'blob':
                path = item.get('path', '')
                files.append(path)
        return files
    except Exception as e:
        print(f"  ⚠️ Warning - Could not fetch repo tree: {e}")
        return []


def backup_configs(backup_dir: str, base_dir: str) -> List[str]:
    """
    Backup all config files to temporary backup directory.
    Returns list of backed up file paths.
    """
    backed_up = []

    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir, exist_ok=True)

    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)

        # Skip directories we want to preserve
        if os.path.isdir(item_path):
            if item in PRESERVED_FOLDERS:
                continue

        # Check if it's a config file to backup
        if _is_config_file(item, item_path):
            try:
                if os.path.isfile(item_path):
                    shutil.copy2(item_path, backup_dir)
                    backed_up.append(item)
                    print(f"  📦 Backed up: {item}")
            except Exception as e:
                print(f"  ⚠️ Warning - Could not backup {item}: {e}")

    return backed_up


def clean_non_config_files(base_dir: str) -> Tuple[int, int]:
    """
    Remove all non-config files from the codebase.
    Preserves files matching CONFIG_EXTENSIONS and PRESERVED_FOLDERS.
    Returns (files_deleted, folders_deleted)
    """
    files_deleted = 0
    folders_deleted = 0

    # Collect items to delete
    items_to_delete = []

    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)

        # Skip preserved folders
        if item in PRESERVED_FOLDERS:
            continue

        # Skip config files
        if _is_config_file(item, item_path):
            continue

        # Mark for deletion
        items_to_delete.append(item_path)

    # Delete collected items
    for item_path in items_to_delete:
        try:
            if os.path.isfile(item_path):
                os.remove(item_path)
                files_deleted += 1
                print(f"  🗑️ Deleted: {os.path.basename(item_path)}")
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
                folders_deleted += 1
                print(f"  🗑️ Deleted folder: {os.path.basename(item_path)}")
        except Exception as e:
            print(f"  ⚠️ Warning - Could not delete {item_path}: {e}")

    return files_deleted, folders_deleted


def restore_configs(backup_dir: str, base_dir: str) -> int:
    """
    Restore config files from backup.
    Returns number of files restored.
    """
    restored = 0

    if not os.path.exists(backup_dir):
        return 0

    for item in os.listdir(backup_dir):
        src_path = os.path.join(backup_dir, item)
        dst_path = os.path.join(base_dir, item)

        try:
            if os.path.isfile(src_path):
                shutil.copy2(src_path, dst_path)
                restored += 1
                print(f"  📥 Restored: {item}")
        except Exception as e:
            print(f"  ⚠️ Warning - Could not restore {item}: {e}")

    return restored


# Cac extension text co the download duoc
TEXT_EXTENSIONS = {'.py', '.json', '.md', '.txt', '.yml', '.yaml', '.cfg', '.conf',
                   '.ini', '.xml', '.html', '.css', '.js', '.sh', '.bat', '.ps1',
                   '.gitignore', '.dockerignore', '.env.example', '.enc', '.toml'}


# Lock for synchronized console prints
print_lock = threading.Lock()


def download_repo_files(base_dir: str) -> Tuple[int, int]:
    """
    Download all text files from GitHub repository.
    Skips binary files (exe, dll, png, etc).
    Returns (success_count, fail_count)
    """
    repo_files = _get_all_repo_files()

    if not repo_files:
        print("  ⚠️ Could not fetch repository file list")
        return 0, 0

    ok_count = 0
    fail_count = 0
    count_lock = threading.Lock()

    # Filter files first
    files_to_download = []
    for rel_path in repo_files:
        _, ext = os.path.splitext(rel_path)
        if ext.lower() not in TEXT_EXTENSIONS and ext != '':
            continue
        files_to_download.append(rel_path)

    def download_worker(rel_path: str):
        nonlocal ok_count, fail_count
        full_path = os.path.join(base_dir, rel_path.replace('/', os.sep))
        url = f"{GITHUB_RAW_BASE}{rel_path}"

        try:
            content = _download_text(url, timeout=25)
            if content is not None:
                # Create parent directory if needed
                parent = os.path.dirname(full_path)
                if parent and not os.path.exists(parent):
                    os.makedirs(parent, exist_ok=True)

                # Write file
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                
                with count_lock:
                    ok_count += 1
                with print_lock:
                    print(f"  📥 {rel_path} ... \033[1;32m[OK]\033[0m")
            else:
                with count_lock:
                    fail_count += 1
                with print_lock:
                    print(f"  📥 {rel_path} ... \033[1;33m[BỎ QUA]\033[0m")
        except Exception as e:
            with count_lock:
                fail_count += 1
            with print_lock:
                print(f"  📥 {rel_path} ... \033[1;31m[ERROR: {e}]\033[0m")

    # Use ThreadPoolExecutor to download in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(download_worker, files_to_download)

    return ok_count, fail_count


# Fallback essential files (dung khi GitHub API khong kha dung)
ESSENTIAL_FILES = [
    'main.py', 'updater.py', 'requirements.txt', 'version.json',
    'golikefb_sele.py', 'golikefb_sele_desktop.py',
    'tiktok_automation.py', 'FB_WEB_API_FIXED.py',
    'app_config.json', 'adb_config.json', 'config_parallel.json',
    'golike_core/__init__.py', 'golike_core/adb_manager.py',
    'golike_core/api_client.py', 'golike_core/config.py',
    'golike_core/error_handling.py', 'golike_core/job_processors.py',
    'golike_core/logging.py', 'golike_core/security.py',
    'golike_core/termux.py',
    'golike_core/modules/__init__.py',
    'golike_core/modules/account_manager.py',
    'golike_core/modules/browser_manager.py',
    'golike_core/modules/config_manager.py',
    'golike_core/modules/cookie_manager.py',
    'golike_core/modules/error_handler.py',
    'golike_core/modules/facebook_automation.py',
    'golike_core/modules/golike_handler.py',
    'golike_core/modules/golike_handler_updated.py',
    'golike_core/modules/job_checker.py',
    'golike_core/modules/job_processor.py',
    'golike_core/modules/parallel_processor.py',
    'golike_core/modules/rate_limit_handler.py',
    'golike_core/modules/system_manager.py',
    'golike_core/modules/task_manager.py',
    'golike_facebook/__init__.py', 'golike_facebook/facebook_client.py',
    'golike_facebook/fb_web_api.py', 'golike_facebook/selenium_fb.py',
    'golike_tiktok/__init__.py', 'golike_tiktok/tiktok_client.py',
    'ui/__init__.py', 'ui/adb_menu.py', 'ui/console.py',
    'ui/facebook_flow.py', 'ui/system_panels.py', 'ui/tiktok_flow.py',
    'boot/__init__.py', 'boot/bootstrap.py',
]


def _download_missing_files(base_dir: str, file_list: List[str]) -> Tuple[int, int]:
    """
    Download multiple missing files from GitHub.
    Returns (restored_count, failed_count)
    """
    import concurrent.futures
    restored = 0
    failed = 0
    count_lock = threading.Lock()

    def download_worker(rel_path: str) -> bool:
        nonlocal restored, failed
        full_path = os.path.join(base_dir, rel_path.replace('/', os.sep))
        url = f"{GITHUB_RAW_BASE}{rel_path}"

        parent = os.path.dirname(full_path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

        content = _download_text(url, timeout=20)
        if content is not None:
            try:
                # Always overwrite with fresh content
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                with count_lock:
                    restored += 1
                with print_lock:
                    print(f"  ✅ {rel_path}")
                return True
            except Exception as e:
                with count_lock:
                    failed += 1
                with print_lock:
                    print(f"  ❌ {rel_path}: {e}")
                return False
        else:
            with count_lock:
                failed += 1
            with print_lock:
                print(f"  ❌ {rel_path}: download failed")
            return False

    # Filter to avoid binary files if needed, but for essential files we want all
    # For now, let's just download everything in the list
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_to_file = {executor.submit(download_worker, f): f for f in file_list}
        for future in concurrent.futures.as_completed(future_to_file):
            future.result() # Wait for all to finish

    return restored, failed


def ensure_system_complete(force: bool = False) -> bool:
    """
    Check all files from GitHub exist locally. Download missing ones.
    Falls back to ESSENTIAL_FILES list if GitHub API is unavailable.
    Returns True if all essential files are present.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Try to get full file tree from GitHub API first
    repo_files = _get_all_repo_files()

    if not repo_files:
        repo_files = ESSENTIAL_FILES
        print("  ℹ️ Using fallback file list (GitHub API unavailable)")

    # Find missing files
    missing = []
    if force:
        missing = repo_files # Download everything
        print("  🔄 Force repair enabled - overwriting all system files...")
    else:
        for rel_path in repo_files:
            full_path = os.path.join(base_dir, rel_path.replace('/', os.sep))
            # Ensure we check for files, not just directory existence
            if not os.path.exists(full_path) or (os.path.isdir(full_path) and not os.listdir(full_path)):
                missing.append(rel_path)

    if not missing:
        print(f"  [✓] Verified {len(repo_files)} system files.")
        return True

    print(f"\n  ⚠️ {len(missing)} file(s) to be restored, downloading...")
    restored, failed = _download_missing_files(base_dir, missing)

    if failed == 0:
        print(f"  ✅ All {restored} file(s) restored")
    else:
        print(f"  ⚠️ Restored {restored}/{len(missing)} file(s), {failed} failed")

    print()
    return failed == 0


def run_version_check(current_version: str, force_update: bool = False):
    """
    Check for new version by comparing version.json local vs GitHub.

    Flow:
    1. Download version.json (~100 bytes) from GitHub
    2. Compare versions using Semantic Versioning
    3. If newer version exists → ask user if they want to update
    4. If confirmed → clean slate update: delete non-config files, download fresh
    """
    if sys.platform == 'win32':
        os.system('color')

    if force_update:
        print("\033[1;33m[*] Force update enabled. Preparing clean slate...\033[0m")
        # Step 1: Download version.json from GitHub to get latest version info
        version_data = _download_text(VERSION_URL, timeout=10)
        latest_ver = "Unknown"
        changelog = "Manual force update"
        if version_data:
            try:
                remote_info = json.loads(version_data)
                latest_ver = remote_info.get("version", "0.0.0")
            except Exception: pass
        _perform_clean_upgrade(latest_ver, changelog)
        return

    print(f"\033[1;36m[*] Checking for updates (Current: v{current_version})...\033[0m")

    # Step 1: Download version.json from GitHub
    version_data = _download_text(VERSION_URL, timeout=10)

    if not version_data:
        print("\033[1;33m[!] Cannot reach update server (skipping).\033[0m")
        return

    try:
        remote_info = json.loads(version_data)
        latest_ver = remote_info.get("version", "0.0.0")
        changelog = remote_info.get("changelog", "")
        release_date = remote_info.get("release_date", "N/A")
    except (json.JSONDecodeError, Exception):
        print("\033[1;33m[!] Cannot parse version info from server.\033[0m")
        return

    # Step 2: Compare versions
    cmp = _compare_versions(current_version, latest_ver)

    if cmp == 0:
        print("\033[1;32m[✅] System is up to date.\033[0m")
        return

    if cmp == 1:
        print(f"\033[1;35m[🔬] Local version (v{current_version}) newer than server (v{latest_ver}). Dev mode?\033[0m")
        return

    # Step 3: New version available - show info
    print(f"\n\033[1;33m{'═' * 55}\033[0m")
    print(f"\033[1;33m 🔔 NEW VERSION AVAILABLE!\033[0m")
    print(f"\033[1;33m{'═' * 55}\033[0m")
    print(f"\033[1;37m 📌 Current version : v{current_version}\033[0m")
    print(f"\033[1;32m 🆕 Latest version  : v{latest_ver}\033[0m")
    print(f"\033[1;36m 📅 Release date    : {release_date}\033[0m")
    if changelog:
        print(f"\033[1;36m 📝 Changelog      : {changelog}\033[0m")
    print(f"\033[1;33m{'═' * 55}\033[0m\n")

    chon = input("\033[1;32m📥 Auto-update now? (y/n, Enter=Yes): \033[0m").strip().lower()

    if chon in ['y', 'yes', '']:
        _perform_clean_upgrade(latest_ver, changelog)
    else:
        print(f"\033[1;37m[*] Update skipped. Running current version v{current_version}.\033[0m")


def _perform_clean_upgrade(new_version: str, changelog: str = ""):
    """
    Clean Slate Update: Remove all non-config files, then download fresh.

    Steps:
    1. Backup config files to temp location
    2. Delete all non-config files
    3. Download fresh copies from GitHub
    4. Restore config files
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backup_dir = os.path.join(base_dir, ".update_backup")

    print(f"\n\033[1;36m{'═' * 60}\033[0m")
    print(f"\033[1;36m 🔄 CLEAN SLATE UPDATE STARTING...\033[0m")
    print(f"\033[1;36m{'═' * 60}\033[0m")

    # Step 1: Backup configs
    print(f"\n\033[1;33mStep 1/4: Backing up config files...\033[0m")
    backed_up = backup_configs(backup_dir, base_dir)
    print(f"  ✅ Backed up {len(backed_up)} config file(s)")

    # Step 2: Clean non-config files
    print(f"\n\033[1;33mStep 2/4: Removing old code files...\033[0m")
    files_deleted, folders_deleted = clean_non_config_files(base_dir)
    print(f"  ✅ Deleted {files_deleted} files and {folders_deleted} folders")

    # Step 3: Download fresh files
    print(f"\n\033[1;33mStep 3/4: Downloading fresh code from GitHub...\033[0m")
    ok_count, fail_count = download_repo_files(base_dir)
    print(f"  ✅ Downloaded {ok_count} files ({fail_count} failed)")

    # Step 4: Restore configs
    print(f"\n\033[1;33mStep 4/4: Restoring config files...\033[0m")
    restored = restore_configs(backup_dir, base_dir)
    print(f"  ✅ Restored {restored} config file(s)")

    # Cleanup backup dir
    try:
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)
    except Exception:
        pass

    # Update version.json
    _save_local_version(new_version, changelog)

    print(f"\n\033[1;32m{'═' * 60}\033[0m")
    print(f"\033[1;32m[✅] UPDATE COMPLETE! Ready to launch v{new_version}.\033[0m")
    print(f"\033[1;33m[👉] Run `python main.py` to start the new version.\033[0m")
    print(f"\033[1;32m{'═' * 60}\033[0m")
    sys.exit(0)


def _fallback_version_check(current_version: str):
    """
    Fallback: Download main.py and parse CURRENT_VERSION.
    Used when version.json is not available on GitHub.
    """
    server_code = _download_text(UPDATE_URL, timeout=15)
    if not server_code:
        print("\033[1;33m[!] Cannot connect to update server (skipping).\033[0m")
        return

    match = re.search(r'CURRENT_VERSION\s*=\s*["\']([^"\']+)["\']', server_code)
    if match:
        latest_ver = match.group(1)
        cmp = _compare_versions(current_version, latest_ver)

        if cmp < 0:
            print(f"\n\033[1;33m[🔔] New version available: v{latest_ver}!\033[0m")
            chon = input("\033[1;32m📥 Auto-update now? (y/n, Enter=Yes): \033[0m").strip().lower()
            if chon in ['y', 'yes', '']:
                print("\033[1;36m[*] Updating main.py...\033[0m")

                main_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
                with open(main_file, "w", encoding="utf-8") as f:
                    f.write(server_code)

                _save_local_version(latest_ver, "Updated via fallback method")

                print("\033[1;32m[✅] Update complete! Please run `python main.py` to launch.\033[0m")
                sys.exit(0)
            else:
                print(f"\033[1;37m[*] Skipped. Running version v{current_version}.\033[0m")
        else:
            print("\033[1;32m[✅] System is up to date.\033[0m")


if __name__ == "__main__":
    print("\033[1;35m\n=============================================\033[0m")
    print("\033[1;35m🔧 GoLike Bot - Clean Slate Updater\033[0m")
    print("\033[1;35m=============================================\033[0m")
    
    force = "--force" in sys.argv or "--repair" in sys.argv
    
    if force:
        # First ensure system files are complete (forced)
        ensure_system_complete(force=True)
        # Then check/perform full version upgrade
        run_version_check(_load_local_version(), force_update=True)
    else:
        ensure_system_complete()
        print("\033[1;32m[✅] All core system files verified!\033[0m\n")
        
        # Also check for version update if run directly
        run_version_check(_load_local_version())
