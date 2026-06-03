import os
import sys
import time
from typing import Dict, Any
from golike_facebook.selenium_fb import FacebookSeleniumBot
from golike_core.adb_manager import colored

def perform_fb_reaction(bot: FacebookSeleniumBot, link: str, reaction: str) -> Dict[str, Any]:
    """
    Hàm module để thực hiện thả cảm xúc Facebook.
    Sử dụng engine FacebookSeleniumBot với logic đã được kiểm chứng.
    """
    print(colored(f"[*] [Module Test] Đang thực hiện '{reaction}' trên bài viết...", "yellow"))
    
    # Đảm bảo bot đang ở chế độ Desktop để có độ tin cậy cao nhất
    if not bot.use_desktop:
        print(colored("[!] Cảnh báo: Bot đang ở chế độ Mobile, đang chuyển sang logic tối ưu...", "yellow"))
    
    # Gọi logic thực hiện reaction từ engine chính
    result = bot.do_reaction(link, reaction_type=reaction, current_tab_only=True)
    return result

def main():
    print(colored("====================================================", "cyan"))
    print(colored("   TOOL AUTO REACT FACEBOOK BẰNG COOKIE (SELENIUM)   ", "cyan", attrs=["bold"]))
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

    # 4. Chọn cảm xúc
    print("\n[4] Nhập loại cảm xúc:")
    print("    - Tiếng Việt: Thích, Yêu thích, Thương thương, Haha, Wow, Buồn, Phẫn nộ")
    print("    - Tiếng Anh : LIKE, LOVE, CARE, HAHA, WOW, SAD, ANGRY")
    reaction = input("👉 Nhập cảm xúc (mặc định Thích): ").strip() or "Thích"

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
        result = perform_fb_reaction(bot, link, reaction)

        if result.get("success"):
            print(colored(f"\n✅ THÀNH CÔNG: Đã thả cảm xúc '{reaction}'!", "green", attrs=["bold"]))
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
    main()
