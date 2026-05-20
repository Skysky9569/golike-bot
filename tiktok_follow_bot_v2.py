import uiautomator2 as u2
import time
import logging

# Cấu hình logging để theo dõi hoạt động
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def connect_device():
    """
    Kết nối tới thiết bị Android hiện tại
    """
    try:
        # Kết nối tới thiết bị hiện tại (thường là thiết bị cục bộ)
        device = u2.connect("127.0.0.1:55555")
        logger.info("Đã kết nối tới thiết bị")
        return device
    except Exception as e:
        logger.error(f"Lỗi kết nối thiết bị: {e}")
        return None

def tiktok_auto_follow():
    """
    Hàm tự động theo dõi người dùng trên TikTok sử dụng UI Automator 2
    """
    device = connect_device()
    if device is None:
        logger.error("Không thể kết nối thiết bị")
        return

    # Vòng lặp tự động theo dõi
    follow_count = 0
    max_follows = 10  # Số lượng theo dõi tối đa trong một lần chạy

    while follow_count < max_follows:
        try:
            # Tìm nút theo dõi trên TikTok
            # Thử tìm theo resource-id thông thường của nút Follow
            follow_button = device(resourceId="com.zhiliaoapp.musically:id/follow")

            # Nếu không tìm thấy theo resource-id, thử tìm theo content-desc
            if not follow_button.exists:
                follow_button = device(text="Follow")

            # Nếu vẫn không tìm thấy, thử tìm theo xpath
            if not follow_button.exists:
                follow_button = device.xpath('//android.widget.Button[contains(@text, "Follow")]')

            if follow_button.exists:
                # Kiểm tra xem đã follow chưa để tránh nhấn nhầm
                # Ở đây ta có thể kiểm tra text của nút
                follow_info = follow_button.info
                button_text = follow_info.get('text', '').lower() if follow_info.get('text') else ''

                # Nếu nút là "Following" hoặc "Đang theo dõi" thì bỏ qua
                if 'following' in button_text or 'đang theo dõi' in button_text or 'followed' in button_text:
                    logger.info(f"Bỏ qua, đã follow rồi (lượt {follow_count + 1})")
                    # Cuộn xuống để đến video tiếp theo
                    device(scrollable=True).scroll.forward(steps=10)
                    time.sleep(2)
                    continue

                # Click nút follow
                follow_button.click()
                logger.info(f"Đã theo dõi người dùng thứ {follow_count + 1}")
                follow_count += 1

                # Đợi một chút giữa các lần nhấn để tránh bị chặn
                time.sleep(3)

                # Cuộn xuống để đến video tiếp theo
                device(scrollable=True).scroll.forward(steps=10)
                time.sleep(2)
            else:
                logger.warning("Không tìm thấy nút theo dõi")
                break

        except Exception as e:
            logger.error(f"Lỗi khi theo dõi (lượt {follow_count + 1}): {e}")
            # Khi có lỗi, vẫn tiếp tục với lượt tiếp theo
            # Cuộn xuống để đến video tiếp theo
            try:
                device(scrollable=True).scroll.forward(steps=10)
                time.sleep(2)
            except:
                pass
            continue

    logger.info(f"Đã hoàn thành theo dõi {follow_count} người dùng")

def main():
    """
    Hàm chính để chạy chương trình
    """
    logger.info("Bắt đầu chương trình tự động theo dõi TikTok")
    tiktok_auto_follow()
    logger.info("Chương trình đã hoàn thành")

if __name__ == "__main__":
    main()