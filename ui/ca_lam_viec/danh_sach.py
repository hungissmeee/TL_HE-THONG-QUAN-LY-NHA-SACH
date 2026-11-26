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
)
from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    create_table_action_panel,
    prepare_sortable_table,
    pause_table_sorting,
    resume_table_sorting,
)
from .tao_bieu_mau import ShiftCreateDialog


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
        self.username = (getattr(db, "username", "") or "").strip()
        self.employee_role = ""
        self.is_manager = self.username.casefold() == "admin"
        self.is_accountant = False

        self._load_current_user_role()
        self.is_accountant = self.employee_role.strip().casefold() == "kế toán"

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
        """Lấy vai trò của nhân viên đang đăng nhập để phân biệt quyền đăng ký, xem và chốt ca."""
        conn = self.db.get_connection()
        if conn is None:
            raise RuntimeError("Chưa có kết nối database!")

        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT VAITRO FROM dbo.NHAN_VIEN WHERE MANV = ?",
                (self.username,)
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError(
                    f"Không tìm thấy hồ sơ nhân viên có MANV = {self.username}."
                )

            self.employee_role = (row[0] or "").strip()
            if self.employee_role.casefold() == "quản lý" or self.username.casefold() == "admin":
                self.is_manager = True
        finally:
            cursor.close()

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
        self.employee_shift_table.itemSelectionChanged.connect(
            self.update_employee_shift_actions
        )
        root.addWidget(self.employee_shift_table)

        self.employee_total_label = QLabel("Số ca: 0")
        root.addWidget(self.employee_total_label)

        self.shift_action_panel, shift_action_layout, self.shift_action_hint = (
            create_table_action_panel(
                "Chọn một ca để đăng ký hoặc ghi tiền cuối ca nếu bạn có quyền.",
                self,
            )
        )
        self.register_shift_button = QPushButton("Đăng ký ca")
        self.register_shift_button.setEnabled(False)
        self.register_shift_button.clicked.connect(self.register_selected_shift)
        shift_action_layout.addWidget(self.register_shift_button)

        self.closing_cash_button = QPushButton("Ghi tiền cuối ca")
        self.closing_cash_button.setEnabled(False)
        self.closing_cash_button.clicked.connect(self.record_selected_closing_cash)
        shift_action_layout.addWidget(self.closing_cash_button)
        root.addWidget(self.shift_action_panel)

    def refresh_employee_view(self):
        """Làm mới danh sách ca có thể đăng ký của nhân viên."""
        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối database!")
            return

        cursor = conn.cursor()
        try:
            cursor.execute("SELECT SYSDATETIME()")
            server_now = cursor.fetchone()[0]
            self.employee_server_time_label.setText(
                "Giờ SQL Server: " + server_now.strftime("%d/%m/%Y %H:%M:%S")
            )
        except Exception as error:
            self._show_db_error("Không lấy được thời gian SQL Server", error)
            return
        finally:
            cursor.close()

        self.load_employee_shifts()

    def load_employee_shifts(self):
        """Nhân viên chỉ thấy ca đang diễn ra; kế toán thấy thêm ca đã kết thúc chưa chốt."""
        conn = self.db.get_connection()
        if conn is None:
            return

        cursor = conn.cursor()
        try:
            sql = """
                SELECT
                    C.MACA,
                    C.SOCA,
                    CAST(C.NGAYLAM AS DATE) AS NGAYLAM,
                    C.TGMO,
                    C.TGDONG,
                    COUNT(DISTINCT L.MANV) AS EmployeeCount,
                    CASE
                        WHEN MAX(CASE WHEN L.MANV = ? THEN 1 ELSE 0 END) = 1
                        THEN 1 ELSE 0
                    END AS IsRegistered,
                    C.TMCUOICA,
                    CASE WHEN SYSDATETIME() >= T.EndAt THEN 1 ELSE 0 END AS IsEnded
                FROM dbo.CA_LAM_VIEC C
                CROSS APPLY (
                    SELECT
                        DATEADD(
                            SECOND,
                            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGMO),
                            CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                        ) AS StartAt,
                        DATEADD(
                            SECOND,
                            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGDONG),
                            DATEADD(
                                DAY,
                                CASE WHEN C.TGDONG <= C.TGMO THEN 1 ELSE 0 END,
                                CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                            )
                        ) AS EndAt
                ) T
                LEFT JOIN dbo.LAMCA L ON L.MACA = C.MACA
                WHERE C.TGMO IS NOT NULL
                  AND C.TGDONG IS NOT NULL
                  AND (
                        (SYSDATETIME() >= T.StartAt AND SYSDATETIME() < T.EndAt)
                        OR
                        (? = 1 AND SYSDATETIME() >= T.EndAt AND C.TMCUOICA IS NULL)
                  )
                GROUP BY C.MACA, C.SOCA, C.NGAYLAM, C.TGMO, C.TGDONG,
                         C.TMCUOICA, T.EndAt
                ORDER BY C.NGAYLAM DESC, C.SOCA;
            """
            # Hai dấu ? trong SQL: tài khoản hiện tại và cờ kế toán.
            cursor.execute(sql, (self.username, int(self.is_accountant)))
            rows = cursor.fetchall()

            pause_table_sorting(self.employee_shift_table)

            self.employee_shift_table.setRowCount(0)

            for row_index, shift in enumerate(rows):
                self.employee_shift_table.insertRow(row_index)
                maca = int(shift[0])
                registered = bool(shift[6])
                closing_cash = shift[7]
                is_ended = bool(shift[8])

                values = [
                    maca,
                    shift[1],
                    self._format_date(shift[2]),
                    self._format_time(shift[3]),
                    self._format_time(shift[4]),
                    shift[5],
                    "Đã kết thúc" if is_ended else "Đang diễn ra",
                    "Đã đăng ký" if registered else "Chưa đăng ký",
                    self._format_cash(closing_cash),
                ]

                for col, value in enumerate(values):
                    self._set_item(self.employee_shift_table, row_index, col, value)

                # Lưu trạng thái theo dòng để thanh thao tác không cần truy vấn lại.
                first_item = self.employee_shift_table.item(row_index, 0)
                first_item.setData(Qt.ItemDataRole.UserRole, maca)
                first_item.setData(Qt.ItemDataRole.UserRole + 1, registered)
                first_item.setData(Qt.ItemDataRole.UserRole + 2, closing_cash is not None)
                first_item.setData(Qt.ItemDataRole.UserRole + 3, is_ended)

            if rows:
                if self.is_accountant:
                    self.employee_total_label.setText(
                        f"Có {len(rows)} ca đang diễn ra hoặc chờ kế toán ghi tiền cuối ca."
                    )
                else:
                    self.employee_total_label.setText(
                        f"Có {len(rows)} ca đang diễn ra. Chỉ đăng ký được ca hiện tại."
                    )
            else:
                self.employee_total_label.setText(
                    "Hiện không có ca đang diễn ra hoặc ca chờ kế toán ghi tiền."
                    if self.is_accountant
                    else "Hiện tại không có ca làm việc nào đang diễn ra."
                )

        except Exception as error:
            self._show_db_error("Không thể tải ca làm việc", error)
        finally:
            resume_table_sorting(self.employee_shift_table)
            cursor.close()

    def update_employee_shift_actions(self):
        """Cập nhật nút đăng ký và chốt tiền theo ca đang được chọn."""
        row = self.employee_shift_table.currentRow()
        item = self.employee_shift_table.item(row, 0) if row >= 0 else None
        if item is None:
            self.register_shift_button.setEnabled(False)
            self.closing_cash_button.setEnabled(False)
            self.shift_action_hint.setText(
                "Chọn một ca để đăng ký hoặc ghi tiền cuối ca nếu bạn có quyền."
            )
            return

        shift_id = int(item.data(Qt.ItemDataRole.UserRole))
        is_registered = bool(item.data(Qt.ItemDataRole.UserRole + 1))
        has_closing_cash = bool(item.data(Qt.ItemDataRole.UserRole + 2))
        is_ended = bool(item.data(Qt.ItemDataRole.UserRole + 3))

        if is_ended:
            register_text = "Ca đã kết thúc"
        elif is_registered:
            register_text = "Đã đăng ký"
        elif has_closing_cash:
            register_text = "Ca đã chốt"
        else:
            register_text = "Đăng ký ca hiện tại"
        self.register_shift_button.setText(register_text)
        self.register_shift_button.setEnabled(
            not is_ended and not is_registered and not has_closing_cash
        )

        if has_closing_cash:
            cash_text = "Đã ghi tiền cuối ca"
        elif not self.is_accountant:
            cash_text = "Kế toán ghi tiền"
        elif not is_ended:
            cash_text = "Chờ ca kết thúc"
        else:
            cash_text = "Ghi tiền cuối ca"
        self.closing_cash_button.setText(cash_text)
        self.closing_cash_button.setEnabled(
            self.is_accountant and is_ended and not has_closing_cash
        )
        self.shift_action_hint.setText(
            f"Đang chọn ca {shift_id}. Các thao tác bên phải sẽ áp dụng cho ca này."
        )

    def register_selected_shift(self):
        """Đăng ký ca đang chọn; điều kiện nghiệp vụ vẫn được kiểm tra ở SQL Server."""
        row = self.employee_shift_table.currentRow()
        item = self.employee_shift_table.item(row, 0) if row >= 0 else None
        if item is not None:
            self._register_current_shift(int(item.data(Qt.ItemDataRole.UserRole)))

    def record_selected_closing_cash(self):
        """Ghi tiền cuối ca cho ca đang chọn."""
        row = self.employee_shift_table.currentRow()
        item = self.employee_shift_table.item(row, 0) if row >= 0 else None
        if item is not None:
            self._record_closing_cash(int(item.data(Qt.ItemDataRole.UserRole)))

    def _register_current_shift(self, maca):
        """Đăng ký nhân viên vào ca đang diễn ra sau khi kiểm tra điều kiện."""
        answer = QMessageBox.question(
            self,
            "Xác nhận đăng ký ca",
            "Bạn có chắc muốn đăng ký ca đang diễn ra này?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối database!")
            return

        cursor = conn.cursor()
        try:
            # Chỉ 2 tham số: MACA và MANV. Dùng biến SQL để tái sử dụng.
            sql = """
                SET XACT_ABORT ON;
                DECLARE @Maca INT = ?;
                DECLARE @Manv VARCHAR(20) = ?;
                DECLARE @Now DATETIME2 = SYSDATETIME();
                DECLARE @WorkDate DATE;
                DECLARE @StartTime TIME;
                DECLARE @EndTime TIME;
                DECLARE @StartAt DATETIME2;
                DECLARE @EndAt DATETIME2;
                DECLARE @ClosingCash DECIMAL(15,2);

                IF LOWER(ORIGINAL_LOGIN()) <> LOWER(@Manv)
                    THROW 51100, N'Tài khoản SQL Server không khớp với mã nhân viên.', 1;

                SELECT
                    @WorkDate = CAST(NGAYLAM AS DATE),
                    @StartTime = TGMO,
                    @EndTime = TGDONG,
                    @ClosingCash = TMCUOICA
                FROM dbo.CA_LAM_VIEC WITH (UPDLOCK, HOLDLOCK)
                WHERE MACA = @Maca;

                IF @WorkDate IS NULL OR @StartTime IS NULL OR @EndTime IS NULL
                    THROW 51101, N'Không tìm thấy ca hoặc ca chưa được cấu hình giờ làm.', 1;

                SET @StartAt = DATEADD(
                    SECOND,
                    DATEDIFF(SECOND, CAST('00:00:00' AS TIME), @StartTime),
                    CAST(@WorkDate AS DATETIME2)
                );

                SET @EndAt = DATEADD(
                    SECOND,
                    DATEDIFF(SECOND, CAST('00:00:00' AS TIME), @EndTime),
                    DATEADD(
                        DAY,
                        CASE WHEN @EndTime <= @StartTime THEN 1 ELSE 0 END,
                        CAST(@WorkDate AS DATETIME2)
                    )
                );

                IF NOT (@Now >= @StartAt AND @Now < @EndAt)
                    THROW 51102, N'Chỉ được đăng ký ca đang diễn ra tại thời điểm hiện tại.', 1;

                IF @ClosingCash IS NOT NULL
                    THROW 51103, N'Ca này đã được chốt, không thể đăng ký thêm.', 1;

                IF EXISTS (
                    SELECT 1
                    FROM dbo.LAMCA
                    WHERE MANV = @Manv AND MACA = @Maca
                )
                    THROW 51104, N'Bạn đã đăng ký ca này rồi.', 1;

                IF EXISTS (
                    SELECT 1
                    FROM dbo.LAMCA L
                    INNER JOIN dbo.CA_LAM_VIEC C ON C.MACA = L.MACA
                    CROSS APPLY (
                        SELECT
                            DATEADD(
                                SECOND,
                                DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGMO),
                                CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                            ) AS ExistingStartAt,
                            DATEADD(
                                SECOND,
                                DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGDONG),
                                DATEADD(
                                    DAY,
                                    CASE WHEN C.TGDONG <= C.TGMO THEN 1 ELSE 0 END,
                                    CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                                )
                            ) AS ExistingEndAt
                    ) ExistingShift
                    WHERE L.MANV = @Manv
                      AND C.MACA <> @Maca
                      AND C.TGMO IS NOT NULL
                      AND C.TGDONG IS NOT NULL
                      AND @StartAt < ExistingShift.ExistingEndAt
                      AND @EndAt > ExistingShift.ExistingStartAt
                )
                    THROW 51105, N'Ca này bị trùng thời gian với ca bạn đã đăng ký.', 1;

                INSERT INTO dbo.LAMCA (MANV, MACA)
                VALUES (@Manv, @Maca);
            """
            cursor.execute(sql, (int(maca), self.username))
            conn.commit()
            QMessageBox.information(
                self, "Thành công", "Đăng ký ca làm việc hiện tại thành công."
            )
            self.refresh_employee_view()

        except Exception as error:
            conn.rollback()
            message = str(error)
            if "permission" in message.lower() or "denied" in message.lower():
                message += (
                    "\n\nTài khoản SQL Server hiện tại chưa có quyền đọc "
                    "CA_LAM_VIEC/LAMCA hoặc thêm bản ghi vào LAMCA."
                )
            self._show_db_error("Không thể đăng ký ca", message)
        finally:
            cursor.close()

    def _record_closing_cash(self, maca):
        """Kế toán được ghi tiền bất cứ lúc nào sau khi ca kết thúc, chỉ một lần."""
        if not self.is_accountant:
            QMessageBox.warning(
                self, "Không có quyền",
                "Chỉ nhân viên có vai trò Kế toán được ghi tiền mặt cuối ca."
            )
            return

        amount_text, ok = QInputDialog.getText(
            self,
            "Ghi tiền mặt cuối ca",
            "Nhập tổng tiền mặt cuối ca của cả ca (VNĐ):"
        )
        if not ok:
            return

        try:
            amount_text = amount_text.strip().replace(",", "").replace(" ", "")
            if not amount_text:
                raise ValueError("Vui lòng nhập tiền mặt cuối ca.")
            closing_cash = Decimal(amount_text)
            if not closing_cash.is_finite() or closing_cash < 0:
                raise ValueError("Tiền mặt cuối ca phải là số không âm.")
            if closing_cash > Decimal("9999999999999.99"):
                raise ValueError("Số tiền vượt quá giới hạn DECIMAL(15,2).")
            closing_cash = closing_cash.quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError) as error:
            QMessageBox.warning(self, "Số tiền không hợp lệ", str(error))
            return

        answer = QMessageBox.question(
            self,
            "Xác nhận ghi tiền cuối ca",
            f"Xác nhận ghi tiền mặt cuối ca {maca} với số tiền {closing_cash:,.2f} VNĐ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối database!")
            return

        cursor = conn.cursor()
        try:
            # 3 dấu ? và đúng 3 tham số: MACA, MANV, số tiền.
            # UPDLOCK/HOLDLOCK khóa dòng trong lúc kiểm tra và cập nhật.
            sql = """
                SET XACT_ABORT ON;
                DECLARE @Maca INT = ?;
                DECLARE @Manv VARCHAR(20) = ?;
                DECLARE @Cash DECIMAL(15,2) = ?;
                DECLARE @Now DATETIME2 = SYSDATETIME();
                DECLARE @WorkDate DATE;
                DECLARE @StartTime TIME;
                DECLARE @EndTime TIME;
                DECLARE @EndAt DATETIME2;
                DECLARE @ExistingCash DECIMAL(15,2);

                IF LOWER(ORIGINAL_LOGIN()) <> LOWER(@Manv)
                    THROW 51200, N'Tài khoản SQL Server không khớp với nhân viên kế toán.', 1;

                IF NOT EXISTS (
                    SELECT 1
                    FROM dbo.NHAN_VIEN
                    WHERE MANV = @Manv
                      AND LTRIM(RTRIM(VAITRO)) = N'Kế toán'
                )
                    THROW 51201, N'Chỉ nhân viên có vai trò Kế toán được ghi tiền cuối ca.', 1;

                SELECT
                    @WorkDate = CAST(NGAYLAM AS DATE),
                    @StartTime = TGMO,
                    @EndTime = TGDONG,
                    @ExistingCash = TMCUOICA
                FROM dbo.CA_LAM_VIEC WITH (UPDLOCK, HOLDLOCK)
                WHERE MACA = @Maca;

                IF @WorkDate IS NULL OR @EndTime IS NULL OR @StartTime IS NULL
                    THROW 51202, N'Không tìm thấy ca hoặc ca chưa có giờ làm hợp lệ.', 1;

                SET @EndAt = DATEADD(
                    SECOND,
                    DATEDIFF(SECOND, CAST('00:00:00' AS TIME), @EndTime),
                    DATEADD(
                        DAY,
                        CASE WHEN @EndTime <= @StartTime THEN 1 ELSE 0 END,
                        CAST(@WorkDate AS DATETIME2)
                    )
                );

                IF @Now < @EndAt
                    THROW 51203, N'Chỉ được ghi tiền sau khi ca đã kết thúc.', 1;

                IF @ExistingCash IS NOT NULL
                    THROW 51204, N'Tiền cuối ca đã được ghi trước đó. Mỗi ca chỉ được ghi một lần.', 1;

                UPDATE dbo.CA_LAM_VIEC
                SET TMCUOICA = @Cash
                WHERE MACA = @Maca
                  AND TMCUOICA IS NULL;

                IF @@ROWCOUNT <> 1
                    THROW 51205, N'Không thể ghi tiền. Có thể ca đã được chốt bởi kế toán khác.', 1;
            """
            cursor.execute(sql, (int(maca), self.username, closing_cash))
            conn.commit()
            QMessageBox.information(
                self,
                "Ghi tiền cuối ca thành công",
                "Đã ghi tiền mặt cuối ca. Mỗi ca chỉ được ghi một lần."
            )
            self.refresh_employee_view()

        except Exception as error:
            conn.rollback()
            message = str(error)
            if "permission" in message.lower() or "denied" in message.lower():
                message += (
                    "\n\nTài khoản Kế toán cần quyền SELECT trên các bảng liên quan "
                    "và UPDATE cột TMCUOICA của dbo.CA_LAM_VIEC."
                )
            self._show_db_error("Không thể ghi tiền cuối ca", message)
        finally:
            cursor.close()

    # ---------------------------------------------------------
    # MANAGER UI
    # ---------------------------------------------------------
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
        current_layout = QVBoxLayout(current_group)
        self.current_table = self._make_table(
            ["Mã ca", "Ngày làm", "Ca", "Giờ mở", "Giờ đóng", "Số nhân viên", "Tiền cuối ca"],
            stretch_column=2,
            default_sort_column=2
        )
        self.current_table.setMaximumHeight(190)
        self.current_table.cellClicked.connect(self._current_shift_selected)
        current_layout.addWidget(self.current_table)
        root.addWidget(current_group)

        history_group = QGroupBox("Lịch làm việc và lịch sử ca")
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
        self.history_table.setMaximumHeight(250)
        self.history_table.cellClicked.connect(self._history_shift_selected)
        history_layout.addWidget(self.history_table)
        root.addWidget(history_group)

        roster_group = QGroupBox("Nhân viên thuộc ca được chọn")
        roster_layout = QVBoxLayout(roster_group)
        self.selected_shift_label = QLabel("Chọn một ca để xem danh sách nhân viên.")
        roster_layout.addWidget(self.selected_shift_label)
        self.roster_table = self._make_table(
            ["Mã nhân viên", "Họ tên", "Vai trò", "Số điện thoại"],
            stretch_column=1
        )
        self.roster_table.setMaximumHeight(180)
        roster_layout.addWidget(self.roster_table)
        root.addWidget(roster_group)

    def add_shift(self):
        """Tạo ca mới theo một trong các khung giờ cố định trong ngày."""
        if not self.is_manager:
            QMessageBox.warning(self, "Không có quyền", "Chỉ Quản lý/Admin mới được thêm ca.")
            return

        dialog = ShiftCreateDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            values = dialog.get_values()
        except ValueError as error:
            QMessageBox.warning(self, "Thông tin chưa hợp lệ", str(error))
            return

        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối database!")
            return

        cursor = conn.cursor()
        try:
            # Chỉ có 3 ca cố định; kiểm tra ca đã tồn tại cùng ngày.
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM dbo.CA_LAM_VIEC
                WHERE CONVERT(date, NGAYLAM) = ? AND SOCA = ?
                """,
                (values["ngaylam"], values["soca"])
            )
            if int(cursor.fetchone()[0]) > 0:
                raise ValueError(
                    f"Ca {values['soca']} đã tồn tại trong ngày {dialog.work_date.date().toString('dd/MM/yyyy')}."
                )

            cursor.execute(
                """
                INSERT INTO dbo.CA_LAM_VIEC
                    (SOCA, TGMO, TGDONG, NGAYLAM, TMDAUCA, TMCUOICA)
                OUTPUT INSERTED.MACA
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    values["soca"], values["tgmo"], values["tgdong"],
                    values["ngaylam"], values["tmdauca"], values["tmcuoica"]
                )
            )
            inserted = cursor.fetchone()
            maca = inserted[0] if inserted else None
            conn.commit()

            QMessageBox.information(
                self, "Thành công", f"Đã tạo ca làm việc thành công.\nMã ca: {maca}"
            )
            self.refresh_manager_view()

        except ValueError as error:
            conn.rollback()
            QMessageBox.warning(self, "Không thể tạo ca", str(error))
        except Exception as error:
            conn.rollback()
            message = str(error)
            if "permission" in message.lower() or "denied" in message.lower():
                message += "\n\nTài khoản hiện tại chưa có quyền INSERT trên dbo.CA_LAM_VIEC."
            self._show_db_error("Không thể tạo ca làm việc", message)
        finally:
            cursor.close()

    def refresh_manager_view(self):
        """Làm mới các bảng ca hiện tại, lịch sử và danh sách nhân viên."""
        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối database!")
            return

        cursor = conn.cursor()
        try:
            cursor.execute("SELECT SYSDATETIME()")
            server_now = cursor.fetchone()[0]
            self.manager_server_time_label.setText(
                "Giờ SQL Server: " + server_now.strftime("%d/%m/%Y %H:%M:%S")
            )

            cursor.execute("""
                SELECT
                    COUNT(DISTINCT C.MACA) AS ActiveShifts,
                    COUNT(DISTINCT L.MANV) AS ActiveEmployees
                FROM dbo.CA_LAM_VIEC C
                CROSS APPLY (
                    SELECT
                        DATEADD(
                            SECOND,
                            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGMO),
                            CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                        ) AS StartAt,
                        DATEADD(
                            SECOND,
                            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGDONG),
                            DATEADD(
                                DAY, CASE WHEN C.TGDONG <= C.TGMO THEN 1 ELSE 0 END,
                                CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                            )
                        ) AS EndAt
                ) T
                LEFT JOIN dbo.LAMCA L ON L.MACA = C.MACA
                WHERE SYSDATETIME() >= T.StartAt
                  AND SYSDATETIME() < T.EndAt;
            """)
            active = cursor.fetchone()
            self.active_shift_stat.setText(f"Ca đang diễn ra: {active[0] or 0}")
            self.active_employee_stat.setText(f"Nhân viên đang làm: {active[1] or 0}")

            cursor.execute("""
                SELECT COUNT(*)
                FROM dbo.CA_LAM_VIEC
                WHERE NGAYLAM >= CONVERT(date, SYSDATETIME())
                  AND NGAYLAM < DATEADD(day, 1, CONVERT(date, SYSDATETIME()));
            """)
            self.today_shift_stat.setText(f"Ca trong ngày: {cursor.fetchone()[0] or 0}")

        except Exception as error:
            self._show_db_error("Không thể tải tổng quan ca làm", error)
            return
        finally:
            cursor.close()

        self.load_current_shifts()
        self.load_shift_history()

    def load_current_shifts(self):
        """Tải các ca hiện tại và trạng thái hoạt động của từng ca."""
        conn = self.db.get_connection()
        if conn is None:
            return
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    C.MACA,
                    C.NGAYLAM,
                    C.SOCA,
                    C.TGMO,
                    C.TGDONG,
                    COUNT(DISTINCT L.MANV) AS EmployeeCount,
                    C.TMCUOICA
                FROM dbo.CA_LAM_VIEC C
                CROSS APPLY (
                    SELECT
                        DATEADD(
                            SECOND,
                            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGMO),
                            CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                        ) AS StartAt,
                        DATEADD(
                            SECOND,
                            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGDONG),
                            DATEADD(
                                DAY, CASE WHEN C.TGDONG <= C.TGMO THEN 1 ELSE 0 END,
                                CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                            )
                        ) AS EndAt
                ) T
                LEFT JOIN dbo.LAMCA L ON L.MACA = C.MACA
                WHERE SYSDATETIME() >= T.StartAt
                  AND SYSDATETIME() < T.EndAt
                GROUP BY C.MACA, C.NGAYLAM, C.SOCA, C.TGMO, C.TGDONG, C.TMCUOICA
                ORDER BY C.SOCA;
            """)
            rows = cursor.fetchall()

            pause_table_sorting(self.current_table)

            self.current_table.setRowCount(0)
            for row_index, shift in enumerate(rows):
                self.current_table.insertRow(row_index)
                values = [
                    shift[0], self._format_date(shift[1]), shift[2],
                    self._format_time(shift[3]), self._format_time(shift[4]),
                    shift[5], self._format_cash(shift[6])
                ]
                for col, value in enumerate(values):
                    self._set_item(
                        self.current_table, row_index, col, value,
                        user_data=int(shift[0]) if col == 0 else None
                    )

            if rows:
                self.current_table.selectRow(0)
                self.load_roster(int(rows[0][0]), f"Ca {rows[0][2]}")
            else:
                self.roster_table.setRowCount(0)
                self.selected_shift_label.setText("Hiện không có ca nào đang diễn ra.")
        except Exception as error:
            self._show_db_error("Không thể tải các ca đang diễn ra", error)
        finally:
            cursor.close()

    def load_shift_history(self, *_):
        """Tải lịch sử ca làm việc theo bộ lọc thời gian."""
        conn = self.db.get_connection()
        if conn is None:
            return
        cursor = conn.cursor()
        period = self.history_filter.currentData()
        try:
            sql = """
                DECLARE @Period VARCHAR(10) = ?;

                SELECT
                    C.MACA,
                    C.NGAYLAM,
                    C.SOCA,
                    C.TGMO,
                    C.TGDONG,
                    COUNT(DISTINCT L.MANV) AS EmployeeCount,
                    C.TMDAUCA,
                    C.TMCUOICA,
                    CASE
                        WHEN SYSDATETIME() >= T.StartAt AND SYSDATETIME() < T.EndAt
                            THEN N'Đang diễn ra'
                        WHEN SYSDATETIME() < T.StartAt
                            THEN N'Sắp bắt đầu'
                        ELSE N'Đã kết thúc'
                    END AS ShiftStatus
                FROM dbo.CA_LAM_VIEC C
                CROSS APPLY (
                    SELECT
                        DATEADD(
                            SECOND,
                            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGMO),
                            CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                        ) AS StartAt,
                        DATEADD(
                            SECOND,
                            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGDONG),
                            DATEADD(
                                DAY, CASE WHEN C.TGDONG <= C.TGMO THEN 1 ELSE 0 END,
                                CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                            )
                        ) AS EndAt
                ) T
                LEFT JOIN dbo.LAMCA L ON L.MACA = C.MACA
                WHERE
                    @Period = 'all'
                    OR (
                        @Period = 'today'
                        AND C.NGAYLAM >= CONVERT(date, SYSDATETIME())
                        AND C.NGAYLAM < DATEADD(day, 1, CONVERT(date, SYSDATETIME()))
                    )
                    OR (
                        @Period = '7days'
                        AND C.NGAYLAM >= DATEADD(day, -6, CONVERT(date, SYSDATETIME()))
                        AND C.NGAYLAM < DATEADD(day, 1, CONVERT(date, SYSDATETIME()))
                    )
                    OR (
                        @Period = '30days'
                        AND C.NGAYLAM >= DATEADD(day, -29, CONVERT(date, SYSDATETIME()))
                        AND C.NGAYLAM < DATEADD(day, 1, CONVERT(date, SYSDATETIME()))
                    )
                GROUP BY C.MACA, C.NGAYLAM, C.SOCA, C.TGMO, C.TGDONG,
                         C.TMDAUCA, C.TMCUOICA, T.StartAt, T.EndAt
                ORDER BY C.NGAYLAM DESC, C.SOCA DESC;
            """
            # Chỉ có 1 dấu ? trong SQL: @Period.
            cursor.execute(sql, (period,))
            rows = cursor.fetchall()
            pause_table_sorting(self.history_table)
            self.history_table.setRowCount(0)
            for row_index, shift in enumerate(rows):
                self.history_table.insertRow(row_index)
                values = [
                    shift[0], self._format_date(shift[1]), shift[2],
                    self._format_time(shift[3]), self._format_time(shift[4]),
                    shift[5], self._format_cash(shift[6]),
                    self._format_cash(shift[7]), shift[8]
                ]
                for col, value in enumerate(values):
                    self._set_item(
                        self.history_table, row_index, col, value,
                        user_data=int(shift[0]) if col == 0 else None
                    )
        except Exception as error:
            self._show_db_error("Không thể tải lịch sử ca", error)
        finally:
            resume_table_sorting(self.history_table)
            cursor.close()

    def _current_shift_selected(self, row, column):
        """Lấy mã ca hiện đang được chọn trong bảng ca hiện tại."""
        item = self.current_table.item(row, 0)
        if item is not None:
            maca = item.data(Qt.ItemDataRole.UserRole)
            self.load_roster(int(maca), f"Ca {self.current_table.item(row, 2).text()}")

    def _history_shift_selected(self, row, column):
        """Lấy mã ca được chọn trong bảng lịch sử."""
        item = self.history_table.item(row, 0)
        if item is not None:
            maca = item.data(Qt.ItemDataRole.UserRole)
            self.load_roster(int(maca), f"Ca {self.history_table.item(row, 2).text()}")

    def load_roster(self, maca, shift_description=""):
        """Tải danh sách nhân viên đã đăng ký vào ca được chọn."""
        conn = self.db.get_connection()
        if conn is None:
            return
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT NV.MANV, NV.TENNV, NV.VAITRO, NV.SDT
                FROM dbo.LAMCA LC
                INNER JOIN dbo.NHAN_VIEN NV ON NV.MANV = LC.MANV
                WHERE LC.MACA = ?
                ORDER BY NV.MANV;
                """,
                (int(maca),)
            )
            rows = cursor.fetchall()
            pause_table_sorting(self.roster_table)
            self.roster_table.setRowCount(0)
            for row_index, employee in enumerate(rows):
                self.roster_table.insertRow(row_index)
                for col, value in enumerate(employee):
                    self._set_item(self.roster_table, row_index, col, value)
            self.selected_shift_label.setText(
                f"{shift_description} | Mã ca: {maca} | Số nhân viên: {len(rows)}"
            )
        except Exception as error:
            self._show_db_error("Không thể tải danh sách nhân viên trong ca", error)
        finally:
            resume_table_sorting(self.roster_table)
            cursor.close()


