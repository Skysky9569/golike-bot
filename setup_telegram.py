"""Cấu hình thông báo Telegram cho GoLike bot."""
import json
import os
import requests

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

    # Show current settings
    print(f"\n📋 Cau hinh hien tai:")
    print(f"   Telegram enabled: {config.get('telegram_enabled', False)}")
    token = config.get('telegram_bot_token', '')
    if token:
        print(f"   Bot token: {token[:20]}...{token[-10:]}")
    else:
        print(f"   Bot token: (chu thiet lap)")
    print(f"   Chat ID: {config.get('telegram_chat_id', '(chu thiet lap)')}")

    # Ask to enable/disable
    choice = input("\n👉 Ban co muon bat thong bao Telegram? (y/n): ").strip().lower()
    if choice not in ('y', 'yes'):
        config['telegram_enabled'] = False
        print("❌ Da tat thong bao Telegram.")
    else:
        config['telegram_enabled'] = True

        # Get bot token
        token = input("   Nhap Bot Token (hoac Enter de giu nguyen): ").strip()
        if token:
            config['telegram_bot_token'] = token

        # Get chat ID
        chat_id = input("   Nhap Chat ID (hoac Enter de giu nguyen): ").strip()
        if chat_id:
            config['telegram_chat_id'] = chat_id

    # Test connection if enabled
    if config.get('telegram_enabled') and config.get('telegram_bot_token') and config.get('telegram_chat_id'):
        print("\n🔍 Dang kiem tra ket noi Telegram...")
        if test_telegram(config['telegram_bot_token'], config['telegram_chat_id']):
            print("✅ Ket noi Telegram thanh cong!")
        else:
            print("❌ Ket noi Telegram that bai. Kiem tra lai token va chat_id.")

    # Save config
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Da luu cau vao {CONFIG_PATH}")
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
