# CHANGELOG

## [v1.8.6] - 2026-05-22

### Thêm Mới (Added)
- **Fast Switch Sequential Single Mode (Chế độ chạy đơn nối tiếp mượt mà)**:
  - Cho phép nhập danh sách Cookie & UID một lần để chạy nối tiếp (lưu tại `multi_accounts.json`).
  - Khi một tài khoản gặp Rate Limit (100 jobs/ngày), hệ thống tự động đăng xuất và điều khiển Chrome chuyển sang tài khoản tiếp theo.
  - Vượt qua vòng bắt Captcha lần 2, không cần khởi động lại Selenium.
- **Tính năng Khóa Server (Server Lock)**:
  - Bổ sung tuỳ chọn nhập đích danh máy chủ muốn chạy (VD: `SV1`, `SV2`).
  - Nếu đã nhập, tool sẽ tự động khóa và chuyển sang thẻ máy chủ này khi quét job, đồng thời vô hiệu hóa tính năng auto-switch sau X phút để tránh trôi job.

### Tối Ưu (Optimized)
- **Chống lỗi thao tác quá nhanh ở SV1 (Anti-Spam)**:
  - Khắc phục tình trạng spam nút Tải lại (`loader-new`).
  - Tool tự động nhận diện màn hình. Khi ở `SV1`, thay vì spam click `loader-new`, tool sẽ đứng hóng (WebDriverWait) để đón lõng Job Auto-push trả về.
  - Chỉ bấm nút Tải lại (Refresh) khi máy chủ hiện hành là `SV2`.
- **Thông báo Telegram chi tiết**: Tích hợp thông báo qua Telegram, gửi kèm UID tài khoản cụ thể bị rate limit 100 jobs.

### Sửa Lỗi (Fixed)
- Sửa lỗi ngốn RAM và văng quá nhiều popup khi Auto-Switch Server bị treo.
