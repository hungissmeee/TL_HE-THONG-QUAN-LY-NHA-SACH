# BookHub Web Frontend

Frontend React + TypeScript + Vite, dùng Ant Design và theme tối đồng bộ với ứng dụng Desktop.

## Chạy lần đầu

Tại thư mục gốc dự án:

    cd frontend
    npm install
    npm run dev

Mở địa chỉ Vite hiển thị (mặc định http://127.0.0.1:5173).

Backend cần chạy song song ở cửa sổ Terminal khác:

    python run_backend.py

Vite proxy các request /api/v1 sang Backend theo BOOKHUB_WEB_HOST và BOOKHUB_WEB_PORT trong file .env gốc. Trình duyệt dùng cùng origin với Vite trong quá trình phát triển, không cần cấu hình CORS riêng cho Vite.

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
