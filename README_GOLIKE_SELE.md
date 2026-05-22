# GoLike Facebook Selenium - Hướng dẫn sử dụng

## 🚀 Khởi động

```bash
python golikefb_sele.py
```

## 📋 Menu chính

```
1. Chạy ĐƠN LẺ 1 tài khoản (Hỗ trợ cấu hình trực tiếp)
2. Chạy SONG SONG nhiều tài khoản (Đọc từ config_parallel.json)
3. Setup Delay Config
0. Thoát chương trình
```

## ⏱️ Setup Delay Config

Chọn **option 3** để tùy chỉnh thời gian delay giữa các hành động:

- **Delay giữa các job**: Thời gian chờ trước khi tìm job mới (default: 10s)
- **Delay sau API call**: Chờ sau khi gọi API Facebook (default: 3.5s)
- **Delay sau Hoàn thành**: Chờ sau khi nhấn nút Hoàn thành (default: 4s)
- **Delay sau báo lỗi**: Chờ sau khi báo lỗi job (default: 1.5s)
- **Delay khi tải lại job**: Chờ khi không tìm thấy job (default: 12s)
- **Sleep khi reset trang**: Thời gian nghỉ khi refresh lại trang (default: 30s)

Config được lưu vào file `config_golike_sele.json`.

## 🛑 Xử lý Ctrl+C

- **Ấn Ctrl+C**: Đóng Selenium nhưng tool vẫn chạy, quay về menu chính
- **Gõ 0**: Thoát hoàn toàn

## 📁 Files cấu hình

| File | Mô tả |
|------|-------|
| `config_golike_sele.json` | Delay config cho tool |
| `config_parallel.json` | Cấu hình chạy đa luồng |
| `facebook_cookie.enc` | Cookie Facebook đã mã hóa |
| `golike_token.enc` | Token GoLike đã mã hóa |

## 🔧 Tweaks

Bạn có thể chỉnh sửa file `config_golike_sele.json` thủ công để thay đổi delay:

```json
{
  "delay_between_jobs": 15,
  "delay_after_api_call": 5
}
```

**Lưu ý:** Tăng delay nếu tool bị chặn atau rate limit bởi Facebook/Golike.

---

**Version:** 1.6.1