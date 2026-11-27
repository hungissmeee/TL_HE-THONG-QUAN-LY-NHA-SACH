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

from .chi_tiet import EmployeeDetailDialog

class EmployeeWindow(QWidget):

    """Trang tìm kiếm, xem và quản lý hồ sơ nhân viên; chỉ admin được tạo tài khoản."""
    def __init__(self, db):
        """Khởi tạo trang nhân viên và chỉ bật chức năng tạo nhân viên cho admin."""
        super().__init__()

        self.db = db
        self.service = NhanVienService(NhanVienRepository(db))

        self.is_admin = (
            str(getattr(self.db, "username", "") or "").strip().lower() == "admin"
        )

        # Stack chứa các giao diện con
        self.stack = QStackedWidget()

        self.list_page = self.create_list_page()

        self.stack.addWidget(self.list_page)

        # Chỉ admin mới có giao diện thêm nhân viên
        if self.is_admin:
            self.add_page = self.create_add_page()
            self.stack.addWidget(self.add_page)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self.load_employees()

    # ======================================
    # GIAO DIỆN DANH SÁCH NHÂN VIÊN
    # ======================================

    def create_list_page(self):
        """Tạo bảng danh sách nhân viên, tìm kiếm và mở quản lý quyền."""

        page = QWidget()
        layout = QVBoxLayout(page)

        # Tiêu đề
        top_layout = QHBoxLayout()

        title = QLabel("DANH SÁCH NHÂN VIÊN")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
        """)

        top_layout.addWidget(title)
        top_layout.addStretch()

        # Nút thêm nhân viên - chỉ admin
        if self.is_admin:

            add_button = QPushButton("+ Thêm nhân viên")
            add_button.setObjectName("primaryButton")
            add_button.clicked.connect(self.show_add_page)

            top_layout.addWidget(add_button)

        # Nút làm mới
        refresh_button = QPushButton("Làm mới")
        refresh_button.clicked.connect(self.load_employees)

        top_layout.addWidget(refresh_button)

        layout.addLayout(top_layout)

        # Tìm kiếm
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Tìm theo mã nhân viên hoặc họ tên..."
        )

        search_button = QPushButton("Tìm kiếm")
        search_button.clicked.connect(self.load_employees)

        self.search_input.returnPressed.connect(
            self.load_employees
        )

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_button)

        layout.addLayout(search_layout)

        # Bảng nhân viên
        self.table = QTableWidget()

        self.table.setColumnCount(4)

        self.table.setHorizontalHeaderLabels([
            "Mã nhân viên",
            "Họ tên",
            "Vai trò",
            "Số điện thoại"
        ])
        prepare_sortable_table(self.table)

        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        # Một lần nhấn chỉ chọn dòng; double-click mở popup thông tin nhân viên.
        self.table.cellDoubleClicked.connect(self.open_employee_detail)

        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()

        header.setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )

        header.setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )

        layout.addWidget(self.table)

        # Tổng số nhân viên
        self.total_label = QLabel("Tổng số nhân viên: 0")
        layout.addWidget(self.total_label)

        return page

    # ======================================
    # TẢI DANH SÁCH NHÂN VIÊN
    # ======================================

    def load_employees(self):
        """Tải danh sách nhân viên qua Service."""
        try:
            employees = self.service.list_employees(self.search_input.text())
            pause_table_sorting(self.table)
            self.table.setRowCount(0)
            for row_index, employee in enumerate(employees):
                self.table.insertRow(row_index)
                for col_index, value in enumerate(employee):
                    self.table.setItem(
                        row_index, col_index,
                        QTableWidgetItem("" if value is None else str(value))
                    )
            self.total_label.setText(f"Tổng số nhân viên: {len(employees)}")
        except Exception as error:
            QMessageBox.critical(
                self, "Lỗi", f"Không thể tải danh sách nhân viên!\n{error}"
            )
        finally:
            resume_table_sorting(self.table)

    def create_add_page(self):
        """Tạo biểu mẫu nhập thông tin và cấp tài khoản SQL Server cho nhân viên mới."""

        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("THÊM NHÂN VIÊN")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
        """)

        description = QLabel(
            "Tạo tài khoản đăng nhập SQL Server cho nhân viên mới."
        )

        # Các trường thông tin
        self.manv = QLineEdit()
        self.manv.setPlaceholderText("Mã nhân viên được tạo tự động")
        self.manv.setMaxLength(20)
        self.manv.setReadOnly(True)

        self.tennv = QLineEdit()
        self.tennv.setPlaceholderText("Nhập họ tên")
        self.tennv.setMaxLength(100)

        self.vaitro = QComboBox()

        self.vaitro.addItem("-- Chọn vai trò --")

        self.vaitro.addItems([
            "Quản lý",
            "Thu ngân",
            "Nhân viên kho",
            "Kế toán"
        ])

        self.sdt = QLineEdit()
        self.sdt.setPlaceholderText("Nhập số điện thoại")
        self.sdt.setMaxLength(15)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Nhập mật khẩu")
        self.password.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        self.confirm_password = QLineEdit()
        self.confirm_password.setPlaceholderText(
            "Xác nhận mật khẩu"
        )
        self.confirm_password.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        # Form
        form = QFormLayout()
        form.setSpacing(15)

        form.addRow("Mã nhân viên:", self.manv)
        form.addRow("Họ tên:", self.tennv)
        form.addRow("Vai trò:", self.vaitro)
        form.addRow("Số điện thoại:", self.sdt)
        form.addRow("Mật khẩu:", self.password)
        form.addRow(
            "Xác nhận mật khẩu:",
            self.confirm_password
        )

        # Nút
        button_layout = QHBoxLayout()

        save_button = QPushButton("Tạo tài khoản")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self.create_employee)

        back_button = QPushButton("Quay lại")
        back_button.clicked.connect(self.show_list_page)

        button_layout.addWidget(save_button)
        button_layout.addWidget(back_button)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(20)
        layout.addLayout(form)
        layout.addSpacing(15)
        layout.addLayout(button_layout)
        layout.addStretch()

        self.refresh_employee_code()
        return page

    # ======================================
    # TẠO NHÂN VIÊN VÀ TÀI KHOẢN SQL
    # ======================================

    def create_employee(self):
        """Kiểm tra biểu mẫu và tạo hồ sơ/tài khoản qua Service."""
        if not self.is_admin:
            QMessageBox.warning(self, "Từ chối", "Chỉ admin được tạo nhân viên!")
            return
        try:
            employee_code = self.service.create_employee({
                "name": self.tennv.text(),
                "role": self.vaitro.currentText() if self.vaitro.currentIndex() > 0 else "",
                "phone": self.sdt.text(),
                "password": self.password.text(),
                "confirm_password": self.confirm_password.text(),
            })
            QMessageBox.information(
                self, "Thành công",
                f"Đã tạo nhân viên {employee_code} và tài khoản thành công!"
            )
            self.clear_form()
            self.show_list_page()
            self.load_employees()
        except (ValueError, PermissionError) as error:
            QMessageBox.warning(self, "Không thể tạo nhân viên", str(error))
        except Exception as error:
            QMessageBox.critical(
                self, "Lỗi tạo nhân viên",
                f"{error}\n\nGiao dịch đã được hoàn tác."
            )

    def show_add_page(self):
        """Chuyển sang biểu mẫu tạo nhân viên sau khi kiểm tra quyền."""

        if not self.is_admin:
            return

        self.refresh_employee_code()
        self.stack.setCurrentIndex(1)

    def show_list_page(self):
        """Quay lại trang danh sách nhân viên."""

        self.stack.setCurrentIndex(0)

    # ======================================
    # XÓA DỮ LIỆU FORM
    # ======================================

    def _next_employee_code(self, cursor, lock_table=False):
        """Giữ API tương thích; quy tắc sinh mã thuộc Repository."""
        return NhanVienRepository._next_employee_code(cursor, lock_table)

    def refresh_employee_code(self):
        """Hiển thị mã nhân viên dự kiến do Service/Repository sinh."""
        if not hasattr(self, "manv"):
            return
        try:
            self.manv.setText(self.service.preview_next_employee_code())
        except Exception as error:
            self.manv.setText("Không tạo được mã")
            QMessageBox.warning(
                self, "Không thể tạo mã nhân viên", str(error)
            )

    def clear_form(self):
        """Xóa các trường nhập và tạo lại mã nhân viên dự kiến."""

        self.tennv.clear()
        self.vaitro.setCurrentIndex(0)
        self.sdt.clear()
        self.password.clear()
        self.confirm_password.clear()
        self.refresh_employee_code()

    def open_employee_detail(self, row, column):
        """Mở popup xem thông tin nhân viên; quyền quản trị nằm trong popup này."""
        values = []
        for index in range(self.table.columnCount()):
            item = self.table.item(row, index)
            values.append(item.text() if item else "")

        if not values or not values[0]:
            return

        account_info = {}
        if self.is_admin:
            try:
                account_info = self.service.get_employee_permissions(values[0])
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Lỗi tải trạng thái tài khoản",
                    str(e)
                )
                return

        dialog = EmployeeDetailDialog(
            values,
            can_manage=self.is_admin,
            on_manage=lambda: self.open_employee_permissions(row),
            account_exists=account_info.get("account_exists", False),
            account_enabled=account_info.get("account_enabled", False),
            on_toggle_account=lambda enabled: self.toggle_employee_account(
                values[0], enabled
            ),
            parent=self,
        )
        dialog.exec()

    def toggle_employee_account(self, manv, enabled):
        """Xác nhận và đổi trạng thái SQL Login; chỉ admin được thực hiện."""
        if not self.is_admin:
            QMessageBox.warning(
                self,
                "Từ chối",
                "Chỉ Admin mới được thay đổi trạng thái tài khoản!"
            )
            return False

        action = "kích hoạt lại" if enabled else "ngưng hoạt động"
        confirm = QMessageBox.question(
            self,
            "Xác nhận",
            f"Bạn có chắc muốn {action} tài khoản {manv}?"
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return False

        try:
            self.service.set_account_enabled(manv, enabled)
            message = (
                "Đã kích hoạt lại tài khoản."
                if enabled
                else "Đã ngưng hoạt động tài khoản."
            )
            QMessageBox.information(self, "Thành công", message)
            return True
        except Exception as e:
            QMessageBox.critical(
                self,
                "Không thể cập nhật tài khoản",
                str(e)
            )
            return False

    def open_employee_permissions(self, row=None, column=None):
        """Mở hộp thoại quản lý quyền của nhân viên đang chọn; chỉ admin được phép."""

        if row is None:
            row = self.table.currentRow()
        if row < 0:
            return

        if not self.is_admin:
            QMessageBox.warning(
                self,
                "Thông báo",
                "Chỉ Admin mới được quản lý tài khoản!"
            )
            return

        item = self.table.item(row, 0)

        if item is None:
            return

        manv = item.text().strip()

        try:
            print("Đang mở popup:", manv)

            dialog = EmployeePermissionDialog(
                self.db,
                manv,
                self
            )

            dialog.exec()

            self.load_employees()

        except Exception as e:

            QMessageBox.critical(
                self,
                "Lỗi mở quản lý tài khoản",
                str(e)
            )

