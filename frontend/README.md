# BookHub Web Frontend

Frontend React + TypeScript + Vite, dùng Ant Design và theme tối đồng bộ với ứng dụng Desktop.

## Chạy toàn bộ Web

Tại thư mục gốc dự án, chỉ cần chạy:

    python run_web.py

Launcher tự kiểm tra Node.js/npm, tự cài dependencies frontend nếu chưa có, rồi chạy Backend và Frontend cùng lúc. Nhấn `Ctrl+C` để dừng cả hai. Giao diện mặc định ở `http://127.0.0.1:5173`.

Không cần chạy `run_backend.py` riêng khi dùng `run_web.py`. Lệnh `npm run dev` bên dưới chỉ cần khi muốn phát triển/tách riêng Frontend.

## Cấu hình

Các tuỳ chọn mặc định:

    BOOKHUB_WEB_FRONTEND_HOST=127.0.0.1
    BOOKHUB_WEB_FRONTEND_PORT=5173
    VITE_API_BASE_URL=/api/v1

Khi cần truy cập từ máy khác trong LAN, đổi host frontend thành 0.0.0.0 và cấu hình firewall phù hợp. Khi triển khai production, nên phục vụ frontend và Backend dưới cùng domain qua reverse proxy HTTPS.

## Xác thực

- Đăng nhập bằng mã nhân viên và mật khẩu SQL Server hiện có.
- Access token lưu ở sessionStorage cho tab hiện tại và gửi bằng Bearer token.
- Khi Backend trả 401, frontend xóa token và chuyển về màn hình đăng nhập.
- Đăng xuất xóa token tại trình duyệt. Backend hiện chưa có thu hồi JWT tức thời.
- Không lưu mật khẩu nhân viên.

Đây là nền tảng đăng nhập và khung điều hướng ban đầu. Các menu nghiệp vụ sẽ được nối vào API riêng theo từng giai đoạn.
