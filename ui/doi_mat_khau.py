"""Hộp thoại đổi mật khẩu đăng nhập SQL Server."""

from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QMessageBox
)

from PySide6.QtCore import Qt


class ChangePasswordDialog(QDialog):

    """Hộp thoại kiểm tra và đổi mật khẩu SQL Server của tài khoản hiện tại."""
    def __init__(self, db, parent=None):
        super().__init__(parent)

        self.db = db

        self.setWindowTitle("Đổi mật khẩu")
        self.setFixedSize(350, 280)
        self.setWindowModality(Qt.WindowModality.WindowModal)

        # Tiêu đề
        title = QLabel("ĐỔI MẬT KHẨU SQL SERVER")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Mật khẩu hiện tại
        self.old_password = QLineEdit()
        self.old_password.setPlaceholderText("Mật khẩu hiện tại")
        self.old_password.setEchoMode(QLineEdit.EchoMode.Password)

        # Mật khẩu mới
        self.new_password = QLineEdit()
        self.new_password.setPlaceholderText("Mật khẩu mới")
        self.new_password.setEchoMode(QLineEdit.EchoMode.Password)

        # Xác nhận mật khẩu
        self.confirm_password = QLineEdit()
        self.confirm_password.setPlaceholderText("Xác nhận mật khẩu mới")
        self.confirm_password.setEchoMode(QLineEdit.EchoMode.Password)

        # Nút đổi mật khẩu
        self.change_button = QPushButton("Đổi mật khẩu")
        self.change_button.clicked.connect(self.change_password)

        # Nút hủy
        self.cancel_button = QPushButton("Hủy")
        self.cancel_button.clicked.connect(self.reject)

        # Layout
        layout = QVBoxLayout()

        layout.addWidget(title)
        layout.addSpacing(10)
        layout.addWidget(self.old_password)
        layout.addWidget(self.new_password)
        layout.addWidget(self.confirm_password)
        layout.addSpacing(10)
        layout.addWidget(self.change_button)
        layout.addWidget(self.cancel_button)

        self.setLayout(layout)

    def change_password(self):

        old_password = self.old_password.text()
        new_password = self.new_password.text()
        confirm_password = self.confirm_password.text()

        # Kiểm tra dữ liệu
        if not old_password or not new_password or not confirm_password:
            QMessageBox.warning(
                self,
                "Thông báo",
                "Vui lòng nhập đầy đủ thông tin!"
            )
            return

        if new_password != confirm_password:
            QMessageBox.warning(
                self,
                "Thông báo",
                "Mật khẩu xác nhận không khớp!"
            )
            return

        if old_password == new_password:
            QMessageBox.warning(
                self,
                "Thông báo",
                "Mật khẩu mới phải khác mật khẩu hiện tại!"
            )
            return

        try:
            # Gọi Database để đổi mật khẩu
            self.db.change_password(
                old_password,
                new_password
            )

            QMessageBox.information(
                self,
                "Thành công",
                "Đổi mật khẩu thành công!"
            )

            self.accept()

        except Exception as e:

            QMessageBox.critical(
                self,
                "Lỗi",
                f"Không thể đổi mật khẩu!\n{e}"
            )