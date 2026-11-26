"""Trang danh sách và quản lý chương trình khuyến mãi."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
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
from .bieu_mau import PromotionFormDialog


class PromotionWindow(QWidget):
    """Quản lý khuyến mãi; không sửa tỷ lệ/thời hạn, chỉ thêm và xóa mềm."""

    def __init__(self, db):
        super().__init__()
        self.db = db
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
        """Lấy vai trò của tài khoản đang đăng nhập."""
        if self.username.casefold() == "admin":
            return "Quản lý"

        conn = self.db.get_connection()
        if conn is None or not self.username:
            return ""

        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT VAITRO FROM dbo.NHAN_VIEN WHERE MANV = ?",
                self.username,
            )
            row = cursor.fetchone()
            return str(row[0] or "").strip() if row else ""
        except Exception:
            return ""
        finally:
            if cursor is not None:
                cursor.close()

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
        self.add_button.clicked.connect(self.add_promotion)
        header.addWidget(self.add_button)

        self.delete_button = QPushButton("Xóa khuyến mãi")
        self.delete_button.clicked.connect(self.delete_selected_promotion)
        header.addWidget(self.delete_button)

        self.refresh_button = QPushButton("Làm mới")
        self.refresh_button.clicked.connect(self.load_promotions)
        header.addWidget(self.refresh_button)
        root.addLayout(header)

        description = QLabel(
            "Tỷ lệ giảm và thời hạn được cố định sau khi tạo để bảo toàn "
            "giá trị lịch sử của hóa đơn. Xóa khuyến mãi chỉ chuyển sang "
            "trạng thái ngừng áp dụng; dữ liệu lịch sử vẫn được giữ."
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
        self.table.itemSelectionChanged.connect(
            self.update_action_buttons
        )
        root.addWidget(self.table, 1)

        self.total_label = QLabel("Tổng số khuyến mãi: 0")
        root.addWidget(self.total_label)

        if not self.can_manage:
            self.add_button.hide()
            self.delete_button.hide()

        if not self.can_view:
            self.add_button.hide()
            self.delete_button.hide()
            self.show_deleted_check.hide()
            self.search_input.hide()
            self.table.hide()
            self.total_label.setText(
                "Tài khoản hiện tại không có quyền xem khuyến mãi."
            )

        self.update_action_buttons()

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
        """Tải danh sách, mặc định ẩn các chương trình đã xóa mềm."""
        if not self.can_view:
            return

        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(
                self, "Thông báo", "Chưa có kết nối SQL Server."
            )
            return

        keyword = self.search_input.text().strip()
        sql = """
            SELECT
                MAKM,
                TENKM,
                TYLEGIAM,
                NGAYBD,
                NGAYKT,
                ISNULL(IS_DELETED, 0) AS IS_DELETED,
                CASE
                    WHEN ISNULL(IS_DELETED, 0) = 1 THEN N'Đã xóa'
                    WHEN NGAYBD > SYSDATETIME() THEN N'Sắp diễn ra'
                    WHEN NGAYKT < SYSDATETIME() THEN N'Đã kết thúc'
                    ELSE N'Đang áp dụng'
                END AS TRANGTHAI
            FROM dbo.CHUONG_TRINH_KM
            WHERE 1 = 1
        """
        params = []

        if not self.show_deleted_check.isChecked():
            sql += " AND ISNULL(IS_DELETED, 0) = 0"

        if keyword:
            like = f"%{keyword}%"
            sql += " AND (MAKM LIKE ? OR TENKM LIKE ?)"
            params.extend([like, like])

        sql += """
            ORDER BY
                CASE WHEN ISNULL(IS_DELETED, 0) = 0 THEN 0 ELSE 1 END,
                NGAYBD DESC,
                MAKM DESC
        """

        cursor = None
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, *params)
            else:
                cursor.execute(sql)
            rows = cursor.fetchall()

            pause_table_sorting(self.table)
            self.table.setRowCount(0)

            for row_index, row in enumerate(rows):
                self.table.insertRow(row_index)
                values = [
                    row[0],
                    row[1],
                    self._format_rate(row[2]),
                    self._format_datetime(row[3]),
                    self._format_datetime(row[4]),
                    row[6],
                ]
                for column, value in enumerate(values):
                    item = QTableWidgetItem(
                        "" if value is None else str(value)
                    )
                    if column == 0:
                        item.setData(
                            Qt.ItemDataRole.UserRole, str(row[0])
                        )
                        item.setTextAlignment(
                            Qt.AlignmentFlag.AlignCenter
                            | Qt.AlignmentFlag.AlignVCenter
                        )
                    elif column == 2:
                        item.setTextAlignment(
                            Qt.AlignmentFlag.AlignRight
                            | Qt.AlignmentFlag.AlignVCenter
                        )
                    self.table.setItem(row_index, column, item)

            self.total_label.setText(
                f"Tổng số khuyến mãi: {len(rows)}"
            )
        except Exception as error:
            QMessageBox.critical(
                self, "Lỗi tải khuyến mãi", str(error)
            )
        finally:
            resume_table_sorting(self.table)
            if cursor is not None:
                cursor.close()
        self.update_action_buttons()

    def clear_search(self):
        self.search_input.clear()
        self.load_promotions()

    def _selected_code(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        return str(value if value is not None else item.text()).strip()

    def update_action_buttons(self):
        """Chỉ bật nút xóa khi đang chọn một chương trình chưa bị xóa."""
        code = self._selected_code()
        if not self.can_manage or not code:
            self.delete_button.setEnabled(False)
            return

        row = self.table.currentRow()
        status_item = self.table.item(row, 5)
        is_deleted = (
            status_item is not None and status_item.text() == "Đã xóa"
        )
        self.delete_button.setEnabled(not is_deleted)

    def add_promotion(self):
        """Mở biểu mẫu tạo chương trình khuyến mãi."""
        if not self.can_manage:
            QMessageBox.warning(
                self, "Không có quyền",
                "Chỉ Admin/Quản lý được thêm khuyến mãi.",
            )
            return

        dialog = PromotionFormDialog(self.db, self)
        if dialog.exec():
            self.load_promotions()

    def delete_selected_promotion(self):
        """Xóa mềm chương trình; không tác động các hóa đơn đã dùng nó."""
        if not self.can_manage:
            QMessageBox.warning(
                self, "Không có quyền",
                "Chỉ Admin/Quản lý được xóa khuyến mãi.",
            )
            return

        code = self._selected_code()
        if not code:
            QMessageBox.information(
                self, "Chưa chọn khuyến mãi",
                "Vui lòng chọn chương trình cần xóa.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Xác nhận xóa khuyến mãi",
            f"Bạn có chắc muốn ngừng áp dụng chương trình {code}?\n\n"
            "Chương trình sẽ được đánh dấu IS_DELETED = 1. "
            "Hóa đơn cũ và dữ liệu tính tiền hoàn vẫn được giữ nguyên.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(
                self, "Thông báo", "Chưa có kết nối SQL Server."
            )
            return

        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE dbo.CHUONG_TRINH_KM
                SET IS_DELETED = 1
                OUTPUT inserted.MAKM
                WHERE MAKM = ?
                  AND ISNULL(IS_DELETED, 0) = 0
            """, code)

            if cursor.fetchone() is None:
                raise RuntimeError(
                    "Khuyến mãi không tồn tại hoặc đã được xóa trước đó."
                )

            conn.commit()
            QMessageBox.information(
                self, "Thành công",
                f"Đã ngừng áp dụng khuyến mãi {code}.",
            )
            self.load_promotions()
        except Exception as error:
            conn.rollback()
            QMessageBox.critical(
                self, "Không thể xóa khuyến mãi", str(error)
            )
        finally:
            if cursor is not None:
                cursor.close()
