# Hướng Dẫn Cài Đặt GoLike Bot Trên Termux (Android)

## 📋 Yêu Cầu

- Android 5.0 trở lên
- Ít nhất 2GB RAM
- Kết nối internet
- Storage permission

## 🚀 Cài Đặt

### Bước 1: Cài Termux và Package cần thiết

```bash
# Mở Termux, chạy các lệnh sau:
pkg update && pkg upgrade

# Cài Python, git, requests
pkg install python git requests

# Cài ADB (quan trọng cho TikTok automation)
pkg install android-tools
```

### Bước 2: Clone repository

```bash
# Clone từ GitHub
git clone https://github.com/Skysky9569/golike-bot.git
cd golike-bot

# Cài đặt dependencies
pip install -r requirements.txt
```

### Bước 3: Chạy tool

```bash
# Khởi động
python main.py

# Nếu gặp lỗi encoding, thêm:
export PYTHONIOENCODING=utf-8
python main.py
```

## ⚙️ Cấu Hình

### Lưu Authorization Token

```bash
# Lưu token an toàn
mkdir -p ~/.golike-bot
echo "YOUR_AUTH_TOKEN" > ~/.golike-bot/token
chmod 600 ~/.golike-bot/token
```

### Cấu hình ADB (cho TikTok)

```bash
# Kết nối ADB qua WiFi (nếu dùng với điện thoại khác)
adb connect 192.168.1.XXX:5555

# Kiểm tra kết nối
adb devices
```

## ⚠️ Lưu Ý Quan Trọng

### 1. Selenium Không Hoạt Động
- Termux không chạy được Selenium (không có GUI browser)
- Chỉ sử dụng được **API mode** cho Facebook
- TikTok automation hoạt động qua ADB

### 2. Encoding
Nếu gặp lỗi font tiếng Việt:
```bash
export PYTHONIOENCODING=utf-8
```

### 3. Permission
Termux cần được cấp permission:
```bash
termux-setup-storage
```

### 4. Pin & Battery Optimization
- Tắt battery optimization cho Termux
- Dùng `termux-wake-lock` để tránh sleep

## 🔧 Troubleshooting

### Lỗi: `ModuleNotFoundError: No module named 'requests'`
```bash
pip install requests
```

### Lỗi: `Permission denied`
```bash
chmod +x main.py
termux-setup-storage
```

### Lỗi: `ADB not found`
```bash
pkg install android-tools
export PATH=$PATH:/data/data/com.termux/files/usr/bin
```

### Lỗi: `Connection timeout`
```bash
# Kiểm tra internet
ping google.com

# Thử lại với timeout dài hơn
python main.py --timeout=60
```

## 📦 Packages Cần Thiết

```bash
# Bắt buộc
pkg install python git

# Khuyến nghị
pkg install wget curl nano

# ADB cho TikTok automation
pkg install android-tools

# Python packages
pip install requests selenium playwright
```

## 🎯 Sử Dụng

Sau khi cài xong:

```bash
cd golike-bot
python main.py
```

Menu chính:
- **1**: TikTok automation (cần ADB)
- **2**: Facebook automation (API mode)
- **3**: Facebook Selenium (KHÔNG hoạt động trên Termux)
- **4**: ADB Manager
- **0**: Thoát

## 📝 Tips

1. **Giữ Termux chạy nền**: Dùng `termux-wake-lock`
2. **Copy paste**: Tap 3 lần để paste
3. **Scrolling**: Swipe 2 ngón tay
4. **Keyboard shortcut**: Cài `termux:boot` để auto-start

## 🔗 Links Hữu Ích

- [Termux Wiki](https://wiki.termux.org/)
- [Android ADB](https://developer.android.com/studio/command-line/adb)
- [GitHub Issues](https://github.com/Skysky9569/golike-bot/issues)

---

**Version:** 1.8.1 (Termux Compatible)
**Last Updated:** 2026-05-20
