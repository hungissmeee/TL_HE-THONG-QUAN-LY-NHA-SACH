# BookHub Web Backend

Backend chạy độc lập với ứng dụng Desktop và hiện cung cấp hai endpoint health check:

- GET /api/v1/health/live: kiểm tra tiến trình FastAPI, không kết nối database.
- GET /api/v1/health/ready: mở kết nối SQL Server theo request và chạy SELECT 1.

## Cài đặt

    python -m pip install -r requirements.txt

## Cấu hình

Backend chỉ đọc biến môi trường hệ điều hành, không tự động nạp tệp .env. Cấu hình ví dụ nằm trong .env.example.

Dùng tài khoản SQL Server riêng cho Backend qua BOOKHUB_WEB_SQL_USERNAME và BOOKHUB_WEB_SQL_PASSWORD. Không dùng tài khoản cá nhân của nhân viên, không dùng tài khoản Admin Desktop và không commit thông tin đăng nhập vào Git.

Tài khoản dịch vụ cần được cấp quyền tối thiểu cho các bảng/view/procedure mà API được phép dùng. Chưa dùng chung các repository có kiểm tra quyền dựa trên SQL Login nhân viên cho đến khi hoàn thiện xác thực Web và ngữ cảnh người thực hiện được xác minh ở Backend.

Production phải dùng mã hóa SQL Server với chứng chỉ được tin cậy; giữ BOOKHUB_WEB_SQL_TRUST_SERVER_CERTIFICATE=false. Chỉ bật true trong môi trường phát triển dùng chứng chỉ tự ký.

## Chạy phát triển

    uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

Muốn truy cập từ máy khác trong mạng LAN, bind --host 0.0.0.0 và cấu hình firewall/reverse proxy phù hợp. Không mở cổng SQL Server trực tiếp ra Internet. Chưa triển khai public trực tiếp Uvicorn; Internet cần reverse proxy HTTPS.
