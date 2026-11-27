# Kế hoạch triển khai phiên bản Web

> Trạng thái: Kế hoạch ban đầu  
> Nhánh làm việc: `feature/web-app`  
> Nhánh nền: `fix/refactor-business-logic-and-setup`  
> Mục tiêu: phát triển Web song song với Desktop, dùng chung SQL Server và phục vụ cả mạng nội bộ lẫn truy cập Internet.

## 1. Mục tiêu và nguyên tắc

- Giữ nguyên ứng dụng Desktop PySide6; không thay thế, xóa hoặc đổi hành vi của bản Desktop trong quá trình phát triển Web.
- Tạo ứng dụng Web riêng, có giao diện và luồng thao tác gần với Desktop hiện tại: sidebar bên trái, nhóm chức năng, thanh tiêu đề, bộ lọc, bảng dữ liệu, hộp thoại chi tiết và biểu mẫu.
- Dùng chung cơ sở dữ liệu SQL Server hiện tại. Không tạo database Web thứ hai và không tự ý đổi tên bảng/cột hoặc quy tắc nghiệp vụ.
- Tái sử dụng câu SQL và logic đã được xác minh, nhưng không tái sử dụng trực tiếp các lớp PySide6 trong Backend.
- Backend là nơi duy nhất được phép kết nối SQL Server. Trình duyệt chỉ giao tiếp với Backend qua HTTPS.
- Mọi quyền được kiểm tra ở Backend cho từng API; việc ẩn menu/nút trên giao diện chỉ là hỗ trợ trải nghiệm, không phải cơ chế bảo mật.
- Tách từng giai đoạn thành commit nhỏ, có kiểm thử và có thể rà soát trước khi hợp nhất.

## 2. Hiện trạng mã nguồn đã kiểm tra

- Ứng dụng Desktop hiện tại dùng Python, PySide6 và `pyodbc`; `requirements.txt` khai báo các thư viện chạy ứng dụng.
- `main.py` khởi tạo đối tượng `Database`; `database/connection.py` quản lý kết nối SQL Server và các thao tác tài khoản/role ở cấp SQL Server.
- Mỗi phân hệ trong `core/` hiện được tổ chức theo feature: `xu_ly_du_lieu.py` là Service xử lý/kiểm tra nghiệp vụ; `truy_van_sql.py` là Repository chứa truy vấn SQL và transaction.
- Các trang trong `ui/` chủ yếu phụ trách giao diện và gọi Service. Các kiểm tra quyền theo trạng thái mới nhất của chứng từ được đưa về tầng dữ liệu thay vì tự viết SQL trong màn hình.
- Các đường dẫn `core/repositories/` và `core/services/` cũ được giữ làm wrapper tương thích; code mới nên import trực tiếp từ package phân hệ.
- `ui/main_windows.py` khởi tạo cửa sổ và các trang; `ui/sidebar_navigation.py` phụ trách nhóm menu, điều hướng và quyền hiển thị. Giao diện nhân viên được chia thành package danh sách và chi tiết.
- Database dùng các SQL Server Login/Database User và các role như `rl_QuanLy`, `rl_ThuNgan`, `rl_NhanVienKho`, `rl_KeToan`. Tài khoản admin có quyền rộng để quản trị.
- Tầng Service/Repository hiện có thể được tái sử dụng khi phát triển Backend, nhưng Backend vẫn cần lớp xác thực, phân quyền theo từng request và quản lý kết nối riêng; không dùng trực tiếp các lớp PySide6 hoặc chia sẻ một kết nối Desktop toàn cục cho nhiều request.
## 3. Kiến trúc mục tiêu

```text
Trình duyệt (LAN / Internet)
          |
          | HTTPS
          v
Reverse proxy (Caddy / Nginx / IIS)
          |
          +----------------------+
          |                      |
          v                      v
React Web                 FastAPI Backend
                               |
                    +----------+----------+
                    |                     |
                 Services             Security/RBAC
                    |
                Repositories
                    |
                 pyodbc
                    |
                SQL Server
```

### Công nghệ dự kiến

| Thành phần | Công nghệ | Trách nhiệm |
|---|---|---|
| Frontend | React + TypeScript + Vite | Giao diện Web, định tuyến trang, trạng thái và gọi API |
| Bộ giao diện | Ant Design tùy biến theme hoặc component dùng chung | Bảng, biểu mẫu, modal, date picker, phân trang |
| Backend | FastAPI + Pydantic | REST API, xác thực, kiểm tra dữ liệu và quyền |
| Truy cập dữ liệu | pyodbc, giữ SQL có tham số | Kết nối SQL Server và transaction |
| Kiểm thử API | pytest + TestClient/httpx | Kiểm thử endpoint và quyền |
| Kiểm thử UI | Playwright | Kiểm thử luồng người dùng trên trình duyệt |
| Reverse proxy | Chọn Caddy, Nginx hoặc IIS theo máy chủ triển khai | HTTPS, định tuyến frontend/API và giới hạn truy cập |

Không bắt buộc đưa ORM vào ngay từ đầu. Ưu tiên giữ SQL hiện có, chuẩn hóa vào Repository và dùng tham số truy vấn; chỉ cân nhắc ORM khi có lợi ích rõ ràng.

## 4. Cấu trúc thư mục mục tiêu

Cấu trúc dưới đây là đích dự kiến, có thể điều chỉnh sau khi hoàn thành giai đoạn tách nghiệp vụ:

```text
project/
├── database/                 # Kết nối và script SQL hiện tại
├── core/
│   ├── hoa_don/
│   │   ├── xu_ly_du_lieu.py  # Service nghiệp vụ
│   │   └── truy_van_sql.py   # Repository SQL
│   ├── phieu_nhap/
│   ├── san_pham/
│   ├── doi_tra/
│   ├── nha_cung_cap/
│   ├── nhan_vien/
│   ├── ca_lam_viec/
│   ├── khuyen_mai/
│   ├── danh_muc/
│   ├── bao_cao/
│   └── common/               # Cấu hình và tiện ích dùng chung
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/               # Routers/endpoints
│   │   ├── schemas/           # Pydantic request/response
│   │   ├── security/           # Session, RBAC, dependencies
│   │   └── config.py
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── features/
│   │   └── services/          # API client
│   └── tests/
├── ui/                       # Desktop PySide6, tiếp tục được duy trì
├── tests/                    # Kiểm thử Desktop hiện tại
└── docs/
```

### Quy tắc phân lớp

- **`xu_ly_du_lieu.py` (Service):** chứa quy tắc nghiệp vụ, kiểm tra đầu vào, tính tiền và điều phối các bước xử lý.
- **`truy_van_sql.py` (Repository):** đảm nhiệm truy vấn SQL, đọc/ghi dữ liệu và transaction; các kiểm tra cần khóa/trạng thái mới nhất phải nằm trong cùng transaction.
- **API Router:** nhận request, xác thực đầu vào, gọi service và chuyển kết quả thành response; không viết truy vấn SQL dài trực tiếp trong router.
- **Schema:** định nghĩa dữ liệu vào/ra; không trả thông tin nhạy cảm như mật khẩu, chuỗi kết nối hoặc dữ liệu nội bộ không cần thiết.
- **Frontend:** không chứa bí mật hoặc thông tin kết nối SQL; không tự tính lại kết quả tài chính để thay thế Backend.

## 5. Các quyết định kỹ thuật cần chốt trước khi viết chức năng

### 5.1. Xác thực và phân quyền

Desktop hiện đăng nhập bằng SQL Server Login và các role ở SQL Server. Mô hình này không thể bê nguyên sang trình duyệt vì kết nối database phải nằm ở máy chủ Backend và nhiều người dùng có thể thao tác đồng thời.

Phương án mục tiêu cần đánh giá trong giai đoạn nền tảng:

1. Backend xác thực thông tin đăng nhập ở máy chủ; không lưu mật khẩu dạng rõ và không gửi lại thông tin SQL cho trình duyệt.
2. Phiên Web gắn với mã nhân viên, vai trò và trạng thái tài khoản; session/token có thời hạn, có cơ chế đăng xuất và thu hồi.
3. Backend dùng tài khoản kết nối riêng có quyền tối thiểu cần thiết; kiểm tra role và quyền theo từng endpoint/service. Role SQL hiện tại của Desktop vẫn được giữ nguyên.
4. Thao tác quản trị SQL Login (tạo/khóa tài khoản) phải đi qua một service riêng, chỉ gọi được bởi Admin, có kiểm tra đầu vào và ghi log; không dùng tài khoản SQL quyền cao cho mọi request.
5. Trước khi chốt, phải quyết định cơ chế xác thực Web có dùng chung mật khẩu SQL Login của Desktop hay có thông tin đăng nhập Web riêng. Không lưu mật khẩu SQL người dùng trong session hoặc database.

Không được dựa vào việc ẩn nút hoặc menu React để bảo vệ endpoint. Mặc định từ chối khi không xác định được quyền. Admin có quyền vượt các giới hạn nghiệp vụ theo chính sách đã có, nhưng hành động vẫn phải được ghi nhận.

### 5.2. Kết nối và transaction

- Không dùng một đối tượng kết nối toàn cục chia sẻ giữa nhiều request/người dùng như cách Desktop đang truyền `db` vào các cửa sổ.
- Mỗi request hoặc đơn vị công việc lấy kết nối riêng từ lớp quản lý kết nối; đóng cursor/kết nối đúng cách.
- Mỗi thao tác nhiều bước phải có transaction rõ ràng: commit khi toàn bộ bước thành công, rollback khi có lỗi.
- Kiểm thử cạnh tranh khi hai thu ngân bán cùng sản phẩm hoặc cùng lúc cập nhật tồn kho.
- Không trả lỗi SQL thô, chuỗi kết nối hoặc thông tin máy chủ cho trình duyệt.

### 5.3. Phiên đăng nhập và trình duyệt

- Ưu tiên cookie `HttpOnly`, `Secure`, `SameSite` khi frontend và API được phục vụ cùng domain; bổ sung CSRF protection phù hợp. Nếu chọn Bearer token thì access token ngắn hạn và refresh token phải được bảo vệ/thu hồi.
- Giới hạn CORS theo domain được cấu hình; không dùng wildcard trong production.
- Có rate limit cho đăng nhập, khóa hoặc trì hoãn thử sai theo chính sách; ghi log sự kiện đăng nhập và thao tác nhạy cảm.
- Bí mật và cấu hình theo môi trường phải đặt trong biến môi trường/secret store, không commit vào Git.

## 6. Phạm vi chức năng Web

Các phân hệ giữ tương ứng với Desktop:

| Phân hệ | Phạm vi dự kiến |
|---|---|
| Đăng nhập | Đăng nhập, đăng xuất, phiên hết hạn, đổi mật khẩu theo cơ chế được chốt |
| Tổng quan | KPI và dữ liệu tổng quan theo quyền |
| Sản phẩm | Danh sách, thêm/sửa/chi tiết, tìm theo mã, tên, barcode và ISBN |
| Nhà cung cấp | Danh sách, thêm/sửa/chi tiết, tra cứu MST nếu dịch vụ nguồn đáp ứng |
| Phiếu nhập | Lập phiếu, chi tiết, tìm kiếm/lọc, hủy theo quyền và quy tắc hiện tại |
| Hóa đơn | POS, tìm/chọn sản phẩm, barcode, số lượng, khuyến mãi, thanh toán, in |
| Đổi trả | Tra cứu hóa đơn, lập/duyệt/xử lý phiếu theo đúng quyền và trạng thái |
| Ca làm việc | Phân ca, xem chi tiết, bắt đầu/kết thúc/chốt ca và quy tắc xóa ca |
| Nhân viên/tài khoản | Hồ sơ, vai trò, trạng thái tài khoản và thao tác Admin |
| Danh mục | Tác giả, thể loại, nhà xuất bản, thương hiệu |
| Khuyến mãi | Danh sách, tạo/sửa và điều kiện áp dụng |
| Báo cáo | Tổng quan, doanh thu, hóa đơn, phiếu nhập, đổi trả, tồn kho, sản phẩm, ca |

Chưa tự ý thêm module khách hàng/đăng ký khách hàng vì phạm vi hiện tại là phần mềm nội bộ do nhân viên sử dụng.

## 7. Giao diện Web gần giống Desktop

### Khung giao diện

- Sidebar bên trái có logo/tên hệ thống, các nhóm menu và trạng thái thu gọn/mở rộng.
- Vùng nội dung bên phải có tiêu đề trang, mô tả ngắn, thông tin tài khoản và thao tác chính.
- Bảng dữ liệu giữ cách trình bày quen thuộc: tiêu đề cột rõ ràng, sắp xếp, tìm kiếm, lọc ngày, phân trang, trạng thái và thao tác chi tiết.
- Thêm/sửa/chi tiết ưu tiên modal hoặc drawer khi phù hợp, tránh chuyển trang không cần thiết.
- Màn hình POS ưu tiên thao tác bàn phím và máy quét barcode; tự focus ô tìm kiếm, chọn sản phẩm nhanh và cập nhật giỏ hàng.
- Màu sắc, khoảng cách, kiểu nút, trạng thái hover/disabled và cách đặt tên chức năng bám sát Desktop; điều chỉnh riêng để hợp với trình duyệt.
- Responsive: ưu tiên desktop/laptop; trên tablet sidebar có thể thu gọn; trên điện thoại bảng rộng chuyển thành dạng cuộn ngang hoặc danh sách thẻ.

### Các component dùng chung

- `AppLayout`, `Sidebar`, `Topbar`, `PageHeader`
- `DataTable`, `SearchToolbar`, `DateRangeFilter`, `StatusTag`
- `ConfirmDialog`, `DetailDrawer`, `FormModal`
- `MoneyInput`, `ProductLookup`, `BarcodeInput`
- `PermissionGuard`, `LoadingState`, `EmptyState`, `ErrorState`

## 8. Kế hoạch triển khai theo giai đoạn

### Giai đoạn 0 — Chuẩn bị nhánh và đặc tả

- [x] Tạo nhánh `feature/web-app` từ `fix/refactor-business-logic-and-setup`.
- [x] Ghi kế hoạch triển khai ban đầu vào tài liệu này.
- [ ] Chốt cơ chế đăng nhập Web và ranh giới quyền SQL/API.
- [ ] Chốt máy chủ chạy Backend, nơi đặt SQL Server và domain truy cập Internet.

**Kết quả:** đặc tả kiến trúc và quyết định bảo mật được thống nhất trước khi viết chức năng.

### Giai đoạn 1 — Tách nghiệp vụ khỏi PySide6

- [x] Rà soát các luồng sản phẩm và danh mục; ghi nhận truy vấn, quy tắc mã tự sinh, xóa mềm, kiểm tra tồn và liên kết sách.
- [x] Tạo Repository và Service dùng chung cho sản phẩm và bốn nhóm danh mục.
- [x] Chuyển Desktop gọi Service mới ở danh sách/chi tiết/form sản phẩm và các màn hình danh mục.
- [x] Tạo Repository/Service cho nhà cung cấp và phiếu nhập; chuyển Desktop dùng Service cho danh sách, biểu mẫu, chi tiết, lập phiếu và hủy phiếu.
- [x] Giữ SQL có tham số; transaction lập/hủy phiếu nhập và cập nhật tồn kho/giá nhập, lập/hủy hóa đơn và hoàn kho nằm trong Repository.
- [x] Bổ sung kiểm thử service sản phẩm, nhà cung cấp, phiếu nhập, hóa đơn và đổi trả bằng repository giả; kiểm tra cú pháp và toàn bộ unit test qua GitHub Actions (133 test đạt).
- [ ] Chạy kiểm thử tích hợp trên SQL Server thử nghiệm và kiểm tra thủ công các luồng Desktop trên Windows.

**Ghi chú tiến độ:** Đã tách sản phẩm, danh mục, nhà cung cấp, phiếu nhập, hóa đơn, đổi trả, nhân viên/tài khoản, ca làm việc, khuyến mãi và 8 báo cáo. Desktop đã chuyển các màn hình tương ứng sang Service. Thao tác SQL Login vẫn được giữ sau cổng Admin, chưa mở thành API Web. Các báo cáo hiện dùng Repository/Service chuyên biệt, không còn truy vấn SQL trực tiếp trong trang báo cáo. Chưa nghiệm thu tích hợp SQL Server thật hoặc kiểm tra thủ công Desktop trên Windows.

**Kết quả:** Desktop vẫn chạy, Backend có thể tái sử dụng cùng service/repository.

### Giai đoạn 2 — Nền tảng Backend

- [ ] Tạo FastAPI app, cấu hình môi trường và dependency quản lý kết nối.
- [ ] Tạo health check không tiết lộ thông tin nhạy cảm.
- [ ] Xây dựng xác thực, session, logout, đổi mật khẩu và RBAC.
- [ ] Chuẩn hóa response, validation, lỗi và logging.
- [ ] Viết kiểm thử API cho đăng nhập, quyền truy cập và quyền Admin.

**Kết quả:** API nền tảng an toàn, có thể tích hợp Frontend.

### Giai đoạn 3 — Khung Frontend

- [ ] Khởi tạo React + TypeScript + Vite.
- [ ] Dựng layout gần giống Desktop: sidebar, nhóm menu, topbar và vùng nội dung.
- [ ] Dựng trang đăng nhập, trang tổng quan và quản lý session.
- [ ] Tạo API client, xử lý lỗi/hết phiên, loading/empty state.
- [ ] Tạo component dùng chung cho bảng, bộ lọc, modal và form.

**Kết quả:** có thể đăng nhập và điều hướng giao diện Web theo quyền.

### Giai đoạn 4 — Danh mục và kho

- [ ] Sản phẩm, barcode, ISBN.
- [ ] Tác giả, thể loại, nhà xuất bản, thương hiệu.
- [ ] Nhà cung cấp và tra cứu MST.
- [ ] Phiếu nhập, chi tiết phiếu, hủy phiếu theo quyền.
- [ ] Kiểm thử đối chiếu dữ liệu với Desktop.

**Kết quả:** hoàn thành các nghiệp vụ quản lý danh mục và nhập kho.

### Giai đoạn 5 — Bán hàng và đổi trả

- [ ] POS và tìm kiếm/quét barcode.
- [ ] Giỏ hàng, số lượng, VAT, khuyến mãi và thanh toán.
- [ ] In hóa đơn hoặc xuất bản in phù hợp trên trình duyệt.
- [ ] Phiếu đổi trả, tình trạng hàng và hình thức xử lý.
- [ ] Kiểm thử đồng thời, cập nhật tồn kho và chống ghi nhận giao dịch trùng.

**Kết quả:** hoàn thành luồng bán hàng và đổi trả quan trọng nhất.

### Giai đoạn 6 — Nhân sự, ca và báo cáo

- [x] Tách Repository/Service cho hồ sơ nhân viên, tạo tài khoản, đọc quyền, đổi vai trò, bật/tắt và xóa SQL Login; Desktop gọi Service.
- [ ] Thiết kế xác thực Web, phiên đăng nhập và RBAC phía Backend; không tái sử dụng quyền UI làm ranh giới bảo mật.
- [x] Tách Repository/Service cho lịch ca, đăng ký ca, tạo ca, ghi tiền cuối ca, lịch sử, danh sách nhân viên theo ca và xóa ca; Desktop gọi Service.
- [ ] Kiểm thử tích hợp SQL Server cho thời gian ca, đăng ký trùng, chốt tiền một lần, hóa đơn liên kết và xóa ca.
- [x] Tách Repository/Service cho khuyến mãi: danh sách, lọc, xem chi tiết, tạo, đổi tên và xóa mềm; kiểm tra quyền Admin/Quản lý tại SQL Repository; Desktop gọi Service.
- [x] Tách Repository/Service cho 8 báo cáo: tổng quan, doanh thu, hóa đơn, phiếu nhập, đổi trả, tồn kho, sản phẩm và ca làm việc; giữ bộ lọc, KPI, biểu đồ, bảng và xuất CSV ở Desktop.
- [ ] Kiểm thử quyền theo ma trận vai trò.

**Kết quả:** độ phủ chức năng Web tương đương các phân hệ Desktop trong phạm vi dự án.

### Giai đoạn 7 — Triển khai LAN và Internet

- [ ] Đóng gói frontend/backend và cấu hình production.
- [ ] Triển khai LAN qua địa chỉ nội bộ hoặc DNS nội bộ.
- [ ] Cấu hình domain Internet và HTTPS tại reverse proxy.
- [ ] Chỉ công khai cổng HTTPS; không mở cổng SQL Server ra Internet.
- [ ] Firewall chỉ cho Backend truy cập SQL Server; cấu hình VPN hoặc lớp bảo vệ truy cập từ xa phù hợp.
- [ ] Cấu hình backup database, log, giám sát sức khỏe và quy trình khôi phục.
- [ ] Kiểm thử từ mạng LAN, mạng di động bên ngoài và nhiều tài khoản cùng lúc.

**Kết quả:** cùng một hệ thống Web hoạt động được cả trong LAN và từ Internet.

## 9. An toàn và vận hành bắt buộc

- SQL Server không được public trực tiếp ra Internet; chỉ Backend có quyền truy cập database.
- Dùng HTTPS cho toàn bộ đăng nhập và thao tác Web.
- Tách tài khoản SQL cho ứng dụng thường và tác vụ quản trị; cấp đúng quyền tối thiểu.
- Có backup định kỳ và đã thử khôi phục, không chỉ xác nhận job backup chạy thành công.
- Có audit log cho tạo/hủy hóa đơn, phiếu nhập, đổi trả, chốt ca, thay đổi quyền và tài khoản.
- Có timeout, xử lý lỗi, giới hạn request và log không chứa mật khẩu/token.
- Kiểm tra quyền ở cả API lẫn thao tác dữ liệu; không tin role do trình duyệt tự gửi lên.
- Các thao tác ghi nhận tiền/tồn kho phải nằm trong transaction và có kiểm soát cập nhật đồng thời.

## 10. Tiêu chí nghiệm thu

1. Desktop hiện tại tiếp tục chạy và không bị thay đổi ngoài các refactor đã kiểm thử.
2. Web dùng đúng database hiện tại; dữ liệu tạo từ Desktop thấy được trên Web và ngược lại.
3. Các role chỉ thực hiện được đúng thao tác đã được cấp quyền; gọi API trực tiếp cũng không vượt quyền.
4. Hóa đơn, nhập kho, đổi trả và chốt ca cập nhật dữ liệu đúng, không tạo giao dịch dở dang khi có lỗi.
5. Barcode và ISBN hoạt động ở các màn hình đã hỗ trợ trên Desktop.
6. Nhiều người dùng có thể thao tác đồng thời mà không dùng chung cursor/connection hoặc làm sai số lượng tồn.
7. Truy cập qua địa chỉ nội bộ và domain Internet đều dùng HTTPS; SQL Server không mở công khai.
8. Có kiểm thử tự động cho service/API và kiểm thử trình duyệt cho các luồng quan trọng.
9. Có tài liệu cài đặt, cấu hình, backup/restore và triển khai.

## 11. Rủi ro và cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| SQL và UI đang gắn chặt | Tách từng phân hệ, chuyển Desktop sang dùng Service trước |
| Quyền SQL khác quyền Web | Chốt mô hình RBAC và kiểm thử ma trận quyền trước khi mở chức năng |
| Nhiều request chạy đồng thời | Kết nối theo request, transaction, kiểm thử cạnh tranh cập nhật tồn |
| Dữ liệu Desktop/Web không nhất quán | Dùng cùng database và cùng Service/Repository khi có thể |
| Truy cập Internet làm lộ database | Reverse proxy HTTPS, firewall, không expose SQL Server |
| Phạm vi quá lớn | Triển khai theo module, ưu tiên luồng kho và bán hàng |

## 12. Quy tắc làm việc trên nhánh

- Chỉ phát triển Web trên `feature/web-app`; không commit trực tiếp lên nhánh nền.
- Các thay đổi tách nghiệp vụ phải bảo đảm Desktop tiếp tục hoạt động.
- Commit theo từng giai đoạn/chức năng, ghi rõ phạm vi.
- Chạy test hiện có và test mới trước mỗi mốc.
- Khi đủ chức năng, tạo Pull Request từ `feature/web-app` về `fix/refactor-business-logic-and-setup` để review; không tự hợp nhất vào nhánh nền.
- Không commit `.env`, mật khẩu, token, connection string production hoặc dữ liệu thật.
