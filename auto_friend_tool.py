"""
Auto Friend Tool - Kết bạn Facebook tự động qua Selenium + CDP
"""
import time
import json
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


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
                'expires': int(time.time()) + 86400  # +24 hours
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

    # Mở facebook.com trước khi set cookies
    driver.get('https://www.facebook.com')
    time.sleep(2)

    # Enable Network domain trước khi set cookies
    driver.execute_cdp_cmd('Network.enable', {})

    # Parse và inject cookies qua CDP
    cookies = parse_cookies(cookie_string)
    for cookie in cookies:
        result = driver.execute_cdp_cmd('Network.setCookie', cookie)
        print(f"[DEBUG] Set cookie {cookie['name']}: {result}")

    # Reload để cookies có hiệu lực
    driver.refresh()
    time.sleep(3)

    # Verify cookies đã set
    driver.get('https://www.facebook.com')
    time.sleep(2)

    return driver


def send_friend_request(driver: webdriver.Chrome, uid: str) -> str:
    """
    Gửi lời mời kết bạn cho một UID
    Trả về: 'success', 'already_friends', 'no_button', hoặc 'error'
    """
    try:
        url = f'https://www.facebook.com/profile.php?id={uid}'
        driver.get(url)
        time.sleep(random.uniform(3, 5))

        # Chờ nút kết bạn xuất hiện (Facebook dùng "Thêm bạn bè" hoặc "Kết bạn")
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

            # Click nút kết bạn
            driver.execute_script("arguments[0].click();", friend_button)
            time.sleep(2)

            # Check xem có popup "Gửi lời mời" không (lời mời đã tồn tại)
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


def main():
    print("=" * 60)
    print("AUTO FRIEND TOOL - Kết bạn Facebook tự động")
    print("=" * 60)

    # Step 1: Nhập cookies
    print("\n[Dán cookie của bạn (dạng: name=value; name2=value2;)):")
    print("[Nhấn Enter 2 lần để kết thúc input]\n")

    cookie_lines = []
    while True:
        line = input()
        if line == '' and cookie_lines:
            break
        cookie_lines.append(line)

    cookie_string = ' '.join(cookie_lines)

    if not cookie_string:
        print("[ERROR] Cookie không được để trống!")
        return

    # Step 2: Nhập danh sách UID
    print("\n\n[Nhập UID (1 dòng = 1 UID), nhấn Enter để kết thúc]:\n")

    uids = []
    while True:
        uid = input().strip()
        if uid == '':
            break
        uids.append(uid)

    if not uids:
        print("[ERROR] Không có UID để xử lý!")
        return

    print(f"\n[Bắt đầu xử lý {len(uids)} UID...]\n")
    time.sleep(2)

    # Step 3: Khởi tạo driver
    driver = setup_driver(cookie_string)

    try:
        # Step 4: Xử lý từng UID
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

            # Delay random 20-30s giữa các UID
            if i < len(uids):
                delay = random.randint(20, 30)
                print(f"⏰ Chờ {delay}s trước khi xử lý UID tiếp theo...")
                time.sleep(delay)

    finally:
        driver.quit()
        print("\n\n[Done] Tool đã hoàn thành!")


if __name__ == '__main__':
    main()