# Hướng Dẫn Chạy Auto TikTok Trên iOS (Tối Giản 1 File Python)

Để chạy Auto TikTok trên iPhone/iPad (chưa Jailbreak) mượt mà như Android, chúng ta sử dụng cơ chế **WebDriverAgent (WDA)** kết hợp với thư viện **tidevice**. Bạn **chỉ cần Xcode 1 lần duy nhất** để cài đặt, sau đó không cần bật lại nữa.

---

## 🛠 BƯỚC 1: Cài đặt thư viện Python (Máy Mac)
Mở Terminal và chạy lệnh sau để tải thư viện giao tiếp với iPhone:
```bash
python3 -m pip install -U facebook-wda tidevice
```

---

## 📱 BƯỚC 2: Cài đặt WebDriverAgent vào iPhone (Chỉ làm 1 lần)
Apple cấm các phần mềm tự click màn hình, nên ta phải tự "Build" một app có tên là WebDriverAgent (WDA) vào máy để nó click hộ.

1. Tải source code WDA về máy Mac:
   ```bash
   git clone https://github.com/appium/WebDriverAgent.git
   cd WebDriverAgent
   ```
2. Mở file `WebDriverAgent.xcodeproj` bằng **Xcode**.
3. Cắm iPhone vào máy Mac.
4. Chọn project `WebDriverAgentRunner`, vào tab **Signing & Capabilities**:
   - Tích chọn `Automatically manage signing`.
   - Chọn Team là tài khoản Apple ID của bạn.
   - Đổi Bundle Identifier thành một tên bất kỳ (ví dụ: `com.tenban.wda.runner`). **Nhớ lưu lại Bundle ID này**.
5. Chọn đích đến là iPhone của bạn, ấn nút **Play (Build)**.
6. Mở iPhone: **Cài đặt -> Cài đặt chung -> Quản lý VPN & Thiết bị** -> Bấm tin cậy tài khoản của bạn.
*(Xong bước này, bạn có thể tắt Xcode đi cho nhẹ máy)*

---

## 🚀 BƯỚC 3: Khởi động WDA (Làm mỗi khi cắm cáp chuẩn bị auto)
Mở Terminal và gõ lệnh sau để đánh thức WDA trên điện thoại:
```bash
tidevice wdaproxy -B <Bundle_ID_của_bạn_ở_bước_2> -p 8100
```
*Ví dụ:* `tidevice wdaproxy -B com.phu.wda.runner -p 8100`

Kiểm tra xem WDA đã chạy chưa bằng cách mở Terminal mới và gõ:
```bash
curl http://localhost:8100/status
```
*(Nếu thấy chữ "success" và "ready: true" là thành công)*

---

## ▶️ BƯỚC 4: Chạy Tool
Bây giờ mọi thứ đã sẵn sàng, bạn chỉ cần chạy Tool như bình thường:
```bash
python3 main.py
```
* Chọn menu **[7] Vào Tool TikTok (iOS - Appium/WDA)**.
* Tool sẽ tự động kết nối qua cổng 8100, mở TikTok, tìm nút và Auto Click cho bạn!
