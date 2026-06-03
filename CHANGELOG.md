# CHANGELOG

## [v1.13.1] - 2026-06-03

### Sửa Lỗi (Bug Fixes)
- **Fix lỗi API 'Vui lòng cập nhật phiên bản mới nhất'**:
  - Bổ sung Header bảo mật mới `g-auth` và `g-device-id` vào các request API.
  - Cập nhật User-Agent mặc định theo mẫu trình duyệt thực tế mới nhất.
  - Cải tiến trình nhập Token: Hỗ trợ dán trực tiếp chuỗi JSON từ trình duyệt để tự động bóc tách các header bảo mật.
  - Tự động lưu và đồng bộ `g-auth`, `g-device-id` vào file `golike_token.json`.

## [v1.13.0] - 2026-06-02

### Tính Năng Mới & Nâng Cấp (Features & Upgrades)
- **Chế độ Full DOM (100% Selenium Browser)**:
  - Tách biệt hoàn toàn chế độ chạy Hybrid (API) và Full DOM (Trình duyệt).
  - Tự động thực hiện mọi bước từ Nhận Job, Làm nhiệm vụ đến Hoàn thành ngay trên trình duyệt.
- **Selective Mobile User-Agent (CDP Simulation)**:
  - Sử dụng Chrome DevTools Protocol để ép riêng tab GoLike sang giao diện Mobile.
  - Các tab khác (như Facebook) vẫn giữ giao diện Desktop giúp ổn định và tránh bị quét.
- **Siêu Thả Cảm Xúc (Advanced Reactions)**:
  - Tích hợp mô phỏng sự kiện đa tầng (Pointer + Mouse + Touch) để thả Love, Haha, Wow... cực kỳ chính xác.
  - JavaScript Scanner thông minh tìm nút dựa trên nhãn tiếng Việt/Anh và cấu trúc Comet mới.
- **Tối Ưu Hóa cho macOS**:
  - Tự động nhận diện hệ điều hành và hiển thị 🍏 macOS trên Menu.
  - Cơ chế Cleanup mới sử dụng `pkill` và `ps` để dọn dẹp sạch tiến trình Chrome chạy ngầm trên Mac.

### Cải Tiến & Sửa Lỗi (Improvements & Bug fixes)
- **Kiểm tra bài viết tồn tại**: Tự động phát hiện bài viết bị xóa hoặc bị chặn và báo lỗi "Không tìm thấy bài viết" lên GoLike.
- **Manual Fallback**: Thêm 20 giây chờ đợi để người dùng can thiệp thủ công nếu bot gặp khó khăn.
- **Highlight & Scroll**: Tự động cuộn tới nút và highlight viền đỏ/nền đỏ mờ để dễ quan sát.
- **Fix lỗi xác thực**: Khắc phục lỗi SSL trên macOS và cải tiến hệ thống bơm Cookie tự động.
- **Sửa lỗi logic**: Fix các lỗi `NameError`, `UnboundLocalError` và lỗi báo cáo quá nhanh.

## [v1.12.11] - 2026-06-01

### Sửa lỗi tương thích hệ điều hành (OS Compatibility Fixed)
- **Khắc phục lỗi "Exec format error" khi chạy trên macOS**:
  - Cập nhật logic phát hiện đường dẫn ADB để tự động chọn ADB phù hợp với hệ điều hành hiện tại
  - Ưu tiên sử dụng ADB hệ thống trên các hệ điều hành không phải Windows
  - Tự động chuyển sang sử dụng ADB hệ thống khi phát hiện file ADB cục bộ là file .exe trên hệ điều hành không phải Windows
  - Cập nhật file cấu hình `app_config.json` để sử dụng ADB hệ thống thay vì đường dẫn Windows cố định

## [v1.12.10] - 22-05-30

### Sửa lỗi kết nối WiFi (WiFi Connection Fixed)
- **Tự động kích hoạt adb connect cho uiautomator2 WiFi**:
  - Tự động kiểm tra và thực thi lệnh `adb connect <IP:Port>` ngầm trước khi khởi tạo kết nối `uiautomator2`.
  - Giúp giải quyết triệt để lỗi thiết bị báo ngoại tuyến (offline) hoặc không tìm thấy serial khi uiautomator2 cố gắng liên lạc với thiết bị chưa được đăng ký trong daemon ADB.
  - Áp dụng đồng bộ trong cả module chính `TikTokUIAutomator` và `U2JobProcessor` (trình xử lý mở link).

## [v1.12.9] - 2026-05-30

### Cải Tiến & Tối Ưu (Improved & Optimized)
- **Tải tệp tin song song (Parallel Downloading)**:
  - Tích hợp `ThreadPoolExecutor` trong `updater.py` để tải nhiều tệp cùng lúc từ GitHub (tối đa 10 luồng song song).
  - Tăng tốc độ cập nhật hệ thống và khôi phục tệp thiếu nhanh hơn gấp 5 - 10 lần so với tải tuần tự trước đó.
  - Sử dụng cơ chế khóa in ấn (`print_lock`) và khóa đếm (`count_lock`) để bảo toàn trạng thái log đầu ra không bị đè hay trùng lắp.

## [v1.12.8] - 2026-05-30

### Cải Tiến & Kiểm Soát (Improved & Controlled)
- **Kiểm tra kết nối uiautomator2 WiFi trước khi chạy**:
  - Tự động kiểm tra trạng thái hoạt động của thiết bị uiautomator2 ngay khi người dùng nhập IP:Port hoặc chọn tiếp tục dùng thiết bị đã lưu.
  - Hiển thị hướng dẫn sửa lỗi và cho phép nhập lại IP:Port hoặc đổi phương thức kết nối nếu thiết bị không online.
  - Ngăn ngừa tình trạng bot tự động nhận và cày job khi kết nối đến thiết bị WiFi thực tế đã bị ngắt.

## [v1.12.3] - 2026-05-28

### Thêm Mới & Sửa Lỗi (Added & Fixed)
- **Tính năng tạm dừng bằng phím Enter và tiếp tục bằng phím 'r'**:
  - Tự động nhận diện sự kiện gõ phím non-blocking trên hệ điều hành Windows qua thư viện `msvcrt`.
  - Hỗ trợ phản hồi nhanh: Tạm dừng lập tức khi ấn `Enter` và tiếp tục chạy tiếp bình thường khi ấn `r`.
  - Tích hợp trên các phiên bản tool TikTok (`tiktok_flow.py`, `golikebydom.py`).

## [v1.12.2] - 2026-05-28

### Sửa Lỗi (Fixed)
- **Hiển thị thông báo kết quả từ API hoàn thành job TikTok (`complete-jobs`)**:
  - Sửa lỗi đọc trường `message` từ cấp root của JSON response thay vì nhánh `data` bị lỗi `None`.
  - Hiển thị đầy đủ thông điệp từ hệ thống (VD: "Báo cáo thành công, số TIỀN làm được sẽ được cộng sau ÍT PHÚT ! Số jobs đã làm trong ngày...") trên cả bản `tiktok_flow.py`, `golikebydom.py` và `tiktok_client.py`.

## [v1.12.1] - 2026-05-28

### Thêm Mới & Sửa Lỗi (Added & Fixed)
- **Tự động quét và xử lý yêu cầu thả cảm xúc đặc biệt (ví dụ: thả tim/Love) trên Golike**:
  - Tự động nhận diện block `.reaction-required` / `.reaction-text` trên trang chi tiết công việc.
  - Tự động ghi đè loại reaction gốc (như Like) bằng loại cảm xúc được yêu cầu (Love, Haha, Wow, Sad, Angry, Care) để gửi reaction chính xác qua API.
  - Bổ sung thông tin log chi tiết khi phát hiện và xử lý cảm xúc đặc biệt.

## [v1.12.0] - 2026-05-28

### Cải Tiến & Sửa Lỗi (Improved & Fixed)
- **Tự động nhận diện định dạng IP:Port hoặc chỉ IP khi kết nối ADB WiFi**:
  - Hỗ trợ người dùng nhập trực tiếp định dạng `IP:Port` (ví dụ `192.168.1.10:5555`) ở ô nhập địa chỉ IP mà không bị lỗi xác thực/cắt chuỗi.
  - Tự động gán cổng mặc định `:5555` nếu người dùng chỉ nhập IP khi kết nối qua Uiautomator2 WiFi.
  - Cập nhật đồng bộ trên cả Menu ADB, TikTok Flow và phiên bản đơn giản `golikebydom.py`.

## [v1.11.1] - 2026-05-26

### Sửa Lỗi (Fixed)
- **Sửa lỗi khởi động Captcha**: Thêm đối số `is_parallel` vào hàm `handle_2captcha_captcha` để tránh lỗi hệ thống bị crash khi chạy song song.
- **Tối ưu hóa Báo lỗi Job**: 
  - Cải tiến XPath để click chính xác vào nhãn `h6` thay vì phần tử hàng (`row`), loại bỏ hoàn toàn khả năng click nhầm vào các thanh menu xung quanh.
  - Tích hợp tính năng cuộn phần tử mục tiêu ra giữa màn hình (`scrollIntoView({block: 'center'})`) trước khi nhấp chuột để tránh bị che bởi thanh menu cố định.
- **Tăng tốc đăng nhập**: Bỏ cơ chế quét các file JS của Facebook để tìm `doc_id`, mặc định gán `'null'` giúp đăng nhập nhanh hơn, giảm đáng kể số lượng HTTP request và tiết kiệm dữ liệu mạng proxy.

## [v1.11.0] - 2026-05-25

### Thêm Mới & Nâng Cấp (Added & Upgraded)
- **Cải tiến hệ thống Anti-ban (Giả lập hành vi) cực mạnh cho TikTok ADB**:
  - **Tự động vuốt ngẫu nhiên (Random Swipe)**: Tự động vuốt xem thêm video khác trên Feed hoặc lướt trang cá nhân trong thời gian chờ (delay) để giả lập người dùng thật đang xem TikTok.
  - **Xem video trước khi thả tim**: Tool tự động dừng từ 5-12s để xem video trước khi nhấp đúp thả tim, tránh bị TikTok đánh dấu spam.
  - **Nghỉ giải lao thông minh**: Tự động cho hệ thống nghỉ 5 phút sau mỗi 40 nhiệm vụ để chống bị quét checkpoint.
  - **Đa dạng hóa mốc Delay**: Các mốc thời gian chờ (Action, Job, Empty) đều được cấu hình ngẫu nhiên trong khoảng Min-Max an toàn thay vì cố định một con số.
  - **Random tọa độ (Click/Swipe Jitter)**: Các thao tác nhấp đúp, bấm nút Follow hay đường vuốt màn hình đều được gắn thêm các độ lệch ngẫu nhiên về tọa độ X, Y, triệt tiêu hoàn toàn khả năng bị nhận diện là Bot do click cứng ở một điểm.

### Sửa Lỗi (Fixed)
- **Fix lỗi bấm nhầm nút Follow**: Xóa bỏ các selector nhận diện lỗi (`id/title`) để tool không bao giờ bấm nhầm vào Tiêu đề/Tên người dùng thay vì bấm Follow.
- **Fix lỗi trượt mất nút Follow khi vuốt**: Tự động vuốt ngược về vị trí ban đầu (đỉnh trang cá nhân) sau khi lướt xem nội dung để đảm bảo không bị mất dấu nút Follow đỏ.
- **Fix bug kẹt account khi đổi tài khoản TikTok**: Đảm bảo ID account mới được lưu trữ và sử dụng ngay lập tức khi chức năng tự động đổi account (do fail nhiều lần) kích hoạt.
- **Tối ưu hiển thị Console**: Dọn dẹp bảng log gọn gàng hơn, tách biệt thông báo dài từ hệ thống thành dòng riêng dễ nhìn thay vì nối vào đuôi bảng.
## [v1.10.4] - 2026-05-25

### Sửa Lỗi & Tối Ưu (Fixed & Optimized)
- **Tối ưu hóa logic tự động chuyển tài khoản ở chế độ Đơn Lẻ (Single Mode)**:
  - Trước đây: Tool sẽ chờ 5 phút ngủ nguội sau đó mới đổi tài khoản hoặc báo lỗi sai mục đích nếu hụt job nhiều lần.
  - Đã sửa: Khi hụt job 3 lần liên tiếp, tool sẽ lập tức chuyển sang tài khoản tiếp theo một cách gọn gàng, không cần ngủ 5 phút và không thao tác báo lỗi thừa thãi.
  - Quản lý xoay vòng thông minh: Tài khoản hụt job vẫn được giữ trong danh sách xoay vòng. Chỉ khi nào tài khoản báo chạm mốc "MAX JOB" (100 jobs/ngày) thì mới bị loại bỏ vĩnh viễn khỏi danh sách xoay vòng trong phiên chạy đó.
- **Sửa lỗi SyntaxError tiềm ẩn**: Cập nhật lại format chuỗi hiển thị khi khởi tạo cấu hình từ file `.env` giúp ngăn chặn khả năng bị văng ứng dụng lúc vừa mở lên.

## [v1.10.3] - 2026-05-24

### Sửa Lỗi (Fixed)
- **Fix hoàn toàn lỗi tự động giải Captcha bằng 2Captcha trên Golike (Vue.js)**:
  - Tình trạng: Trình duyệt bị văng lỗi (crash) khi cố click vào checkbox của reCAPTCHA, hoặc nếu điền token ẩn thì trang web không tự động đăng nhập và bị kẹt.
  - Đã sửa: 
    - Ép đè (override) hàm `window.grecaptcha.getResponse` của Google để ép khung Vue.js luôn nhận được token từ 2Captcha khi nó kiểm tra.
    - Dùng Javascript giả lập gửi sự kiện (`input`, `change`) để báo hiệu cho Vue Component nhận token.
    - Ra lệnh tắt (hide) hoàn toàn khung ảnh chọn (image challenge) của Captcha để không che khuất màn hình.
    - Cuối cùng tự động mô phỏng click chuột vật lý vào nút Đăng nhập để kích hoạt luồng Submit form.

## [v1.10.2] - 2026-05-24

### Sửa Lỗi (Fixed)
- **Fix Single Mode không tự chọn được account**:
  - Sự cố: Khi chạy chế độ đơn lẻ (Sequential Single Mode), tool yêu cầu nhập UID Facebook nhưng dropdown GoLike hiển thị GoLike UID (`i_user`) thay vì Facebook UID (`c_user`) → Không match được, bắt user phải chọn số thủ công.
  - Đã sửa: Tự động extract cả `i_user` (GoLike UID) và `c_user` (Facebook UID) từ cookie khi nhập, tool match đúng UID hiển thị trong dropdown GoLike.

### Cải Thiện (Enhanced)
- **Thêm config file riêng cho Single Mode** (`single_mode_accounts.json`):
  - Lưu trữ rõ ràng: `profile_name`, `cookie`, `golike_uid` (i_user), `facebook_uid` (c_user)
  - Hỗ trợ 2 cách quản lý: sửa file config hoặc nhập từ tool
  - Fallback về `multi_accounts.json` (format cũ) để tương thích ngược
- **Tự động phát hiện UID khi nhập cookie**:
  - Tool tự extract `i_user` và hiển thị, user có thể ấn Enter để dùng UID tự động
  - Yêu cầu nhập `profile_name` để dễ nhận biết account

## [v1.10.1] - 2026-05-24

### Sửa Lỗi (Fixed)
- **Fix Regex tìm JS Bundle bị miss 100%**:
  - Nguyên nhân: Facebook trả về mã HTML với các URL bị escape dấu slash (`https:\/\/static.xx.fbcdn.net\/...`). Regex cũ viết là `https://static...` nên **không tìm được bất kỳ file JS nào** → Dẫn đến luôn dùng `doc_id` dự phòng đã cũ kỹ.
  - Đã sửa: Cập nhật regex để bắt cả các URL bị escape, sau đó `replace('\\/', '/')` để tải file về quét. Đồng thời tăng số lượng quét lên 50 files. Đảm bảo fetch được `doc_id` mới nhất thành công.
- **Thêm lại tham số `doc_id` cho `Fb.REACTION`**:
  - Cho phép gọi `Fb.REACTION("LIKE", uid)` (tự động lấy doc_id) hoặc `Fb.REACTION("LIKE", uid, "1234...")` (ép buộc dùng doc_id truyền vào). Tương thích ngược với file gốc.

## [v1.10.0] - 2026-05-24

### Cải thiện Chạy Song Song (Parallel Mode)
- **Fix lỗi `CRITICAL` khi Reaction ở chế độ song song**:
  - Nguyên nhân: Facebook có thể trả về các phiên bản JS (A/B testing) khác nhau cho từng tài khoản/IP. Việc dùng chung `doc_id` giữa các tài khoản (class-level cache) khiến acc này dùng nhầm `doc_id` của acc kia → Facebook từ chối mutation.
  - Đã sửa: Xóa cache `doc_id` toàn cục. Giờ đây, mỗi tài khoản sẽ tự fetch `doc_id` từ chính phiên bản Facebook của nó, đảm bảo an toàn 100% khi chạy song song.
- **Hiển thị lỗi rõ ràng hơn**:
  - Khi Facebook trả về lỗi GraphQL (thiếu `code`, `api_error_code`), script trước đây chỉ in ra các giá trị `None`.
  - Đã thêm việc trích xuất `message` gốc từ Facebook để bạn biết chính xác tại sao hành động bị chặn (VD: "You can't perform this action right now").

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
