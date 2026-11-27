"""Trang danh sách và quản lý chương trình khuyến mãi."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QInputDialog,
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
from .bieu_mau import PromotionFormDialog
from core.repositories.khuyen_mai_repository import KhuyenMaiRepository
from core.services.khuyen_mai_service import KhuyenMaiService


class PromotionDetailDialog(QDialog):
    """Popup xem chi tiết khuyến mãi và thao tác đổi tên hoặc xóa mềm."""

    def __init__(
        self, values, can_manage=False, on_rename=None, on_delete=None,
        parent=None
    ):
        super().__init__(parent)
        self.on_rename = on_rename
        self.on_delete = on_delete

        self.setWindowTitle("Chi tiết chương trình khuyến mãi")
        self.setMinimumWidth(460)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        title = QLabel("CHI TIẾT KHUYẾN MÃI")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        root.addWidget(title)

        group = QGroupBox("Thông tin chương trình")
        form = QFormLayout(group)
        for label, value in values:
            value_label = QLabel("" if value is None else str(value))
            value_label.setWordWrap(True)
            form.addRow(label, value_label)
        root.addWidget(group)

        actions = QHBoxLayout()
        if can_manage:
            rename_button = QPushButton("Đổi tên")
            rename_button.clicked.connect(self._rename)
            actions.addWidget(rename_button)

            delete_button = QPushButton("Xóa mềm")
            delete_button.setObjectName("dangerButton")
            delete_button.clicked.connect(self._delete)
            actions.addWidget(delete_button)

        actions.addStretch()
        close_button = QPushButton("Đóng")
        close_button.clicked.connect(self.reject)
        actions.addWidget(close_button)
        root.addLayout(actions)

    def _run_action(self, callback):
        """Đóng popup chi tiết trước khi thực hiện thao tác trên bản ghi."""
        if callback is None:
            return
        self.accept()
        callback()

    def _rename(self):
        self._run_action(self.on_rename)

    def _delete(self):
        self._run_action(self.on_delete)


class PromotionWindow(QWidget):
    """Quản lý khuyến mãi; tỷ lệ và thời hạn cố định, chỉ cho đổi tên và xóa mềm."""

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.service = KhuyenMaiService(KhuyenMaiRepository(db))
        self.username = (getattr(db, "username", "") or "").strip()
        self.employee_role = self._get_employee_role()
        self.is_admin = self.username.casefold() == "admin"
        self.can_view = (
            self.is_admin or self.employee_role.casefold() == "quản lý"
        )
        self.can_manage = self.can_view

        self._build_ui()
        if self.can_view:
            self.load_promotions()

    def _get_employee_role(self):
        """Lấy vai trò của tài khoản đang đăng nhập qua Service."""
        try:
            return self.service.get_employee_role(self.username)
        except Exception:
            return ""

    def _build_ui(self):
        """Tạo thanh thao tác, bộ lọc và bảng khuyến mãi."""
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("QUẢN LÝ KHUYẾN MÃI")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        self.add_button = QPushButton("+ Thêm khuyến mãi")
        self.add_button.setProperty("buttonRole", "primary")
        self.add_button.setObjectName("primaryButton")
        self.add_button.clicked.connect(self.add_promotion)
        header.addWidget(self.add_button)

        self.refresh_button = QPushButton("Làm mới")
        self.refresh_button.clicked.connect(self.load_promotions)
        header.addWidget(self.refresh_button)
        root.addLayout(header)

        description = QLabel(
            "Tỷ lệ giảm và thời gian áp dụng được giữ cố định sau khi tạo. "
            "Có thể đổi tên; xóa khuyến mãi chỉ chuyển sang trạng thái "
            "ngừng áp dụng để giữ nguyên lịch sử hóa đơn."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #AAB7C8; font-size: 11px;")
        root.addWidget(description)

        search = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm theo mã hoặc tên khuyến mãi...")
        self.search_input.returnPressed.connect(self.load_promotions)

        search_button = QPushButton("Tìm kiếm")
        search_button.clicked.connect(self.load_promotions)

        clear_button = QPushButton("Xóa tìm kiếm")
        clear_button.clicked.connect(self.clear_search)

        self.show_deleted_check = QCheckBox(
            "Hiện cả khuyến mãi đã xóa"
        )
        self.show_deleted_check.toggled.connect(self.load_promotions)

        search.addWidget(self.search_input, 1)
        search.addWidget(search_button)
        search.addWidget(clear_button)
        search.addWidget(self.show_deleted_check)
        root.addLayout(search)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Mã khuyến mãi",
            "Tên chương trình",
            "Tỷ lệ giảm",
            "Bắt đầu",
            "Kết thúc",
            "Trạng thái",
        ])
        prepare_sortable_table(
            self.table,
            default_column=3,
            default_order=Qt.SortOrder.DescendingOrder,
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        table_header = self.table.horizontalHeader()
        table_header.setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        table_header.setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table.cellDoubleClicked.connect(
            self.open_promotion_detail
        )
        root.addWidget(self.table, 1)

        self.total_label = QLabel("Tổng số khuyến mãi: 0")
        root.addWidget(self.total_label)

        if not self.can_manage:
            self.add_button.hide()

        if not self.can_view:
            self.add_button.hide()
            self.show_deleted_check.hide()
            self.search_input.hide()
            self.table.hide()
            self.total_label.setText(
                "Tài khoản hiện tại không có quyền xem khuyến mãi."
            )

    @staticmethod
    def _format_datetime(value):
        if value is None:
            return ""
        if hasattr(value, "strftime"):
            return value.strftime("%d/%m/%Y %H:%M")
        return str(value)

    @staticmethod
    def _format_rate(value):
        if value is None:
            return ""
        return f"{float(value):.2f}".replace(".", ",") + "%"

    def load_promotions(self, *_):
        """Tải danh sách khuyến mãi qua Service."""
        if not self.can_view:
            return
        try:
            rows = self.service.list_promotions(
                self.search_input.text().strip(),
                self.show_deleted_check.isChecked(),
            )
            pause_table_sorting(self.table)
            self.table.setRowCount(0)
            for row_index, row in enumerate(rows):
                self.table.insertRow(row_index)
                values = [
                    row[0], row[1], self._format_rate(row[2]),
                    self._format_datetime(row[3]),
                    self._format_datetime(row[4]), row[6],
                ]
                for column, value in enumerate(values):
                    item = QTableWidgetItem("" if value is None else str(value))
                    if column == 0:
                        item.setData(Qt.ItemDataRole.UserRole, str(row[0]))
                        item.setTextAlignment(
                            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
                        )
                    elif column == 2:
                        item.setTextAlignment(
                            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                        )
                    self.table.setItem(row_index, column, item)
            self.total_label.setText(f"Tổng số khuyến mãi: {len(rows)}")
        except Exception as error:
            QMessageBox.critical(self, "Lỗi tải khuyến mãi", str(error))
        finally:
            resume_table_sorting(self.table)

    def clear_search(self):
        self.search_input.clear()
        self.load_promotions()

    def add_promotion(self):
        """Mở biểu mẫu tạo chương trình khuyến mãi."""
        if not self.can_manage:
            QMessageBox.warning(
                self,
                "Không có quyền",
                "Chỉ Admin/Quản lý được thêm khuyến mãi.",
            )
            return

        dialog = PromotionFormDialog(self.db, self)
        if dialog.exec():
            self.load_promotions()

    def open_promotion_detail(self, row, column):
        """Mở popup chi tiết khi nhấp đúp vào một chương trình khuyến mãi."""
        code_item = self.table.item(row, 0)
        if code_item is None:
            return

        code = code_item.data(Qt.ItemDataRole.UserRole)
        code = str(code if code is not None else code_item.text()).strip()
        if not code:
            return

        labels = [
            "Mã khuyến mãi:",
            "Tên chương trình:",
            "Tỷ lệ giảm:",
            "Thời gian bắt đầu:",
            "Thời gian kết thúc:",
            "Trạng thái:",
        ]
        values = []
        for index, label in enumerate(labels):
            item = self.table.item(row, index)
            values.append((label, item.text() if item else ""))

        name_item = self.table.item(row, 1)
        current_name = name_item.text() if name_item else ""
        status_item = self.table.item(row, 5)
        is_deleted = (
            status_item is not None and status_item.text() == "Đã xóa"
        )

        dialog = PromotionDetailDialog(
            values,
            can_manage=self.can_manage and not is_deleted,
            on_rename=lambda: self.rename_promotion(code, current_name),
            on_delete=lambda: self.delete_promotion(code, current_name),
            parent=self,
        )
        dialog.exec()

    def rename_promotion(self, code, current_name):
        """Chỉ đổi tên chương trình, không thay đổi tỷ lệ hoặc thời hạn."""
        if not self.can_manage:
            QMessageBox.warning(
                self, "Không có quyền",
                "Chỉ Admin/Quản lý được đổi tên khuyến mãi.",
            )
            return
        name, accepted = QInputDialog.getText(
            self, "Đổi tên khuyến mãi", "Tên chương trình:",
            QLineEdit.EchoMode.Normal, current_name,
        )
        if not accepted:
            return
        try:
            updated_code = self.service.rename_promotion(
                code, name, can_manage=self.can_manage
            )
            QMessageBox.information(
                self, "Thành công", f"Đã đổi tên chương trình {updated_code}."
            )
            self.load_promotions()
        except (ValueError, LookupError, PermissionError) as error:
            QMessageBox.warning(self, "Không thể đổi tên khuyến mãi", str(error))
        except Exception as error:
            QMessageBox.critical(self, "Không thể đổi tên khuyến mãi", str(error))

    def delete_promotion(self, code, name):
        """Xóa mềm chương trình; không tác động các hóa đơn đã dùng nó."""
        if not self.can_manage:
            QMessageBox.warning(
                self, "Không có quyền",
                "Chỉ Admin/Quản lý được xóa khuyến mãi.",
            )
            return
        answer = QMessageBox.question(
            self, "Xác nhận xóa khuyến mãi",
            f"Bạn có chắc muốn ngừng áp dụng chương trình {code}"
            f"{' - ' + name if name else ''}?\n\n"
            "Chương trình sẽ được đánh dấu IS_DELETED = 1. "
            "Hóa đơn cũ và dữ liệu tính tiền hoàn vẫn được giữ nguyên.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            deleted_code = self.service.soft_delete_promotion(
                code, can_manage=self.can_manage
            )
            QMessageBox.information(
                self, "Thành công",
                f"Đã ngừng áp dụng khuyến mãi {deleted_code}.",
            )
            self.load_promotions()
        except (ValueError, LookupError, PermissionError) as error:
            QMessageBox.warning(self, "Không thể xóa khuyến mãi", str(error))
        except Exception as error:
            QMessageBox.critical(self, "Không thể xóa khuyến mãi", str(error))
