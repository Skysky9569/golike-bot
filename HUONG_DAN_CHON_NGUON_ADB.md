# Hướng dẫn sử dụng tính năng chọn nguồn ADB

## Tổng quan

Từ phiên bản này trở đi, ứng dụng cho phép người dùng tùy chọn nguồn ADB (Android Debug Bridge) mà ứng dụng sẽ sử dụng. Điều này đặc biệt hữu ích khi bạn có nhiều phiên bản ADB cài đặt (ví dụ: ADB từ Homebrew, ADB cục bộ trong dự án, hoặc ADB tùy chỉnh) và muốn chỉ định rõ phiên bản nào sẽ được dùng.

## Truy cập tính năng

1. Chạy ứng dụng như bình thường
2. Từ menu chính, chọn tùy chọn **4** để vào **ADB WiFi/USB management menu**
3. Trong menu ADB, bạn sẽ thấy tùy chọn mới: **⚙️  Nhập 7 : Chọn nguồn ADB (Homebrew/Local/Custom)**

## Các tùy chọn nguồn ADB

Khi chọn tùy chọn 7, bạn sẽ thấy các lựa chọn sau:

### [1] ADB từ Homebrew (tự động phát hiện)
- Chương trình sẽ tự động tìm kiếm `adb` trong biến môi trường PATH
- Nếu tìm thấy và xác nhận là file adb hợp lệ, nó sẽ được sử dụng
- Đây là lựa chọn được khuyên dùng trên macOS nếu bạn đã cài ADB qua Homebrew (`brew install android-platform-tools`)

### [2] ADB cục bộ trong thư mục dự án
- Chương trình sẽ tìm file `adb` (hoặc `adb.exe` trên Windows) trong thư mục `ADB/` của dự án
- Đường dẫn thường là: `<thư_muc_du_an>/ADB/adb`
- Hữu ích khi bạn muốn sử dụng phiên bản ADB cụ thể được ship cùng với dự án

### [3] Nhập đường dẫn tùy chỉnh
- Cho phép bạn chỉ định đầy đủ đường dẫn tới file adb executable trên máy của mình
- Ví dụ trên macOS: `/opt/homebrew/bin/adb` hoặc `/usr/local/bin/adb`
- Ví dụ trên Windows: `C:\Android\platform-tools\adb.exe`
- Sau khi nhập, chương trình sẽ kiểm tra xem file đó có thực sự là adb hợp lệ không trước khi lưu

### [0] Quay lại
- Quay về menu ADB chính mà không thay đổi gì

## Lưu trữ và sử dụng lựa chọn

- Lựa chọn nguồn ADB của bạn sẽ được lưu tự động trong file `adb_config.json` dưới khóa `selected_adb_path`
- File này nằm trong thư mục gốc của dự án
- Lựa chọn sẽ được duy trì giữa các lần chạy ứng dụng
- Khi khởi tạo `ADBManager`, nó sẽ:
  1. Kiểm tra xem có đường dẫn ADB được lưu trong config không và xem liệu nó có tồn tại và hợp lệ không
  2. Nếu có, sử dụng đường dẫn đó
  3. Nếu không, quay lại логика tự động phát hiện gốc đầu tiên (kiểm tra thư mục ADB cục bộ, sau đó PATH, sau đó config, cuối cùng là hardcoded path)

## Ví dụ sử dụng

### Trên macOS với Homebrew
1. Vào menu ADB → chọn 7 → chọn 1
2. Chương trình sẽ tự động détect `/opt/homebrew/bin/adb` (nếu là đường dẫn đúng) và lưu lại
- Lần sau khi chạy ứng dụng, ADBManager sẽ sử dụng đường dẫn này trực tiếp

### Sử dụng ADB tùy chỉnh
1. Vào menu ADB → chọn 7 → chọn 3
2. Nhập đầy đủ đường dẫn, ví dụ: `/Users/ten_ban/Android/Sdk/platform-tools/adb`
3. Chương trình sẽ verifiction và lưu lại nếu hợp lệ

## Ghi chú quan trọng

- Nếu bạn chọn một nguồn ADB không hợp lệ (file không tồn tại hoặc không phải là adb), chương trình sẽ thông báo lỗi và giữ nguyên lựa chọn cũ
- Luôn đề xuất kiểm tra kết nối ADB sau khi thay đổi nguồn bằng cách sử dụng tùy chọn "Khởi động lại ADB Server" (tùy chọn 1) hoặc kiểm tra thiết bị trong menu ADB chính
- File `adb_config.json` có thể được sửa thủ công nếu cần, nhưng tốt nhất là sử dụng giao diện menu để đảm bảo định dạng đúng

## Khắc phục sự cố

Nếu gặp lỗi "Không tìm thấy adb.exe!" hoặc "Loi ket noi ADB":
1. Quay lại menu ADB → chọn 7 để xem nguồn ADB hiện tại đang được cấu hình
2. Kiểm tra xem đường dẫn đó có tồn tại và là file adb hợp lệ không
3. Nếu không chắc chắn, chọn tùy chọn 1 (ADB từ Homebrew) để позволять hệ thống tự động phát hiện lại
4. Đảm bảo bạn có quyền thực thi trên file adb (trên Linux/macOS: `chmod +x /path/to/adb`)

---
*Cập nhật lần cuối: 2026-06-01*