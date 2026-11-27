# Hệ thống quản lý nhà sách - Backend

Backend chạy độc lập với ứng dụng Desktop. Các API hiện có gồm xác thực nhân viên, health check và phân hệ quản lý sản phẩm:

- GET /api/v1/health/live: kiểm tra tiến trình FastAPI, không kết nối database.
- GET /api/v1/products: danh sách, tìm kiếm, lọc, sắp xếp và phân trang sản phẩm.
- GET /api/v1/products/{product_code}: xem chi tiết sản phẩm.
- POST/PUT/DELETE /api/v1/products: thêm, sửa và xóa mềm sản phẩm (có kiểm tra quyền và tồn kho).
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

## Xác thực nhân viên Web

Backend dùng tài khoản SQL Server Login hiện có của nhân viên để xác thực:

- Trường username là mã nhân viên (ví dụ NV001), password là mật khẩu SQL Server hiện tại.
- Backend mở một kết nối SQL tạm bằng thông tin người dùng nhập, kiểm tra hồ sơ trong `dbo.NHAN_VIEN` và vai trò SQL thực tế (`rl_QuanLy`, `rl_ThuNgan`, `rl_NhanVienKho`, `rl_KeToan`, hoặc `db_owner` cho admin).
- Kết nối xác thực được đóng ngay sau khi kiểm tra; Backend không lưu mật khẩu nhân viên.
- Đăng nhập thành công trả JWT access token. Frontend gửi token ở header `Authorization: Bearer <token>` cho các API cần đăng nhập.
- `GET /api/v1/auth/me` trả về thông tin nhân viên gắn với token. Health-check vẫn là endpoint công khai.

Cấu hình thêm trong `.env`:

    BOOKHUB_WEB_JWT_SECRET=thay-bang-chuoi-ngau-nhien-rieng-dai-it-nhat-32-ky-tu
    BOOKHUB_WEB_ACCESS_TOKEN_MINUTES=30

Tự tạo secret bằng trình tạo mật khẩu an toàn, tối thiểu 32 ký tự; không dùng ví dụ trên làm secret thật và tuyệt đối không commit `.env`. Access token hiện có thời hạn mặc định 30 phút. Khi triển khai qua Internet, toàn bộ đăng nhập và API phải chạy qua HTTPS. Không gửi mật khẩu SQL hoặc JWT qua URL, không lưu password nhân viên ở localStorage. JWT hiện là access token stateless: thay đổi role hoặc khóa tài khoản sẽ không thu hồi token đã cấp ngay lập tức; cần chờ token hết hạn (tối đa theo cấu hình) trong phiên bản hiện tại.

## Khởi động toàn bộ Web bằng một lệnh

Tại thư mục gốc dự án, chạy:

    python run_web.py

Launcher tự kiểm tra Python dependencies, Node.js/npm, tự chạy `npm install` nếu thiếu thư viện Frontend, rồi khởi động Backend và Frontend đồng thời. Mặc định mở giao diện tại `http://127.0.0.1:5173`; API tại `http://127.0.0.1:8000`. Nhấn `Ctrl+C` một lần để dừng cả hai máy chủ.

Cấu hình host/port trong `.env` bằng `BOOKHUB_WEB_HOST`, `BOOKHUB_WEB_PORT`, `BOOKHUB_WEB_FRONTEND_HOST` và `BOOKHUB_WEB_FRONTEND_PORT`. Cần cài Node.js bản LTS và cài dependencies Python (`python -m pip install -r requirements.txt`) trước lần chạy đầu; launcher sẽ báo rõ nếu thiếu. Máy chủ SQL Server và Microsoft ODBC Driver cũng phải sẵn sàng.

## Khởi động riêng Backend (tuỳ chọn)

1. Cài thư viện một lần:

       python -m pip install -r requirements.txt

2. Mở file `.env` và chỉnh các mục khởi động:

       BOOKHUB_WEB_HOST=127.0.0.1
       BOOKHUB_WEB_PORT=8000
       BOOKHUB_WEB_RELOAD=true
       BOOKHUB_WEB_LOG_LEVEL=info

3. Chạy riêng Backend (không cần Frontend) bằng:

       python run_backend.py

Launcher tự nạp `.env`, kiểm tra host/port/reload và khởi chạy Uvicorn. Khi dùng để phát triển, `reload=true` tự khởi động lại API khi mã nguồn thay đổi. Trong production phải đặt `BOOKHUB_WEB_RELOAD=false`.

Muốn truy cập từ máy khác trong mạng LAN, bind --host 0.0.0.0 và cấu hình firewall/reverse proxy phù hợp. Không mở cổng SQL Server trực tiếp ra Internet. Chưa triển khai public trực tiếp Uvicorn; Internet cần reverse proxy HTTPS.


## Chuẩn bị quyền SQL Server cho phân hệ sản phẩm

Backend không dùng tài khoản SQL của nhân viên để truy vấn nghiệp vụ. Nhân viên đăng nhập để xác thực và nhận JWT; các API đọc/ghi dữ liệu bằng SQL Login dịch vụ được cấu hình ở `BOOKHUB_WEB_SQL_USERNAME` và `BOOKHUB_WEB_SQL_PASSWORD`.

Với database `CSDLTEST`, thực hiện trên SQL Server Management Studio bằng tài khoản có quyền quản trị database:

1. Đảm bảo SQL Login `bookhub_web_app` đã được tạo và mật khẩu trùng với `BOOKHUB_WEB_SQL_PASSWORD` trong `.env`. Đây là tài khoản dịch vụ riêng, không phải tài khoản đăng nhập nhân viên.
2. Sau khi tạo database và các role nghiệp vụ, sao lưu database rồi chạy `database/migrations/004_product_barcode.sql`. Migration tự thêm cột `BARCODE` nếu chưa tồn tại và tạo unique filtered index để chống trùng mã vạch; cần xử lý dữ liệu barcode trùng trước nếu script báo lỗi.
3. Chạy `database/migrations/005_bookhub_web_products_permissions.sql`. Script tạo role `rl_BookHubWeb`, ánh xạ user dịch vụ và cấp quyền giới hạn trên các bảng/cột dùng cho phân hệ sản phẩm. Không cấp `db_owner`, `db_datareader` hoặc `db_datawriter`.
4. Kiểm tra `BOOKHUB_WEB_SQL_SERVER`, `BOOKHUB_WEB_SQL_DATABASE=CSDLTEST`, `BOOKHUB_WEB_SQL_USERNAME=bookhub_web_app` và mật khẩu trong `.env`, sau đó khởi động lại bằng `python run_web.py`.
5. Đăng nhập bằng tài khoản nhân viên đã được cấp role. Mở mục **Sản phẩm** để kiểm tra dữ liệu.

Quyền nghiệp vụ ở API: mọi vai trò nhân viên hợp lệ có thể xem/tìm kiếm sản phẩm; Quản lý, Nhân viên kho và admin mới được thêm, sửa hoặc xóa mềm. Sản phẩm chỉ được xóa mềm khi tồn kho bằng 0. Giá nhập và số lượng tồn không được sửa từ biểu mẫu sản phẩm vì do các giao dịch nhập/xuất kho cập nhật.

Lưu ý: migration chỉ được lưu trong repository; cần tự chạy trên đúng SQL Server của bạn. CI kiểm tra API bằng dữ liệu giả, không thay thế việc xác nhận kết nối và quyền trên database thực tế.