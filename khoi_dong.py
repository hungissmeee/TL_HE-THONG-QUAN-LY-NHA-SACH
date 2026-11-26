import sys

from PySide6.QtWidgets import QApplication

from database.connection import Database
from ui.login import LoginWindow


app = QApplication(sys.argv)

# Khởi tạo database duy nhất
db = Database()

# Mở màn hình đăng nhập
window = LoginWindow(db)
window.show()

# Chạy chương trình
exit_code = app.exec()

# Đóng kết nối khi thoát phần mềm
db.close()

sys.exit(exit_code)