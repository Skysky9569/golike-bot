# Kế hoạch phát triển Tool Golike Facebook

## Tổng quan

Phát triển tool Golike Facebook tương tự tool TikTok hiện tại, hỗ trợ:
- Nhận job từ API Golike
- Thực hiện job bằng Facebook API (requests)
- Hoàn thành job và nhận tiền

## Các loại job hỗ trợ

| Type | Mô tả | API Facebook |
|------|-------|--------------|
| `like` | Like reel | `FB_API.REACTION('LIKE', object_id)` |
| `like_page` | Like page | `FB_API.FOLLOW(object_id)` |
| `facebook_like_v1` | Like bài viết | `FB_API.REACTION('LIKE', object_id)` |
| `comment` | Comment bài viết | `FB_API.CMT(content, object_id)` |
| `follow` | Follow người dùng | `FB_API.FOLLOW(object_id)` |
| `reaction` | Reaction | `FB_API.REACTION(reaction_type, object_id)` |

## Cấu trúc module

```
pythonadb/
├── golike_core/              # Module chung
│   ├── __init__.py
│   ├── api_client.py         # Golike API client
│   ├── security.py           # Credential, validation
│   ├── logging.py            # Logging system
│   ├── config.py             # Configuration
│   └── error_handling.py     # Error handling
├── golike_tiktok/            # TikTok specific
│   ├── __init__.py
│   ├── tiktok_automation.py  # UI automation
│   └── tiktok_client.py      # TikTok logic
├── golike_facebook/          # Facebook specific
│   ├── __init__.py
│   ├── fb_web_api.py         # Facebook API (refactor từ FB_WEB_API.py)
│   └── facebook_client.py    # Facebook logic
├── main.py                   # Main menu
└── config/                   # Config files
    ├── adb_config.json
    └── app_config.json
```

## API Golike Facebook

| Hành động | Endpoint | Method | Params |
|-----------|----------|--------|--------|
| Lấy danh sách account | `/api/fb-account` | GET | `limit=200` |
| Lấy job | `/api/advertising/publishers/get-jobs-2026` | GET | `fb_id`, `server`, `low_job` |
| Hoàn thành job | `/api/advertising/publishers/complete-jobs-2026` | POST | `object_id`, `job_id`, `type`, `uid`, `users_fb_account_id`, `users_advertising_id` |
| Báo cáo/Skip job | `/api/report/send` | POST | `users_advertising_id`, `type`, `fb_id`, `error_type`, `provider` |

## Các bước implement

### Phase 1: Tạo module chung (golike_core)

1. **api_client.py**
   - `GolikeAPIClient` class
   - Methods: `get_accounts()`, `get_jobs()`, `complete_job()`, `report_job()`
   - Support cả TikTok và Facebook

2. **security.py**
   - `CredentialManager` - Mã hóa/lưu token, cookie
   - `InputValidator` - Validate input
   - `SecureHeaderBuilder` - Build headers

3. **logging.py**
   - `AppLogger` - Logging với màu sắc
   - `ColoredFormatter` - Format log

4. **config.py**
   - `AppConfig` - Cấu hình ứng dụng
   - Load từ environment/file

5. **error_handling.py**
   - `ErrorHandler` - Xử lý lỗi tập trung
   - `RetryPolicy` - Chính sách retry
   - Custom exceptions

### Phase 2: Refactor TikTok vào module

1. Di chuyển code từ `golikebydom_complete_demo.py` vào `golike_tiktok/`
2. Tạo `tiktok_client.py` với `TikTokJobProcessor`
3. Giữ nguyên `tiktok_automation.py`

### Phase 3: Tạo module Facebook

1. **fb_web_api.py**
   - Refactor từ `FB_WEB_API.py`
   - `FacebookSession`, `GenData`, `FB_API` classes

2. **facebook_client.py**
   - `FacebookJobProcessor` class
   - Methods cho mỗi type job:
     - `_like_post(object_id)`
     - `_like_page(object_id)`
     - `_comment(object_id, content)`
     - `_follow(object_id)`
     - `_reaction(object_id, reaction_type)`

### Phase 4: Main menu

1. **main.py**
   - Menu chính với TikTok và Facebook
   - Xử lý cookie Facebook (nhập + lưu)
   - Quản lý ADB (chỉ cho TikTok)

2. Menu structure:
   ```
   ════════════════════════════════════════════════
   👑 Tool Đóm Remake: 💀 Golike 💀
   ════════════════════════════════════════════════
   🥇 Nhập 1 để vào Tool TikTok
   📱 Nhập 2 để vào Tool Facebook
   🥈 Nhập 3 Để Xóa Authorization Hiện Tại
   ⚙️  Nhập 4 để xem cấu hình bảo mật
   📊 Nhập 5 để xem Logs
   🧪 Nhập 6 để chạy Tests
   🔧 Nhập 7 để Debug Mode
   ════════════════════════════════════════════════
   ```

### Phase 5: Testing

1. Unit tests cho từng module
2. Integration tests cho API
3. End-to-end tests cho flow hoàn chỉnh

## Lưu ý quan trọng

1. **Cookie Facebook**: Cần lưu an toàn như authorization token
2. **object_id**: Sử dụng trực tiếp từ API Golike
3. **Error handling**: Retry khi thất bại, skip job sau 2 lần
4. **Logging**: Log chi tiết để debug
5. **Security**: Validate input, mã hóa credential
