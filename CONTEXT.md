# CONTEXT - Domain Language

This file captures the domain language and key concepts for the GoLike TikTok automation tool.

## Core Concepts

### Job Types
- **Follow Job**: Nhiệm vụ yêu cầu follow một TikTok user. Tool mở link profile và tìm nút "Follow" để click.
- **Like Job**: Nhiệm vụ yêu cầu like một TikTok video. Tool mở link video và tìm nút "Like" (trái tim) để click.

### UI Automation
- **UIAutomator2**: Thư viện Python để tương tác với UI Android. Cần cài đặt trên cả máy tính và thiết bị Android.
- **Element Selector**: Cách để tìm element trên UI. Tool dùng kết hợp nhiều selector (text, resource-id, content-description) để tăng độ tin cậy.
- **Follow Button**: Nút "Follow" trên profile TikTok. Tool tìm theo text "Follow"/"Theo dõi" hoặc resource-id.
- **Like Button**: Nút "Like" (trái tim) trên video TikTok. Tool tìm theo resource-id hoặc content-description.
- **Already Followed/Liked**: Trạng thái khi user đã follow/like target trước đó. Tool sẽ báo cáo fail và skip job trong trường hợp này.

### Retry Logic
- **Retry Count**: Số lần thử lại khi không tìm thấy element. Mặc định: 3 lần.
- **Retry Delay**: Thời gian đợi giữa các lần retry. Mặc định: 2 giây.
- **Verify Delay**: Thời gian đợi sau khi click để verify action thành công. Mặc định: 1 giây.

### Error Handling
- **UI Automation Fail**: Khi không tìm thấy element hoặc click thất bại. Tool sẽ log lỗi và tiếp tục job khác.
- **Already Done**: Khi đã follow/like rồi. Tool sẽ báo cáo fail và skip job.

## Configuration

### ADB Configuration
- **ADB Path**: Đường dẫn đến ADB executable. Mặc định: `D:\pythonadb\ADB\adb.exe`
- **Device ID**: ID thiết bị ADB để kết nối. Nếu None, dùng thiết bị mặc định.
- **Open Method**: Cách mở link (adb/termux/manual/search). Search mode: follow = search trong app, like = ADB.

### Search Mode (Tim kiem user qua thanh search)
- **Search-based Follow**: Mode [4] trong menu ket noi, option [3] trong menu job type. Follow jobs su dung thanh search TikTok app de tim user thay vi mo link. Like jobs van mo link bang ADB.
- **API Integration**: Search mode lay job tu API nhu binh thuong, khong can nhap UID thu cong. Username duoc extract tu link job.
- **Flow Follow**: Lay job tu API → extract username tu link → tap search icon → clear text → go username → tap "Tim kiem" → tap tab "Nguoi dung" → tap user dau tien → click Follow → bao cao complete-jobs.
- **Flow Like**: Lay job tu API → mo link bang ADB → click Like → bao cao complete-jobs.
- **Username Extraction**: Parse @username tu path URL. Link rut gon (vt.tiktok.com) duoc resolve redirect qua HTTP HEAD/GET truoc khi parse.
- **Search Timeout**: Thoi gian cho toi da sau khi search (mac dinh: 5 giay).
- **Search Retry**: So lan thu lai neu khong tim thay ket qua (mac dinh: 3).
- **Ho tro ca Follow va Like jobs**, khac voi phien ban cu chi ho tro Follow.

### UI Automation Configuration
- **UI Automator Device ID**: ID thiết bị để kết nối uiautomator2. Thường trùng với ADB device ID.
- **Follow Selectors**: Danh sách selectors để tìm nút Follow.
- **Like Selectors**: Danh sách selectors để tìm nút Like.
- **Search Selectors**: Danh sách selectors để tìm thanh search, tab "Người dùng", và user item đầu tiên trong kết quả.

## API Integration

### GoLike API
- **Base URL**: `https://gateway.golike.net`
- **Get Jobs Endpoint**: `/api/advertising/publishers/tiktok/jobs`
- **Complete Job Endpoint**: `/api/advertising/publishers/tiktok/complete-jobs`
- **Skip Job Endpoint**: `/api/advertising/publishers/tiktok/skip-jobs`
- **Report Endpoint**: `/api/report/send`

### Job Data Structure
- `id`: Job ID
- `link`: TikTok link
- `type`: Job type ("follow" hoặc "like")
- `object_id`: Target object ID

## Security

### Credential Storage
- **Authorization Token**: Token để xác thực với GoLike API. Được mã hóa và lưu trong file `secure_credentials.enc`.
- **Encryption Method**: XOR + Base64 encoding với key từ machine ID.

### Input Validation
- **IP Validation**: Validate địa chỉ IP (format: xxx.xxx.xxx.xxx)
- **Port Validation**: Validate port number (1-65535)
- **Token Validation**: Validate authorization token (10-500 ký tự)
- **Account ID Validation**: Validate account ID (alphanumeric với _ và -)

## Logging

### Log Levels
- **DEBUG**: Chi tiết về API calls, ADB operations, UI automation
- **INFO**: Thông tin chung về job processing
- **WARNING**: Cảnh báo về job trùng, đã follow/like, retry
- **ERROR**: Lỗi về API, ADB, UI automation

### Log Files
- **Daily Log**: `logs/golikebydom_YYYYMMDD.log`
- **Error Log**: `logs/errors.log`