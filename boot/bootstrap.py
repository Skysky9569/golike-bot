"""
Pre-flight bootstrap: Download and verify required files from GitHub.
Lightweight initializer - only ensures absolute minimum files exist.
"""
import os
import sys
import time
import hashlib
from typing import Tuple

# Minimum bootstrap files - just enough to run updater
MINIMUM_FILES = {
    "updater.py": f"https://raw.githubusercontent.com/skysky9569/golike-bot/main/updater.py",
}

GITHUB_RAW_URL = "https://raw.githubusercontent.com/skysky9569/golike-bot/main"


def download_file(url: str, local_path: str, max_retries: int = 3) -> bool:
    """
    Download file from URL with retry logic.

    Args:
        url: File URL on GitHub
        local_path: Local save path
        max_retries: Number of retry attempts

    Returns:
        bool: True if success, False if failed
    """
    # Auto-detect HTTP client
    try:
        import requests
        use_requests = True
    except ImportError:
        import urllib.request
        use_requests = False

    for attempt in range(1, max_retries + 1):
        try:
            if use_requests:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    parent_dir = os.path.dirname(local_path)
                    if parent_dir and not os.path.exists(parent_dir):
                        os.makedirs(parent_dir, exist_ok=True)

                    with open(local_path, "w", encoding="utf-8") as f:
                        f.write(response.text)
                    return True
                else:
                    print(f"  ⚠️ Attempt {attempt}: HTTP {response.status_code}")
            else:
                with urllib.request.urlopen(url, timeout=30) as resp:
                    if resp.status == 200:
                        parent_dir = os.path.dirname(local_path)
                        if parent_dir and not os.path.exists(parent_dir):
                            os.makedirs(parent_dir, exist_ok=True)

                        with open(local_path, "w", encoding="utf-8") as f:
                            f.write(resp.read().decode('utf-8'))
                        return True
        except Exception as e:
            print(f"  ⚠️ Attempt {attempt}/{max_retries}: {type(e).__name__}")

            if attempt < max_retries:
                print(f"  ⏳ Retrying in 2 seconds...")
                time.sleep(2)

    return False


def check_and_download_missing_files() -> bool:
    """
    Check for missing core files and download them.
    Only downloads updater.py - the rest is handled by updater module.

    Returns:
        bool: True if files were downloaded, False otherwise
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    downloaded_something = False

    print("\033[1;36m[*] Checking minimum required files...\033[0m")

    # Check only updater.py - it handles everything else
    filename = "updater.py"
    url = MINIMUM_FILES["updater.py"]
    local_path = os.path.join(base_dir, filename)

    if not os.path.exists(local_path):
        print(f"  \033[1;31m✗ Missing: {filename}\033[0m → Downloading...")
        if download_file(url, local_path):
            print(f"  \033[1;32m✓ Downloaded: {filename}\033[0m")
            downloaded_something = True
        else:
            print(f"  \033[1;31m✗ ERROR: Cannot download {filename}\033[0m")
            return False
    else:
        print(f"  \033[1;32m✓ {filename} exists\033[0m")

    return downloaded_something


def bootstrap_updater():
    """
    Ensure updater.py exists. Download it if missing.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    updater_path = os.path.join(base_dir, "updater.py")

    if not os.path.exists(updater_path):
        print("\033[1;36m[*] Initializing bootloader...\033[0m")
        try:
            import urllib.request
            url = "https://raw.githubusercontent.com/skysky9569/golike-bot/main/updater.py"
            with urllib.request.urlopen(url, timeout=20) as response:
                if response.status == 200:
                    with open(updater_path, "w", encoding="utf-8") as f:
                        f.write(response.read().decode('utf-8'))
                    print("\033[1;32m[✓] Updater initialized successfully!\033[0m")
        except Exception as e:
            print(f"\033[1;31m[🚨] Bootloader error: {e}\033[0m")


def run_bootstrap(skip_download: bool = False) -> None:
    """
    Run the full bootstrap sequence.

    Args:
        skip_download: If True, skip downloading missing files
    """
    bootstrap_updater()

    if skip_download:
        return

    has_downloads = check_and_download_missing_files()

    if has_downloads:
        print("\033[1;33m" + "=" * 60 + "\033[0m")
        print("\033[1;33m⚠️  NEW/UPDATED FILE DETECTED!\033[0m")
        print("\033[1;33m" + "=" * 60 + "\033[0m")
        print(f"\033[1;36m📌 Please RESTART the tool to apply changes:\033[0m")
        print(f"\033[1;36m   cd {os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}\033[0m")
        print("\033[1;36m   python main.py\033[0m")
        print("\033[1;33m" + "=" * 60 + "\033[0m")
        input("\n\033[1;37m👉 Press ENTER to exit...\033[0m")
        sys.exit(0)
