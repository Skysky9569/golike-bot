import os
import sys
import time
from golike_facebook.selenium_fb import FacebookSeleniumBot
from golike_core.adb_manager import colored

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
    use_desktop = (mode != 'm') # Mặc định là Desktop như yêu cầu mới nhất

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

        print(colored(f"[*] Đang truy cập bài viết và thả '{reaction}'...", "yellow"))
        result = bot.do_reaction(link, reaction_type=reaction, current_tab_only=True)

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
