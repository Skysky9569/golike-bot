"""
Auto Friend Tool - Kết bạn Facebook tự động
Với tính năng lưu/chọn cookie từ file
"""
import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Path setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_DIR = os.path.join(SCRIPT_DIR, 'cookies')


def ensure_cookies_dir():
    """Tạo folder cookies nếu chưa tồn tại"""
    if not os.path.exists(COOKIES_DIR):
        os.makedirs(COOKIES_DIR)


def list_saved_cookies() -> list[str]:
    """List tất cả cookie files đã lưu"""
    ensure_cookies_dir()
    files = [f for f in os.listdir(COOKIES_DIR) if f.endswith('.txt')]
    return sorted(files)


def save_cookie_file(name: str, cookie_string: str):
    """Lưu cookie vào file"""
    ensure_cookies_dir()
    filepath = os.path.join(COOKIES_DIR, f"{name}.txt")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(cookie_string.strip())
    print(f"[OK] Cookie đã lưu vào: {filepath}")


def load_cookie_file(filename: str) -> str:
    """Load cookie từ file"""
    filepath = os.path.join(COOKIES_DIR, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def parse_cookies(cookie_string: str) -> list:
    """Parse cookie string thành list dict cho CDP"""
    cookies = []
    for cookie in cookie_string.strip().split(';'):
        cookie = cookie.strip()
        if '=' in cookie:
            name, value = cookie.split('=', 1)
            cookies.append({
                'name': name.strip(),
                'value': value.strip(),
                'domain': '.facebook.com',
                'path': '/',
                'expires': int(time.time()) + 86400
            })
    return cookies


def setup_driver(cookie_string: str) -> webdriver.Chrome:
    """Tạo Chrome driver và inject cookies qua CDP"""
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)

    driver.get('https://www.facebook.com')
    time.sleep(2)

    driver.execute_cdp_cmd('Network.enable', {})

    cookies = parse_cookies(cookie_string)
    for cookie in cookies:
        driver.execute_cdp_cmd('Network.setCookie', cookie)

    driver.refresh()
    time.sleep(3)

    driver.get('https://www.facebook.com')
    time.sleep(2)

    return driver


def send_friend_request(driver: webdriver.Chrome, uid: str) -> str:
    """Gửi lời mời kết bạn cho một UID"""
    try:
        url = f'https://www.facebook.com/profile.php?id={uid}'
        driver.get(url)
        time.sleep(random.uniform(3, 5))

        try:
            friend_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH,
                     "//button[contains(text(), 'Thêm bạn bè')] | "
                     "//button[contains(text(), 'Kết bạn')] | "
                     "//span[contains(text(), 'Thêm bạn bè')]/ancestor::*[contains(@role, 'button')] | "
                     "//span[contains(text(), 'Kết bạn')]/ancestor::*[contains(@role, 'button')]")
                )
            )

            driver.execute_script("arguments[0].click();", friend_button)
            time.sleep(2)

            try:
                existing_request = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located(
                        (By.XPATH,
                         "//div[contains(text(), 'Lời mời đã gửi')] | "
                         "//div[contains(text(), 'Đã kết bạn')] | "
                         "//span[contains(text(), 'Gửi lời mời')]")
                    )
                )
                return 'already_friends'
            except TimeoutException:
                pass

            return 'success'

        except TimeoutException:
            return 'no_button'

    except Exception as e:
        return f'error: {str(e)}'


def input_cookie_string() -> str:
    """Nhập cookie string từ user"""
    print("\n[Dán cookie của bạn (dạng: name=value; name2=value2;)):")
    print("[Nhấn Enter 2 lần để kết thúc input]\n")

    cookie_lines = []
    while True:
        line = input()
        if line == '' and cookie_lines:
            break
        cookie_lines.append(line)

    return ' '.join(cookie_lines)


def input_uids() -> list[str]:
    """Nhập danh sách UID"""
    print("\n[Nhập UID (1 dòng = 1 UID), nhấn Enter trống để kết thúc]:\n")

    uids = []
    while True:
        uid = input().strip()
        if uid == '':
            break
        uids.append(uid)

    return uids


def menu_select_cookie() -> str | None:
    """Menu chọn cookie đã lưu"""
    cookies = list_saved_cookies()

    if not cookies:
        print("\n[!] Chưa có cookie nào được lưu!")
        return None

    print("\n" + "=" * 40)
    print("[Cookies đã lưu:]")
    print("-" * 40)
    for i, cookie in enumerate(cookies, 1):
        print(f"  {i}. {cookie}")
    print("-" * 40)

    while True:
        try:
            choice = input("\nChọn cookie (nhập số): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(cookies):
                return cookies[idx]
            print(f"[!] Vui lòng nhập số từ 1 đến {len(cookies)}")
        except ValueError:
            print("[!] Nhập số hợp lệ!")


def main_menu():
    """Hiển thị menu chính"""
    print("\n" + "=" * 60)
    print("AUTO FRIEND TOOL - Kết bạn Facebook tự động")
    print("=" * 60)
    print("\n  1. Chạy tool với cookie có sẵn")
    print("  2. Lưu cookie mới")
    print("  3. Thoát")
    print()


def run_tool(cookie_string: str):
    """Chạy tool với cookie đã cho"""
    uids = input_uids()

    if not uids:
        print("[ERROR] Không có UID để xử lý!")
        return

    print(f"\n[Bắt đầu xử lý {len(uids)} UID...]\n")
    time.sleep(2)

    driver = setup_driver(cookie_string)

    try:
        for i, uid in enumerate(uids, 1):
            print(f"\n[{i}/{len(uids)}] Đang xử lý UID: {uid}")

            result = send_friend_request(driver, uid)

            if result == 'success':
                print(f"[SUCCESS] Kết bạn thành công với uid: {uid}")
            elif result == 'already_friends':
                print(f"[SKIPPED] Đã kết bạn hoặc đã gửi lời mời - uid: {uid}")
            elif result == 'no_button':
                print(f"[FAILED] Không tìm thấy nút kết bạn - uid: {uid}")
            else:
                print(f"[ERROR]  {result} - uid: {uid}")

            if i < len(uids):
                delay = random.randint(20, 30)
                print(f"Chờ {delay}s trước khi xử lý UID tiếp theo...")
                time.sleep(delay)

    finally:
        driver.quit()
        print("\n\n[Done] Tool đã hoàn thành!")


def main():
    """Main entry point"""
    while True:
        main_menu()

        try:
            choice = input("Chọn chức năng (1-3): ").strip()

            if choice == '1':
                cookie_file = menu_select_cookie()
                if cookie_file:
                    cookie_string = load_cookie_file(cookie_file)
                    run_tool(cookie_string)
                else:
                    print("[!] Vui lòng lưu cookie trước!")

            elif choice == '2':
                cookie_string = input_cookie_string()
                if not cookie_string:
                    print("[ERROR] Cookie không được để trống!")
                    continue

                name = input("\nNhập tên cookie (không cần .txt): ").strip()
                if not name:
                    print("[ERROR] Tên cookie không được để trống!")
                    continue

                save_cookie_file(name, cookie_string)

            elif choice == '3':
                print("\n[Goodbye!]\n")
                break

            else:
                print("[!] Chọn từ 1 đến 3!")

        except KeyboardInterrupt:
            print("\n\n[Interrupted] Thoát!\n")
            break
        except Exception as e:
            print(f"\n[ERROR] {e}\n")


if __name__ == '__main__':
    main()