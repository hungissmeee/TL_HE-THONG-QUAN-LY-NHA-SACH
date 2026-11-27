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
    prepare_sortable_table,
    pause_table_sorting,
    resume_table_sorting,
)
from .bieu_mau import SupplierFormDialog
from .chi_tiet import SupplierDetailDialog
from core.nha_cung_cap.repository import NhaCungCapRepository
from core.nha_cung_cap.service import NhaCungCapService


SUPPLIER_VIEW_ROLES = frozenset({"quản lý", "nhân viên kho", "kế toán"})


def can_view_suppliers(username, employee_role):
    """Xác định tài khoản có quyền đọc danh sách nhà cung cấp."""
    if (username or "").strip().casefold() == "admin":
        return True
    return (employee_role or "").strip().casefold() in SUPPLIER_VIEW_ROLES


class SupplierWindow(QWidget):
    """Quản lý nhà cung cấp; dùng xóa mềm để giữ liên kết với phiếu nhập."""

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.service = NhaCungCapService(NhaCungCapRepository(db))
        self.username = (getattr(db, "username", "") or "").strip()
        self.employee_role = self._get_employee_role()
        self.is_admin = self.username.casefold() == "admin"
        self.can_view = can_view_suppliers(self.username, self.employee_role)
        self.can_manage = self.is_admin or self.employee_role.casefold() == "quản lý"
        self._build_ui()
        # MainWindow tạo sẵn các trang kể cả khi vai trò không có quyền truy cập.
        # Không truy vấn NHA_CUNG_CAP cho Thu ngân hoặc vai trò không được phép xem.
        if self.can_view:
            self.load_data()

    def _get_employee_role(self):
        try:
            return self.service.get_employee_role(self.username)
        except Exception:
            return ""

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
        self.add_button = QPushButton("+ Thêm nhà cung cấp")
        self.add_button.setProperty("buttonRole", "primary")
        self.add_button.setObjectName("primaryButton")
        self.add_button.clicked.connect(self.add_supplier)
        self.add_button.setVisible(self.can_manage)
        header.addWidget(self.add_button)

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
        self.table.cellDoubleClicked.connect(lambda *_: self.view_supplier())
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.table, 1)

        self.total_label = QLabel("Tổng số: 0")
        root.addWidget(self.total_label)

    def load_data(self, *_):
        if not self.can_view:
            return
        try:
            rows = self.service.list_suppliers(
                self.search_input.text().strip(),
                self.show_inactive_check.isChecked(),
            )
            pause_table_sorting(self.table)
            self.table.setRowCount(0)
            for row_index, row in enumerate(rows):
                self.table.insertRow(row_index)
                values = [
                    row[0], row[1], row[2], row[3], row[4],
                    "Ngừng hoạt động" if bool(row[5]) else "Đang hoạt động",
                ]
                for column, value in enumerate(values):
                    item = QTableWidgetItem("" if value is None else str(value))
                    if column == 0:
                        item.setData(Qt.ItemDataRole.UserRole, str(row[0]))
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                    self.table.setItem(row_index, column, item)
            self.total_label.setText(f"Tổng số: {len(rows)} nhà cung cấp")
        except Exception as error:
            QMessageBox.critical(self, "Lỗi tải dữ liệu", str(error))
        finally:
            resume_table_sorting(self.table)

    def clear_search(self):
        """Xóa từ khóa và tải lại danh sách nhà cung cấp."""
        self.search_input.clear()
        self.load_data()

    def _selected_supplier(self):
        """Lấy mã nhà cung cấp từ dòng đang chọn trong bảng."""
        row = self.table.currentRow()
        if row < 0:
            return None

        item = self.table.item(row, 0)
        if item is None:
            return None

        code = item.data(Qt.ItemDataRole.UserRole)
        return str(code if code is not None else item.text()).strip() or None

    def _get_supplier(self, code):
        return self.service.get_supplier(code)

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
        if not self.can_view:
            return

        code = self._selected_supplier()
        if not code:
            return
        supplier = self._get_supplier(code)
        if supplier is None:
            QMessageBox.warning(self, "Không tìm thấy", "Nhà cung cấp không còn tồn tại.")
            self.load_data()
            return
        dialog = SupplierDetailDialog(
            supplier,
            self,
            can_manage=self.can_manage,
            on_edit=self.edit_supplier,
            on_deactivate=self.deactivate_supplier,
            on_restore=self.restore_supplier,
        )
        dialog.exec()
        self.load_data()

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
            f"Bạn có chắc muốn {action} nhà cung cấp {code}?\n\nLịch sử phiếu nhập vẫn được giữ nguyên.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            if not self.service.set_supplier_status(code, inactive):
                raise RuntimeError("Trạng thái nhà cung cấp đã thay đổi hoặc không tìm thấy dữ liệu.")
            QMessageBox.information(self, "Thành công", f"Đã {action} nhà cung cấp {code}.")
            self.load_data()
        except Exception as error:
            QMessageBox.critical(self, "Không thể cập nhật", str(error))

    def deactivate_supplier(self):
        """Chuyển nhà cung cấp sang trạng thái ngừng hoạt động sau khi xác nhận."""
        self._set_supplier_status(True)

    def restore_supplier(self):
        """Khôi phục trạng thái hoạt động cho nhà cung cấp đã ngừng."""
        self._set_supplier_status(False)


