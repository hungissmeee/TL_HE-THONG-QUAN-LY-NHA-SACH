"""Hộp thoại quản lý tài khoản và quyền SQL Server của nhân viên."""

from PySide6.QtWidgets import (
    QDialog, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout,
    QFormLayout, QComboBox,
    QMessageBox, QGroupBox
)

from PySide6.QtCore import Qt


class EmployeePermissionDialog(QDialog):

    """Hộp thoại xem và cập nhật quyền truy cập SQL Server của nhân viên."""
    def __init__(self, db, manv, parent=None):
        super().__init__(parent)

        self.db = db
        self.manv = manv

        self.setWindowTitle("Quản lý tài khoản nhân viên")
        self.setFixedSize(430, 430)

        self.employee = self.db.get_employee_permissions(manv)

        self.setup_ui()

    def setup_ui(self):

        employee = self.employee

        # Tiêu đề
        title = QLabel("QUẢN LÝ TÀI KHOẢN")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
        """)

        # Thông tin nhân viên
        info_group = QGroupBox("Thông tin nhân viên")

        info_layout = QFormLayout(info_group)

        info_layout.addRow(
            "Mã nhân viên:",
            QLabel(str(employee["manv"]))
        )

        info_layout.addRow(
            "Họ tên:",
            QLabel(str(employee["tennv"] or ""))
        )

        info_layout.addRow(
            "Số điện thoại:",
            QLabel(str(employee["sdt"] or ""))
        )

        # Trạng thái tài khoản
        self.status_label = QLabel(
            "Đã tạo tài khoản SQL Server"
            if employee["account_exists"]
            else "Chưa có tài khoản SQL Server"
        )

        info_layout.addRow(
            "Trạng thái:",
            self.status_label
        )

        # Vai trò
        role_group = QGroupBox("Phân quyền nhân viên")

        role_layout = QVBoxLayout(role_group)

        self.role_combo = QComboBox()

        self.role_combo.addItems([
            "Quản lý",
            "Thu ngân",
            "Nhân viên kho",
            "Kế toán"
        ])

        current_role = employee["vaitro"]

        if current_role in [
            "Quản lý",
            "Thu ngân",
            "Nhân viên kho",
            "Kế toán"
        ]:
            self.role_combo.setCurrentText(current_role)

        role_layout.addWidget(
            QLabel("Chọn vai trò:")
        )

        role_layout.addWidget(self.role_combo)

        role_description = QLabel(
            "Phần mềm sẽ tự động cập nhật quyền truy cập "
            "SQL Server theo vai trò được chọn."
        )

        role_description.setWordWrap(True)
        role_description.setStyleSheet(
            "color: #AAB7C8; font-size: 11px;"
        )

        role_layout.addWidget(role_description)

        # Nút lưu
        self.save_button = QPushButton("Lưu thay đổi")
        self.save_button.clicked.connect(self.save_role)


        # Nút đóng
        self.close_button = QPushButton("Đóng")
        self.close_button.clicked.connect(self.reject)

        button_layout = QHBoxLayout()

        button_layout.addWidget(self.save_button)

        # Tổng layout
        layout = QVBoxLayout()

        layout.addWidget(title)
        layout.addWidget(info_group)
        layout.addWidget(role_group)
        layout.addStretch()
        layout.addLayout(button_layout)
        layout.addWidget(self.close_button)

        self.setLayout(layout)

        # Không cho chỉnh sửa tài khoản admin
        is_admin = self.manv.lower() == "admin"

        if is_admin:
            self.role_combo.setEnabled(False)
            self.save_button.setEnabled(False)

            self.status_label.setText(
                "Tài khoản quản trị hệ thống"
            )

        elif not employee["account_exists"]:

            self.role_combo.setEnabled(False)
            self.save_button.setEnabled(False)

    # ==================================
    # CẬP NHẬT VAI TRÒ
    # ==================================

    def save_role(self):

        role = self.role_combo.currentText()

        confirm = QMessageBox.question(
            self,
            "Xác nhận",
            f"Bạn có muốn đổi vai trò của "
            f"{self.employee['tennv']} thành {role}?"
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:

            self.db.update_employee_permissions(
                self.manv,
                role
            )

            QMessageBox.information(
                self,
                "Thành công",
                "Đã cập nhật vai trò và quyền nhân viên!"
            )

            self.accept()

        except Exception as e:

            QMessageBox.critical(
                self,
                "Lỗi",
                str(e)
            )

