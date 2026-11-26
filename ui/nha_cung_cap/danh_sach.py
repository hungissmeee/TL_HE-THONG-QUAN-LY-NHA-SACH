"""SupplierWindow: thành phần giao diện nghiệp vụ."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QHeaderView,
    QMessageBox,
    QAbstractItemView,
    QCheckBox,
)
from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    create_table_action_panel,
    prepare_sortable_table,
    pause_table_sorting,
    resume_table_sorting,
)
from .bieu_mau import SupplierFormDialog
from .chi_tiet import SupplierDetailDialog


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
        """Lấy vai trò của nhân viên để xác định quyền quản lý nhà cung cấp."""
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
        """Tạo bộ lọc, bảng nhà cung cấp và các nút thao tác."""
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
        actions.addWidget(self.add_button)
        actions.addStretch()
        root.addLayout(actions)

        self.edit_button = QPushButton("Chỉnh sửa")
        self.edit_button.clicked.connect(self.edit_supplier)
        self.detail_button = QPushButton("Xem chi tiết")
        self.detail_button.clicked.connect(self.view_supplier)
        self.deactivate_button = QPushButton("Ngừng hoạt động")
        self.deactivate_button.setStyleSheet(
            "QPushButton:enabled { background-color: #A83232; color: white; }"
        )
        self.deactivate_button.clicked.connect(self.deactivate_supplier)
        self.restore_button = QPushButton("Kích hoạt lại")
        self.restore_button.clicked.connect(self.restore_supplier)

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

        self.action_panel, action_layout, self.action_hint = create_table_action_panel(
            "Chọn nhà cung cấp để xem thông tin, chỉnh sửa hoặc thay đổi trạng thái.",
            self,
        )
        for button in (
            self.detail_button, self.edit_button,
            self.deactivate_button, self.restore_button,
        ):
            action_layout.addWidget(button)
        root.addWidget(self.action_panel)

        if not self.can_manage:
            for button in (self.add_button, self.edit_button,
                           self.deactivate_button, self.restore_button):
                button.hide()

    def load_data(self, *_):
        """Tải danh sách nhà cung cấp theo từ khóa và trạng thái đang chọn."""
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
        """Xóa từ khóa và tải lại danh sách nhà cung cấp."""
        self.search_input.clear()
        self.load_data()

    def _selected_supplier(self):
        """Lấy mã nhà cung cấp của dòng đang được chọn."""
        row = self.table.currentRow()
        if row < 0:
            return None
        code_item = self.table.item(row, 0)
        if code_item is None:
            return None
        return code_item.data(Qt.ItemDataRole.UserRole)

    def _selected_is_inactive(self):
        """Kiểm tra nhà cung cấp đang chọn có ở trạng thái ngừng hoạt động hay không."""
        row = self.table.currentRow()
        if row < 0:
            return False
        status_item = self.table.item(row, 5)
        return bool(status_item and status_item.text() == "Ngừng hoạt động")

    def _update_buttons(self):
        """Bật hoặc khóa các nút sửa, xem, ngừng hoạt động và khôi phục theo lựa chọn hiện tại."""
        selected = self._selected_supplier() is not None
        inactive = self._selected_is_inactive() if selected else False
        self.detail_button.setEnabled(selected)
        if selected:
            self.action_hint.setText(
                f"Đang chọn nhà cung cấp {self._selected_supplier()} "
                f"({'ngừng hoạt động' if inactive else 'đang hoạt động'})."
            )
        else:
            self.action_hint.setText(
                "Chọn nhà cung cấp để xem thông tin, chỉnh sửa hoặc thay đổi trạng thái."
            )
        self.edit_button.setEnabled(selected and not inactive and self.can_manage)
        self.deactivate_button.setEnabled(selected and not inactive and self.can_manage)
        self.restore_button.setEnabled(selected and inactive and self.can_manage)

    def _get_supplier(self, code):
        """Lấy thông tin đầy đủ của một nhà cung cấp từ SQL Server."""
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
        """Mở biểu mẫu tạo nhà cung cấp mới và làm mới danh sách sau khi lưu."""
        if not self.can_manage:
            QMessageBox.warning(self, "Không có quyền", "Chỉ Quản lý/Admin được thêm nhà cung cấp.")
            return
        dialog = SupplierFormDialog(self.db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def edit_supplier(self):
        """Mở biểu mẫu chỉnh sửa nhà cung cấp đang chọn."""
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
        """Mở cửa sổ xem chi tiết nhà cung cấp đang chọn."""
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
        """Cập nhật trạng thái hoạt động của nhà cung cấp mà không xóa dữ liệu."""
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
        """Chuyển nhà cung cấp sang trạng thái ngừng hoạt động sau khi xác nhận."""
        self._set_supplier_status(True)

    def restore_supplier(self):
        """Khôi phục trạng thái hoạt động cho nhà cung cấp đã ngừng."""
        self._set_supplier_status(False)


