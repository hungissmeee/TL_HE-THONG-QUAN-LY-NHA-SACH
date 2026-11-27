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
