# 📱 Hướng Dẫn Cài Đặt Bot Golike Facebook Trên Điện Thoại

> Bot chạy hoàn toàn bằng HTTP Request (không cần ADB, không cần máy tính).
> Bạn có thể treo bot 24/7 ngay trên điện thoại cá nhân để tự động kiếm xu.

---

## 📋 Yêu Cầu Chung

| Thành phần | Mô tả |
|---|---|
| **File chính** | `test_golike_fb_web.py` |
| **File phụ thuộc** | `FB_WEB_API_FIXED.py` |
| **File cấu hình** | `single_mode_accounts.json` (tự tạo khi chạy) |
| **Python** | Python 3.8 trở lên |
| **Thư viện bắt buộc** | `requests`, `urllib3` |
| **Thư viện tùy chọn** | `curl_cffi` (bypass Cloudflare mạnh hơn) |

### Thông tin cần chuẩn bị trước khi chạy:
1. **Golike Bearer Token** — Lấy từ trang [app.golike.net](https://app.golike.net), mở DevTools (F12) > Network > copy header `authorization`.
2. **Cookie Facebook** — Lấy từ trình duyệt đã đăng nhập Facebook, mở DevTools (F12) > Application > Cookies > copy toàn bộ cookie string.

---

## 🤖 Phần 1: Cài Đặt Trên Android (Termux)

### Bước 1: Tải và cài đặt Termux

- Tải **Termux** từ [F-Droid](https://f-droid.org/en/packages/com.termux/) (khuyên dùng, bản mới nhất).
- **KHÔNG** tải từ Google Play Store vì bản đó đã lỗi thời và không được cập nhật.
- Mở Termux sau khi cài xong.

### Bước 2: Cập nhật hệ thống và cài Python

Chạy từng lệnh sau trong Termux (copy và dán vào):

```bash
# Cập nhật hệ thống Termux
pkg update -y && pkg upgrade -y

# Cài đặt Python, Git và các công cụ cần thiết
pkg install python git openssl -y
```

### Bước 3: Cài đặt thư viện Python

```bash
# Cài thư viện bắt buộc
pip install requests urllib3

# (Tùy chọn) Cài curl_cffi để bypass Cloudflare mạnh hơn
# Lưu ý: curl_cffi có thể cần thêm thời gian biên dịch trên Termux
pip install curl-cffi
```

> **Lưu ý:** Nếu `curl-cffi` báo lỗi khi cài trên Termux, bạn có thể bỏ qua bước này.
> Bot vẫn hoạt động bình thường nhờ cơ chế tự động fallback về thư viện `requests`.

### Bước 4: Tải code bot về điện thoại

**Cách 1: Dùng Git (khuyên dùng)**
```bash
# Clone repo về thư mục hiện tại
git clone https://github.com/Skysky9569/golike-bot.git
cd golike-bot
```

**Cách 2: Copy thủ công từ máy tính**
```bash
# Tạo thư mục chứa code
mkdir -p ~/golike-bot && cd ~/golike-bot
```
Sau đó copy 2 file `test_golike_fb_web.py` và `FB_WEB_API_FIXED.py` vào thư mục này.
Bạn có thể dùng ứng dụng quản lý file trên Android để copy, hoặc dùng lệnh `scp`/`rsync` nếu quen.

**Cách 3: Tải trực tiếp qua Termux**
Nếu bạn đã upload file lên đâu đó (Google Drive, GitHub, v.v.), có thể dùng `wget` hoặc `curl`:
```bash
mkdir -p ~/golike-bot && cd ~/golike-bot
# Thay URL bằng link thực tế của bạn
wget <URL_FILE_test_golike_fb_web.py>
wget <URL_FILE_FB_WEB_API_FIXED.py>
```

### Bước 5: Chạy bot

```bash
cd ~/golike-bot
python test_golike_fb_web.py
```

Bot sẽ hiển thị các bước cấu hình:
1. Nhập **Golike Bearer Token**.
2. Chọn phương thức nhập Cookie:
   - `[1]` Lấy từ file đã lưu (lần chạy sau).
   - `[2]` Nhập trực tiếp bằng tay (lần đầu).
3. Dán **Cookie Facebook** vào.
4. Chọn tài khoản Golike tương ứng.
5. Bot bắt đầu tự động nhận job và làm nhiệm vụ!

### Bước 6: Chạy bot ở chế độ nền (Treo 24/7)

Để bot chạy liên tục ngay cả khi tắt màn hình hoặc chuyển sang app khác:

**Cách 1: Dùng `nohup` (đơn giản nhất)**
```bash
nohup python test_golike_fb_web.py > bot_log.txt 2>&1 &
```
- Bot sẽ chạy nền, log ghi vào file `bot_log.txt`.
- Xem log: `tail -f bot_log.txt`
- Dừng bot: `pkill -f test_golike_fb_web.py`

**Cách 2: Dùng `tmux` (quản lý tốt hơn)**
```bash
# Cài tmux
pkg install tmux -y

# Tạo session mới
tmux new -s golike

# Chạy bot trong session
python test_golike_fb_web.py

# Để thoát session mà bot vẫn chạy: nhấn Ctrl+B rồi nhấn D
# Để quay lại session: 
tmux attach -t golike
```

**Cách 3: Dùng Termux Wake Lock (giữ điện thoại không ngủ)**
```bash
# Giữ Termux chạy khi tắt màn hình
termux-wake-lock

# Chạy bot
python test_golike_fb_web.py

# Khi muốn tắt wake lock
termux-wake-unlock
```

### Mẹo Termux hữu ích

| Lệnh | Mô tả |
|---|---|
| `termux-wake-lock` | Giữ điện thoại không ngủ |
| `tmux new -s golike` | Tạo session tmux mới |
| `tmux attach -t golike` | Quay lại session đang chạy |
| `tail -f bot_log.txt` | Xem log bot trực tiếp |
| `pkill -f test_golike` | Dừng bot đang chạy nền |

---

## 🍎 Phần 2: Cài Đặt Trên iPhone / iPad (iSH Shell)

### Bước 1: Tải và cài đặt iSH Shell

- Mở **App Store** trên iPhone/iPad.
- Tìm kiếm **"iSH Shell"** và tải về (miễn phí).
- Mở ứng dụng iSH Shell sau khi cài xong.

> **Lưu ý:** iSH Shell giả lập môi trường Linux (Alpine Linux) trên iOS.
> Tốc độ có thể chậm hơn so với Termux trên Android do giới hạn của iOS.

### Bước 2: Cập nhật hệ thống và cài Python

Chạy từng lệnh sau trong iSH Shell:

```bash
# Cập nhật hệ thống
apk update && apk upgrade

# Cài đặt Python 3 và pip
apk add python3 py3-pip

# Cài đặt Git (tùy chọn)
apk add git

# Cài đặt OpenSSL (hỗ trợ kết nối HTTPS)
apk add openssl
```

### Bước 3: Cài đặt thư viện Python

```bash
# Cài thư viện bắt buộc
pip3 install requests urllib3
```

> **Lưu ý quan trọng cho iOS:**
> - `curl-cffi` **KHÔNG** hoạt động trên iSH Shell vì thiếu thư viện native.
> - Bot vẫn chạy bình thường nhờ cơ chế fallback về `requests` + `verify=False`.
> - Không cần lo lắng, bot đã được thiết kế để xử lý trường hợp này tự động.

### Bước 4: Tải code bot

**Cách 1: Dùng Git**
```bash
git clone https://github.com/Skysky9569/golike-bot.git
cd golike-bot
```

**Cách 2: Copy thủ công**

Trên iPhone, bạn có thể dùng app **Files** (Tệp) để copy file vào thư mục của iSH:
1. Mở iSH Shell, gõ `pwd` để biết đường dẫn hiện tại (thường là `/root`).
2. Tạo thư mục: `mkdir -p ~/golike-bot`
3. Trong app **Files** của iOS, tìm mục **iSH** ở thanh bên trái.
4. Copy 2 file `test_golike_fb_web.py` và `FB_WEB_API_FIXED.py` vào thư mục `root/golike-bot`.

**Cách 3: Tải trực tiếp**
```bash
mkdir -p ~/golike-bot && cd ~/golike-bot
# Cài wget nếu chưa có
apk add wget
# Thay URL thực tế
wget <URL_FILE_test_golike_fb_web.py>
wget <URL_FILE_FB_WEB_API_FIXED.py>
```

### Bước 5: Chạy bot

```bash
cd ~/golike-bot
python3 test_golike_fb_web.py
```

Quy trình cấu hình giống hệt như trên Android:
1. Nhập **Golike Bearer Token**.
2. Chọn `[2]` để nhập Cookie trực tiếp.
3. Dán **Cookie Facebook**.
4. Chọn tài khoản Golike.
5. Bot bắt đầu chạy tự động!

### Bước 6: Chạy bot ở chế độ nền trên iOS

**Cách 1: Dùng `nohup`**
```bash
nohup python3 test_golike_fb_web.py > bot_log.txt 2>&1 &
```

**Cách 2: Dùng `tmux`**
```bash
# Cài tmux
apk add tmux

# Tạo session và chạy bot
tmux new -s golike
python3 test_golike_fb_web.py

# Thoát session: Ctrl+B rồi nhấn D
# Quay lại: tmux attach -t golike
```

> **Lưu ý quan trọng cho iOS:**
> - iOS có thể tự động dừng iSH Shell khi chạy nền quá lâu do giới hạn hệ điều hành.
> - Để giữ bot chạy liên tục, hãy **tắt chế độ tự động khóa màn hình** trong **Cài đặt > Màn hình & Độ sáng > Tự động khóa > Không bao giờ**.
> - Hoặc cắm sạc và để điện thoại mở màn hình.

---

## ❓ Câu Hỏi Thường Gặp (FAQ)

### Q: Lỗi `SSL: CERTIFICATE_VERIFY_FAILED` khi chạy?
**A:** Bot đã tự động xử lý lỗi này bằng `verify=False`. Nếu vẫn gặp, hãy chạy:
```bash
pip install certifi
```

### Q: Lỗi `ModuleNotFoundError: No module named 'requests'`?
**A:** Chạy lại lệnh cài thư viện:
```bash
# Trên Termux (Android)
pip install requests urllib3

# Trên iSH (iOS)
pip3 install requests urllib3
```

### Q: Lỗi Cloudflare 403 Forbidden khi gọi API Golike?
**A:** Cài thêm `curl-cffi` (chỉ hỗ trợ trên Android/Termux):
```bash
pip install curl-cffi
```
Nếu không cài được, hãy thử chạy lại sau vài phút (Cloudflare có thể tạm chặn IP).

### Q: Làm sao lấy Cookie Facebook?
**A:** 
1. Mở trình duyệt (Chrome/Safari) trên điện thoại hoặc máy tính.
2. Đăng nhập Facebook.
3. Truy cập trang: `chrome://settings/cookies/detail?site=facebook.com` (Chrome) hoặc dùng tiện ích **EditThisCookie**.
4. Copy toàn bộ chuỗi cookie (dạng: `datr=xxx;sb=xxx;c_user=xxx;xs=xxx;fr=xxx;`).

### Q: Làm sao lấy Golike Bearer Token?
**A:**
1. Đăng nhập [app.golike.net](https://app.golike.net).
2. Mở DevTools (F12 trên máy tính, hoặc dùng trình duyệt Kiwi Browser trên Android).
3. Vào tab **Network** > bấm vào bất kỳ request nào tới `gateway.golike.net`.
4. Tìm header **`authorization`** và copy giá trị `Bearer eyJ0...`.

### Q: Bot có an toàn không? Có bị checkpoint Facebook không?
**A:** Bot đã được thiết kế với các biện pháp giảm thiểu rủi ro:
- Delay ngẫu nhiên 4-8 giây giữa mỗi thao tác.
- Delay ngẫu nhiên 5-10 giây giữa mỗi job.
- Sử dụng `curl_cffi` giả lập TLS fingerprint của Chrome thật.
- Tuy nhiên, **KHÔNG CÓ** bot nào đảm bảo 100% an toàn. Hãy sử dụng tài khoản phụ.

---

## 📊 So Sánh Nền Tảng

| Tiêu chí | Android (Termux) | iOS (iSH Shell) |
|---|---|---|
| **Tốc độ** | ⚡ Nhanh | 🐢 Chậm hơn (giả lập) |
| **Chạy nền** | ✅ Rất tốt (tmux + wake-lock) | ⚠️ Hạn chế (iOS giới hạn) |
| **curl_cffi** | ✅ Hỗ trợ | ❌ Không hỗ trợ |
| **Dễ cài đặt** | ✅ Dễ | ✅ Dễ |
| **Ổn định 24/7** | ✅ Rất ổn | ⚠️ Cần giữ màn hình mở |
| **Khuyên dùng** | 🌟🌟🌟🌟🌟 | 🌟🌟🌟 |

> **Kết luận:** Nếu có cả 2 thiết bị, ưu tiên chạy trên **Android + Termux** để có hiệu suất tốt nhất.
