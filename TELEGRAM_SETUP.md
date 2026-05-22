# Telegram Notification Setup

Khi tài khoản đạt giới hạn 100 jobs/ngày, bot sẽ gửi thông báo qua Telegram.

## Cài đặt

### 1. Tạo bot Telegram

1. Mở Telegram, tìm **@BotFather**
2. Gửi lệnh `/newbot`
3. Nhập tên bot (ví dụ: `GoLike Bot`)
4. Nhập username cho bot (phải kết thúc bằng `bot`, ví dụ: `golike_notifier_bot`)
5. Copy **Bot Token** (dạng `123456:ABC-def...`)

### 2. Lấy Chat ID

1. Tìm Chat ID của bạn:
   - Mở Telegram, tìm **@userinfobot** hoặc **@myidbot**
   - Bot sẽ trả về Chat ID (dạng số, ví dụ: `123456789`)

2. Hoặc lấy từ web:
   - Truy cập: `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates`
   - Tìm `"chat":{"id":12345678...`

### 3. Cấu hình trong GoLike

Chạy file setup:
```bash
python setup_telegram.py
```

Hoặc chỉnh sửa `config_golike_sele.json`:
```json
{
  "telegram_enabled": true,
  "telegram_bot_token": "123456:ABC-def...",
  "telegram_chat_id": "123456789"
}
```

### 4. Test

Gửi lệnh:
```bash
python -c "from telegram_notifier import notify_job_limit; notify_job_limit('BOT_TOKEN', 'CHAT_ID', 'Test', '123')"
```

## Files created

- `telegram_notifier.py` - Module gửi thông báo Telegram
- `setup_telegram.py` - Script cấu hình
- `TELEGRAM_SETUP.md` - Documentation này

## Usage

Khi tài khoản đạt 100 jobs/ngày, bot sẽ gửi thông báo:
```
🚨 GoLike Job Limit Alert
Account: Nick Số 1
UID: 100093602988096
Status: Đã đạt giới hạn 100 jobs/ngày
Time: 2026-05-21 15:30:45
Vui lòng chuyển tài khoản hoặc đợi mai.
```
