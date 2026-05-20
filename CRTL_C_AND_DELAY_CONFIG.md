# Cập nhật: Ctrl+C Handling và Delay Config cho Golike FB Selenium

## 📋 Tổng kết

Hai tính năng đã được implement vào file `golikefb_sele.py`:

1. **Ctrl+C Handling** - Đóng Selenium nhưng giữ tool chạy
2. **Delay Config** - File config JSON để tùy chỉnh delay

---

## 1️⃣ Ctrl+C Handling

### **Thay đổi:**

- **Cũ:** Khi ấn Ctrl+C → Tool thoát hoàn toàn (`sys.exit(1)`)
- **Mới:** Khi ấn Ctrl+C → Đóng Selenium → Đợi user ấn Enter → Quay về menu chính

### **Luồng hoạt động:**

```
Ấn Ctrl+C
    ↓
Đóng Selenium drivers
    ↓
Print: "[🛑] Đã nhận Ctrl+C. Đóng Selenium nhưng tool vẫn chạy..."
    ↓
Print: "[💡] Ấn Enter để trở về menu chính hoặc gõ 'exit' để thoát"
    ↓
 User nhập:
    - Enter → "[✓] Trở về menu chính..." → Hiển thị menu
    - "exit" → "[✅] Thoát chương trình..." → cleanup() → sys.exit(0)
```

### **Cấu trúc code:**

```python
# Global flag để kiểm soát việc dừng tool
STOP_FLAG = False

def handle_exit_signal(signum, frame):
    """Xử lý Ctrl+C - chỉ đóng Selenium, tool vẫn chạy"""
    global STOP_FLAG

    print("\n[🛑] Đã nhận Ctrl+C. Đóng Selenium nhưng tool vẫn chạy...")

    # Đóng tất cả trình duyệt đang chạy
    with drivers_lock:
        for drv in active_drivers[:]:
            try:
                drv.quit()
                active_drivers.remove(drv)
            except:
                pass

    print("[ℹ️] Selenium đã đóng. Tool vẫn tiếp tục chạy.")
    print("[💡] Ấn Enter để trở về menu chính hoặc gõ 'exit' để thoát.")

    # Đợi user ấn Enter để trở về menu
    try:
        user_input = input().strip().lower()
        if user_input == 'exit':
            print("[✅] Thoát chương trình...")
            cleanup()
            sys.exit(0)
        else:
            print("[✓] Trở về menu chính...")
    except:
        pass

    STOP_FLAG = True
    return None  # Không gọi sys.exit()
```

### **Thiết lập menu vòng lặp:**

```python
if __name__ == "__main__":
    # Load config delay khi khởi động
    load_delay_config()

    while True:  # Vòng lặp menu
        print("\n" + "="*65)
        print("🔥 HỆ THỐNG AUTO CÀY COIN GOLIKE & FACEBOOK v" + CURRENT_VERSION + " 🔥")
        print("="*65)
        print("1. Chạy ĐƠN LẺ 1 tài khoản")
        print("2. Chạy SONG SONG many tài khoản")
        print("3. Setup Delay Config")
        print("0. Thoát chương trình")
        print("-"*65)

        try:
            lua_chon = input("👉 Lựa chọn (1/2/3/0): ").strip()

            if lua_chon == "0":
                print("\n[✅] Tạm biệt!")
                cleanup()
                break  # Thoát vòng lặp
            elif lua_chon == "3":
                setup_delay_config()
                load_delay_config()
                continue
            elif lua_chon == "2":
                run_parallel_mode()
            else:
                run_single_mode()
        except KeyboardInterrupt:
            print("\n[!] Đã nhận Ctrl+C. Không thoát, vui lòng chọn menu...")
        except Exception as e:
            print(f"\n🚨 Lỗi hệ thống khởi chạy: {e}")
```

---

## 2️⃣ Delay Config

### **File config: `config_golike_sele.json`**

```json
{
  "delay_between_jobs": 10,
  "delay_after_api_call": 3.5,
  "delay_after_complete": 4,
  "delay_after_report_error": 1.5,
  "delay_on_job_hunt_retry": 12,
  "delay_between_accounts": 60,
  "wait_for_captcha": 5,
  "timeout_driver_load": 10,
  "timeout_wait_element": 8,
  "sleep_on_reset": 30,
  "sleep_on_hunt_retry": 10
}
```

### **Các tham số delay:**

| Tham số | Mặc định | Mô tả |
|---------|----------|-------|
| `delay_between_jobs` | 10s | Delay giữa các job |
| `delay_after_api_call` | 3.5s | Delay sau khi gọi API Facebook |
| `delay_after_complete` | 4s | Delay sau khi nhấn "Hoàn thành" |
| `delay_after_report_error` | 1.5s | Delay sau khi báo lỗi job |
| `delay_on_job_hunt_retry` | 12s | Delay khi tải lại danh sách job |
| `delay_between_accounts` | 60s | Delay khi chuyển đổi tài khoản |
| `wait_for_captcha` | 5s | Chờ user giải Captcha |
| `timeout_driver_load` | 10s | Timeout tải ChromeDriver |
| `timeout_wait_element` | 8s | Timeout chờ element |
| `sleep_on_reset` | 30s | Sleep khi reset trang |
| `sleep_on_hunt_retry` | 10s | Sleep khi retry hunt job |

### **Menu Setup Delay Config:**

Chọn option **3** trong menu chính:

```
============================================================
CẤU HÌNH DELAY CHO GOLIKE FACEBOOK SELENIUM
============================================================
[File lưu tại: D:\pythonadb\config_golike_sele.json]

Delay giữa các job (giây) [mặc định: 10]: 
Delay sau API call (giây) [mặc định: 3.5]: 
Delay sau khi nhấn Hoàn thành (giây) [mặc định: 4]: 
...
```

---

## 🔄 Files thay đổi

| File | Thay đổi |
|------|----------|
| `golikefb_sele.py` | Sửa signal handler, thêm config functions, thay sleep() |
| `config_golike_sele.json` | **File mới** - Delay config |

---

**Version:** 1.6.1  
**Cập nhật:** 2026-05-17