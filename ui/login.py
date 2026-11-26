"""Cửa sổ xác thực tài khoản nhân viên trước khi mở phần mềm."""

from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QMessageBox
)

from ui.cua_so_chinh import MainWindow


class LoginWindow(QWidget):

    """Cửa sổ đăng nhập, xác thực tài khoản và chuyển sang cửa sổ chính."""
    """Cửa sổ đăng nhập và xác thực nhân viên."""
    def __init__(self, db):
        super().__init__()

        self.db = db
        self.main_window = None

        self.setWindowTitle("Đăng nhập")
        self.setFixedSize(300, 200)

        self.title = QLabel("ĐĂNG NHẬP HỆ THỐNG")

        self.username = QLineEdit()
        self.username.setPlaceholderText("Tài khoản SQL Server")

        self.password = QLineEdit()
        self.password.setPlaceholderText("Mật khẩu")
        self.password.setEchoMode(QLineEdit.Password)

        self.login_button = QPushButton("Đăng nhập")
        self.login_button.clicked.connect(self.login)

        layout = QVBoxLayout()
        layout.addWidget(self.title)
        layout.addWidget(self.username)
        layout.addWidget(self.password)
        layout.addWidget(self.login_button)

        self.setLayout(layout)

    def login(self):

        username = self.username.text().strip()
        password = self.password.text()

        if not username or not password:
            QMessageBox.warning(
                self, "Thông báo",
                "Vui lòng nhập đầy đủ thông tin!"
            )
            return

        try:
            # Xác thực SQL Server
            self.db.connect(username, password)

            # Mở cửa sổ chính
            self.main_window = MainWindow(
                self.db,
                login_window=self
            )

            self.main_window.show()

            # Ẩn thay vì đóng LoginWindow
            self.hide()

        except Exception as e:
            QMessageBox.critical(
                self, "Đăng nhập thất bại",
                f"Không thể đăng nhập!\n{e}"
            )