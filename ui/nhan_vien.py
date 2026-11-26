"""Trang quản lý hồ sơ và tài khoản nhân viên."""


import re

from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QFormLayout,
    QTableWidget, QHeaderView,
    QStackedWidget, QMessageBox, QAbstractItemView, QComboBox
)

from PySide6.QtCore import Qt
from ui.tai_khoan import EmployeePermissionDialog
from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table,
    pause_table_sorting,
    resume_table_sorting,
)

class EmployeeWindow(QWidget):

    """Trang tìm kiếm, xem và quản lý hồ sơ nhân viên; chỉ admin được tạo tài khoản."""
    def __init__(self, db):
        """Khởi tạo trang nhân viên và chỉ bật chức năng tạo nhân viên cho admin."""
        super().__init__()

        self.db = db

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

        # Kết nối sự kiện nhấn vào ô; hàm xử lý bên dưới sẽ kiểm tra quyền Admin.
        self.table.cellClicked.connect(
            self.open_employee_permissions
        )

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
        """Tải hồ sơ nhân viên theo từ khóa tìm kiếm."""

        conn = self.db.get_connection()

        if conn is None:
            QMessageBox.warning(
                self, "Thông báo",
                "Chưa có kết nối database!"
            )
            return

        cursor = None

        try:

            keyword = self.search_input.text().strip()

            cursor = conn.cursor()

            cursor.execute("""
                SELECT MANV, TENNV, VAITRO, SDT
                FROM NHAN_VIEN
                WHERE MANV LIKE ?
                   OR TENNV LIKE ?
                ORDER BY MANV
            """, f"%{keyword}%", f"%{keyword}%")

            employees = cursor.fetchall()

            pause_table_sorting(self.table)

            self.table.setRowCount(0)

            for row_index, employee in enumerate(employees):

                self.table.insertRow(row_index)

                values = [
                    employee[0],
                    employee[1],
                    employee[2],
                    employee[3]
                ]

                for col_index, value in enumerate(values):

                    item = QTableWidgetItem(
                        "" if value is None else str(value)
                    )

                    self.table.setItem(
                        row_index,
                        col_index,
                        item
                    )

            self.total_label.setText(
                f"Tổng số nhân viên: {len(employees)}"
            )

        except Exception as e:

            QMessageBox.critical(
                self, "Lỗi",
                f"Không thể tải danh sách nhân viên!\n{e}"
            )

        finally:

            resume_table_sorting(self.table)

            if cursor is not None:
                cursor.close()

    # ======================================
    # GIAO DIỆN THÊM NHÂN VIÊN
    # ======================================

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
        """Kiểm tra thông tin, sinh mã và tạo tài khoản cùng hồ sơ nhân viên."""

        manv = self.manv.text().strip()
        tennv = self.tennv.text().strip()
        vaitro = self.vaitro.currentText()
        sdt = self.sdt.text().strip()

        password = self.password.text()
        confirm = self.confirm_password.text()

        if not self.is_admin:
            QMessageBox.warning(
                self, "Từ chối",
                "Chỉ admin được tạo nhân viên!"
            )
            return
        if self.vaitro.currentIndex() == 0:
            QMessageBox.warning(
                self,
                "Thông báo",
                "Vui lòng chọn vai trò nhân viên!"
            )
            return
        if not all([
            manv, tennv, vaitro,
            password, confirm
        ]):
            QMessageBox.warning(
                self, "Thông báo",
                "Vui lòng nhập đầy đủ thông tin!"
            )
            return

        if password != confirm:
            QMessageBox.warning(
                self, "Thông báo",
                "Mật khẩu xác nhận không khớp!"
            )
            return


        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(
                self, "Thông báo", "Chưa có kết nối database!"
            )
            return

        cursor = None
        try:
            # Khóa bảng và tính lại mã ngay trước khi tạo tài khoản.
            # Hồ sơ NHAN_VIEN được giữ lại khi xóa SQL Login, nên mã cũ
            # vẫn được tính và không bao giờ được cấp lại.
            cursor = conn.cursor()
            manv = self._next_employee_code(cursor, lock_table=True)
            self.manv.setText(manv)
            cursor.close()
            cursor = None

            # create_account phải dùng cùng self.conn và commit/rollback
            # transaction này sau khi tạo Login, User và hồ sơ nhân viên.
            self.db.create_account(
                manv,
                tennv,
                vaitro,
                sdt or None,
                password
            )

            QMessageBox.information(
                self, "Thành công",
                f"Đã tạo nhân viên {manv} và tài khoản thành công!"
            )

            self.clear_form()
            self.show_list_page()
            self.load_employees()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(
                self, "Lỗi tạo nhân viên",
                str(e)
            )
        finally:
            if cursor is not None:
                cursor.close()

    # ======================================
    # CHUYỂN GIAO DIỆN CON
    # ======================================

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
        """Sinh mã NV001, NV002... từ toàn bộ hồ sơ NHAN_VIEN.

        Không lọc theo trạng thái tài khoản hoặc IS_DELETED (nếu có).
        Khi tạo mới, TABLOCKX + HOLDLOCK giữ khóa đến khi create_account
        commit transaction, tránh hai lần thêm cùng sinh một mã.
        """
        table_hint = " WITH (TABLOCKX, HOLDLOCK)" if lock_table else ""
        cursor.execute(f"""
            SELECT COALESCE(
                MAX(TRY_CONVERT(BIGINT, SUBSTRING(MANV, 3, 18))),
                0
            )
            FROM dbo.NHAN_VIEN{table_hint}
            WHERE UPPER(LEFT(MANV, 2)) = 'NV'
              AND TRY_CONVERT(BIGINT, SUBSTRING(MANV, 3, 18)) IS NOT NULL
        """)

        last_number = cursor.fetchone()[0] or 0
        code = f"NV{int(last_number) + 1:03d}"

        if len(code) > 20:
            raise ValueError("Mã nhân viên vượt quá 20 ký tự.")

        return code

    def refresh_employee_code(self):
        """Hiển thị trước mã nhân viên kế tiếp; ô mã không cho nhập tay."""
        if not hasattr(self, "manv"):
            return

        conn = self.db.get_connection()
        if conn is None:
            self.manv.clear()
            return

        cursor = None
        try:
            cursor = conn.cursor()
            code = self._next_employee_code(cursor, lock_table=False)
            self.manv.setText(code)
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.manv.setText("Không tạo được mã")
            QMessageBox.warning(
                self,
                "Không thể tạo mã nhân viên",
                f"Không lấy được mã nhân viên tự động.\n{e}"
            )
        finally:
            if cursor is not None:
                cursor.close()

    def clear_form(self):
        """Xóa các trường nhập và tạo lại mã nhân viên dự kiến."""

        self.tennv.clear()
        self.vaitro.setCurrentIndex(0)
        self.sdt.clear()
        self.password.clear()
        self.confirm_password.clear()
        self.refresh_employee_code()

    def open_employee_permissions(self, row, column):
        """Mở hộp thoại quản lý quyền của nhân viên đang được chọn, chỉ dành cho admin."""

        print("Đã nhấn vào nhân viên!")

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

            print("Lỗi:", e)