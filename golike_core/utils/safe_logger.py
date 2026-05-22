"""Safe logging utility to redact sensitive data from logs"""
from typing import Dict, List, Any, Union

# Default keys to redact
REDACT_KEYS = [
    'token', 'cookie', 'auth', 'password', 'secret', 'key', 'credential',
    'api_key', 'apikey', 'access_token', 'refresh_token'
]


def redact_sensitive(value: Union[str, Dict, List, Any], max_visible: int = 4) -> Union[str, Dict, List, Any]:
    """
    Redact sensitive data recursively.

    Args:
        value: Value to redact
        max_visible: Number of characters visible at start/end

    Returns:
        Redacted value
    """
    if isinstance(value, str):
        # Mask long strings (likely tokens/secrets)
        if len(value) > max_visible * 2:
            return value[:max_visible] + '***REDACTED***' + value[-max_visible:]
        return '***'
    elif isinstance(value, dict):
        return {k: redact_sensitive(v, max_visible) for k, v in value.items()}
    elif isinstance(value, list):
        return [redact_sensitive(item, max_visible) for item in value]
    return value


def safe_log(data: Dict[str, Any], redact_keys: List[str] = None) -> Dict[str, Any]:
    """
    Redact sensitive fields before logging.

    Args:
        data: Dictionary to sanitize
        redact_keys: List of keys to redact (default: REDACT_KEYS)

    Returns:
        Sanitized dictionary
    """
    keys_to_redact = redact_keys or REDACT_KEYS

    def _process(key: str, value: Any) -> Any:
        # Check if key matches any redact pattern
        key_lower = key.lower()
        if any(pattern in key_lower for pattern in keys_to_redact):
            return '***REDACTED***'
        if isinstance(value, dict):
            return {k: _process(k, v) for k, v in value.items()}
        if isinstance(value, list):
            # Check if list contains dict items
            if value and isinstance(value[0], dict):
                return [_process(key, item) for item in value]
            # Check if list contains sensitive strings
            if value and isinstance(value[0], str):
                # Redact if any item looks like a token/cookie
                if any(len(str(v)) > 20 for v in value if isinstance(v, str)):
                    return [redact_sensitive(v) if isinstance(v, str) else v for v in value]
        return value

    return {k: _process(k, v) for k, v in data.items()}


def redact_string(value: str, show_chars: int = 4) -> str:
    """
    Redact a string value, showing only first and last few chars.

    Args:
        value: String to redact
        show_chars: Number of characters to show at each end

    Returns:
        Redacted string
    """
    if not value or len(value) <= show_chars * 2:
        return '***'
    return value[:show_chars] + '***' + value[-show_chars:]
