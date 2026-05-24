# Auto Friend Tool - Kết bạn Facebook tự động

## Cách sử dụng

### 1. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 2. Chạy tool
```bash
python main.py
```

### 3. Menu chức năng

**Option 1: Chạy với cookie có sẵn**
- Hiện danh sách cookies đã lưu
- Chọn số cookie muốn dùng
- Nhập danh sách UID (1 dòng/UID)
- Tool tự động xử lý

**Option 2: Lưu cookie mới**
- Paste cookie string (dạng: `datr=xxx; c_user=xxx; xs=xxx;...`)
- Nhập tên cookie (ví dụ: `account_main`)
- File sẽ được lưu vào `cookies/{tên}.txt`

**Option 3: Thoát**

## Cấu trúc folder
```
auto-friend/
├── main.py              # Tool chính
├── requirements.txt     # Dependencies
├── cookies/             # Folder chứa cookie files
│   ├── account_main.txt
│   └── account_backup.txt
```

## Lấy cookie từ Facebook

1. Đăng nhập Facebook trên Chrome
2. F12 → Application → Cookies → https://www.facebook.com
3. Copy các cookies: `datr`, `c_user`, `xs`, `sb`, `fr`...
4. Paste vào tool

## Lưu ý
- Delay 20-30s giữa mỗi UID để tránh spam detection
- Kiểm tra nút "Thêm bạn bè" hoặc "Kết bạn" trên profile
- Tool sẽ bỏ qua UID không có nút kết bạn