"""Telegram notification module for GoLike bot."""
import requests
from datetime import datetime


def send_telegram_notification(bot_token: str, chat_id: str, message: str) -> bool:
    """Send notification via Telegram Bot API.

    Args:
        bot_token: Telegram bot token
        chat_id: Target chat ID
        message: Message to send

    Returns:
        True if sent successfully, False otherwise
    """
    if not bot_token or not chat_id:
        return False

    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    params = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }

    try:
        response = requests.post(url, json=params, timeout=10)
        return response.status_code == 200
    except Exception:
        return False


def notify_job_limit(bot_token: str, chat_id: str, account_name: str, uid: str = "N/A") -> bool:
    """Send job limit notification.

    Args:
        bot_token: Telegram bot token
        chat_id: Target chat ID
        account_name: GoLike account name
        uid: Facebook UID

    Returns:
        True if sent successfully
    """
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    message = f"""🚨 GoLike Job Limit Alert
Account: {account_name}
UID: {uid}
Status: Đã đạt giới hạn 100 jobs/ngày
Time: {now}
Vui lòng chuyển tài khoản hoặc đợi mai."""

    return send_telegram_notification(bot_token, chat_id, message)
