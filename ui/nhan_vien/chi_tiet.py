"""Trang quản lý hồ sơ và tài khoản nhân viên."""


import re

from PySide6.QtWidgets import (
    QWidget, QDialog, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QTableWidget, QHeaderView,
    QStackedWidget, QMessageBox, QAbstractItemView, QComboBox
)

from PySide6.QtCore import Qt
from ui.tai_khoan import EmployeePermissionDialog
from core.nhan_vien.repository import NhanVienRepository
from core.nhan_vien.service import NhanVienService
from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table,
    pause_table_sorting,
    resume_table_sorting,
)

class EmployeeDetailDialog(QDialog):
    """Hộp thoại xem thông tin nhân viên và quản lý tài khoản khi được phép."""

    def __init__(
        self,
        employee,
        can_manage=False,
        on_manage=None,
        account_exists=False,
        account_enabled=False,
        on_toggle_account=None,
        parent=None,
    ):
        super().__init__(parent)
        self.on_manage = on_manage
        self.on_toggle_account = on_toggle_account
        self.manv = str(employee[0])
        self.account_exists = bool(account_exists)
        self.account_enabled = bool(account_enabled)

        self.setWindowTitle(f"Chi tiết nhân viên - {employee[0]}")
        self.setMinimumWidth(480)

        root = QVBoxLayout(self)
        title = QLabel("CHI TIẾT NHÂN VIÊN")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        root.addWidget(title)

        group = QGroupBox("Thông tin nhân viên")
        form = QFormLayout(group)
        for label, value in zip(
            ("Mã nhân viên:", "Họ tên:", "Vai trò:", "Số điện thoại:"),
            employee,
        ):
            value_label = QLabel("" if value is None else str(value))
            value_label.setWordWrap(True)
            form.addRow(label, value_label)

        self.account_status_label = None
        if can_manage:
            self.account_status_label = QLabel(self._account_status_text(employee[0]))
            form.addRow("Trạng thái tài khoản:", self.account_status_label)

        root.addWidget(group)

        actions = QHBoxLayout()
        if can_manage:
            if self.account_exists and str(employee[0]).strip().lower() != "admin":
                self.account_toggle_button = QPushButton(
                    self._account_toggle_text()
                )
                self.account_toggle_button.clicked.connect(
                    self._toggle_account_status
                )
                actions.addWidget(self.account_toggle_button)

            manage_button = QPushButton("Quản lý tài khoản")
            manage_button.clicked.connect(self._manage_account)
            actions.addWidget(manage_button)

        actions.addStretch()
        close_button = QPushButton("Đóng")
        close_button.clicked.connect(self.reject)
        actions.addWidget(close_button)
        root.addLayout(actions)

    def _account_status_text(self, manv):
        if str(manv).strip().lower() == "admin":
            return "Tài khoản quản trị hệ thống"
        if not self.account_exists:
            return "Chưa có tài khoản SQL Server"
        return "Đang hoạt động" if self.account_enabled else "Đã ngưng hoạt động"

    def _account_toggle_text(self):
        return (
            "Ngưng hoạt động tài khoản"
            if self.account_enabled
            else "Kích hoạt lại tài khoản"
        )

    def _toggle_account_status(self):
        """Gọi thao tác bật/tắt tài khoản và cập nhật trạng thái hiển thị."""
        if self.on_toggle_account is None:
            return

        target_enabled = not self.account_enabled
        if not self.on_toggle_account(target_enabled):
            return

        self.account_enabled = target_enabled
        self.account_status_label.setText(
            self._account_status_text(self.manv)
        )
        self.account_toggle_button.setText(self._account_toggle_text())

    def _manage_account(self):
        """Đóng chi tiết rồi mở hộp thoại phân quyền cho nhân viên này."""
        if self.on_manage is None:
            return
        self.accept()
        self.on_manage()


