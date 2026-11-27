# Test case – Hệ thống quản lý nhà sách

Tài liệu này là danh sách kiểm thử chức năng (manual/acceptance test). Mỗi test case có thể thực hiện độc lập trên cơ sở dữ liệu kiểm thử đã được tạo theo database/script.sql. Không chạy các thao tác xóa, hủy hoặc cập nhật dữ liệu trên cơ sở dữ liệu thật.

## Quy ước

- Kết quả mong đợi được xem là điều kiện đạt (PASS). Ghi lại kết quả thực tế và bằng chứng khi thực hiện.
- Vai trò Admin dùng tài khoản SQL admin; các vai trò còn lại dùng tài khoản đã được gán đúng Database Role.
- Chuẩn bị tối thiểu: một Quản lý, một Thu ngân, một Nhân viên kho, một Kế toán; một sản phẩm còn hàng, một sản phẩm hết hàng, một sản phẩm đã xóa mềm; một NCC đang hoạt động và một NCC đã ngừng hoạt động; chương trình khuyến mãi còn hiệu lực; các ca chưa bắt đầu, đang diễn ra và đã kết thúc.
- Với case có thay đổi tồn kho, ghi lại SLTON trước và sau thao tác. Với case tiền, đối chiếu đơn giá, VAT, giảm giá và số tiền sau cùng.
- Ưu tiên: P0 = luồng cốt lõi hoặc toàn vẹn dữ liệu; P1 = chức năng thường dùng; P2 = hiển thị/tiện ích.

## 1. Đăng nhập, đăng xuất và mật khẩu

| ID | Ưu tiên | Vai trò | Bước kiểm thử | Kết quả mong đợi |
|---|---|---|---|---|
| AUTH-01 | P0 | Tất cả | Để trống tài khoản hoặc mật khẩu rồi nhấn Đăng nhập. | Hiển thị cảnh báo yêu cầu nhập đủ; không mở cửa sổ chính. |
| AUTH-02 | P0 | Tất cả | Nhập tài khoản/mật khẩu SQL Server không hợp lệ. | Đăng nhập thất bại; hiển thị lỗi; ứng dụng vẫn ở cửa sổ đăng nhập. |
| AUTH-03 | P0 | Nhân viên hợp lệ | Đăng nhập bằng Login có Database User và hồ sơ NHAN_VIEN tương ứng. | Mở cửa sổ chính; tên, mã, vai trò và SĐT hiển thị đúng. |
| AUTH-04 | P1 | Tài khoản không có hồ sơ | Đăng nhập bằng SQL Login chưa có hồ sơ NHAN_VIEN. | Không hiển thị nhầm thông tin nhân viên; thông báo trạng thái hồ sơ không khớp. |
| AUTH-05 | P1 | Nhân viên | Nhấn Đăng xuất và xác nhận. | Kết nối hiện tại được đóng; trở về màn hình đăng nhập; mật khẩu cũ được xóa khỏi ô nhập. |
| AUTH-06 | P1 | Nhân viên | Đăng xuất nhưng chọn Không ở hộp thoại xác nhận. | Không đăng xuất; cửa sổ chính và kết nối vẫn hoạt động. |
| AUTH-07 | P1 | Nhân viên | Đổi mật khẩu với mật khẩu cũ sai. | SQL Server từ chối; mật khẩu không thay đổi. |
| AUTH-08 | P1 | Nhân viên | Đổi mật khẩu với hai ô mật khẩu mới không trùng nhau. | Hiển thị cảnh báo; không gửi lệnh đổi mật khẩu. |
| AUTH-09 | P1 | Nhân viên | Đổi mật khẩu mới giống mật khẩu hiện tại. | Hiển thị cảnh báo; không thực hiện thay đổi. |
| AUTH-10 | P0 | Nhân viên | Đổi mật khẩu hợp lệ, sau đó đăng xuất và đăng nhập lại bằng mật khẩu mới. | Đổi mật khẩu thành công; mật khẩu mới đăng nhập được, mật khẩu cũ không còn dùng được. |

## 2. Nhân viên và phân quyền tài khoản

| ID | Ưu tiên | Vai trò | Bước kiểm thử | Kết quả mong đợi |
|---|---|---|---|---|
| NV-01 | P1 | Admin | Mở Nhân viên, tìm theo mã và theo tên. | Danh sách trả về đúng các hồ sơ phù hợp; xóa từ khóa hiển thị lại danh sách. |
| NV-02 | P0 | Admin | Tạo nhân viên mới với họ tên, vai trò và mật khẩu hợp lệ. | Sinh MANV mới; tạo SQL Login, Database User, gán đúng role và lưu hồ sơ NHAN_VIEN. |
| NV-03 | P1 | Admin | Tạo nhân viên nhưng bỏ trống họ tên, vai trò hoặc mật khẩu; nhập xác nhận mật khẩu khác. | Hiển thị cảnh báo; không tạo Login/User/hồ sơ dở dang. |
| NV-04 | P1 | Admin | Thử tạo tài khoản có SQL Login hoặc Database User đã tồn tại. | Từ chối tạo; không ghi đè tài khoản hiện hữu. |
| NV-05 | P0 | Admin | Mở chi tiết nhân viên đã có tài khoản và đổi vai trò. | Role cũ bị gỡ, role mới được gán; VAITRO trong NHAN_VIEN đồng bộ. |
| NV-06 | P0 | Admin | Mở chi tiết tài khoản admin. | Không cho sửa vai trò hoặc xóa tài khoản admin. |
| NV-07 | P1 | Admin | Xóa tài khoản SQL của một nhân viên không phải admin. | SQL Login/Database User bị xóa; hồ sơ NHAN_VIEN và lịch sử chứng từ vẫn còn. |
| NV-08 | P1 | Nhân viên thường | Thử mở chức năng quản lý/tạo tài khoản nhân viên. | Không thấy hoặc không thực hiện được chức năng chỉ dành cho admin. |

## 3. Sản phẩm

| ID | Ưu tiên | Vai trò | Bước kiểm thử | Kết quả mong đợi |
|---|---|---|---|---|
| SP-01 | P0 | Admin/Quản lý/Nhân viên kho theo quyền SQL | Tạo một sản phẩm loại Sách, chọn NXB, tác giả và thể loại. | Sinh mã SP mới; lưu SAN_PHAM, SACH và các liên kết THUOC_TG/THUOC_TL chính xác. |
| SP-02 | P0 | Người có quyền thêm | Tạo một Sản phẩm khác, chọn thương hiệu và ngày sản xuất. | Lưu SAN_PHAM và SAN_PHAM_KHAC; thông tin thương hiệu/ngày sản xuất hiển thị đúng. |
| SP-03 | P1 | Người có quyền thêm | Bỏ trống tên hoặc đơn vị tính; nhập giá âm, số lượng âm hoặc dữ liệu số không hợp lệ. | Không lưu; hiển thị thông báo cho trường không hợp lệ. |
| SP-04 | P0 | Người có quyền sửa | Sửa tên, đơn vị, giá, VAT và thông tin riêng của sản phẩm. | Dữ liệu được cập nhật; mã sản phẩm và loại sản phẩm không bị thay đổi. |
| SP-05 | P1 | Nhân viên có quyền xem | Tìm theo mã, tên, ISBN, tác giả, thể loại, NXB hoặc thương hiệu. | Trả về đúng sản phẩm khớp với thông tin liên quan. |
| SP-06 | P0 | Người có quyền xóa | Xóa mềm một sản phẩm đã có lịch sử hóa đơn/phiếu nhập. | IS_DELETED chuyển thành 1; sản phẩm không còn trong danh sách bán hàng nhưng lịch sử chứng từ và dòng chi tiết vẫn còn. |
| SP-07 | P0 | Thu ngân | Thử thêm sản phẩm hết tồn hoặc đã xóa mềm vào hóa đơn. | Sản phẩm không được phép thêm vào giỏ/bán. |
| SP-08 | P1 | Người có quyền sửa | Chỉnh sửa sản phẩm đang tham chiếu tới tác giả/thể loại/NXB/thương hiệu đã xóa mềm. | Giá trị cũ vẫn hiển thị để bảo toàn liên kết; không tự đổi sang danh mục khác. |
| SP-09 | P0 | Người có quyền thêm/sửa sản phẩm | Mở biểu mẫu thêm mới hoặc chỉnh sửa sản phẩm. | Giá nhập và số lượng tồn chỉ đọc; sản phẩm mới khởi tạo hai giá trị bằng 0; lưu chỉnh sửa thông tin sản phẩm không làm thay đổi hai giá trị này. |
| SP-10 | P0 | Quản lý/Nhân viên kho/Admin | Lập phiếu nhập rồi hủy phiếu nhập; tiếp tục bán hoặc đổi trả sản phẩm. | Phiếu nhập cập nhật tồn kho và giá nhập bình quân; hủy phiếu nhập hoàn tác đúng; hóa đơn/đổi trả chỉ thay đổi tồn kho; các thao tác nằm trong transaction. |
| SP-11 | P0 | Người có quyền xóa | Thử xóa mềm sản phẩm có SLTON lớn hơn 0, sau đó thử với sản phẩm có SLTON bằng 0. | Sản phẩm còn tồn bị từ chối xóa và giữ IS_DELETED = 0; chỉ sản phẩm hết tồn mới được xóa mềm; kiểm tra tồn kho và cập nhật IS_DELETED nằm trong cùng transaction. |

## 4. Danh mục: tác giả, thể loại, nhà xuất bản, thương hiệu

| ID | Ưu tiên | Vai trò | Bước kiểm thử | Kết quả mong đợi |
|---|---|---|---|---|
| DM-01 | P1 | Người có quyền | Thêm mới từng loại danh mục với dữ liệu hợp lệ. | Sinh đúng tiền tố mã TG/TL/NXB/TH; lưu đúng bảng tương ứng. |
| DM-02 | P1 | Người có quyền | Bỏ trống trường bắt buộc khi thêm danh mục. | Hiển thị cảnh báo; không thêm bản ghi. |
| DM-03 | P1 | Người có quyền | Chỉnh sửa tên và thông tin mô tả/xuất xứ/địa chỉ. | Bản ghi được cập nhật; mã định danh không đổi. |
| DM-04 | P0 | Người có quyền xóa | Xóa mềm danh mục đang được sản phẩm tham chiếu. | IS_DELETED chuyển thành 1; liên kết sản phẩm không bị xóa; danh mục ẩn khỏi danh sách mặc định. |
| DM-05 | P1 | Người có quyền xem | Tìm kiếm theo mã, tên và thông tin liên quan; bấm tiêu đề cột để sắp xếp. | Kết quả tìm chính xác; sắp xếp tăng/giảm đúng kiểu dữ liệu. |
| DM-06 | P0 | Người có quyền thêm | Xóa mềm bản ghi có mã lớn nhất, sau đó thêm bản ghi mới. | Mã mới tăng theo mã lớn nhất đã từng cấp; không tái sử dụng mã đã xóa mềm. |

## 5. Nhà cung cấp

| ID | Ưu tiên | Vai trò | Bước kiểm thử | Kết quả mong đợi |
|---|---|---|---|---|
| NCC-01 | P1 | Quản lý/Admin | Thêm nhà cung cấp với tên, SĐT, địa chỉ và MST hợp lệ. | Sinh mã NCC; lưu đủ thông tin; trạng thái mặc định đang hoạt động. |
| NCC-02 | P1 | Quản lý/Admin | Thử thêm nhà cung cấp không có tên. | Hiển thị cảnh báo; không ghi dữ liệu. |
| NCC-03 | P1 | Người có quyền xem | Tìm theo mã, tên, SĐT, địa chỉ hoặc MST. | Kết quả đúng; bộ lọc nhà cung cấp ngừng hoạt động hoạt động chính xác. |
| NCC-04 | P1 | Quản lý/Admin | Sửa thông tin nhà cung cấp đang hoạt động. | Thông tin mới được lưu; lịch sử phiếu nhập vẫn liên kết với cùng MANCC. |
| NCC-05 | P0 | Quản lý/Admin | Ngừng hoạt động nhà cung cấp đã có phiếu nhập. | IS_DELETED chuyển thành 1; không xóa dữ liệu và không làm mất liên kết chứng từ. |
| NCC-06 | P1 | Quản lý/Admin | Kích hoạt lại nhà cung cấp đã ngừng hoạt động. | IS_DELETED chuyển thành 0; nhà cung cấp xuất hiện lại trong danh sách chọn nhập hàng. |
| NCC-07 | P1 | Nhân viên không có quyền quản lý | Thử thêm, sửa hoặc thay đổi trạng thái nhà cung cấp. | Không có nút hoặc thao tác bị từ chối. |

## 6. Phiếu nhập

| ID | Ưu tiên | Vai trò | Bước kiểm thử | Kết quả mong đợi |
|---|---|---|---|---|
| PN-01 | P0 | Quản lý/Nhân viên kho/Admin | Lập phiếu nhập có NCC và nhiều sản phẩm, số lượng/đơn giá hợp lệ. | Sinh MAPN; tạo PHIEU_NHAP và chi tiết; SLTON tăng đúng; GIANHAP được tính lại theo bình quân gia quyền. |
| PN-02 | P0 | Quản lý/Nhân viên kho/Admin | Nhập cùng một sản phẩm nhiều lần trong giỏ với các đơn giá khác nhau. | Chi tiết được gộp thành một dòng; đơn giá được tính bình quân theo số lượng. |
| PN-03 | P1 | Người lập phiếu | Không chọn NCC hoặc không có sản phẩm; nhập đơn giá bằng 0. | Không cho lưu phiếu; hiển thị lỗi cụ thể. |
| PN-04 | P0 | Người lập phiếu | Nhập SHDNCC đã tồn tại cho cùng NCC và còn hiệu lực. | Từ chối trùng chứng từ; không tăng tồn kho. |
| PN-05 | P0 | Quản lý/Admin | Hủy phiếu nhập còn hiệu lực, kể cả khi đã có giao dịch kho khác phát sinh sau đó. | Chỉ cần tồn kho tổng hiện tại của từng sản phẩm đủ để trừ số lượng nhập; phiếu chuyển trạng thái đã hủy; GIANHAP tính lại từ các phiếu nhập còn hiệu lực. |
| PN-06 | P0 | Nhân viên kho | Hủy phiếu do người khác lập hoặc đã quá 5 phút. | Bị từ chối; trạng thái phiếu, SLTON và GIANHAP không đổi. |
| PN-07 | P0 | Quản lý/Admin | Hủy phiếu nhưng tồn kho tổng hiện tại của ít nhất một sản phẩm thấp hơn lượng cần hoàn tác. | Từ chối hủy; toàn bộ transaction rollback, không cập nhật dở dang. |
| PN-08 | P1 | Người có quyền xem | Tìm phiếu theo mã, SHDNCC, NCC, nhân viên và khoảng ngày; mở chi tiết/in. | Bộ lọc đúng; chi tiết và bản in thể hiện đúng NCC, sản phẩm, VAT và tổng giá trị. |
| PN-09 | P0 | Admin | Lập phiếu nhập khi tài khoản admin không có hồ sơ NHAN_VIEN. | Vẫn tạo được phiếu nhập; MANV để NULL nếu không có hồ sơ tương ứng; tồn kho và giá nhập bình quân cập nhật đúng. |

## 7. Hóa đơn

| ID | Ưu tiên | Vai trò | Bước kiểm thử | Kết quả mong đợi |
|---|---|---|---|---|
| HD-01 | P0 | Thu ngân/Quản lý/Admin | Lập hóa đơn với sản phẩm còn tồn và ca đang diễn ra. | Sinh MAHD; lưu hóa đơn và chi tiết; SLTON giảm đúng; trạng thái hóa đơn có hiệu lực. |
| HD-02 | P0 | Thu ngân | Thử lập hóa đơn khi không thuộc ca đang diễn ra. | Không mở/lưu được hóa đơn; tồn kho không thay đổi. |
| HD-03 | P0 | Thu ngân | Chọn số lượng bán vượt SLTON hoặc nhập tiền khách đưa thấp hơn tổng thanh toán. | Không lưu hóa đơn; SLTON không đổi. |
| HD-04 | P0 | Thu ngân | Lập hóa đơn có khuyến mãi và VAT. | Đơn giá đã gồm VAT không bị cộng VAT lần hai; mức giảm và tổng thanh toán tính đúng; tiền thừa đúng. |
| HD-05 | P1 | Người có quyền xem | Tìm hóa đơn theo mã, nhân viên, ca, khuyến mãi, sản phẩm và khoảng ngày. | Kết quả phù hợp bộ lọc; sắp xếp ngày giảm dần mặc định. |
| HD-06 | P1 | Người có quyền xem | Mở chi tiết và in hóa đơn. | Thông tin nhân viên, ca, từng dòng hàng, VAT, khuyến mãi và tổng tiền chính xác; nội dung in không bị thiếu dữ liệu. |
| HD-07 | P0 | Admin/Quản lý | Hủy hóa đơn còn hiệu lực, kể cả khi đã có giao dịch kho khác phát sinh sau đó. | Không yêu cầu hóa đơn là giao dịch kho mới nhất; nếu chưa có phiếu đổi trả gắn với hóa đơn thì được hủy, trạng thái chuyển 0 và toàn bộ sản phẩm được cộng lại kho đúng một lần. |
| HD-08 | P0 | Thu ngân | Hủy hóa đơn của chính mình trong 5 phút đầu, sau đó thử hủy hóa đơn người khác/quá 5 phút. | Chỉ lần hủy hợp lệ được chấp nhận; các lần còn lại bị từ chối. |
| HD-09 | P0 | Tất cả vai trò có quyền hủy | Hủy lại hóa đơn đã hủy hoặc kiểm tra khi transaction lỗi. | Không hoàn kho lần hai; lỗi phải rollback cả cập nhật tồn kho và trạng thái. |
| HD-10 | P0 | Admin | Lập hóa đơn khi admin không có đăng ký ca hoặc không có hồ sơ NHAN_VIEN. | Admin vẫn lập được hóa đơn; MACA và/hoặc MANV được để NULL nếu không có dữ liệu liên kết phù hợp; tồn kho và thanh toán vẫn được kiểm tra. |

## 8. Đổi trả

| ID | Ưu tiên | Vai trò | Bước kiểm thử | Kết quả mong đợi |
|---|---|---|---|---|
| DT-01 | P0 | Quản lý | Mở đổi trả và chọn hóa đơn còn hiệu lực được lập trong ngày. | Hóa đơn đủ điều kiện hiển thị; chỉ sản phẩm thuộc hóa đơn được chọn để xử lý. |
| DT-02 | P0 | Admin | Mở trang Đổi trả, tìm kiếm, xem chi tiết, lập và xử lý một phiếu hợp lệ. | Admin xem được toàn bộ lịch sử và thực hiện được thao tác như Quản lý; các giới hạn số lượng, ngày đổi trả và tồn kho vẫn được kiểm tra. |
| DT-03 | P0 | Quản lý | Chọn hàng còn nguyên vẹn và hình thức hoàn tiền. | Tính tiền hoàn theo đơn giá sau khuyến mãi; số lượng hàng nguyên vẹn được cộng lại kho. |
| DT-04 | P0 | Quản lý | Chọn hàng đã hỏng và hình thức hoàn tiền. | Tính tiền hoàn đúng; hàng hỏng không được cộng lại tồn kho bán được. |
| DT-05 | P0 | Quản lý | Chọn hàng đã hỏng và đổi sản phẩm cùng mã. | Không hoàn tiền; SLTON giảm theo số lượng hàng mới xuất để đổi. |
| DT-06 | P0 | Quản lý | Chọn hàng còn nguyên vẹn nhưng yêu cầu đổi sản phẩm; hoặc trả vượt số lượng còn được xử lý. | Bị từ chối; không tạo phiếu và không biến động tồn kho. |
| DT-07 | P0 | Quản lý | Thử xử lý hóa đơn đã hủy hoặc hóa đơn không còn trong ngày; thực hiện hai thao tác đồng thời. | Bị từ chối khi không đủ điều kiện; không thể trả vượt lượng mua; lỗi giữa chừng phải rollback. |
| DT-08 | P1 | Quản lý/Admin | Xem chi tiết phiếu đổi trả đã lập. | Hiển thị hóa đơn gốc, lý do, tình trạng hàng, hình thức xử lý, số lượng và tổng tiền hoàn. |
| DT-09 | P0 | Quản lý/Admin | Mở chi tiết một phiếu đổi trả, nhấn Xóa phiếu; thử trường hợp đã có giao dịch kho khác phát sinh sau phiếu. | Không yêu cầu phiếu đổi trả là giao dịch kho mới nhất; đảo đúng biến động do phiếu tạo ra; nếu cần trừ tồn kho thì chỉ xóa khi tồn kho tổng hiện tại đủ, nếu không thì từ chối và rollback toàn bộ. |
| DT-10 | P1 | Quản lý/Admin | Hoàn tiền một sản phẩm còn nguyên vẹn nhưng sản phẩm đã bị xóa mềm khỏi danh mục. | Trước khi lưu, hệ thống cảnh báo và liệt kê các sản phẩm cần khôi phục; chỉ khi người dùng xác nhận mới đặt IS_DELETED = 0 và cộng tồn kho trong cùng transaction; từ chối xác nhận thì không tạo phiếu và không đổi dữ liệu. |

## 9. Ca làm việc

| ID | Ưu tiên | Vai trò | Bước kiểm thử | Kết quả mong đợi |
|---|---|---|---|---|
| CA-01 | P0 | Quản lý/Admin | Tạo ca 1, 2 hoặc 3 cho một ngày. | Giờ ca đúng lịch cố định; không tạo trùng cùng số ca/ngày. |
| CA-02 | P1 | Nhân viên | Mở trang ca làm việc trong thời gian ca diễn ra. | Chỉ nhìn thấy ca đang diễn ra; hiển thị giờ SQL Server và trạng thái đăng ký. |
| CA-03 | P0 | Nhân viên | Đăng ký ca đang diễn ra. | Tạo LAMCA; không cho đăng ký trùng ca hoặc ca đã kết thúc/chốt tiền. |
| CA-04 | P0 | Nhân viên | Đăng ký hai ca có thời gian trùng nhau. | SQL Server từ chối; không tạo đăng ký chồng lấn. |
| CA-05 | P1 | Quản lý/Admin | Xem ca hiện tại, lịch sử và danh sách nhân viên thuộc từng ca. | Số lượng và danh sách nhân viên đúng; bộ lọc ngày/tuần/tháng hoạt động đúng. |
| CA-06 | P0 | Kế toán | Ghi tiền cuối ca trước khi ca kết thúc, sau khi ca kết thúc và ghi lần thứ hai. | Chỉ cho ghi sau khi ca kết thúc; mỗi ca chỉ ghi một lần. |
| CA-07 | P0 | Nhân viên không phải Kế toán và không phải Admin | Thử ghi tiền cuối ca. | Bị từ chối cả ở giao diện và kiểm tra SQL. Admin vẫn được phép ghi sau khi ca kết thúc. |
| CA-08 | P0 | Quản lý/Admin | Xóa ca chưa bắt đầu và ca đã có hóa đơn/đã bắt đầu. | Chỉ ca chưa bắt đầu, chưa có hóa đơn liên kết mới được xóa; lịch sử có chứng từ được bảo toàn. |
| CA-09 | P0 | Admin | Mở ca đã kết thúc chưa có tiền cuối ca và thực hiện ghi tiền; thử ghi lại lần hai. | Admin được xem các ca và ghi tiền cuối ca; chỉ ghi thành công một lần cho mỗi ca. |

## 10. Báo cáo và xuất dữ liệu

| ID | Ưu tiên | Vai trò | Bước kiểm thử | Kết quả mong đợi |
|---|---|---|---|---|
| BC-01 | P0 | Kế toán/Admin | Chọn kỳ báo cáo tổng quan có hóa đơn hợp lệ, hóa đơn hủy, phiếu đổi trả, phiếu nhập còn hiệu lực và phiếu nhập đã hủy. | KPI và bảng xu hướng khớp chứng từ nguồn; hóa đơn hủy không tính vào doanh thu và phiếu nhập đã hủy không tính vào giá trị nhập hàng. |
| BC-02 | P0 | Kế toán/Admin | Đối chiếu báo cáo doanh thu theo ngày/tháng/năm. | Tiền hàng, tiền giảm, doanh thu hợp lệ, tiền hoàn và doanh thu sau hoàn khớp dữ liệu nguồn. |
| BC-03 | P1 | Kế toán/Admin | Mở báo cáo hóa đơn có cả hóa đơn hợp lệ và đã hủy. | Hiển thị đủ chứng từ; hóa đơn hủy không được tính vào doanh thu được ghi nhận. |
| BC-04 | P0 | Kế toán/Admin | Đối chiếu báo cáo nhập hàng với các phiếu nhập có hiệu lực và phiếu đã hủy. | Tổng lượng và trị giá phản ánh đúng trạng thái nghiệp vụ; phiếu hủy không được tính là nhập thực tế. |
| BC-05 | P1 | Kế toán/Admin | Đối chiếu báo cáo đổi trả. | Số phiếu, số lượng và tiền hoàn khớp chi tiết phiếu đổi trả. |
| BC-06 | P1 | Kế toán/Admin | Lọc báo cáo tồn kho theo tất cả/sắp hết/hết hàng, ngưỡng và từ khóa. | Danh sách, trạng thái và giá trị tồn được tính đúng theo SLTON và GIANHAP. |
| BC-07 | P1 | Kế toán/Admin | Đổi cách sắp xếp và tìm sản phẩm trong báo cáo sản phẩm. | Xếp hạng, số lượng bán, doanh thu sau khuyến mãi và tồn kho hiển thị đúng. |
| BC-08 | P1 | Kế toán/Admin | Xuất CSV từng bảng báo cáo và mở bằng Excel. | Tệp CSV có tiêu đề, đủ dòng/cột, nội dung tiếng Việt và số liệu không bị mất. |
| BC-09 | P0 | Kế toán/Admin | Xem báo cáo hóa đơn có hóa đơn đã phát sinh hoàn tiền và đổi sản phẩm. | Số phiếu đổi trả, SL hoàn tiền, SL đổi hàng, tiền hoàn và doanh thu sau hoàn khớp tất cả phiếu đổi trả gắn với từng hóa đơn; hóa đơn hủy không tạo doanh thu. |
| BC-10 | P0 | Kế toán/Admin | Chọn kỳ báo cáo doanh thu có hóa đơn và phiếu hoàn phát sinh ở những ngày khác nhau. | Doanh thu được nhóm theo ngày lập hóa đơn; tiền hoàn theo ngày lập phiếu đổi trả; doanh thu sau hoàn trong kỳ bằng doanh thu bán hàng trừ tiền hoàn phát sinh trong kỳ. |
| BC-11 | P1 | Kế toán/Admin | Đối chiếu báo cáo đổi trả có cả hoàn tiền, đổi sản phẩm, hàng nguyên vẹn và hàng hỏng. | Các nhóm số lượng được tách đúng theo HINH_THUC_XU_LY và TINHTRANGHANG; chỉ tiền hoàn thực tế được cộng vào tổng tiền hoàn. |
| BC-12 | P1 | Kế toán/Admin | Lọc báo cáo sản phẩm có bán hàng và có phiếu hoàn trong kỳ. | Doanh thu sau hoàn theo từng mã sản phẩm bằng doanh thu sau khuyến mãi trừ tiền hoàn của dòng hoàn tiền; đổi hàng không bị tính thành tiền hoàn. |
| BC-13 | P1 | Kế toán/Admin | Đối chiếu bảng hiệu quả khuyến mãi và bảng nhập theo nhà cung cấp. | Số hóa đơn, tiền giảm, tiền hoàn và doanh thu theo chương trình khớp hóa đơn nguồn; số phiếu, lượng nhập và trị giá theo NCC chỉ tính phiếu nhập còn hiệu lực. |
| BC-14 | P1 | Quản lý/Kế toán/Admin | Xem báo cáo ca làm việc có ca đã kết thúc nhưng chưa chốt và ca đã chốt tiền. | Trạng thái kết thúc ca tách biệt trạng thái chốt tiền; lượt đăng ký được tính theo số lượt LAMCA; tiền cuối ca không bị gọi nhầm là doanh thu. |
| BC-15 | P1 | Kế toán/Admin | Lọc báo cáo tồn kho theo trạng thái, ngưỡng và từ khóa. | KPI đầu trang dùng đúng cùng tập sản phẩm với bảng chi tiết sau khi áp dụng bộ lọc. |


## 11. Điều hướng và giao diện dùng chung

| ID | Ưu tiên | Vai trò | Bước kiểm thử | Kết quả mong đợi |
|---|---|---|---|---|
| UI-01 | P1 | Tất cả | Đăng nhập lần lượt với bốn vai trò và mở các nhóm sidebar. | Chỉ hiển thị trang đúng quyền; nhóm rỗng được ẩn; chọn trang tự mở nhóm đang thu gọn. |
| UI-02 | P2 | Tất cả | Sắp xếp các bảng theo mã, tên, tiền, số lượng và ngày; tải lại dữ liệu. | Mũi tên chỉ cột sắp xếp; thứ tự tăng/giảm đúng kiểu dữ liệu; không nhảy dòng khi nạp lại. |

## 12. Kiểm thử tự động hiện có

Các kiểm thử chạy trên GitHub Actions được đặt trong thư mục tests:

- test_dinh_dang.py: định dạng tiền, số, ngày giờ và chuyển Decimal.
- test_nghiep_vu.py: chuỗi kết nối, kiểm tra quyền admin, sắp xếp bảng, widget chọn danh mục, sinh mã, kiểm tra số tiền và lịch ca.
- test_import.py: kiểm tra đường dẫn import nội bộ.
- test_giao_dien.py: import smoke-test toàn bộ package giao diện.

Các case AUTH/NV/SP/DM/NCC/PN/HD/DT/CA/BC/UI ở trên là checklist kiểm thử chấp nhận cần chạy với SQL Server và tài khoản theo từng vai trò. CI hiện không tự động thao tác toàn bộ giao dịch trên database SQL Server thật; các test unit không thay thế cho kiểm thử tích hợp có dữ liệu.

## 13. Chạy test trên máy phát triển

Từ thư mục gốc dự án:

    python -m compileall -q main.py database ui tests
    python -m unittest discover -s tests -p "test_*.py" -v
    python tests/test_giao_dien.py

Trên Windows, cần cài PySide6, pyodbc và Microsoft ODBC Driver for SQL Server nếu chạy các chức năng cần kết nối database. Các test unit không cần kết nối SQL Server.
