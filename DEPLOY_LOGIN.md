# Đăng nhập cá nhân

Ứng dụng dùng một tài khoản cấu hình ở backend, không cần bảng người dùng hoặc migration.

## Cấu hình trên Render

Trong service backend, mở **Environment** và thêm:

```env
APP_USERNAME=ten_dang_nhap_cua_ban
APP_PASSWORD=mat_khau_rieng_cua_ban
```

Thay các giá trị ví dụ bằng tài khoản riêng. Dùng mật khẩu dài, khó đoán. Không commit mật khẩu, không đặt chúng vào biến `VITE_*`, không đưa chúng lên Vercel.

Giữ một instance với một worker:

```sh
uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
```

Deploy backend mới sau khi thiết lập hai biến, rồi deploy frontend mới lên Vercel. Frontend vẫn chỉ cần `VITE_API_URL` trỏ tới backend. Không cần sửa Supabase.

Chạy local: thêm hai biến vào `backend/.env`, rồi khởi động lại backend.

## Hành vi

- Chưa đăng nhập: không tải kho từ, tài liệu, flashcard hoặc gọi Gemini.
- Backend kiểm tra token cho tất cả đường dẫn trừ `GET /health`, `POST /auth/login` và yêu cầu CORS preflight.
- Thiếu cấu hình tài khoản: API riêng trả 503, không tự mở quyền truy cập.
- Sau khi nhập đúng tài khoản, backend cấp token ngẫu nhiên dùng trong 12 giờ. Token được lưu trong `sessionStorage` của tab, mật khẩu không được lưu ở frontend.
- Đăng xuất thu hồi token ở backend và xóa token ở tab. Hết hạn trả 401 và hiện màn hình đăng nhập.
- Tối đa 5 yêu cầu đăng nhập trong 60 giây trên toàn service, kể cả yêu cầu thành công. Vượt giới hạn trả 429 kèm `Retry-After`.
- Phiên và giới hạn đăng nhập nằm trong RAM. Render sleep/restart/redeploy làm mất phiên: đăng nhập lại để tiếp tục. Dữ liệu học trong Supabase vẫn được giữ.
- Chỉ hỗ trợ một worker/instance. Nếu cần mở rộng nhiều instance, chuyển kho phiên và giới hạn đăng nhập sang kho dùng chung trước.
- Đường dẫn audio có chữ ký đã cấp vẫn có hiệu lực tới khi chữ ký hết hạn; đăng xuất ngăn cấp đường dẫn mới.

## Kiểm tra sau deploy

1. Mở website trong cửa sổ riêng tư: thấy màn hình đăng nhập.
2. Nhập sai: báo lỗi, không thấy dữ liệu.
3. Nhập đúng: mở kho từ, học và nghe audio bình thường.
4. Tải lại trang: giữ đăng nhập trong cùng tab khi backend chưa khởi động lại.
5. Đăng xuất: quay lại màn hình đăng nhập.
6. Gọi `/entries` không có Authorization: trả 401; `/health` vẫn trả 200.
