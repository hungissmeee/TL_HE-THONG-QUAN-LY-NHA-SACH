"""Điểm khởi chạy Hệ thống quản lý nhà sách, tạo QApplication và mở cửa sổ đăng nhập."""

import sys

from PySide6.QtWidgets import QApplication

from database.connection import Database
from ui.login import LoginWindow
from ui.styles import install_bookhub_style


APP_NAME = "Hệ thống quản lý nhà sách"

app = QApplication(sys.argv)
app.setApplicationName(APP_NAME)
app.setApplicationDisplayName(APP_NAME)
install_bookhub_style(app)

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