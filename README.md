# Tổng quan
- Môn học: Công Nghệ Phần Mềm
    - Tên dự án: Hệ thống quản lý nhà sách
    - Giảng viên: Trần Văn Long
- Thành viên:
  - [Nguyễn Quang Hưng](https://github.com/hungissmeee) - 25S1020043
  - [Nguyễn Trung Hậu](https://github.com/nguyentrunghauqh2-netizen) - 25S1020033
  - [Trần Hưng Hiếu](https://github.com/hiramytran-dev) - 25S1020037
  - [Châu Nguyên Phúc](https://github.com/pcphuc) - 25S1020079
  - [Nguyễn Văn Thuận](https://github.com/vanthuan230620079865-lab) - 25S1020105
  - [Cao Tiến Khang](https://github.com/caotienkhang2007-dev) - 25S1020051
  - [Nguyễn Văn Hoàng](https://github.com/nguyenvanhoang070207-arch) - 25S1020040
- Công nghệ:
  - Ngôn ngữ: Python
  - Database: SQL Server

---

## Mục Lục
- [1. Giới thiệu dự án](#-giới-thiệu-dự-án)
- [2. Đối tượng sử dụng hệ thống](#-đối-tượng-sử-dụng-hệ-thống)
- [3. Quy ước viết mã](#3-quy-ước-viết-mã)

---

## 1. Giới Thiệu Dự Án

Dự án xây dựng giải pháp quản lý tập trung cho mô hình kinh doanh nhà sách với danh mục hàng hóa đa dạng (sách giáo khoa, sách tham khảo, từ điển, văn phòng phẩm, dụng cụ học tập và các mặt hàng tiêu dùng khác).

**Mục tiêu chính của dự án:**
- Thay thế phương thức ghi chép sổ sách thủ công bằng hệ thống cơ sở dữ liệu quan hệ chuẩn hóa, nhất quán.
- Tự động hóa việc theo dõi biến động tồn kho qua từng phiếu nhập, hóa đơn bán hàng và phiếu đổi trả.
- Minh bạch hóa doanh thu theo từng ca làm việc và phân quyền thao tác chặt chẽ theo vai trò nhân sự.

---

## 2. Đối Tượng Sử Dụng Hệ Thống

| Vai trò | Chức năng & Quyền hạn chính |
| :--- | :--- |
| **Quản lý** | Giám sát nhân sự, kiểm tra hàng hóa, phê duyệt phiếu đổi trả trong ngày, xử lý sự cố đền bù hàng hỏng/vỡ. |
| **Nhân viên kho** | Thêm mới thông tin sản phẩm, lập phiếu nhập kho, phiếu xuất chuyển kho và kiểm soát số lượng tồn. |
| **Nhân viên thu ngân** | Quét mã vạch lập hóa đơn, áp dụng khuyến mãi, nhận thanh toán, in phiếu tính tiền và chốt tiền cuối ca. |
| **Kế toán** | Tổng hợp doanh thu từ hóa đơn bán hàng, đối soát chi phí nhập kho và xuất hóa đơn đỏ (VAT) theo yêu cầu. |

---

# 3. Quy ước viết mã

## 3.1. Quy tắc đặt tên
| Kiểu | Mô tả | Ví dụ |
| :--- | :--- | :--- |
| `snake_case` | Tất cả các chữ cái đều viết thường, các từ được nối với nhau bằng dấu gạch dưới (`_`). | `coding_conv`, `ma_sach` |
| `PascalCase` (CapWords) | Chữ cái đầu tiên của mỗi từ đều viết hoa, không sử dụng dấu gạch dưới. | `CodingConv`, `HoaDon` |
| `UPPER_SNAKE_CASE` | Tất cả các chữ cái đều viết hoa, các từ được nối với nhau bằng dấu gạch dưới (`_`). | `FIRST_WEEK_DAY`, `MAX_ITEMS` |
| `_leading_underscore` | Có một dấu gạch dưới ở đầu để biểu thị thành phần sử dụng nội bộ (private/protected). | `_tinh_tong_tien` |

## 3.2. Quy tắc sử dụng khi code
| Loại | Kiểu | Ví dụ | Ghi chú |
| :--- | :--- | :--- | :--- |
| Tên biến | `snake_case` | `first_name`, `so_luong_ton` | Danh từ |
| Tham số | `snake_case` | `display_time`, `ma_nhan_vien` | Danh từ |
| Hằng số | `UPPER_SNAKE_CASE` | `FIRST_WEEK_DAY`, `VAT_RATE` | Viết hoa toàn bộ, có gạch dưới giữa các từ |
| Tên class, Enum, Exception | `PascalCase` | `CreateUser`, `PhieuNhap`, `BookNotFoundError` | Danh từ (Exception dùng hậu tố `Error`) |
| Thuộc tính (Attribute/Property) | `snake_case` | `background_color`, `don_gia` | Danh từ |
| Hàm, phương thức (Function/Method) | `snake_case` | `get_age()`, `tinh_thanh_tien()` | Động từ hoặc cụm động từ |
| Thành phần nội bộ (Private) | `_snake_case` | `_validate_input()` | Bắt đầu bằng 1 dấu gạch dưới |
| Tên file (Module) & thư mục (Package) | `snake_case` | `book_service.py`, `repositories` | Viết thường toàn bộ, nối bằng gạch dưới |
| Lớp trừu tượng / Giao diện (`ABC`, `Protocol`) | `PascalCase` | `BaseRepository`, `PaymentProtocol` | Dùng tiền tố `Base` hoặc hậu tố `ABC`/`Protocol` |

## 3.3. Quy định phân bố mã nguồn
- Tên file mã nguồn Python (`.py`) phải viết theo quy tắc `snake_case` và phản ánh đúng nội dung bên trong. Mỗi file thường chứa một class chính trùng nghĩa với tên file (ví dụ: class `Student` đặt trong file `student.py`, class `HoaDon` đặt trong file `hoa_don.py`).
- Cho phép gộp các class phụ trợ nhỏ, `Enum`, `dataclass` hoặc các lớp ngoại lệ (`Exception`) có liên quan mật thiết trong cùng một module (`.py`) để tránh phân mảnh file không cần thiết.
- Python không có từ khóa `interface` riêng biệt; các giao diện chuẩn được định nghĩa thông qua lớp cơ sở trừu tượng (`abc.ABC`) hoặc `typing.Protocol` và phải được khai báo trong các module riêng biệt (ví dụ: `base_repository.py` hoặc đặt trong package `interfaces/`).
- Chỉ thêm `__init__.py` khi package cần công bố API, tái xuất thành phần hoặc có khởi tạo riêng. Có thể dùng namespace package cho thư mục chỉ tổ chức module, không cần file rỗng.

---

# 4. Cấu trúc mã nguồn hiện tại

Mã nguồn được tổ chức theo từng phân hệ nghiệp vụ. Trong mỗi phân hệ của `core/`, hai tệp có tên cố định giúp nhận biết ngay trách nhiệm: `service.py` chứa Service và quy tắc nghiệp vụ; `repository.py` chứa Repository và câu lệnh SQL.

```text
.
├── main.py
├── database/
│   ├── connection.py
│   ├── script.sql
│   └── migrations/
├── core/
│   ├── hoa_don/
│   │   ├── service.py
│   │   └── repository.py
│   ├── phieu_nhap/
│   ├── san_pham/
│   ├── doi_tra/
│   ├── nha_cung_cap/
│   ├── nhan_vien/
│   ├── ca_lam_viec/
│   ├── khuyen_mai/
│   ├── danh_muc/
│   ├── bao_cao/
│   ├── catalog_config.py
│   └── sql_support.py
├── ui/
│   ├── main_windows.py
│   ├── sidebar_navigation.py
│   ├── nhan_vien/
│   │   ├── danh_sach.py
│   │   └── chi_tiet.py
│   ├── hoa_don/
│   ├── phieu_nhap/
│   ├── san_pham/
│   ├── nha_cung_cap/
│   ├── ca_lam_viec/
│   ├── doi_tra/
│   ├── khuyen_mai/
│   └── bao_cao/
└── tests/
```

Mỗi phân hệ `core/` chỉ có `service.py` và `repository.py` làm hai điểm vào chính. Không duy trì thư mục wrapper hoặc facade legacy. Các `__init__.py` trong phân hệ nghiệp vụ chỉ được giữ khi cần tái xuất Service/Repository như API công khai.

## 4.1. Quy ước phân chia trách nhiệm

- `ui/`: nhận thao tác, hiển thị dữ liệu và gọi Service; không tự mở cursor hoặc viết SQL.
- `core/<phan_he>/service.py`: kiểm tra đầu vào, tính toán và điều phối quy tắc nghiệp vụ.
- `core/<phan_he>/repository.py`: truy vấn, đọc/ghi SQL Server và transaction của thao tác dữ liệu.
- `database/connection.py`: quản lý kết nối và phiên đăng nhập SQL Server; `core/nhan_vien/repository.py` chịu trách nhiệm các thao tác Login/User và role.
- `core/sql_support.py`: tiện ích dùng chung để phân giải nguồn kết nối.
- `ui/sidebar_navigation.py`: nhóm menu, điều hướng trang và quyền hiển thị sidebar.
- `ui/formatters.py`, `ui/styles.py`, `ui/table_sort.py`: tiện ích hiển thị dùng chung.
- `ui/bao_cao/`: các trang báo cáo dùng chung lớp nền `ReportBasePage`.
## 4.2. Nguyên tắc refactor

- Giữ nguyên câu SQL, tên bảng/cột, quy tắc tính tiền, cập nhật tồn kho và phân quyền khi chỉ thực hiện refactor cấu trúc.
- Khi thêm hoặc đổi tên module, phải cập nhật toàn bộ import và chạy `tests/test_import.py` cùng UI import smoke-test; không tạo facade legacy nếu không có yêu cầu tương thích bên ngoài.
- Mỗi thay đổi nghiệp vụ cần có kiểm thử riêng, không gộp chung với commit chỉ định dạng hoặc sắp xếp mã nguồn.


## 4.3. Kiểm thử tự động

- `tests/test_dinh_dang.py`: kiểm thử định dạng tiền, ngày giờ và số liệu.
- `tests/test_import.py`: kiểm tra import nội bộ trỏ tới module/package có tồn tại.
- `tests/test_giao_dien.py`: kiểm tra import toàn bộ package `ui` hiện tại với PySide6.
- GitHub Actions chạy `compileall`, unit test và UI import smoke-test khi có push lên nhánh refactor hoặc mở Pull Request vào `main`.


## 4.4. Quy ước chú thích trong code

- Mỗi module có docstring đầu tệp nêu mục đích và phạm vi trách nhiệm.
- Mỗi class giao diện hoặc lớp xử lý chính có docstring mô tả vai trò.
- Các hàm có xử lý nghiệp vụ, truy vấn dữ liệu, kiểm tra quyền, tính tiền, cập nhật tồn kho hoặc xử lý giao dịch cần có docstring hoặc comment giải thích rõ mục đích và lý do xử lý.
- Comment tập trung giải thích những quyết định không hiển nhiên, không lặp lại nguyên văn từng câu lệnh.
- Nội dung comment và docstring dùng tiếng Việt; tên kỹ thuật, tên thư viện, API và thuật ngữ SQL/Python giữ nguyên khi cần thiết.


---

# 5. Cài đặt và cấu hình môi trường

## 5.1. Cài thư viện Python

Yêu cầu Python 3.11 trở lên và Microsoft ODBC Driver for SQL Server tương thích với máy triển khai.

```bash
python -m pip install -r requirements.txt
```

## 5.2. Cấu hình SQL Server

Sao chép `.env.example` để tham khảo các biến môi trường. Ứng dụng đọc trực tiếp biến môi trường của hệ điều hành, không tự nạp tệp `.env`.

PowerShell:

```powershell
$env:BOOKHUB_SQL_SERVER = "localhost"
$env:BOOKHUB_SQL_DATABASE = "CSDLQLNHASACH"
$env:BOOKHUB_SQL_DRIVER = "ODBC Driver 18 for SQL Server"
$env:BOOKHUB_SQL_ENCRYPT = "yes"
$env:BOOKHUB_TRUST_SERVER_CERTIFICATE = "yes"
python main.py
```

Linux/macOS:

```bash
export BOOKHUB_SQL_SERVER="localhost"
export BOOKHUB_SQL_DATABASE="CSDLQLNHASACH"
export BOOKHUB_SQL_DRIVER="ODBC Driver 18 for SQL Server"
export BOOKHUB_SQL_ENCRYPT="yes"
export BOOKHUB_TRUST_SERVER_CERTIFICATE="yes"
python main.py
```

Đổi `BOOKHUB_SQL_SERVER` theo SQL Server instance của máy chạy ứng dụng. Trong môi trường production, nên dùng chứng chỉ máy chủ được hệ điều hành tin cậy và đặt `BOOKHUB_TRUST_SERVER_CERTIFICATE=no`; giá trị `yes` chỉ nhằm tương thích với chứng chỉ tự ký ở môi trường phát triển.

## 5.3. Cập nhật ràng buộc dữ liệu

Sau khi database đã được tạo bằng quy trình cài đặt hiện tại, sao lưu database rồi chạy:

`database/migrations/001_data_integrity_constraints.sql`

Migration bổ sung các CHECK constraint cho giá, tồn kho, số lượng, VAT, tiền và thời gian ca. Migration kiểm tra cả dữ liệu hiện có; cần xử lý các dòng dữ liệu không hợp lệ trước khi chạy. Các cột nullable được giữ nguyên để không tự ý thay đổi dữ liệu lịch sử và quy tắc nghiệp vụ.

## 5.4. Cập nhật nghiệp vụ đổi trả

Sao lưu database trước khi cập nhật, sau đó chạy:

`database/migrations/001_remove_return_unit_refund.sql`

## 5.5. Trung tâm báo cáo POS

Phân hệ báo cáo được tổ chức thành **một Trung tâm báo cáo**. Danh mục được chia theo nhóm nghiệp vụ; nội dung là bảng báo cáo dạng chứng từ, có kỳ báo cáo, bộ lọc, dòng tổng cộng và chức năng xuất Excel `.xlsx`. Không sử dụng các thẻ KPI tiền lớn.

| Nhóm | Báo cáo | Nội dung |
|---|---|---|
| Bán hàng | Báo cáo cuối ngày | Mã chứng từ, thời gian, số lượng sản phẩm, doanh thu, giảm giá, thực thu, các chỉ tiêu trả/đổi, nhân viên, ca và trạng thái |
| Bán hàng | Bán hàng theo thời gian | Tổng hợp ngày/tháng/năm: số đơn, số lượng bán, tiền hàng, giảm giá, doanh số, số lượng trả, số phiếu trả, tiền hoàn và chênh lệch phát sinh trong kỳ |
| Bán hàng | Bán hàng theo nhân viên | Doanh số theo nhân viên lập hóa đơn; số phiếu hoàn/đổi và tiền hoàn theo nhân viên lập phiếu đổi trả |
| Bán hàng | Bán hàng theo sản phẩm | Số lượng bán, doanh số bán, doanh thu thuần, số hóa đơn, hoàn tiền, đổi hàng và tồn hiện tại; không phân bổ tiền hoàn xuống từng sản phẩm hoặc nhóm theo khách hàng |
| Bán hàng | Hiệu quả khuyến mãi | Số hóa đơn, tiền hàng, tiền giảm, doanh số và tiền hoàn lũy kế gắn với các hóa đơn của chương trình |
| Hàng hóa/kho | Nhập – xuất – tồn | Mã hàng, tên hàng, đơn vị; tồn đầu, tổng nhập, tổng xuất và tồn cuối theo số lượng/giá trị |
| Hàng hóa/kho | Xuất nhập tồn chi tiết (thẻ kho) | Số dư đầu kỳ và từng giao dịch theo mặt hàng, ngày chứng từ, mã chứng từ, diễn giải, lượng nhập/xuất và tồn sau giao dịch |
| Hàng hóa/kho | Tồn kho hiện tại | STT, mã/tên hàng, đơn vị, số lượng tồn, giá trị tồn ước tính, giá nhập/giá bán và tình trạng |
| Nhập hàng | Chi tiết nhập hàng | Từng dòng hàng trên phiếu nhập hợp lệ: nhà cung cấp, mã/tên hàng, đơn vị, số lượng, đơn giá, thành tiền và thông tin chứng từ |
| Nhập hàng | Tổng hợp mua hàng theo mặt hàng | Tổng số lượng, giá trị mua, đơn giá bình quân và số phiếu nhập theo sản phẩm |
| Nhập hàng | Nhập hàng theo nhà cung cấp | Số phiếu, tổng số lượng và trị giá nhập theo nhà cung cấp |
| Đổi trả | Chi tiết đổi trả | Mã phiếu, hóa đơn gốc, nhân viên xử lý, lý do, số dòng, số lượng hoàn/đổi, tình trạng hàng và tổng tiền hoàn cấp phiếu |
| Ca làm việc | Báo cáo cuối ca | Lượt nhân viên, số hóa đơn, số lượng bán, doanh số, phiếu trả, tiền hoàn, tiền đầu ca, tiền kiểm kê cuối ca và trạng thái chốt |


### Quy ước số liệu

- Doanh số bán được xác định từ hóa đơn hợp lệ sau khuyến mãi; tiền giảm được làm tròn riêng từng hóa đơn theo cách tính của ứng dụng.
- Báo cáo cuối ngày lấy tiền hoàn lũy kế theo hóa đơn gốc. Báo cáo bán hàng theo thời gian nhóm doanh số theo ngày lập hóa đơn và tiền hoàn theo ngày lập phiếu; chênh lệch theo kỳ không phải doanh thu thuần theo hóa đơn gốc.
- Hóa đơn không lưu thông tin khách hàng; nhãn “Khách lẻ” là nhãn hiển thị, không phải dữ liệu khách hàng được lưu.
- Báo cáo bán hàng theo sản phẩm chỉ tổng hợp theo mặt hàng; không thể nhóm theo từng khách hàng vì CSDL không có hồ sơ khách hàng.
- Phiếu nhập không lưu chiết khấu mua/giá trị giảm giá hoặc phiếu trả nhà cung cấp; báo cáo tổng hợp mua theo mặt hàng chỉ hiển thị các chỉ tiêu có dữ liệu thực tế (số lượng, giá trị mua, đơn giá bình quân và số phiếu nhập).
- Báo cáo tồn hiện tại chỉ liệt kê hàng hóa trong danh mục sản phẩm; hệ thống không quản lý tài sản máy móc, thiết bị.
- Tiền hoàn chỉ lưu ở `PHIEU_DOI_TRA.TONG_TIEN_HOAN`; báo cáo sản phẩm không tính hoặc phân bổ đơn giá hoàn cho từng mã hàng.
- Báo cáo tồn kho hiện tại là ảnh chụp theo `SAN_PHAM.SLTON`. Giá trị tồn dùng `SAN_PHAM.GIANHAP` hiện lưu, không phải giá vốn lịch sử theo ngày.
- Báo cáo nhập–xuất–tồn và thẻ kho tái dựng từ số tồn hiện tại cùng các hóa đơn, phiếu nhập và phiếu đổi trả còn hiệu lực. CSDL chưa có nhật ký điều chỉnh kho riêng; nếu đã chỉnh tồn thủ công hoặc có giao dịch ngoài hệ thống thì tồn đầu/tồn chạy tái dựng có thể chênh lệch. Tổng nhập gồm phiếu nhập nhà cung cấp và hàng hoàn tiền nguyên vẹn nhập lại; tổng xuất gồm bán hàng và hàng xuất đổi. Giá trị tồn, hàng trả nhập lại và xuất kho ước tính theo giá nhập hiện lưu; trị giá mua vào từ nhà cung cấp lấy theo đơn giá trên phiếu nhập.
- Tiền cuối ca là số kiểm kê ghi nhận, không đồng nghĩa với doanh số hoặc dòng tiền thực thu.

### Phạm vi kế toán

Đây là báo cáo quản trị nội bộ/POS, không phải bộ báo cáo tài chính hoặc sổ kế toán chính thức. CSDL hiện chưa có sổ cái/bút toán, chi phí vận hành, sổ quỹ thu–chi đầy đủ, thanh toán công nợ, phương thức thanh toán hoặc lịch sử giá vốn theo từng lần xuất. Vì vậy hệ thống chưa thể tính chính xác lợi nhuận ròng, công nợ phải thu/phải trả hay lập báo cáo tài chính/thuế chính thức.

### Xuất Excel

Nút **Xuất Excel** tạo tệp `.xlsx` có tên báo cáo, đơn vị, kỳ báo cáo, ngày xuất, tiêu đề nhóm cột (với báo cáo nhập–xuất–tồn), định dạng số/ngày/tiền, bộ lọc cột, cố định hàng tiêu đề và công thức tổng cộng. Báo cáo có thể gồm các bảng riêng; mỗi bảng có thể xuất độc lập theo lựa chọn tương ứng nếu được đăng ký trong trung tâm.

