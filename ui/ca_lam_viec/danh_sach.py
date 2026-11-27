"""ShiftWindow: thành phần giao diện nghiệp vụ."""

from decimal import (
    Decimal,
    InvalidOperation,
)
from PySide6.QtCore import (
    Qt,
    QTimer,
)
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QHeaderView,
    QAbstractItemView,
    QMessageBox,
    QComboBox,
    QGroupBox,
    QDialog,
    QInputDialog,
    QSizePolicy,
)
from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table,
    pause_table_sorting,
    resume_table_sorting,
)
from .tao_bieu_mau import ShiftCreateDialog
from .chi_tiet import ShiftDetailDialog
from ui.permissions import is_admin_account
from core.repositories.ca_lam_viec_repository import CaLamViecRepository
from core.services.ca_lam_viec_service import CaLamViecService


class ShiftWindow(QWidget):
    """Quản lý lịch ca, đăng ký nhân viên, theo dõi trạng thái và chốt tiền cuối ca."""
    """Trang ca làm việc dùng trực tiếp CA_LAM_VIEC, LAMCA, NHAN_VIEN.

    Nhân viên thông thường:
        - Chỉ nhìn thấy ca đang diễn ra.
        - Chỉ đăng ký được ca đang diễn ra.

    Kế toán:
        - Có các quyền đăng ký ca đang diễn ra như nhân viên.
        - Ngoài ra thấy các ca đã kết thúc nhưng chưa ghi tiền cuối ca.
        - Có thể ghi tiền bất cứ lúc nào sau khi ca kết thúc, một lần duy nhất.

    Quản lý/Admin:
        - Xem ca hiện tại, lịch sử và danh sách nhân viên từng ca.
        - Tạo ca theo lịch cố định 07:00–12:00, 12:00–17:00, 17:00–22:00.

    Không sử dụng stored procedure hoặc yêu cầu tạo bảng mới.
    """

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.service = CaLamViecService(CaLamViecRepository(db))
        self.username = (getattr(db, "username", "") or "").strip()
        self.is_admin = is_admin_account(self.username)
        self.employee_role = ""
        self.is_manager = self.is_admin
        self.is_accountant = self.is_admin

        self._load_current_user_role()
        self.is_accountant = (
            self.is_admin or self.employee_role.strip().casefold() == "kế toán"
        )

        if self.is_manager:
            self._build_manager_ui()
            self.refresh_manager_view()
        else:
            self._build_employee_ui()
            self.refresh_employee_view()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(30000)
        if self.is_manager:
            self.refresh_timer.timeout.connect(self.refresh_manager_view)
        else:
            self.refresh_timer.timeout.connect(self.refresh_employee_view)
        self.refresh_timer.start()

    # ---------------------------------------------------------
    # COMMON HELPERS
    # ---------------------------------------------------------
    def _load_current_user_role(self):
        self.employee_role = self.service.get_employee_role(self.username)
        self.is_manager = self.is_admin or self.employee_role.casefold() == "quản lý"

    @staticmethod
    def _format_date(value):
        """Định dạng ngày làm theo cách hiển thị thống nhất."""
        if value is None:
            return ""
        return value.strftime("%d/%m/%Y") if hasattr(value, "strftime") else str(value)[:10]

    @staticmethod
    def _format_time(value):
        """Định dạng giờ bắt đầu và kết thúc của ca."""
        if value is None:
            return ""
        return value.strftime("%H:%M") if hasattr(value, "strftime") else str(value)[:5]

    @staticmethod
    def _format_cash(value):
        """Định dạng tiền đầu ca hoặc cuối ca."""
        if value is None:
            return "Chưa ghi"
        try:
            return f"{Decimal(str(value)):,.2f}"
        except (InvalidOperation, ValueError):
            return str(value)

    @staticmethod
    def _make_table(
            headers,
            stretch_column=None,
            default_sort_column=0,
            default_sort_order=Qt.SortOrder.AscendingOrder
    ):
        """Tạo bảng có cấu hình cột, sắp xếp và lựa chọn dòng."""
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)

        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)

        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        if stretch_column is not None:
            header.setSectionResizeMode(
                stretch_column, QHeaderView.ResizeMode.Stretch
            )

        prepare_sortable_table(
            table,
            default_column=default_sort_column,
            default_order=default_sort_order
        )

        return table

    @staticmethod
    def _fit_table_height(table, maximum_height):
        """Co chiều cao bảng theo header và số dòng, không để khoảng trống thừa."""
        header_height = max(36, table.horizontalHeader().sizeHint().height())
        rows_height = sum(
            table.rowHeight(row) for row in range(table.rowCount())
        )
        frame_height = table.frameWidth() * 2
        content_height = header_height + rows_height + frame_height + 4

        # Khi chưa có dữ liệu, chỉ giữ đủ chỗ cho hàng tiêu đề.
        table.setFixedHeight(min(maximum_height, content_height))

    @staticmethod
    def _set_item(table, row, column, value, user_data=None):
        """Đặt giá trị và kiểu hiển thị cho một ô trong bảng ca làm việc."""
        item = QTableWidgetItem("" if value is None else str(value))
        if user_data is not None:
            item.setData(Qt.ItemDataRole.UserRole, user_data)
        table.setItem(row, column, item)
        return item

    def _show_db_error(self, title, error):
        """Hiển thị thông báo lỗi truy vấn cơ sở dữ liệu cho người dùng."""
        QMessageBox.critical(self, title, str(error))

    # ---------------------------------------------------------
    # EMPLOYEE / ACCOUNTANT UI
    # ---------------------------------------------------------
    def _build_employee_ui(self):
        """Tạo giao diện ca làm việc dành cho nhân viên thông thường."""
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("CA LÀM VIỆC")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        self.employee_refresh_button = QPushButton("Làm mới")
        self.employee_refresh_button.clicked.connect(self.refresh_employee_view)
        header.addWidget(self.employee_refresh_button)
        root.addLayout(header)

        info = QHBoxLayout()
        self.employee_name_label = QLabel(
            f"Tài khoản: {self.username} | Vai trò: {self.employee_role}"
        )
        self.employee_server_time_label = QLabel("Giờ SQL Server: --")
        info.addWidget(self.employee_name_label)
        info.addStretch()
        info.addWidget(self.employee_server_time_label)
        root.addLayout(info)

        if self.is_accountant:
            note_text = (
                "Bạn chỉ đăng ký các ca đang diễn ra. Với vai trò Kế toán, "
                "bạn còn thấy các ca đã kết thúc nhưng chưa ghi tiền cuối ca; "
                "có thể ghi tiền bất cứ lúc nào sau khi ca kết thúc."
            )
        else:
            note_text = "Chỉ hiển thị ca đang diễn ra tại thời điểm hiện tại. Bạn chỉ có thể đăng ký ca đang diễn ra."
        note = QLabel(note_text)
        note.setWordWrap(True)
        note.setStyleSheet("color: #AAB7C8; font-size: 11px;")
        root.addWidget(note)

        self.employee_shift_table = self._make_table(
            ["Mã ca", "Ca", "Ngày làm", "Giờ mở", "Giờ đóng",
             "Số nhân viên", "Trạng thái ca", "Đăng ký", "Tiền cuối ca"],
            stretch_column=6,
            default_sort_column=2,
            default_sort_order=Qt.SortOrder.DescendingOrder
        )
        # Double-click mở popup; các thao tác ca được đặt bên trong popup.
        self.employee_shift_table.cellDoubleClicked.connect(
            self.open_employee_shift_detail
        )
        root.addWidget(self.employee_shift_table)

        self.employee_total_label = QLabel("Số ca: 0")
        root.addWidget(self.employee_total_label)

    def refresh_employee_view(self):
        try:
            server_now = self.service.get_server_time()
            self.employee_server_time_label.setText(
                "Giờ SQL Server: " + server_now.strftime("%d/%m/%Y %H:%M:%S")
            )
        except Exception as error:
            self._show_db_error("Không lấy được thời gian SQL Server", error)
            return
        self.load_employee_shifts()

    def load_employee_shifts(self):
        try:
            rows = self.service.list_employee_shifts(self.username, self.is_accountant)
            pause_table_sorting(self.employee_shift_table)
            self.employee_shift_table.setRowCount(0)
            for row_index, shift in enumerate(rows):
                self.employee_shift_table.insertRow(row_index)
                maca, registered, closing_cash, is_ended = int(shift[0]), bool(shift[6]), shift[7], bool(shift[8])
                values = [maca, shift[1], self._format_date(shift[2]), self._format_time(shift[3]), self._format_time(shift[4]), shift[5], "Đã kết thúc" if is_ended else "Đang diễn ra", "Đã đăng ký" if registered else "Chưa đăng ký", self._format_cash(closing_cash)]
                for col, value in enumerate(values):
                    self._set_item(self.employee_shift_table, row_index, col, value)
                first = self.employee_shift_table.item(row_index, 0)
                first.setData(Qt.ItemDataRole.UserRole, maca)
                first.setData(Qt.ItemDataRole.UserRole + 1, registered)
                first.setData(Qt.ItemDataRole.UserRole + 2, closing_cash is not None)
                first.setData(Qt.ItemDataRole.UserRole + 3, is_ended)
            self.employee_total_label.setText(
                f"Có {len(rows)} ca đang diễn ra hoặc chờ kế toán ghi tiền cuối ca."
                if self.is_accountant and rows else
                f"Có {len(rows)} ca đang diễn ra. Chỉ đăng ký được ca hiện tại."
                if rows else
                "Hiện không có ca đang diễn ra hoặc ca chờ kế toán ghi tiền."
                if self.is_accountant else
                "Hiện tại không có ca làm việc nào đang diễn ra."
            )
        except Exception as error:
            self._show_db_error("Không thể tải ca làm việc", error)
        finally:
            resume_table_sorting(self.employee_shift_table)

    def open_employee_shift_detail(self, row, column):
        """Mở popup một ca cùng các thao tác phù hợp với vai trò hiện tại."""
        item = self.employee_shift_table.item(row, 0)
        if item is None:
            return

        shift_id = int(item.data(Qt.ItemDataRole.UserRole))
        registered = bool(item.data(Qt.ItemDataRole.UserRole + 1))
        has_closing_cash = bool(item.data(Qt.ItemDataRole.UserRole + 2))
        is_ended = bool(item.data(Qt.ItemDataRole.UserRole + 3))

        shift = {
            "maca": shift_id,
            "soca": self.employee_shift_table.item(row, 1).text(),
            "ngaylam": self.employee_shift_table.item(row, 2).text(),
            "tgmo": self.employee_shift_table.item(row, 3).text(),
            "tgdong": self.employee_shift_table.item(row, 4).text(),
            "so_nhan_vien": self.employee_shift_table.item(row, 5).text(),
            "trang_thai": self.employee_shift_table.item(row, 6).text(),
            "dang_ky": "Đã đăng ký" if registered else "Chưa đăng ký",
            "tien_cuoi_ca": self.employee_shift_table.item(row, 8).text(),
        }

        can_register = not is_ended and not registered and not has_closing_cash
        can_record_cash = self.is_accountant and is_ended and not has_closing_cash
        dialog = ShiftDetailDialog(
            shift,
            parent=self,
            on_register=(
                lambda shift_id=shift_id: self._register_current_shift(shift_id)
            ) if can_register else None,
            on_closing_cash=(
                lambda shift_id=shift_id: self._record_closing_cash(shift_id)
            ) if can_record_cash else None,
        )
        dialog.exec()

    def _register_current_shift(self, maca):
        answer = QMessageBox.question(self, "Xác nhận đăng ký ca", "Bạn có chắc muốn đăng ký ca đang diễn ra này?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.register_current_shift(maca, self.username)
            QMessageBox.information(self, "Thành công", "Đăng ký ca làm việc hiện tại thành công.")
            self.refresh_employee_view()
        except Exception as error:
            self._show_db_error("Không thể đăng ký ca", error)

    def _record_closing_cash(self, maca):
        if not self.is_accountant:
            QMessageBox.warning(self, "Không có quyền", "Chỉ nhân viên có vai trò Kế toán được ghi tiền mặt cuối ca.")
            return
        amount_text, ok = QInputDialog.getText(self, "Ghi tiền mặt cuối ca", "Nhập tổng tiền mặt cuối ca của cả ca (VNĐ):")
        if not ok:
            return
        try:
            closing_cash = self.service.parse_cash(amount_text, "tiền cuối ca")
        except ValueError as error:
            QMessageBox.warning(self, "Số tiền không hợp lệ", str(error))
            return
        answer = QMessageBox.question(self, "Xác nhận ghi tiền cuối ca", f"Xác nhận ghi tiền mặt cuối ca {maca} với số tiền {closing_cash:,.2f} VNĐ?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.record_closing_cash(maca, self.username, closing_cash)
            QMessageBox.information(self, "Ghi tiền cuối ca thành công", "Đã ghi tiền mặt cuối ca. Mỗi ca chỉ được ghi một lần.")
            self.refresh_employee_view()
        except Exception as error:
            self._show_db_error("Không thể ghi tiền cuối ca", error)

    def _build_manager_ui(self):
        """Tạo giao diện quản lý lịch ca và danh sách nhân viên theo ca."""
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("QUẢN LÝ CA LÀM VIỆC")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        self.add_shift_button = QPushButton("+ Thêm ca")
        self.add_shift_button.clicked.connect(self.add_shift)
        header.addWidget(self.add_shift_button)

        self.manager_server_time_label = QLabel("Giờ SQL Server: --")
        header.addWidget(self.manager_server_time_label)

        self.manager_refresh_button = QPushButton("Làm mới")
        self.manager_refresh_button.clicked.connect(self.refresh_manager_view)
        header.addWidget(self.manager_refresh_button)
        root.addLayout(header)

        stats = QHBoxLayout()
        self.active_shift_stat = QLabel("Ca đang diễn ra: 0")
        self.active_employee_stat = QLabel("Nhân viên đang làm: 0")
        self.today_shift_stat = QLabel("Ca trong ngày: 0")
        for label in (self.active_shift_stat, self.active_employee_stat, self.today_shift_stat):
            label.setStyleSheet(
                "QLabel { background-color: #29374B; color: white; "
                "padding: 10px; border-radius: 6px; font-weight: bold; }"
            )
            stats.addWidget(label)
        root.addLayout(stats)

        current_group = QGroupBox("Các ca đang diễn ra ngay lúc này")
        current_group.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )
        current_layout = QVBoxLayout(current_group)
        self.current_table = self._make_table(
            ["Mã ca", "Ngày làm", "Ca", "Giờ mở", "Giờ đóng", "Số nhân viên", "Tiền cuối ca"],
            stretch_column=2,
            default_sort_column=2
        )
        self._fit_table_height(self.current_table, 190)
        # Double-click mở popup chi tiết ca và danh sách nhân viên.
        self.current_table.cellDoubleClicked.connect(self._current_shift_selected)
        current_layout.addWidget(self.current_table)
        root.addWidget(current_group)

        history_group = QGroupBox("Lịch làm việc và lịch sử ca")
        history_group.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )
        history_layout = QVBoxLayout(history_group)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Khoảng thời gian:"))
        self.history_filter = QComboBox()
        self.history_filter.addItem("Toàn bộ lịch", "all")
        self.history_filter.addItem("Hôm nay", "today")
        self.history_filter.addItem("7 ngày gần đây", "7days")
        self.history_filter.addItem("30 ngày gần đây", "30days")
        self.history_filter.currentIndexChanged.connect(self.load_shift_history)
        filter_layout.addWidget(self.history_filter)
        filter_layout.addStretch()
        history_layout.addLayout(filter_layout)

        self.history_table = self._make_table(
            ["Mã ca", "Ngày làm", "Ca", "Giờ mở", "Giờ đóng", "Số nhân viên",
             "Tiền đầu ca", "Tiền cuối ca", "Trạng thái ca"],
            stretch_column=8,
            default_sort_column=1,
            default_sort_order=Qt.SortOrder.DescendingOrder
        )
        self._fit_table_height(self.history_table, 250)
        self.history_table.cellDoubleClicked.connect(self._history_shift_selected)
        history_layout.addWidget(self.history_table)
        root.addWidget(history_group)

        # Phần chiều cao dư được dồn xuống cuối trang thay vì làm giãn hai khung bảng.
        root.addStretch(1)

    def add_shift(self):
        if not self.is_manager:
            QMessageBox.warning(self, "Không có quyền", "Chỉ Quản lý/Admin mới được thêm ca.")
            return
        dialog = ShiftCreateDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            shift_id = self.service.create_shift(dialog.get_values(), is_manager=self.is_manager)
            QMessageBox.information(self, "Thành công", f"Đã tạo ca làm việc thành công.\\nMã ca: {shift_id}")
            self.refresh_manager_view()
        except ValueError as error:
            QMessageBox.warning(self, "Không thể tạo ca", str(error))
        except Exception as error:
            self._show_db_error("Không thể tạo ca làm việc", error)

    def refresh_manager_view(self):
        try:
            summary = self.service.get_manager_summary()
            self.manager_server_time_label.setText("Giờ SQL Server: " + summary["server_time"].strftime("%d/%m/%Y %H:%M:%S"))
            self.active_shift_stat.setText(f"Ca đang diễn ra: {summary['active_shifts']}")
            self.active_employee_stat.setText(f"Nhân viên đang làm: {summary['active_employees']}")
            self.today_shift_stat.setText(f"Ca trong ngày: {summary['today_shifts']}")
        except Exception as error:
            self._show_db_error("Không thể tải tổng quan ca làm", error)
            return
        self.load_current_shifts()
        self.load_shift_history()

    def load_current_shifts(self):
        try:
            rows = self.service.list_current_shifts()
            pause_table_sorting(self.current_table)
            self.current_table.setRowCount(0)
            for row_index, shift in enumerate(rows):
                self.current_table.insertRow(row_index)
                values = [shift[0], self._format_date(shift[1]), shift[2], self._format_time(shift[3]), self._format_time(shift[4]), shift[5], self._format_cash(shift[6])]
                for col, value in enumerate(values):
                    self._set_item(self.current_table, row_index, col, value, user_data=int(shift[0]) if col == 0 else None)
        except Exception as error:
            self._show_db_error("Không thể tải các ca đang diễn ra", error)
        finally:
            self._fit_table_height(self.current_table, 190)
            resume_table_sorting(self.current_table)

    def load_shift_history(self, *_):
        try:
            rows = self.service.list_shift_history(self.history_filter.currentData())
            pause_table_sorting(self.history_table)
            self.history_table.setRowCount(0)
            for row_index, shift in enumerate(rows):
                self.history_table.insertRow(row_index)
                values = [shift[0], self._format_date(shift[1]), shift[2], self._format_time(shift[3]), self._format_time(shift[4]), shift[5], self._format_cash(shift[6]), self._format_cash(shift[7]), shift[8]]
                for col, value in enumerate(values):
                    self._set_item(self.history_table, row_index, col, value, user_data=int(shift[0]) if col == 0 else None)
        except Exception as error:
            self._show_db_error("Không thể tải lịch sử ca", error)
        finally:
            resume_table_sorting(self.history_table)
            self._fit_table_height(self.history_table, 250)

    def _current_shift_selected(self, row, column):
        """Mở popup thông tin và danh sách nhân viên của ca đang diễn ra."""
        self._open_manager_shift_detail(self.current_table, row)

    def _history_shift_selected(self, row, column):
        """Mở popup thông tin và danh sách nhân viên của ca trong lịch sử."""
        self._open_manager_shift_detail(self.history_table, row)

    def _open_manager_shift_detail(self, table, row):
        """Tải danh sách nhân viên và hiển thị mọi thông tin ca trong popup."""
        item = table.item(row, 0)
        if item is None:
            return

        shift_id = int(item.data(Qt.ItemDataRole.UserRole))
        shift = {"maca": shift_id}
        for column in range(table.columnCount()):
            header = table.horizontalHeaderItem(column)
            cell = table.item(row, column)
            if header is not None and cell is not None:
                shift[header.text()] = cell.text()

        employees = self._get_shift_roster(shift_id)
        if employees is None:
            return

        shift.update({
            "soca": shift.get("Ca", ""),
            "ngaylam": shift.get("Ngày làm", ""),
            "tgmo": shift.get("Giờ mở", ""),
            "tgdong": shift.get("Giờ đóng", ""),
            "so_nhan_vien": shift.get("Số nhân viên", str(len(employees))),
            "trang_thai": shift.get("Trạng thái ca", "Đang diễn ra"),
            "tien_dau_ca": shift.get("Tiền đầu ca", ""),
            "tien_cuoi_ca": shift.get("Tiền cuối ca", ""),
        })
        # Chỉ ca sắp bắt đầu mới được hiển thị nút xóa; điều kiện thời gian
        # và các liên kết chứng từ vẫn được kiểm tra lại trong transaction.
        can_delete = (
            shift.get("Trạng thái ca") == "Sắp bắt đầu"
            and self.is_manager
        )
        closing_cash_text = str(shift.get("Tiền cuối ca", "")).strip()
        can_record_cash = (
            self.is_admin
            and shift.get("Trạng thái ca") == "Đã kết thúc"
            and closing_cash_text in ("", "Chưa ghi")
        )
        ShiftDetailDialog(
            shift,
            parent=self,
            employees=employees,
            on_closing_cash=(
                lambda shift_id=shift_id: self._record_closing_cash(shift_id)
            ) if can_record_cash else None,
            on_delete=(
                lambda shift_id=shift_id: self.delete_shift(shift_id)
            ) if can_delete else None,
        ).exec()

    def delete_shift(self, maca):
        if not self.is_manager:
            QMessageBox.warning(self, "Không có quyền", "Chỉ Quản lý/Admin mới được xóa ca làm việc.")
            return
        answer = QMessageBox.question(self, "Xác nhận xóa ca", f"Bạn có chắc muốn xóa ca làm việc mã {maca}?\\n\\nCa chỉ được xóa nếu chưa bắt đầu và chưa có hóa đơn liên kết. Các đăng ký nhân viên của ca này cũng sẽ bị xóa.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.delete_shift(maca, is_manager=self.is_manager)
            QMessageBox.information(self, "Thành công", f"Đã xóa ca làm việc mã {maca}.")
            self.refresh_manager_view()
        except (ValueError, LookupError, PermissionError) as error:
            QMessageBox.warning(self, "Không thể xóa ca", str(error))
        except Exception as error:
            self._show_db_error("Không thể xóa ca làm việc", error)

    def _get_shift_roster(self, maca):
        try:
            return self.service.get_shift_roster(maca)
        except Exception as error:
            self._show_db_error("Không thể tải danh sách nhân viên trong ca", error)
            return None
