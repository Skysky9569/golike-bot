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

__all__ = [
    'CredentialManager',
    'AppConfig',
    'CONFIG',
    'AppLogger',
    'logger',
    'ErrorHandler',
    'GolikeAPIClient',
]
