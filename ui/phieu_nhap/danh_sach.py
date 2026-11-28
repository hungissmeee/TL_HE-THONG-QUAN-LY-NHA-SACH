"""ImportWindow: thành phần giao diện nghiệp vụ phiếu nhập."""

from PySide6.QtCore import (
    Qt,
    QDate,
    QTimer,
)
from PySide6.QtWidgets import (
    QWidget,
    QDialog,
    QLabel,
    QPushButton,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QHeaderView,
    QAbstractItemView,
    QMessageBox,
    QDateEdit,
)
from ui.calendar_utils import configure_date_edit_calendar
from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table,
    pause_table_sorting,
    resume_table_sorting,
)
from .dung_chung import money, date_text
from .tao_bieu_mau import CreateImportDialog
from .chi_tiet import ImportDetailDialog
from core.phieu_nhap.repository import PhieuNhapRepository
from core.phieu_nhap.service import PhieuNhapService


IMPORT_VIEW_ROLES = frozenset({"quản lý", "nhân viên kho", "kế toán"})


def can_view_imports(username, employee_role):
    """Xác định tài khoản có quyền xem trang phiếu nhập hay không."""
    if (username or "").strip().casefold() == "admin":
        return True
    return (employee_role or "").strip().casefold() in IMPORT_VIEW_ROLES


class ImportWindow(QWidget):
    """Trang danh sách phiếu nhập, tìm kiếm, lập mới, xem chi tiết và hủy phiếu theo quyền."""

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.service = PhieuNhapService(PhieuNhapRepository(db))
        self.username = (getattr(db, "username", "") or "").strip()
        self.employee_role = self._get_employee_role()
        self.is_admin = self.username.casefold() == "admin"
        self.is_manager = self.employee_role.casefold() == "quản lý"
        self.is_warehouse = self.employee_role.casefold() == "nhân viên kho"
        self.can_view = can_view_imports(self.username, self.employee_role)
        self.can_create = self.is_admin or self.is_manager or self.is_warehouse
        self.can_cancel = self.is_admin or self.is_manager or self.is_warehouse
        self._build_ui()
        # Trang được khởi tạo cho mọi tài khoản trong MainWindow, kể cả tài khoản
        # không có menu Phiếu nhập. Không được chạy truy vấn JOIN nhà cung cấp
        # khi vai trò hiện tại không có quyền xem trang này.
        if self.can_view:
            self.load_imports()

        # Khóa nút hủy của Nhân viên kho sau khi hết giới hạn 5 phút.
        self._cancel_permission_timer = QTimer(self)
        self._cancel_permission_timer.setInterval(5000)
        self._cancel_permission_timer.timeout.connect(self.update_action_buttons)
        self._cancel_permission_timer.start()

    def _get_employee_role(self):
        try:
            return self.service.get_employee(self.username, self.username.casefold() == "admin")["vaitro"]
        except Exception:
            return ""

    def _build_ui(self):
        """Tạo bộ lọc, bảng phiếu nhập và các nút thao tác."""
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(10)

        top = QHBoxLayout()
        title = QLabel("QUẢN LÝ PHIẾU NHẬP")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        top.addWidget(title)
        top.addStretch()
        self.create_button = QPushButton("+ Lập phiếu nhập")
        self.create_button.setProperty("buttonRole", "primary")
        self.create_button.setObjectName("primaryButton")
        self.create_button.setVisible(self.can_create)
        self.create_button.clicked.connect(self.open_create_import)
        top.addWidget(self.create_button)
        refresh_button = QPushButton("Làm mới")
        refresh_button.clicked.connect(self.load_imports)
        top.addWidget(refresh_button)
        root.addLayout(top)

        filters = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Tìm mã phiếu, số HĐ NCC, nhà cung cấp hoặc nhân viên..."
        )
        self.search_input.returnPressed.connect(self.load_imports)
        self.from_date = QDateEdit()
        configure_date_edit_calendar(self.from_date)
        self.from_date.setDisplayFormat("dd/MM/yyyy")
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.to_date = QDateEdit()
        configure_date_edit_calendar(self.to_date)
        self.to_date.setDisplayFormat("dd/MM/yyyy")
        self.to_date.setDate(QDate.currentDate())
        search_button = QPushButton("Tìm kiếm")
        search_button.clicked.connect(self.load_imports)
        clear_button = QPushButton("Xóa lọc")
        clear_button.clicked.connect(self.clear_filters)
        filters.addWidget(self.search_input, 2)
        filters.addWidget(QLabel("Từ ngày:"))
        filters.addWidget(self.from_date)
        filters.addWidget(QLabel("Đến ngày:"))
        filters.addWidget(self.to_date)
        filters.addWidget(search_button)
        filters.addWidget(clear_button)
        root.addLayout(filters)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "Mã phiếu", "Ngày nhập", "Nhà cung cấp", "Nhân viên lập",
            "Loại phiếu", "Số HĐ NCC", "Tổng giá trị", "Trạng thái"
        ])
        prepare_sortable_table(
            self.table,
            default_column=1,
            default_order=Qt.SortOrder.DescendingOrder
        )
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(self.open_import_detail)
        self.table.itemSelectionChanged.connect(self.update_action_buttons)
        root.addWidget(self.table, 1)

        self.total_label = QLabel("Tổng số phiếu nhập: 0")
        root.addWidget(self.total_label)


    def clear_filters(self):
        """Xóa các điều kiện lọc và tải lại danh sách phiếu nhập."""
        self.search_input.clear()
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.to_date.setDate(QDate.currentDate())
        self.load_imports()

    def load_imports(self):
        if not self.can_view:
            return
        if self.from_date.date() > self.to_date.date():
            QMessageBox.warning(self, "Khoảng ngày không hợp lệ", "Ngày bắt đầu không được lớn hơn ngày kết thúc.")
            return
        try:
            rows = self.service.list_imports(
                self.from_date.date().toString("yyyy-MM-dd"),
                self.to_date.date().toString("yyyy-MM-dd"),
                self.search_input.text().strip(),
            )
            pause_table_sorting(self.table)
            self.table.setRowCount(0)
            for index, row in enumerate(rows):
                self.table.insertRow(index)
                status = "Có hiệu lực" if int(row[9] or 0) == 1 else "Đã hủy"
                supplier = f"{row[5] or ''} ({row[4] or ''})"
                employee = f"{row[3] or ''} ({row[2] or ''})"
                values = [row[0], date_text(row[1]), supplier, employee, row[6], row[7], money(row[8]), status]
                for column, value in enumerate(values):
                    item = QTableWidgetItem(str(value or ""))
                    if column == 0:
                        item.setData(Qt.ItemDataRole.UserRole, str(row[2] or "").strip())
                        item.setData(Qt.ItemDataRole.UserRole + 1, row[9])
                        item.setData(Qt.ItemDataRole.UserRole + 2, row[1])
                    self.table.setItem(index, column, item)
            self.total_label.setText(f"Tổng số phiếu nhập: {len(rows)}")
            self.update_action_buttons()
        except Exception as error:
            QMessageBox.critical(self, "Lỗi tải phiếu nhập", str(error))
        finally:
            resume_table_sorting(self.table)

    def update_action_buttons(self):
        """Xác định quyền hủy phiếu nhập đang chọn để truyền vào popup chi tiết."""
        if not self.can_view:
            self._selected_can_cancel = False
            return

        row = self.table.currentRow()
        self._selected_can_cancel = False
        if not self.can_cancel or row < 0:
            return
        code_item = self.table.item(row, 0)
        if code_item is None:
            return
        status = int(code_item.data(Qt.ItemDataRole.UserRole + 1) or 0)
        if status != 1:
            return
        if self.is_admin or self.is_manager:
            self._selected_can_cancel = True
            return

        owner = str(code_item.data(Qt.ItemDataRole.UserRole) or "")
        can_cancel = self.is_warehouse and owner.casefold() == self.username.casefold()
        if can_cancel:
            conn = self.db.get_connection()
            if conn is None:
                return
            cursor = None
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT CASE
                        WHEN NGAYNHAP >= DATEADD(MINUTE, -5, SYSDATETIME())
                         AND NGAYNHAP <= SYSDATETIME()
                        THEN 1 ELSE 0
                    END
                    FROM dbo.PHIEU_NHAP
                    WHERE MAPN = ? AND MANV = ?
                      AND ISNULL(TRANGTHAI, 1) = 1
                """, code_item.text(), self.username)
                result = cursor.fetchone()
                self._selected_can_cancel = bool(result and result[0] == 1)
            except Exception:
                self._selected_can_cancel = False
            finally:
                if cursor is not None:
                    cursor.close()

    def cancel_selected_import(self):
        if not self.can_cancel:
            QMessageBox.warning(self, "Không có quyền", "Tài khoản của bạn không có quyền hủy phiếu nhập.")
            return
        row = self.table.currentRow()
        if row < 0:
            return
        code_item = self.table.item(row, 0)
        if code_item is None:
            return
        import_code = code_item.text().strip()
        owner = str(code_item.data(Qt.ItemDataRole.UserRole) or "")
        if self.is_warehouse and not (self.is_admin or self.is_manager):
            if owner.casefold() != self.username.casefold():
                QMessageBox.warning(self, "Không có quyền", "Nhân viên kho chỉ được hủy phiếu do mình lập.")
                return
        answer = QMessageBox.question(
            self, "Xác nhận hủy phiếu nhập",
            f"Bạn có chắc chắn muốn hủy phiếu nhập {import_code}?\n\n"
            "Hệ thống sẽ trừ lại số lượng đã nhập khỏi tồn kho. "
            "Phiếu vẫn được giữ lại trong lịch sử với trạng thái Đã hủy.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.cancel_import(
                import_code, self.username, self.employee_role,
                is_admin=self.is_admin,
            )
            QMessageBox.information(
                self, "Đã hủy phiếu nhập",
                f"Phiếu {import_code} đã được hủy và tồn kho đã được hoàn tác.",
            )
            self.load_imports()
        except Exception as error:
            QMessageBox.critical(
                self, "Không thể hủy phiếu nhập",
                f"{error}\n\nMọi thay đổi đã được hoàn tác.",
            )
            self.load_imports()

    def open_selected_import(self):
        """Mở phiếu nhập đang được chọn."""
        if not self.can_view:
            return

        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Chưa chọn phiếu", "Vui lòng chọn phiếu nhập.")
            return
        item = self.table.item(row, 0)
        if item:
            self.open_import_detail(row, 0)

    def open_import_detail(self, row, column):
        """Hiển thị chi tiết phiếu nhập và nội dung in."""
        if not self.can_view:
            return

        item = self.table.item(row, 0)
        if item is None:
            return
        try:
            self.update_action_buttons()
            detail_data = self.service.get_import_detail(
                item.text(), self.username, self.is_admin
            )
            has_later = bool(detail_data["header"].get("has_later_stock_movement"))
            active_import = int(detail_data["header"].get("status") or 0) == 1
            can_edit_header = active_import and (
                self.is_admin or self.is_manager or self.is_warehouse
            )
            can_manage_stock = active_import and (
                self.is_admin or self.is_manager
            )
            dialog = ImportDetailDialog(
                self.db,
                item.text(),
                self,
                on_cancel=(
                    self.cancel_selected_import
                    if can_manage_stock and not has_later else None
                ),
                can_edit=can_manage_stock,
                can_edit_header=can_edit_header,
                has_later_stock_movement=has_later,
            )
            dialog.exec()
            self.load_imports()
        except Exception as error:
            QMessageBox.critical(self, "Lỗi xem phiếu nhập", str(error))

    def open_create_import(self):
        """Mở hộp thoại lập phiếu nhập mới."""
        if not self.can_create:
            QMessageBox.warning(self, "Không có quyền", "Tài khoản không có quyền lập phiếu nhập.")
            return
        try:
            dialog = CreateImportDialog(self.db, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_imports()
                if dialog.saved_import_code:
                    answer = QMessageBox.question(
                        self, "In phiếu nhập",
                        f"Đã tạo phiếu nhập {dialog.saved_import_code}. Bạn có muốn in ngay không?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )
                    if answer == QMessageBox.StandardButton.Yes:
                        detail = ImportDetailDialog(
                            self.db, dialog.saved_import_code, self
                        )
                        detail.print_import()
        except Exception as error:
            QMessageBox.critical(self, "Không thể lập phiếu nhập", str(error))



