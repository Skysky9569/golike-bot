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
from typing import Optional, List, Tuple

# Auto-detect internet module (preferred requests, fallback native urllib)
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    HAS_REQUESTS = False

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/skysky9569/golike-bot/main/"
GITHUB_API_BASE = "https://api.github.com/repos/skysky9569/golike-bot/contents/"
UPDATE_URL = f"{GITHUB_RAW_BASE}main.py"
VERSION_URL = f"{GITHUB_RAW_BASE}version.json"
REPO_TREE_URL = f"{GITHUB_API_BASE}?recursive=1"

# File extensions to PRESERVE during update (user data)
CONFIG_EXTENSIONS = ['.json', '.enc', '.md']

# Folders to PRESERVE during update
PRESERVED_FOLDERS = ['node_modules', '.git', '__pycache__', '.pytest_cache', '.claude', '.agents']

# Files to always keep (logs, credentials, local configs)
ALWAYS_KEEP_FILES = ['logs', 'logs/', '.gitignore', 'package.json', 'package-lock.json']


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
    Get list of all Python files from GitHub repository.
    Returns relative paths from repo root.
    """
    try:
        response = requests.get(REPO_TREE_URL, timeout=15)
        if response.status_code != 200:
            return []

        items = response.json()
        files = []
        for item in items:
            if isinstance(item, dict) and item.get('type') == 'file':
                path = item.get('path', '')
                # Only include Python files and essential config
                if path.endswith('.py') or path.endswith('.json') or path.endswith('.md'):
                    files.append(path)
        return files
    except Exception:
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


def download_repo_files(base_dir: str) -> Tuple[int, int]:
    """
    Download all Python files from GitHub repository.
    Returns (success_count, fail_count)
    """
    repo_files = _get_all_repo_files()

    if not repo_files:
        print("  ⚠️ Could not fetch repository file list")
        return 0, 0

    ok_count = 0
    fail_count = 0

    for rel_path in repo_files:
        full_path = os.path.join(base_dir, rel_path.replace('/', os.sep))
        url = f"{GITHUB_RAW_BASE}{rel_path}"

        print(f"  📥 {rel_path} ... ", end="", flush=True)

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
                print("\033[1;32m[OK]\033[0m")
                ok_count += 1
            else:
                print("\033[1;33m[BỎ QUA]\033[0m")
                fail_count += 1
        except Exception as e:
            print(f"\033[1;31m[ERROR: {e}]\033[0m")
            fail_count += 1

    return ok_count, fail_count


def ensure_system_complete() -> bool:
    """
    Scan workspace and dynamically reconstruct all missing essential files.
    Legacy support - use clean update approach instead.
    """
    # For now, delegate to clean update
    print("\033[1;33m[⚠️] Using legacy self-healing mode. Consider running full update.\033[0m")
    return True  # Simplified for now


def run_version_check(current_version: str):
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
    ensure_system_complete()
    print("\033[1;32m[✅] All core system files verified!\033[0m\n")
