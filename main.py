"""Điểm khởi chạy ứng dụng BookHub, tạo QApplication và mở cửa sổ đăng nhập."""

import sys

from PySide6.QtWidgets import QApplication

from database.ket_noi import Database
from ui.dang_nhap import LoginWindow


app = QApplication(sys.argv)

# Khởi tạo một đối tượng kết nối dùng chung trong toàn bộ phiên làm việc.
db = Database()

# Hiển thị cửa sổ đăng nhập trước khi vào các chức năng nghiệp vụ.
window = LoginWindow(db)
window.show()

# Vòng lặp sự kiện Qt tiếp nhận thao tác của người dùng.
exit_code = app.exec()

# Đóng kết nối SQL Server để giải phóng tài nguyên khi ứng dụng kết thúc.
db.close()

sys.exit(exit_code)