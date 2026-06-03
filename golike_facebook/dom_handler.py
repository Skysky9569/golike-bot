import os
import sys
import time
from typing import Dict, Any
from golike_facebook.selenium_fb import FacebookSeleniumBot
from golike_core.adb_manager import colored
import requests

def send_tg_notify(message: str):
    """Gửi thông báo Telegram (dùng cho test tool)"""
    # Lấy từ env hoặc hardcode tạm để test
    token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '').strip()

    if not token or not chat_id:
        print(colored("⚠️ Telegram: Chưa cấu hình TELEGRAM_BOT_TOKEN/CHAT_ID trong .env. Skip thông báo.", "yellow"))
        return

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=10)
        if r.status_code == 200:
            print(colored("🔔 Đã gửi thông báo tới Telegram.", "green"))
        else:
            print(colored(f"❌ Lỗi gửi Telegram: {r.text}", "red"))
    except Exception as e:
        print(colored(f"❌ Lỗi kết nối Telegram: {e}", "red"))

def perform_fb_reaction(bot: FacebookSeleniumBot, link: str, reaction: str) -> Dict[str, Any]:
    """
    Hàm module để thực hiện thả cảm xúc Facebook.
    Sử dụng engine FacebookSeleniumBot với logic đã được kiểm chứng.
    """
    print(colored(f"[*] [DOM Handler] Đang thực hiện '{reaction}' trên bài viết...", "yellow"))
    
    # Đảm bảo bot đang ở chế độ Desktop để có độ tin cậy cao nhất
    if not bot.use_desktop:
        print(colored("[!] Cảnh báo: Bot đang ở chế độ Mobile, đang chuyển sang logic tối ưu...", "yellow"))
    
    # Gọi logic thực hiện reaction từ engine chính
    result = bot.do_reaction(link, reaction_type=reaction, current_tab_only=True)
    return result

def perform_fb_follow(bot: FacebookSeleniumBot, link: str) -> Dict[str, Any]:
    """Hàm module để thực hiện theo dõi (follow) Facebook."""
    print(colored("[*] [DOM Handler] Đang thực hiện 'FOLLOW' trên profile...", "yellow"))
    return bot.do_follow(link, current_tab_only=True)

def perform_fb_like_page(bot: FacebookSeleniumBot, link: str) -> Dict[str, Any]:
    """Hàm module để thực hiện thích trang (like page) Facebook."""
    print(colored("[*] [DOM Handler] Đang thực hiện 'LIKE PAGE' trên fanpage...", "yellow"))
    return bot.do_like_page(link, current_tab_only=True)

def process_dom_job(bot: FacebookSeleniumBot, link: str, job_type: str) -> Dict[str, Any]:
    """Điều hướng job đến đúng handler trong module DOM."""
    jt = job_type.lower()
    if jt in ["like", "love", "haha", "wow", "sad", "angry", "care"]:
        return perform_fb_reaction(bot, link, jt)
    elif jt == "follow":
        return perform_fb_follow(bot, link)
    elif jt in ["lik_page", "like_page"]:
        return perform_fb_like_page(bot, link)
    else:
        return {"success": False, "error": f"Loại job '{job_type}' chưa được hỗ trợ trong DOM Handler"}

def standalone_cli():
    print(colored("====================================================", "cyan"))
    print(colored("   GOLIKE FACEBOOK DOM HANDLER - OFFICIAL MODULE    ", "cyan", attrs=["bold"]))
    print(colored("====================================================", "cyan"))

    # 1. Nhập Cookie
    cookie = input("\n[1] Nhập chuỗi Cookie Facebook của bạn:\n>> ").strip()
    if not cookie:
        print(colored("❌ Cookie không được để trống!", "red"))
        return

    # 2. Nhập Link bài viết
    link = input("\n[2] Nhập URL bài viết Facebook:\n>> ").strip()
    if not link:
        print(colored("❌ Link không được để trống!", "red"))
        return

    # 3. Chọn chế độ Desktop/Mobile
    print("\n[3] Chọn chế độ hiển thị:")
    print("    - d: Desktop (Giao diện máy tính www.facebook.com)")
    print("    - m: Mobile  (Giao diện mbasic.facebook.com - Nhanh)")
    mode = input("👉 Lựa chọn (mặc định d): ").strip().lower()
    use_desktop = (mode != 'm')

    # 4. Chọn hành động
    print("\n[4] Chọn hành động:")
    print("    - r: Reaction (Thả cảm xúc)")
    print("    - f: Follow (Theo dõi)")
    print("    - l: Like Page (Thích trang)")
    action_choice = input("👉 Lựa chọn (mặc định r): ").strip().lower() or "r"

    action_type = "reaction"
    reaction = "Thích"
    
    if action_choice == "r":
        print("\n[5] Nhập loại cảm xúc:")
        print("    - Tiếng Việt: Thích, Yêu thích, Thương thương, Haha, Wow, Buồn, Phẫn nộ")
        print("    - Tiếng Anh : LIKE, LOVE, CARE, HAHA, WOW, SAD, ANGRY")
        reaction = input("👉 Nhập cảm xúc (mặc định Thích): ").strip() or "Thích"
    elif action_choice == "f":
        action_type = "follow"
    elif action_choice == "l":
        action_type = "like_page"

    # 5. Khởi chạy Bot
    mode_text = "DESKTOP" if use_desktop else "MOBILE"
    print(colored(f"\n[*] Đang khởi tạo trình duyệt ({mode_text})...", "yellow"))
    bot = FacebookSeleniumBot(
        cookie_str=cookie,
        profile_name="test_session",
        save_profile=False,
        use_desktop=use_desktop
    )

    try:
        success = bot.start()
        if not success:
            print(colored("❌ Đăng nhập thất bại. Kiểm tra lại cookie!", "red"))
            return

        # Gọi hàm module
        if action_type == "reaction":
            result = perform_fb_reaction(bot, link, reaction)
        elif action_type == "follow":
            result = perform_fb_follow(bot, link)
        else:
            result = perform_fb_like_page(bot, link)

        if result.get("success"):
            print(colored(f"\n✅ THÀNH CÔNG: Đã thực hiện xong!", "green", attrs=["bold"]))
            # Gửi Telegram test
            send_tg_notify(f"✅ <b>Test Thành Công!</b>\n🎯 Link: {link[:50]}...\n🔥 Hành động: {action_type.upper()} {reaction if action_type=='reaction' else ''}")
        else:
            error = result.get("error", "Unknown error")
            print(colored(f"\n❌ THẤT BẠI: {error}", "red", attrs=["bold"]))

    except Exception as e:
        print(colored(f"\n🚨 Lỗi hệ thống: {e}", "red"))
    finally:
        print("\n[*] Đang giữ trình duyệt 5 giây để bạn xem kết quả...")
        time.sleep(5)
        bot.stop()
        print("Xong!")

if __name__ == "__main__":
    standalone_cli()
