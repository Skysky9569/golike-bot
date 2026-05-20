# Tái cấu trúc hệ thống GoLike

## Cấu trúc thư mục mới

```
project/
├── golike_core/
│   ├── __init__.py
│   ├── config.py
│   ├── security.py
│   ├── logging.py
│   └── modules/
│       ├── __init__.py
│       ├── config_manager.py
│       ├── job_processor.py
│       ├── facebook_automation.py
│       ├── golike_handler.py
│       ├── browser_manager.py
│       ├── account_manager.py
│       └── task_manager.py
├── main.py
└── main_restructured.py
```

## Mô tả các module

### 1. Module quản lý cấu hình (config_manager.py)
- Xử lý cấu hình hệ thống
- Quản lý các thiết lập delay, timeout
- Xử lý file cấu hình JSON

### 2. Module xử lý tác vụ (job_processor.py)
- Xử lý các tác vụ Facebook (follow, like, like_page, v.v.)
- Quản lý kết quả và báo cáo

### 3. Module tự động hóa (facebook_automation.py)
- Tự động hóa trình duyệt
- Quản lý cookie và session

### 4. Module xử lý GoLike (golike_handler.py)
- Đăng nhập và điều hướng GoLike
- Xử lý giao diện người dùng

### 5. Module trình duyệt (browser_manager.py)
- Quản lý trình duyệt Chrome
- Xử lý các thao tác Selenium

## Cách sử dụng

1. Chạy file main_restructured.py để sử dụng phiên bản tái cấu trúc
2. Cấu hình được lưu trong golike_config_sample.json
3. Các module được tổ chức theo mô-đun để dễ bảo trì và mở rộng