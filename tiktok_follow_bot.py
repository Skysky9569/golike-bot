import uiautomator
import time
import logging

# Cấu hình logging để theo dõi hoạt động
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def tiktok_auto_follow():
    """
    Hàm tự động theo dõi người dùng trên TikTok sử dụng UI Automator 2
    """
    try:
        # Kết nối tới thiết bị
        device = uiautomator.connect()
        logger.info("Đã kết nối tới thiết bị")

    except Exception as e:
        logger.error(f"Lỗi kết nối thiết bị: {e}")
        return

    # Vòng lặp tự động theo dõi
    follow_count = 0
    max_follows = 10  # Số lượng theo dõi tối đa trong một lần chạy

    while follow_count < max_follows:
        try:
            # Tìm nút theo dõi trên TikTok
            # Thường có content-desc="Follow" hoặc text="Follow"
            follow_button = device.xpath('//android.widget.Button[@content-desc="Follow"]')

            if follow_button.exists:
                follow_button.click()
                logger.info(f"Đã theo dõi người dùng thứ {follow_count + 1}")
                follow_count += 1

                # Đợi một chút giữa các lần nhấn để tránh bị chặn
                time.sleep(3)
            else:
                logger.warning("Không tìm thấy nút theo dõi")
                break

        except Exception as e:
            logger.error(f"Lỗi khi theo dõi: {e}")
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