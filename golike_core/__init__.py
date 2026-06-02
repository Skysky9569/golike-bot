"""
Golike Core Package
"""

# Handle security module import with fallback
try:
    from .security import CredentialManager
    HAS_SECURITY = True
except ImportError:
    HAS_SECURITY = False
    # Fallback implementation
    class CredentialManager:
        def __init__(self, *args, **kwargs):
            pass

from .config import AppConfig, CONFIG
from .logging import AppLogger, logger
from .error_handling import ErrorHandler
from .api_client import GolikeAPIClient

# Import các module mới
try:
    from golike_core.modules import config_manager, job_processor, facebook_automation
    from golike_core.modules import golike_handler, browser_manager, account_manager
    from golike_core.modules import task_manager
    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False

__all__ = [
    'CredentialManager',
    'AppConfig',
    'CONFIG',
    'AppLogger',
    'logger',
    'ErrorHandler',
    'GolikeAPIClient',
]
