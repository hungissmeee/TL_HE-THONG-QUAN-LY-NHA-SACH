"""Trang danh sách, tìm kiếm và lập phiếu đổi trả."""

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QDialog, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QTableWidget, QHeaderView,
    QAbstractItemView, QMessageBox, QDateEdit,
)
from ui.permissions import is_admin_account
from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table, pause_table_sorting, resume_table_sorting,
)
from .dung_chung import date_text, money
from .tao_bieu_mau import CreateReturnDialog
from .chi_tiet import ReturnDetailDialog


class ReturnWindow(QWidget):
    """Quản lý lịch sử phiếu đổi trả; chỉ vai trò Quản lý được thao tác."""

    def __init__(self, db):
        super().__init__()
        self.db = db
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
        """Đọc vai trò nhân viên; quyền admin được xử lý độc lập với vai trò nhân viên."""
        conn = self.db.get_connection()
        if conn is None or self.username.casefold() == "admin":
            return ""
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT VAITRO FROM dbo.NHAN_VIEN WHERE MANV = ?",
                self.username
            )
            row = cursor.fetchone()
            return str(row[0] or "").strip() if row else ""
        finally:
            cursor.close()

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
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("dd/MM/yyyy")
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
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
        """Tải lịch sử đổi trả theo ngày và từ khóa."""
        if not self.can_manage:
            self.table.setRowCount(0)
            self.total_label.setText("Không có quyền truy cập chức năng đổi trả.")
            return
        if self.from_date.date() > self.to_date.date():
            QMessageBox.warning(
                self, "Khoảng ngày không hợp lệ",
                "Ngày bắt đầu không được lớn hơn ngày kết thúc."
            )
            return

        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối SQL Server.")
            return
        cursor = conn.cursor()
        keyword = self.search_input.text().strip()
        sql = """
            SELECT
                PDT.MAPDT, PDT.NGAY_DOI_TRA, COALESCE(PDT.MAHD, ''),
                COALESCE(NV.TENNV, PDT.MANV, ''), COALESCE(PDT.LY_DO, ''),
                COALESCE(CT.TONG_SOLUONG, 0), COALESCE(PDT.TONG_TIEN_HOAN, 0)
            FROM dbo.PHIEU_DOI_TRA PDT
            LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = PDT.MANV
            OUTER APPLY (
                SELECT SUM(COALESCE(CTDT.SOLUONG, 0)) AS TONG_SOLUONG
                FROM dbo.CHI_TIET_DOI_TRA CTDT
                WHERE CTDT.MAPDT = PDT.MAPDT
            ) CT
            WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
              AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
        """
        params = [
            self.from_date.date().toString("yyyy-MM-dd"),
            self.to_date.date().toString("yyyy-MM-dd"),
        ]
        if keyword:
            like = f"%{keyword}%"
            sql += """
                AND (
                    PDT.MAPDT LIKE ? OR PDT.MAHD LIKE ?
                    OR PDT.MANV LIKE ? OR NV.TENNV LIKE ?
                    OR PDT.LY_DO LIKE ?
                )
            """
            params.extend([like] * 5)
        sql += " ORDER BY PDT.NGAY_DOI_TRA DESC, PDT.MAPDT DESC"

        try:
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
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
            self.total_label.setText(f"Tổng số phiếu đổi trả: {len(rows)}")
        except Exception as error:
            QMessageBox.critical(self, "Lỗi tải phiếu đổi trả", str(error))
        finally:
            resume_table_sorting(self.table)
            cursor.close()

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
            ReturnDetailDialog(self.db, return_code, self).exec()
        except Exception as error:
            QMessageBox.critical(self, "Lỗi chi tiết phiếu đổi trả", str(error))
