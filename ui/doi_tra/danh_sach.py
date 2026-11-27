"""Trang danh sách, tìm kiếm và lập phiếu đổi trả."""

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QDialog, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QTableWidget, QHeaderView,
    QAbstractItemView, QMessageBox, QDateEdit,
)
from ui.permissions import is_admin_account
from ui.calendar_utils import configure_date_edit_calendar
from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table, pause_table_sorting, resume_table_sorting,
)
from .dung_chung import date_text, money
from .tao_bieu_mau import CreateReturnDialog
from .chi_tiet import ReturnDetailDialog
from core.doi_tra.repository import ReturnRepository
from core.doi_tra.service import ReturnService


class ReturnWindow(QWidget):
    """Quản lý lịch sử phiếu đổi trả; Quản lý và Admin được thao tác."""

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.service = ReturnService(ReturnRepository(db))
        self.username = (getattr(db, "username", "") or "").strip()
        self.is_admin = is_admin_account(self.username)
        self.employee_role = self._get_employee_role()
        self.can_manage = (
            self.is_admin
            or self.employee_role.casefold() == "quản lý"
        )
        self._build_ui()
        self.load_returns()

    def _get_employee_role(self):
        try:
            return self.service.get_employee_role(self.username)
        except Exception:
            return ""

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(10)

        top = QHBoxLayout()
        title = QLabel("QUẢN LÝ ĐỔI TRẢ")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        top.addWidget(title)
        top.addStretch()

        self.create_button = QPushButton("+ Lập phiếu đổi trả")
        self.create_button.setProperty("buttonRole", "primary")
        self.create_button.setObjectName("primaryButton")
        self.create_button.setVisible(self.can_manage)
        self.create_button.clicked.connect(self.open_create_dialog)
        top.addWidget(self.create_button)

        refresh_button = QPushButton("Làm mới")
        refresh_button.clicked.connect(self.load_returns)
        top.addWidget(refresh_button)
        root.addLayout(top)

        if not self.can_manage:
            notice = QLabel(
                "Chức năng đổi trả chỉ dành cho tài khoản có vai trò Quản lý."
            )
            notice.setAlignment(Qt.AlignmentFlag.AlignCenter)
            notice.setStyleSheet("font-size: 15px; color: #B45309;")
            root.addWidget(notice)

        filters = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Tìm mã phiếu, mã hóa đơn, lý do hoặc nhân viên..."
        )
        self.search_input.returnPressed.connect(self.load_returns)
        self.from_date = QDateEdit()
        configure_date_edit_calendar(self.from_date)
        self.from_date.setDisplayFormat("dd/MM/yyyy")
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.to_date = QDateEdit()
        configure_date_edit_calendar(self.to_date)
        self.to_date.setDisplayFormat("dd/MM/yyyy")
        self.to_date.setDate(QDate.currentDate())
        search_button = QPushButton("Tìm kiếm")
        search_button.clicked.connect(self.load_returns)
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

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Mã phiếu", "Ngày đổi trả", "Mã hóa đơn",
            "Nhân viên xử lý", "Lý do", "Số lượng", "Tiền hoàn"
        ])
        prepare_sortable_table(
            self.table, default_column=1,
            default_order=Qt.SortOrder.DescendingOrder
        )
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(self.open_detail)
        root.addWidget(self.table, 1)

        self.total_label = QLabel("Tổng số phiếu đổi trả: 0")
        root.addWidget(self.total_label)

    def clear_filters(self):
        """Xóa từ khóa và đưa khoảng ngày về 30 ngày gần nhất."""
        self.search_input.clear()
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.to_date.setDate(QDate.currentDate())
        self.load_returns()

    def load_returns(self):
        if not self.can_manage:
            self.table.setRowCount(0)
            self.total_label.setText("Không có quyền truy cập chức năng đổi trả.")
            return
        if self.from_date.date() > self.to_date.date():
            QMessageBox.warning(self, "Khoảng ngày không hợp lệ", "Ngày bắt đầu không được lớn hơn ngày kết thúc.")
            return
        try:
            rows = self.service.list_returns(
                self.from_date.date().toString("yyyy-MM-dd"),
                self.to_date.date().toString("yyyy-MM-dd"),
                self.search_input.text().strip(),
            )
            pause_table_sorting(self.table)
            self.table.setRowCount(0)
            for row_index, row in enumerate(rows):
                self.table.insertRow(row_index)
                values = [
                    row[0], date_text(row[1]), row[2], row[3],
                    row[4], str(int(row[5] or 0)), money(row[6]),
                ]
                for column, value in enumerate(values):
                    cell = QTableWidgetItem(str(value or ""))
                    if column == 0:
                        cell.setData(Qt.ItemDataRole.UserRole, str(row[0]))
                    self.table.setItem(row_index, column, cell)
            self.total_label.setText(f" Tổng số phiếu đổi trả: {len(rows)}")
        except Exception as error:
            QMessageBox.critical(self, "Lỗi tải phiếu đổi trả", str(error))
        finally:
            resume_table_sorting(self.table)

    def delete_return(self, return_code, parent_dialog=None):
        if not self.can_manage:
            QMessageBox.warning(self, "Không có quyền", "Chỉ Quản lý và Admin được xóa phiếu đổi trả.")
            return False
        return_code = str(return_code or "").strip()
        if not return_code:
            return False
        dialog_parent = parent_dialog or self
        answer = QMessageBox.question(
            dialog_parent, "Xác nhận xóa phiếu đổi trả",
            f"Bạn có chắc chắn muốn xóa phiếu {return_code}?\n\n"
            "Hệ thống sẽ xóa phiếu và chi tiết, đồng thời đảo biến động tồn kho. "
            "Sản phẩm được cộng tồn (nếu đã xóa mềm) sẽ được khôi phục trạng thái hoạt động. "
            "Khoản tiền đã hoàn thực tế cho khách không tự được thu hồi.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False
        try:
            self.service.delete_return(
                return_code, self.username, is_admin=self.is_admin
            )
            QMessageBox.information(
                dialog_parent, "Thành công",
                f"Đã xóa phiếu {return_code} và đảo tồn kho. "
                "Sản phẩm được cộng tồn đã được khôi phục trạng thái hoạt động nếu cần."
            )
            self.load_returns()
            return True
        except Exception as error:
            QMessageBox.critical(dialog_parent, "Không thể xóa phiếu đổi trả", f"{error}\n\nGiao dịch đã được hoàn tác.")
            self.load_returns()
            return False

    def open_create_dialog(self):
        """Mở form lập phiếu và tải lại danh sách sau khi lưu."""
        if not self.can_manage:
            QMessageBox.warning(self, "Không có quyền", "Chỉ Quản lý được xử lý đổi trả.")
            return
        try:
            dialog = CreateReturnDialog(self.db, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_returns()
        except Exception as error:
            QMessageBox.critical(self, "Không thể mở chức năng đổi trả", str(error))

    def open_detail(self, row, _column=0):
        """Mở hộp thoại chi tiết phiếu đang chọn."""
        if not self.can_manage or row < 0:
            return
        cell = self.table.item(row, 0)
        if cell is None:
            return
        return_code = str(cell.data(Qt.ItemDataRole.UserRole) or cell.text()).strip()
        try:
            dialog = ReturnDetailDialog(
                self.db,
                return_code,
                self,
                on_delete=self.delete_return if self.can_manage else None,
            )
            dialog.exec()
            self.load_returns()
        except Exception as error:
            QMessageBox.critical(self, "Lỗi chi tiết phiếu đổi trả", str(error))
