from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QFormLayout, QTableWidget,
    QHeaderView, QMessageBox, QAbstractItemView, QCheckBox, QGroupBox
)

from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table,
    pause_table_sorting,
    resume_table_sorting,
)


class SupplierFormDialog(QDialog):
    """Form thêm mới hoặc chỉnh sửa nhà cung cấp."""

    def __init__(self, db, parent=None, supplier=None):
        super().__init__(parent)
        self.db = db
        self.supplier = supplier
        self.is_edit = supplier is not None
        self.saved_supplier = None

        self.setWindowTitle("Chỉnh sửa nhà cung cấp" if self.is_edit else "Thêm nhà cung cấp")
        self.setMinimumWidth(500)
        self._build_ui()

        if self.is_edit:
            self._populate()
        else:
            self._refresh_code_preview()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(12)

        title = QLabel("THÔNG TIN NHÀ CUNG CẤP")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        root.addWidget(title)

        group = QGroupBox("Thông tin chung")
        form = QFormLayout(group)
        form.setSpacing(10)

        self.code_input = QLineEdit()
        self.code_input.setReadOnly(True)
        self.code_input.setPlaceholderText("Mã được tạo tự động")

        self.name_input = QLineEdit()
        self.name_input.setMaxLength(100)
        self.name_input.setPlaceholderText("Nhập tên nhà cung cấp")

        self.phone_input = QLineEdit()
        self.phone_input.setMaxLength(15)
        self.phone_input.setPlaceholderText("Số điện thoại")

        self.address_input = QLineEdit()
        self.address_input.setMaxLength(255)
        self.address_input.setPlaceholderText("Địa chỉ nhà cung cấp")

        self.tax_input = QLineEdit()
        self.tax_input.setMaxLength(20)
        self.tax_input.setPlaceholderText("Mã số thuế (nếu có)")

        form.addRow("Mã nhà cung cấp:", self.code_input)
        form.addRow("Tên nhà cung cấp *:", self.name_input)
        form.addRow("Số điện thoại:", self.phone_input)
        form.addRow("Địa chỉ:", self.address_input)
        form.addRow("Mã số thuế:", self.tax_input)
        root.addWidget(group)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Đóng")
        cancel.clicked.connect(self.reject)
        self.save_button = QPushButton("Lưu thay đổi" if self.is_edit else "Thêm nhà cung cấp")
        self.save_button.clicked.connect(self.save)
        buttons.addWidget(cancel)
        buttons.addWidget(self.save_button)
        root.addLayout(buttons)

    def _populate(self):
        row = self.supplier
        self.code_input.setText(str(row[0] or ""))
        self.name_input.setText(str(row[1] or ""))
        self.phone_input.setText(str(row[2] or ""))
        self.address_input.setText(str(row[3] or ""))
        self.tax_input.setText(str(row[4] or ""))

    @staticmethod
    def _next_code(cursor, lock_table=False):
        hint = " WITH (TABLOCKX, HOLDLOCK)" if lock_table else ""
        cursor.execute(f"""
            SELECT COALESCE(
                MAX(TRY_CONVERT(BIGINT, SUBSTRING(MANCC, 4, 17))), 0
            )
            FROM dbo.NHA_CUNG_CAP{hint}
            WHERE UPPER(LEFT(MANCC, 3)) = 'NCC'
              AND TRY_CONVERT(BIGINT, SUBSTRING(MANCC, 4, 17)) IS NOT NULL
        """)
        next_number = int(cursor.fetchone()[0] or 0) + 1
        code = f"NCC{next_number:03d}"
        if len(code) > 20:
            raise ValueError("Mã nhà cung cấp đã vượt quá 20 ký tự.")
        return code

    def _refresh_code_preview(self):
        conn = self.db.get_connection()
        if conn is None:
            return
        cursor = None
        try:
            cursor = conn.cursor()
            self.code_input.setText(self._next_code(cursor))
            conn.commit()
        except Exception as error:
            conn.rollback()
            self.code_input.setText("Tự động khi lưu")
            QMessageBox.warning(self, "Không tạo được mã", str(error))
        finally:
            if cursor is not None:
                cursor.close()

    def save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên nhà cung cấp.")
            self.name_input.setFocus()
            return

        phone = self.phone_input.text().strip() or None
        address = self.address_input.text().strip() or None
        tax = self.tax_input.text().strip() or None

        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối SQL Server.")
            return

        cursor = None
        try:
            cursor = conn.cursor()
            if self.is_edit:
                code = str(self.supplier[0])
                cursor.execute("""
                    UPDATE dbo.NHA_CUNG_CAP
                    SET TENNCC = ?, SDT = ?, DIACHI = ?, MST = ?
                    WHERE MANCC = ? AND ISNULL(IS_DELETED, 0) = 0
                """, (name, phone, address, tax, code))
                if cursor.rowcount != 1:
                    raise RuntimeError("Nhà cung cấp không tồn tại hoặc đã ngừng hoạt động.")
            else:
                # Khóa bảng trong transaction để không sinh trùng mã khi có nhiều người thêm cùng lúc.
                code = self._next_code(cursor, lock_table=True)
                cursor.execute("""
                    INSERT INTO dbo.NHA_CUNG_CAP
                        (MANCC, TENNCC, SDT, DIACHI, MST, IS_DELETED)
                    VALUES (?, ?, ?, ?, ?, 0)
                """, (code, name, phone, address, tax))

            conn.commit()
            self.saved_supplier = (code, name)
            QMessageBox.information(
                self, "Thành công",
                f"Đã {'cập nhật' if self.is_edit else 'thêm'} nhà cung cấp {code}."
            )
            self.accept()
        except Exception as error:
            conn.rollback()
            message = str(error)
            if "permission" in message.casefold() or "denied" in message.casefold():
                message += "\n\nTài khoản cần quyền INSERT/UPDATE trên dbo.NHA_CUNG_CAP."
            QMessageBox.critical(self, "Không thể lưu nhà cung cấp", message)
        finally:
            if cursor is not None:
                cursor.close()


class SupplierDetailDialog(QDialog):
    """Hiển thị thông tin chi tiết nhà cung cấp."""

    def __init__(self, supplier, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chi tiết nhà cung cấp")
        self.setMinimumWidth(440)

        root = QVBoxLayout(self)
        title = QLabel("CHI TIẾT NHÀ CUNG CẤP")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        root.addWidget(title)

        form_box = QGroupBox("Thông tin chung")
        form = QFormLayout(form_box)
        labels = ["Mã nhà cung cấp:", "Tên nhà cung cấp:", "Số điện thoại:", "Địa chỉ:", "Mã số thuế:"]
        for label, value in zip(labels, supplier[:5]):
            display = QLabel("" if value is None else str(value))
            display.setWordWrap(True)
            form.addRow(label, display)
        status = QLabel("Ngừng hoạt động" if bool(supplier[5]) else "Đang hoạt động")
        form.addRow("Trạng thái:", status)
        root.addWidget(form_box)

        close_button = QPushButton("Đóng")
        close_button.clicked.connect(self.accept)
        root.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)


class SupplierWindow(QWidget):
    """Quản lý nhà cung cấp; dùng xóa mềm để giữ liên kết với phiếu nhập."""

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.username = (getattr(db, "username", "") or "").strip()
        self.employee_role = self._get_employee_role()
        self.is_admin = self.username.casefold() == "admin"
        self.can_manage = self.is_admin or self.employee_role.casefold() == "quản lý"
        self._build_ui()
        self.load_data()

    def _get_employee_role(self):
        if (self.username or "").casefold() == "admin":
            return "Quản lý"
        conn = self.db.get_connection()
        if conn is None or not self.username:
            return ""
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT VAITRO FROM dbo.NHAN_VIEN WHERE MANV = ?", self.username)
            row = cursor.fetchone()
            return str(row[0] or "") if row else ""
        except Exception:
            return ""
        finally:
            if cursor is not None:
                cursor.close()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("QUẢN LÝ NHÀ CUNG CẤP")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()
        self.refresh_button = QPushButton("Làm mới")
        self.refresh_button.clicked.connect(self.load_data)
        header.addWidget(self.refresh_button)
        root.addLayout(header)

        description = QLabel(
            "Quản lý thông tin nhà cung cấp. Nhà cung cấp đã phát sinh phiếu nhập được ngừng hoạt động thay vì xóa khỏi cơ sở dữ liệu."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #AAB7C8; font-size: 11px;")
        root.addWidget(description)

        actions = QHBoxLayout()
        self.add_button = QPushButton("+ Thêm nhà cung cấp")
        self.add_button.clicked.connect(self.add_supplier)
        self.edit_button = QPushButton("Chỉnh sửa")
        self.edit_button.clicked.connect(self.edit_supplier)
        self.detail_button = QPushButton("Xem chi tiết")
        self.detail_button.clicked.connect(self.view_supplier)
        self.deactivate_button = QPushButton("Ngừng hoạt động")
        self.deactivate_button.setStyleSheet("QPushButton:enabled { background-color: #A83232; color: white; }")
        self.deactivate_button.clicked.connect(self.deactivate_supplier)
        self.restore_button = QPushButton("Kích hoạt lại")
        self.restore_button.clicked.connect(self.restore_supplier)

        for button in (self.add_button, self.edit_button, self.detail_button,
                       self.deactivate_button, self.restore_button):
            actions.addWidget(button)
        actions.addStretch()
        root.addLayout(actions)

        search = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm theo mã, tên, số điện thoại, địa chỉ hoặc mã số thuế...")
        self.search_input.returnPressed.connect(self.load_data)
        self.search_button = QPushButton("Tìm kiếm")
        self.search_button.clicked.connect(self.load_data)
        self.clear_search_button = QPushButton("Xóa tìm kiếm")
        self.clear_search_button.clicked.connect(self.clear_search)
        search.addWidget(self.search_input, 1)
        search.addWidget(self.search_button)
        search.addWidget(self.clear_search_button)
        root.addLayout(search)

        filters = QHBoxLayout()
        self.show_inactive_check = QCheckBox("Hiện cả nhà cung cấp đã ngừng hoạt động")
        self.show_inactive_check.toggled.connect(self.load_data)
        filters.addWidget(self.show_inactive_check)
        filters.addStretch()
        root.addLayout(filters)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Mã NCC", "Tên nhà cung cấp", "Số điện thoại",
            "Địa chỉ", "Mã số thuế", "Trạng thái"
        ])
        prepare_sortable_table(self.table)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self._update_buttons)
        self.table.cellDoubleClicked.connect(lambda *_: self.view_supplier())
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.table, 1)

        self.total_label = QLabel("Tổng số: 0")
        root.addWidget(self.total_label)

        if not self.can_manage:
            for button in (self.add_button, self.edit_button,
                           self.deactivate_button, self.restore_button):
                button.hide()

    def load_data(self, *_):
        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối SQL Server.")
            return
        cursor = None
        try:
            cursor = conn.cursor()
            sql = """
                SELECT MANCC, TENNCC, SDT, DIACHI, MST, ISNULL(IS_DELETED, 0)
                FROM dbo.NHA_CUNG_CAP
                WHERE 1 = 1
            """
            params = []
            if not self.show_inactive_check.isChecked():
                sql += " AND ISNULL(IS_DELETED, 0) = 0"
            keyword = self.search_input.text().strip()
            if keyword:
                like = f"%{keyword}%"
                sql += " AND (MANCC LIKE ? OR TENNCC LIKE ? OR SDT LIKE ? OR DIACHI LIKE ? OR MST LIKE ?)"
                params.extend([like] * 5)
            sql += " ORDER BY CASE WHEN ISNULL(IS_DELETED, 0) = 0 THEN 0 ELSE 1 END, TENNCC, MANCC"

            cursor.execute(sql, *params)
            rows = cursor.fetchall()

            pause_table_sorting(self.table)

            self.table.setRowCount(0)
            for row_index, row in enumerate(rows):
                self.table.insertRow(row_index)
                values = [row[0], row[1], row[2], row[3], row[4],
                          "Ngừng hoạt động" if bool(row[5]) else "Đang hoạt động"]
                for col_index, value in enumerate(values):
                    item = QTableWidgetItem("" if value is None else str(value))
                    if col_index == 0:
                        item.setData(Qt.ItemDataRole.UserRole, str(row[0]))
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                    self.table.setItem(row_index, col_index, item)
            self.total_label.setText(f"Tổng số: {len(rows)} nhà cung cấp")
            self._update_buttons()
        except Exception as error:
            QMessageBox.critical(self, "Lỗi tải dữ liệu", str(error))
        finally:
            resume_table_sorting(self.table)

            if cursor is not None:
                cursor.close()

    def clear_search(self):
        self.search_input.clear()
        self.load_data()

    def _selected_supplier(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        code_item = self.table.item(row, 0)
        if code_item is None:
            return None
        return code_item.data(Qt.ItemDataRole.UserRole)

    def _selected_is_inactive(self):
        row = self.table.currentRow()
        if row < 0:
            return False
        status_item = self.table.item(row, 5)
        return bool(status_item and status_item.text() == "Ngừng hoạt động")

    def _update_buttons(self):
        selected = self._selected_supplier() is not None
        inactive = self._selected_is_inactive() if selected else False
        self.detail_button.setEnabled(selected)
        self.edit_button.setEnabled(selected and not inactive and self.can_manage)
        self.deactivate_button.setEnabled(selected and not inactive and self.can_manage)
        self.restore_button.setEnabled(selected and inactive and self.can_manage)

    def _get_supplier(self, code):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT MANCC, TENNCC, SDT, DIACHI, MST, ISNULL(IS_DELETED, 0)
                FROM dbo.NHA_CUNG_CAP WHERE MANCC = ?
            """, code)
            row = cursor.fetchone()
            return tuple(row) if row else None
        finally:
            cursor.close()

    def add_supplier(self):
        if not self.can_manage:
            QMessageBox.warning(self, "Không có quyền", "Chỉ Quản lý/Admin được thêm nhà cung cấp.")
            return
        dialog = SupplierFormDialog(self.db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def edit_supplier(self):
        if not self.can_manage:
            return
        code = self._selected_supplier()
        if not code:
            QMessageBox.warning(self, "Chưa chọn nhà cung cấp", "Vui lòng chọn một nhà cung cấp.")
            return
        supplier = self._get_supplier(code)
        if supplier is None or bool(supplier[5]):
            QMessageBox.warning(self, "Không thể chỉnh sửa", "Nhà cung cấp không tồn tại hoặc đã ngừng hoạt động.")
            self.load_data()
            return
        dialog = SupplierFormDialog(self.db, self, supplier=supplier)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def view_supplier(self):
        code = self._selected_supplier()
        if not code:
            return
        supplier = self._get_supplier(code)
        if supplier is None:
            QMessageBox.warning(self, "Không tìm thấy", "Nhà cung cấp không còn tồn tại.")
            self.load_data()
            return
        SupplierDetailDialog(supplier, self).exec()

    def _set_supplier_status(self, inactive):
        if not self.can_manage:
            QMessageBox.warning(self, "Không có quyền", "Chỉ Quản lý/Admin được thay đổi trạng thái nhà cung cấp.")
            return
        code = self._selected_supplier()
        if not code:
            return
        action = "ngừng hoạt động" if inactive else "kích hoạt lại"
        answer = QMessageBox.question(
            self, "Xác nhận",
            f"Bạn có chắc muốn {action} nhà cung cấp {code}?\n\n"
            "Lịch sử phiếu nhập vẫn được giữ nguyên.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        conn = self.db.get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE dbo.NHA_CUNG_CAP
                SET IS_DELETED = ?
                WHERE MANCC = ? AND ISNULL(IS_DELETED, 0) = ?
            """, (1 if inactive else 0, code, 0 if inactive else 1))
            if cursor.rowcount != 1:
                raise RuntimeError("Trạng thái nhà cung cấp đã thay đổi hoặc không tìm thấy dữ liệu.")
            conn.commit()
            QMessageBox.information(self, "Thành công", f"Đã {action} nhà cung cấp {code}.")
            self.load_data()
        except Exception as error:
            conn.rollback()
            QMessageBox.critical(self, "Không thể cập nhật", str(error))
        finally:
            if cursor is not None:
                cursor.close()

    def deactivate_supplier(self):
        self._set_supplier_status(True)

    def restore_supplier(self):
        self._set_supplier_status(False)
