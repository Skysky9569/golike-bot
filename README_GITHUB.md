# Hướng dẫn đưa code lên GitHub & Bật Auto Update

Mình đã khởi tạo Git sẵn cho thư mục code của bạn và tạo file `.gitignore` để đảm bảo an toàn (không bao giờ up file cookie bí mật của bạn lên mạng).

Bây giờ, để đưa code lên GitHub, bạn hãy làm đúng theo các bước sau:

## Bước 1: Tạo Repository trên GitHub
1. Truy cập trang web: https://github.com/new
2. Nhập tên Repository là: `golike-bot`
3. Chọn chế độ **Public** (để máy bạn bè của bạn có thể tải code về được).
4. **KHÔNG** tích chọn bất cứ ô nào như "Add a README", "Add .gitignore", "Choose a license". (Để nó trống trơn hoàn toàn).
5. Bấm nút **Create repository** màu xanh lá cây ở dưới cùng.

## Bước 2: Liên kết và Đẩy code lên GitHub
Sau khi bấm Create, bạn sẽ thấy trang web hướng dẫn có một vài câu lệnh.
Hãy mở cửa sổ CMD hoặc Terminal tại thư mục `d:\pythonadb` này và chạy đúng 2 lệnh sau:

*(Nhớ thay `TEN_TK_GITHUB_CUA_BAN` bằng tên tài khoản GitHub của bạn vào dòng dưới trước khi chạy nhé!)*

```bash
git remote add origin https://github.com/TEN_TK_GITHUB_CUA_BAN/golike-bot.git
git branch -M main
git push -u origin main
```

**(Nếu GitHub hỏi đăng nhập, bạn cứ bấm đăng nhập trên trình duyệt là xong).*

## Bước 3: Sửa Link Auto Update trong Tool
1. Mở file `golikefb_sele.py` (bản của bạn).
2. Tìm đến dòng `UPDATE_URL` (gần dòng 45).
3. Thay chữ `Ten_Tai_Khoan_Cua_Ban` bằng tên đăng nhập GitHub của bạn.
4. Xuống dòng 78, bỏ dấu `#` ở trước lệnh `kiem_tra_cap_nhat()`.
5. Lưu lại và chạy lệnh `git commit -am "Bat auto update"; git push` để đồng bộ bản sửa này lên GitHub.

Từ nay về sau, hễ bạn sửa code trên máy mình xong, bạn chỉ cần gõ lệnh:
`git commit -am "Update moi"; git push`
Là máy của tất cả bạn bè của bạn sẽ tự động cập nhật luôn khi họ mở tool lên!
