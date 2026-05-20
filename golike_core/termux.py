"""
Termux/Android Compatibility Layer
Giúp GoLike Bot chạy được trên Termux (Android) và Linux môi trường khác.
"""
import os
import sys
import platform


def is_termux() -> bool:
    """Check if running in Termux environment"""
    return "TERMUX_VERSION" in os.environ or "/data/data/com.termux" in os.getcwd()


def is_android() -> bool:
    """Check if running on Android (Termux or other)"""
    py_ver = sys.version.lower()
    return "android" in py_ver or is_termux()


def fix_encoding() -> None:
    """
    Fix console encoding for UTF-8 support.
    Handles Windows PowerShell, Linux terminal, and Termux.
    """
    # Termux/Linux: Usually UTF-8 by default
    if sys.platform == 'linux':
        try:
            # Try to set encoding if not UTF-8
            if sys.stdout.encoding != 'UTF-8':
                # For older Python versions without reconfigure
                if hasattr(sys.stdout, 'reconfigure'):
                    sys.stdout.reconfigure(encoding='utf-8')
                elif hasattr(sys.stdout, 'buffer'):
                    # Fallback for Python < 3.7
                    import io
                    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
        except Exception:
            pass  # Ignore if we can't reconfigure

    # Windows: Force UTF-8
    elif sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass


def get_platform_name() -> str:
    """Get human-readable platform name"""
    if is_termux():
        return "Termux (Android)"
    elif sys.platform == 'android':
        return "Android"
    elif sys.platform == 'win32':
        return "Windows"
    elif sys.platform == 'darwin':
        return "macOS"
    elif sys.platform == 'linux':
        return "Linux"
    return sys.platform


def get_python_version() -> str:
    """Get Python version string"""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def check_termux_requirements() -> dict:
    """
    Check if all Termux requirements are met.
    Returns dict with status of each requirement.
    """
    result = {
        'termux': is_termux(),
        'python_version': get_python_version(),
        'platform': get_platform_name(),
        'encoding': sys.stdout.encoding if hasattr(sys.stdout, 'encoding') else 'unknown',
        'has_requests': False,
        'has_selenium': False,
        'has_playwright': False,
    }

    # Check required packages
    try:
        import requests
        result['has_requests'] = True
    except ImportError:
        pass

    try:
        import selenium
        result['has_selenium'] = True
    except ImportError:
        pass

    try:
        import playwright
        result['has_playwright'] = True
    except ImportError:
        pass

    return result


def init_termux() -> bool:
    """
    Initialize Termux environment.
    Call this at the start of main.py
    Returns True if initialization successful.
    """
    # Fix encoding first
    fix_encoding()

    # On Termux, warn about selenium limitations
    if is_termux():
        print(f"\033[1;33m[TERMUX] Phát hiện chạy trên Termux - Selenium có thể không hoạt động.\033[0m")
        print(f"\033[1;33m[TERMUX] Nên sử dụng API mode thay vì DOM/Click mode.\033[0m")

    return True


def get_adb_path() -> str:
    """
    Get ADB executable path.
    On Termux: Look for adb in $PREFIX/bin
    On Windows: Look in project folder or system PATH
    """
    if is_termux():
        # Termux default ADB location
        termux_adb = os.path.join(os.environ.get('PREFIX', '/data/data/com.termux/files/usr'), 'bin', 'adb')
        if os.path.exists(termux_adb):
            return termux_adb
        return 'adb'  # Fallback to PATH

    # Non-Termux (Windows/Linux)
    # Check local ADB folder first
    local_adb = os.path.join(os.getcwd(), 'ADB', 'adb.exe' if sys.platform == 'win32' else 'adb')
    if os.path.exists(local_adb):
        return local_adb

    # Try system PATH
    return 'adb.exe' if sys.platform == 'win32' else 'adb'


def get_config_dir() -> str:
    """
    Get configuration directory path.
    Termux: ~/.config/golike-bot
    Others: project root
    """
    if is_termux():
        home = os.path.expanduser('~')
        config_dir = os.path.join(home, '.config', 'golike-bot')
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        return config_dir

    # Non-Termux: use project root
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Auto-export
__all__ = [
    'is_termux',
    'is_android',
    'fix_encoding',
    'get_platform_name',
    'check_termux_requirements',
    'init_termux',
    'get_adb_path',
    'get_config_dir',
]
