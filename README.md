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
- Các thư mục chức năng (package) cần được tổ chức rõ ràng theo từng tầng (như `models/`, `repositories/`, `services/`, `ui/`) và có file `__init__.py` để quản lý việc import.