# BookHub Web Backend

Backend chạy độc lập với ứng dụng Desktop và hiện cung cấp hai endpoint health check:

- GET /api/v1/health/live: kiểm tra tiến trình FastAPI, không kết nối database.
- GET /api/v1/health/ready: mở kết nối SQL Server theo request và chạy SELECT 1.

## Cài đặt

    python -m pip install -r requirements.txt

## Cấu hình

Trong thư mục gốc repository, sao chép `.env.example` và đổi tên bản sao thành `.env` (có thể thao tác trực tiếp bằng File Explorer). Mở `.env` bằng trình soạn thảo và điền thông tin SQL Server. Cả Desktop và Backend đều tự nạp cùng file này khi khởi động.

- `BOOKHUB_SQL_*`: kết nối của ứng dụng Desktop.
- `BOOKHUB_WEB_SQL_*`: kết nối dịch vụ riêng của Backend. Hãy tạo một SQL Login riêng cho Backend với quyền tối thiểu; không dùng tài khoản nhân viên hoặc Admin Desktop.

Để trống `BOOKHUB_WEB_SQL_PASSWORD` cho đến khi bạn đã tạo tài khoản dịch vụ và có mật khẩu thật.


Backend tự động nạp tệp `.env` tại thư mục gốc dự án bằng python-dotenv khi khởi tạo cấu hình. Desktop cũng nạp cùng tệp khi tạo đối tượng `Database`. Bạn chỉ cần sao chép `.env.example` thành `.env` rồi điền thông tin tại đó; không cần dùng lệnh `$env:` hoặc `export`. Biến môi trường do hệ điều hành/container cung cấp sẽ được ưu tiên hơn giá trị trong `.env`.

Dùng tài khoản SQL Server riêng cho Backend qua BOOKHUB_WEB_SQL_USERNAME và BOOKHUB_WEB_SQL_PASSWORD. Không dùng tài khoản cá nhân của nhân viên, không dùng tài khoản Admin Desktop và không commit thông tin đăng nhập vào Git.

Tài khoản dịch vụ cần được cấp quyền tối thiểu cho các bảng/view/procedure mà API được phép dùng. Chưa dùng chung các repository có kiểm tra quyền dựa trên SQL Login nhân viên cho đến khi hoàn thiện xác thực Web và ngữ cảnh người thực hiện được xác minh ở Backend.

Production phải dùng mã hóa SQL Server với chứng chỉ được tin cậy; giữ BOOKHUB_WEB_SQL_TRUST_SERVER_CERTIFICATE=false. Chỉ bật true trong môi trường phát triển dùng chứng chỉ tự ký.

Tệp `.env` thật đã được loại khỏi Git bởi `.gitignore`; không commit mật khẩu hoặc thông tin kết nối riêng vào repository.

## Chạy phát triển

    uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

Muốn truy cập từ máy khác trong mạng LAN, bind --host 0.0.0.0 và cấu hình firewall/reverse proxy phù hợp. Không mở cổng SQL Server trực tiếp ra Internet. Chưa triển khai public trực tiếp Uvicorn; Internet cần reverse proxy HTTPS.
