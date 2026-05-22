"""Cấu hình thông báo Telegram cho GoLike bot."""
import json
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CONFIG_PATH = "config_golike_sele.json"

def test_telegram(bot_token, chat_id):
    """Test Telegram connection."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {
        'chat_id': chat_id,
        'text': '✅ Test message from GoLike Bot',
    }
    try:
        r = requests.post(url, json=params, timeout=5)
        return r.status_code == 200
    except:
        return False

def main():
    print("\n" + "="*60)
    print("  CAU HINH TELEGRAM CHO GOLIKE BOT")
    print("="*60)
    print("\n1. Tao bot Telegram: @BotFather -> /newbot")
    print("2. Lay Chat ID: @userinfobot hooc @myidbot")
    print("="*60)

    # Load existing config
    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)

    # Get token from env var or config
    env_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    config_token = config.get('telegram_bot_token', '')
    # Replace placeholder with actual env var value
    if config_token.startswith('${') and config_token.endswith('}'):
        config_token = env_token

    # Show current settings
    print(f"\n📋 Cau hinh hien tai:")
    print(f"   Telegram enabled: {config.get('telegram_enabled', False)}")
    token = env_token or config_token
    if token:
        print(f"   Bot token: {token[:4]}***{token[-4:]}")
    else:
        print(f"   Bot token: (cha thiet lap - dat trong .env file)")
    print(f"   Chat ID: {os.getenv('TELEGRAM_CHAT_ID', config.get('telegram_chat_id', '(cha thiet lap)'))}")

    # Ask to enable/disable
    choice = input("\n👉 Ban co muon bat thong bao Telegram? (y/n): ").strip().lower()
    if choice not in ('y', 'yes'):
        print("❌ Da tat thong bao Telegram.")
        # Xóa token khỏi config nếu có
        if 'telegram_bot_token' in config:
            del config['telegram_bot_token']
    else:
        config['telegram_enabled'] = True

        # Hướng dẫn lấy token từ environment variable
        print("\n💡 Khuyen nghi: Neu co the, dat token trong .env file thay vi o day.")
        print("   Tao file .env voi: TELEGRAM_BOT_TOKEN=your_token")
        print("   File .env duoc bo qua trong git (khong bi commit).")

        token = input("\n   Nhap Bot Token hoac de tro (neu da set trong .env): ").strip()
        if token:
            config['telegram_bot_token'] = token  # Backup, nhung khong 네hte

        chat_id = input("   Nhap Chat ID hoac de tro (neu da set trong .env): ").strip()
        if chat_id:
            config['telegram_chat_id'] = chat_id  # Backup, nhung khong het

    # Test connection if enabled
    # Ưu tiên env var, fallback vào config
    final_token = os.getenv('TELEGRAM_BOT_TOKEN', config.get('telegram_bot_token', ''))
    final_chat_id = os.getenv('TELEGRAM_CHAT_ID', config.get('telegram_chat_id', ''))

    if config.get('telegram_enabled') and final_token and final_chat_id:
        print("\n🔍 Dang kiem tra ket noi Telegram...")
        if test_telegram(final_token, final_chat_id):
            print("✅ Ket noi Telegram thanh cong!")
        else:
            print("❌ Ket noi Telegram that bai. Kiem tra lai token va chat_id.")

    # Chỉ lưu config backup, không lưu sensitive data chính
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        # Xóa sensitive data trước khi lưu (để tránh commit)
        config.pop('telegram_bot_token', None)
        config.pop('telegram_chat_id', None)
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Da luu cau vao {CONFIG_PATH}")
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
