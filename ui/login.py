"""Cửa sổ xác thực tài khoản nhân viên trước khi mở phần mềm."""

from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QMessageBox
)

from ui.main_windows import MainWindow


class LoginWindow(QWidget):

    """Cửa sổ đăng nhập, xác thực tài khoản và chuyển sang cửa sổ chính."""
    def __init__(self, db):
        super().__init__()

        self.db = db
        self.main_window = None

        self.setWindowTitle("Hệ thống quản lý nhà sách - Đăng nhập")
        self.setFixedSize(300, 200)

        self.title = QLabel("ĐĂNG NHẬP HỆ THỐNG")

        self.username = QLineEdit()
        self.username.setPlaceholderText("Tài khoản")

        self.password = QLineEdit()
        self.password.setPlaceholderText("Mật khẩu")
        self.password.setEchoMode(QLineEdit.Password)

        self.login_button = QPushButton("Đăng nhập")
        self.login_button.clicked.connect(self.login)
        self.username.returnPressed.connect(self._handle_username_enter)
        self.password.returnPressed.connect(self.login)

        layout = QVBoxLayout()
        layout.addWidget(self.title)
        layout.addWidget(self.username)
        layout.addWidget(self.password)
        layout.addWidget(self.login_button)

        self.setLayout(layout)

    def _handle_username_enter(self):
        """Nhấn Enter ở ô tài khoản sẽ chuyển sang mật khẩu hoặc đăng nhập."""
        if self.password.text():
            self.login()
        else:
            self.password.setFocus()

    @staticmethod
    def login_error_message(error):
        """Chuyển lỗi SQL Server thành thông báo dễ hiểu, không lộ chẩn đoán thô.

        SQL Server thường dùng cùng lỗi 18456 cho tài khoản không tồn tại và
        mật khẩu sai; không thể phân biệt hai trường hợp này chỉ từ phía client.
        """
        import re

        parts = getattr(error, "args", ()) or ()
        diagnostic = " ".join(str(part) for part in parts) or str(error)
        normalized = diagnostic.casefold()
        error_codes = set(re.findall(r"\((\d{1,6})\)", diagnostic))
        sql_state = str(parts[0]).strip().upper() if parts else ""

        if "18470" in error_codes or "account is disabled" in normalized:
            return "Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên."
        if "18487" in error_codes or "password has expired" in normalized:
            return "Mật khẩu đã hết hạn. Vui lòng liên hệ quản trị viên để được hỗ trợ."
        if "18488" in error_codes or "must be changed" in normalized:
            return "Tài khoản yêu cầu đổi mật khẩu trước khi đăng nhập. Vui lòng liên hệ quản trị viên."
        if (
            "18456" in error_codes
            or sql_state == "28000"
            or "login failed for user" in normalized
        ):
            return "Tài khoản hoặc mật khẩu không chính xác. Vui lòng kiểm tra và thử lại."
        if (
            "4060" in error_codes
            or "4064" in error_codes
            or "916" in error_codes
            or "cannot open database" in normalized
        ):
            return "Tài khoản đã được nhận diện nhưng không thể truy cập cơ sở dữ liệu. Vui lòng liên hệ quản trị viên."
        if sql_state == "IM002" or "data source name not found" in normalized:
            return "Không tìm thấy driver ODBC hoặc cấu hình kết nối SQL Server. Vui lòng kiểm tra cài đặt."
        if (
            sql_state.startswith("08")
            or sql_state in {"HYT00", "HYT01"}
            or error_codes.intersection(
                {"26", "40", "53", "64", "121", "10060", "10061", "11001"}
            )
            or "timeout" in normalized
            or "server was not found" in normalized
            or "network-related" in normalized
        ):
            return "Không thể kết nối đến SQL Server. Vui lòng kiểm tra máy chủ và mạng rồi thử lại."
        return "Đã xảy ra lỗi khi đăng nhập hoặc kết nối SQL Server. Vui lòng thử lại hoặc liên hệ quản trị viên."

    def login(self):
        """Xác thực SQL Server; không hiển thị trực tiếp thông báo lỗi kỹ thuật."""
        username = self.username.text().strip()
        password = self.password.text()

        if not username or not password:
            QMessageBox.warning(
                self, "Thông báo",
                "Vui lòng nhập đầy đủ tài khoản và mật khẩu."
            )
            (self.username if not username else self.password).setFocus()
            return

        try:
            self.db.connect(username, password)
        except Exception as error:
            QMessageBox.warning(
                self, "Đăng nhập thất bại",
                self.login_error_message(error)
            )
            self.password.setFocus()
            self.password.selectAll()
            return

        try:
            self.main_window = MainWindow(
                self.db,
                login_window=self
            )
            self.main_window.show()
            self.hide()
        except Exception:
            self.db.close()
            self.main_window = None
            QMessageBox.critical(
                self, "Không thể mở hệ thống",
                "Đăng nhập thành công nhưng không thể tải dữ liệu khởi tạo. "
                "Vui lòng kiểm tra quyền truy cập cơ sở dữ liệu hoặc liên hệ quản trị viên."
            )
