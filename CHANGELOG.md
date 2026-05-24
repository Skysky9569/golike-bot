# CHANGELOG

## [v1.9.9] - 2026-05-24

### Sửa Lỗi Gốc Rễ (Root Fix)
- **Fix REACTION `Empty response from Facebook` — nguyên nhân thật sự**:
  - Facebook `/api/graphql/` **bắt buộc phải có `doc_id` hợp lệ** khi dùng `data=` form-encoded.
  - Gửi `query` field (dù form-encoded hay JSON body) đều bị Facebook **silent reject** → body rỗng.
  - Đã sửa: Quay lại `data=` form-encoded với `doc_id`, nhưng **tự động fetch `doc_id` mới nhất** từ JS bundle mỗi khi khởi tạo session.

### Thêm Mới (Added)
- **`FacebookSession._find_doc_id_from_html()`**: Quét tối đa 25 JS bundle từ `static.xx.fbcdn.net`, tìm `doc_id` của `CometUFIFeedbackReactMutation` bằng 2 regex pattern.
- **Class-level cache `_cached_reaction_doc_id`**: Dùng chung giữa mọi FB_API instance trong cùng tiến trình → chỉ fetch 1 lần duy nhất.
- **Fallback list `_FALLBACK_DOC_IDS`**: 3 doc_id dự phòng khi không tìm được từ JS bundle.
- **Tự động xóa cache** khi gặp lỗi `1675030` hoặc empty response → lần gọi tiếp theo sẽ fetch lại doc_id mới.

## [v1.9.8] - 2026-05-24

### Sửa Lỗi (Fixed)
- **Fix REACTION lỗi `Expecting value: line 1 column 1 (char 0)` (empty response)**:
  - Nguyên nhân: `query` field gửi dạng **form-encoded** (`data=`) không được Facebook chấp nhận → response body rỗng → `response.json()` crash.
  - Đã sửa: Chuyển sang gửi **JSON body** (`json=`, `Content-Type: application/json`). Đây là cách Facebook web app thực sự dùng khi gọi GraphQL.
  - Thêm `json_header` riêng cho REACTION request (header form-encoded và JSON là khác nhau).
- **Cải thiện xử lý lỗi response**:
  - `_format_error()` giờ check `response.text` trống trước khi gọi `.json()`.
  - Log 200 ký tự đầu response khi lỗi để debug dễ hơn.
  - Xử lý riêng trường hợp response không phải JSON.

## [v1.9.7] - 2026-05-24

### Sửa Lỗi (Fixed)
- **Fix chế độ Song Song luôn chọn acc đầu tiên**:
  - Nguyên nhân: selector `div.card.shadow-200.mt-1` cứng không tìm được card đúng trên Golike → `accounts` rỗng hoặc sai → fallback chọn `accounts[0]` cho mọi profile.
  - Đã sửa: Thêm **6 CSS selector dự phòng** tự động thử lần lượt cho đến khi tìm được danh sách acc.
  - Thêm **fallback cuối**: tìm mọi `div.card` bên trong `div.select-account` nếu tất cả selector trước thất bại.

### Cải Tiến (Improved)
- **Thứ tự ưu tiên match acc**: `golike_uid` → `target_fb_uid` → `target_fb_name` (chính xác hơn, rõ lý do match).
- **Extract tên/uid dự phòng**: thử 6 selector con khác nhau để lấy tên, thử 4 attribute khác nhau để lấy uid.
- **Log debug chi tiết**: in ra danh sách toàn bộ acc tìm được (index, name, uid) trước khi chọn → dễ chẩn đoán khi không khớp.
- **Thông báo rõ ràng** khi không match: chỉ dẫn user kiểm tra `golike_uid`/`target_fb_uid`/`target_fb_name` trong config thay vì im lặng chọn acc sai.

## [v1.9.6] - 2026-05-24

### Sửa Lỗi (Fixed)
- **Fix chế độ Song Song lỗi `'str' object has no attribute 'get'`**:
  - Nguyên nhân: `config_parallel.json` có cấu trúc **dict** (chứa key `parallel_accounts` + các delay config), nhưng code đang `json.load()` rồi iterate thẳng kết quả như **list** → mỗi phần tử iterate ra là **string** (tên key của dict) → crash ngay khi gọi `.get()`.
  - Đã sửa: Thêm logic **tự động phát hiện format**:
    - Nếu JSON là **list** → dùng trực tiếp (format cũ).
    - Nếu JSON là **dict** → lấy `parallel_accounts` làm danh sách profile, đồng thời load các delay config vào `CONFIG_DELAY` nếu có.
  - Hiển thị thông báo rõ ràng nếu `parallel_accounts` rỗng hoặc format sai.

## [v1.9.5] - 2026-05-24

### Sửa Lỗi (Fixed)
- **Fix FB API REACTION lỗi 1675030 — `doc_id` hardcode hết hạn**:
  - Nguyên nhân: Facebook thường xuyên thay đổi `doc_id` (Relay persisted query ID). `doc_id: '24198888476452283'` đã bị vô hiệu hóa → FB trả về `api_error_code: 1675030` (Lỗi truy vấn CRITICAL).
  - Đã sửa: **Bỏ hoàn toàn `doc_id`** ra khỏi payload, thay bằng field **`query`** chứa full GraphQL mutation text (`CometUFIFeedbackReactMutation`). Cách này không bị ràng buộc vào bất kỳ version nào của FB Comet.
  - Gọi vẫn giữ nguyên: `fb.REACTION("LIKE", uid)` — không phá vỡ API hiện tại.

### Cải Tiến (Improved)
- **`attribution_id_v2` sinh động theo thời gian thực**:
  - Trước: hardcode timestamp cũ từ năm 2025 → FB có thể từ chối.
  - Nay: timestamp = `int(time.time() * 1000)` + random nonce sinh mỗi request.
- **`variables` dùng `json.dumps()` chuẩn**:
  - Thay thế string concatenation thủ công dễ sinh JSON không hợp lệ.

## [v1.9.1] - 2026-05-22

### Sửa Lỗi (Fixed)
- **Sửa MAX JOB không gửi Telegram + không tự chuyển acc**:
  - Trước đây khi phát hiện max job ở nhánh `if job_limit_reached()` cuối vòng lặp, tool gọi `input()` chặn chương trình → người dùng phải nhấn Enter thủ công, không gửi Telegram, không set `prev_max_job`.
  - Đã sửa: tự động gửi Telegram → set `prev_max_job = True` → `break` sang acc tiếp → chờ 60s → bắt đầu làm việc.
  - Sửa tương tự cho chế độ song song (parallel): nay cũng gửi Telegram khi đạt giới hạn.
- **Sửa lỗi không tìm thấy nick GoLike khi chuyển acc (`golike_uid` vs `uid`)**:
  - `uid` trong `multi_accounts.json` là **Facebook UID** (dùng cho FB API), nhưng dropdown GoLike dùng **GoLike UID** khác hoàn toàn.
  - Thêm field `golike_uid` vào `multi_accounts.json` để phân biệt rõ ràng.
  - Code nay dùng `golike_uid` để khớp nick GoLike trong dropdown, fallback về `uid` nếu chưa có field mới.

### Thêm Mới (Added)
- **Hiển thị cả FB UID và GoLike UID khi chuyển tài khoản**:
  - Log: `🔄 Chuyển sang tài khoản tiếp theo (FB UID: ... | GoLike UID: ...)` để dễ debug.
- **Field `golike_uid` trong `multi_accounts.json`**:
  - Tách biệt FB UID (c_user trong cookie) và GoLike UID (i_user trong cookie) để cấu hình đúng.

## [v1.8.11] - 2026-05-22

### Sửa Lỗi (Fixed)
- **Sửa lỗi nút "Trình duyệt" không tìm thấy**:
  - Thêm hàm `find_browser_button()` thử 9 selector khác nhau (XPATH, CSS, tiếng Anh/Việt, thẻ `<a>`/`<button>`) để thích nghi khi Golike thay đổi UI.
  - Khi vẫn không tìm thấy, in ra 3000 ký tự HTML để chẩn đoán.
- **Sửa lỗi MAX_JOB không chuyển acc** (vòng lặp cứ lặp lại mãi):
  - `raise Exception("MAX_JOB")` trước đây bị nuốt bởi `except Exception` chung. Đã bắt riêng để `break` đúng vòng lặp.
- **Sửa thứ tự delay khi MAX_JOB**:
  - Flow đúng: MAX_JOB → `break` → Home → Kiếm xu → Facebook → chọn nick → chờ 60s → bắt đầu làm.
  - 60s được đặt sau khi đã vào đúng acc mới, tránh thông báo cũ còn sót.

### Thêm Mới (Added)
- **Chờ 60s + Gửi Telegram khi MAX_JOB**:
  - Khi đạt 100 jobs/ngày, gửi ngay thông báo Telegram kèm tên acc và giờ xảy ra.
  - Tự động chờ 60s sau khi chuyển vào acc mới để thông báo cũ biến mất hoàn toàn.
- **Hỏi cấu hình Telegram lúc khởi động** (`setup_telegram_notify()`):
  - Hỏi user có muốn nhận thông báo Telegram không.
  - Nếu có: hiển thị Chat ID đã lưu, cho phép giữ nguyên hoặc nhập mới.
  - Gửi tin nhắn test ngay để xác nhận bot hoạt động, lưu kết quả vào `config_golike_sele.json`.
- **Ctrl+C menu gọn hơn**:
  - Bỏ tùy chọn `c` (Resume) — chỉ còn `m` (đóng Chrome → về Menu) và `exit` (đóng Chrome → thoát).
- **Xóa thông báo khởi động thừa**:
  - Bỏ dòng mô tả "API mode / DOM mode" khi khởi động.
  - Bỏ cảnh báo `[CANH BAO] Khong the import golike_facebook.selenium_fb`.

## [v1.8.10] - 2026-05-22

### Thêm Mới & Sửa Lỗi (Added & Fixed)
- **Cải thiện Nhận diện Max Job (Anti-Timeout)**:
  - Tối ưu hóa vòng lặp bắt thông báo giới hạn 100 jobs/ngày. Quét DOM mỗi giây song song với việc chờ Job, giúp bắt gọn các popup hoặc Toast Message (bất kể là Toast hay SweetAlert2) cho dù nó chỉ xuất hiện lướt qua.
- **Bổ sung Hàm điều hướng còn thiếu**:
  - Fix triệt để lỗi `NameError: name 'click_home_navigation' is not defined` và `click_kiem_xu_navigation` khi hệ thống cố gắng điều hướng để chuyển acc trong Chế độ chạy Đơn Nối Tiếp.
- **Cải tiến Trải nghiệm Nhập liệu & Phím tắt**:
  - Tối ưu chọn Server: Cho phép gõ nhanh `1` hoặc `2` thay vì phải gõ tên đầy đủ của Server.
  - Sửa logic Ctrl+C: Lược bỏ tính năng Tiếp tục (`c`) không cần thiết. Giờ đây khi ấn Ctrl+C rồi chọn Menu (`m`), tool sẽ ngay lập tức **đóng và dọn dẹp sạch sẽ toàn bộ Chrome** đang mở để giải phóng RAM tối đa, sau đó mới quay lại Menu chính.

## [v1.8.9] - 2026-05-22

### Tính Năng (Feature)
- **Safe Boot (Cơ chế bảo vệ khởi động)**:
  - Tool tự động bắt lỗi ModuleNotFoundError hoặc ImportError ở cấp cao nhất trong main.py.
  - Thay vì văng lỗi Python rắc rối, hệ thống hiện thông báo tiếng Việt yêu cầu chạy python updater.py để khôi phục các file lõi bị thiếu. Chống tình trạng hỏng tool khi quá trình nâng cấp bị gián đoạn.



## [v1.8.8] - 2026-05-22

### Sửa Lỗi (Fixed)
- **Sửa lỗi Auto-Update (Tải thư mục con)**:
  - Cập nhật GitHub API endpoint sang /git/trees/main?recursive=1 để updater.py có thể quét và tải được toàn bộ file nằm sâu trong các thư mục con (recursive), thay vì chỉ tải được file ở thư mục gốc như trước đây.



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
