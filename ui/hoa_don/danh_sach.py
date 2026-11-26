"""InvoiceWindow: thành phần giao diện nghiệp vụ hóa đơn."""

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
from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table,
    pause_table_sorting,
    resume_table_sorting,
)
from .dung_chung import money, date_text
from .tao_bieu_mau import CreateInvoiceDialog
from .chi_tiet import InvoiceDetailDialog


class InvoiceWindow(QWidget):
    """Trang danh sách hóa đơn, tìm kiếm, lập hóa đơn, xem chi tiết và xử lý hủy theo quyền."""

    @staticmethod
    def _assert_no_return_vouchers(has_return_vouchers):
        """Không cho hủy hóa đơn đã phát sinh đổi trả để tránh hoàn kho hai lần."""
        if has_return_vouchers:
            raise RuntimeError(
                "Không thể hủy hóa đơn đã phát sinh phiếu đổi trả. "
                "Hãy xử lý chứng từ đổi trả trước."
            )

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.username = (getattr(db, "username", "") or "").strip()
        self.employee_role = self._get_employee_role()
        self.can_create = (
            self.username.casefold() == "admin"
            or self.employee_role.casefold() in {"quản lý", "thu ngân"}
        )
        # Admin/Quản lý được hủy mọi hóa đơn; Thu ngân chỉ được hủy hóa đơn mình lập.
        self.is_admin = self.username.casefold() == "admin"
        self.is_manager = self.employee_role.casefold() == "quản lý"
        self.is_cashier = self.employee_role.casefold() == "thu ngân"
        self.can_cancel = self.is_admin or self.is_manager or self.is_cashier
        self._build_ui()
        self.load_invoices()

        # Tự kiểm tra lại quyền hủy định kỳ để nút tự khóa khi hết 5 phút.
        self._cancel_permission_timer = QTimer(self)
        self._cancel_permission_timer.setInterval(5000)
        self._cancel_permission_timer.timeout.connect(self.update_action_buttons)
        self._cancel_permission_timer.start()

    def _get_employee_role(self):
        """Lấy vai trò của nhân viên; Admin không cần hồ sơ trong NHAN_VIEN."""
        if self.username.casefold() == "admin":
            return ""
        conn = self.db.get_connection()
        if conn is None:
            return ""
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT VAITRO FROM dbo.NHAN_VIEN WHERE MANV = ?",
                self.username
            )
            row = cursor.fetchone()
            return (row[0] or "").strip() if row else ""
        finally:
            cursor.close()

    def _build_ui(self):
        """Tạo bộ lọc, bảng hóa đơn và các nút thao tác theo quyền."""
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("QUẢN LÝ HÓA ĐƠN")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        top.addWidget(title)
        top.addStretch()

        self.create_button = QPushButton("+ Tạo hóa đơn")
        self.create_button.setVisible(self.can_create)
        self.create_button.clicked.connect(self.open_create_invoice)
        top.addWidget(self.create_button)

        refresh_button = QPushButton("Làm mới")
        refresh_button.clicked.connect(self.load_invoices)
        top.addWidget(refresh_button)
        root.addLayout(top)

        # Bộ lọc tương tự trang Phiếu nhập: từ khóa + khoảng ngày.
        filters = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Tìm mã hóa đơn, nhân viên, ca, khuyến mãi hoặc sản phẩm..."
        )
        self.search_input.returnPressed.connect(self.load_invoices)

        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("dd/MM/yyyy")
        self.from_date.setDate(QDate.currentDate().addDays(-30))

        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("dd/MM/yyyy")
        self.to_date.setDate(QDate.currentDate())

        search_button = QPushButton("Tìm kiếm")
        search_button.clicked.connect(self.load_invoices)
        clear_button = QPushButton("Xóa lọc")
        clear_button.clicked.connect(self.clear_search)

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
            "Mã hóa đơn", "Ngày lập", "Nhân viên", "Mã ca",
            "Số ca", "Tổng thanh toán", "Tiền khách đưa", "Trạng thái"
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
        self.table.cellDoubleClicked.connect(self.open_invoice_detail)
        self.table.itemSelectionChanged.connect(self.update_action_buttons)
        root.addWidget(self.table, 1)

        self.total_label = QLabel("Tổng số hóa đơn: 0")
        root.addWidget(self.total_label)


    def clear_search(self):
        """Xóa từ khóa và đặt lại khoảng ngày mặc định như trang Phiếu nhập."""
        self.search_input.clear()
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.to_date.setDate(QDate.currentDate())
        self.load_invoices()

    def load_invoices(self):
        """Truy vấn hóa đơn theo bộ lọc và cập nhật dữ liệu trên bảng."""
        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(
                self, "Thông báo", "Chưa có kết nối database."
            )
            return

        if self.from_date.date() > self.to_date.date():
            QMessageBox.warning(
                self, "Khoảng ngày không hợp lệ",
                "Ngày bắt đầu không được lớn hơn ngày kết thúc."
            )
            return

        cursor = conn.cursor()
        keyword = self.search_input.text().strip()
        sql = """
            SELECT
                HD.MAHD, HD.NGAYLAP, HD.MANV, NV.TENNV,
                HD.MACA, C.SOCA, HD.TIENKHACHDUA,
                COALESCE(SUM(CT.DONGIA * CT.SOLUONG), 0)
                    * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0) AS TOTAL_AMOUNT,
                HD.TRANGTHAI
            FROM dbo.HOA_DON HD
            LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = HD.MANV
            LEFT JOIN dbo.CA_LAM_VIEC C ON C.MACA = HD.MACA
            LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
            LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
            WHERE HD.NGAYLAP >= ?
              AND HD.NGAYLAP < DATEADD(DAY, 1, CAST(? AS date))
        """
        params = [
            self.from_date.date().toString("yyyy-MM-dd"),
            self.to_date.date().toString("yyyy-MM-dd"),
        ]
        if keyword:
            like = f"%{keyword}%"
            sql += """ AND (
                HD.MAHD LIKE ?
                OR HD.MANV LIKE ?
                OR NV.TENNV LIKE ?
                OR CONVERT(NVARCHAR(20), HD.MACA) LIKE ?
                OR CONVERT(NVARCHAR(20), C.SOCA) LIKE ?
                OR KM.MAKM LIKE ?
                OR KM.TENKM LIKE ?
                OR EXISTS (
                    SELECT 1
                    FROM dbo.CHI_TIET_HOA_DON CT_SEARCH
                    INNER JOIN dbo.SAN_PHAM SP_SEARCH
                        ON SP_SEARCH.MASP = CT_SEARCH.MASP
                    WHERE CT_SEARCH.MAHD = HD.MAHD
                      AND (
                          CT_SEARCH.MASP LIKE ?
                          OR SP_SEARCH.TENSP LIKE ?
                      )
                )
            )"""
            params.extend([like] * 9)

        sql += """
            GROUP BY HD.MAHD, HD.NGAYLAP, HD.MANV, NV.TENNV,
                     HD.MACA, C.SOCA, HD.TIENKHACHDUA, HD.TRANGTHAI,
                     KM.TYLEGIAM
            ORDER BY HD.NGAYLAP DESC, HD.MAHD DESC
        """
        try:
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()

            pause_table_sorting(self.table)

            self.table.setRowCount(0)

            for i, row in enumerate(rows):
                self.table.insertRow(i)
                values = [
                    row[0],
                    date_text(row[1]),
                    f"{row[3] or ''} ({row[2] or ''})",
                    row[4],
                    row[5],
                    money(row[7]),
                    money(row[6]),
                    (
                        "Đã hủy" if row[8] == 0
                        else "Đã thanh toán" if row[8] == 1
                        else "Không xác định"
                    ),
                ]
                for col, value in enumerate(values):
                    cell_item = QTableWidgetItem(str(value or ""))
                    # Lưu MANV thật vào UserRole để kiểm tra chủ sở hữu hóa đơn.
                    # Không phân tích MANV từ chuỗi tên hiển thị vì tên có thể chứa ký tự đặc biệt.
                    if col == 0:
                        cell_item.setData(Qt.ItemDataRole.UserRole, str(row[2] or "").strip())
                    self.table.setItem(i, col, cell_item)
            self.total_label.setText(
                f"Tổng số hóa đơn: {len(rows)}"
            )
            self.update_action_buttons()
        except Exception as error:
            QMessageBox.critical(self, "Lỗi tải hóa đơn", str(error))
        finally:
            resume_table_sorting(self.table)
            cursor.close()

    def update_action_buttons(self):
        """Xác định quyền hủy hóa đơn đang chọn để truyền vào popup chi tiết."""
        row = self.table.currentRow()
        self._selected_can_cancel = False
        if not self.can_cancel or row < 0:
            return

        status_item = self.table.item(row, 7)
        invoice_item = self.table.item(row, 0)
        is_active = (
            status_item is not None
            and status_item.text() == "Đã thanh toán"
        )
        invoice_code = invoice_item.text().strip() if invoice_item else ""
        owner_code = (
            str(invoice_item.data(Qt.ItemDataRole.UserRole) or "").strip()
            if invoice_item is not None else ""
        )
        if not is_active or not invoice_code:
            return

        # Admin/Quản lý được hủy mọi hóa đơn còn hiệu lực.
        if self.is_admin or self.is_manager:
            self._selected_can_cancel = True
            return

        # Thu ngân chỉ được hủy hóa đơn của mình trong 5 phút đầu.
        if self.is_cashier and owner_code.casefold() == self.username.casefold():
            conn = self.db.get_connection()
            if conn is None:
                return
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT CASE
                        WHEN TRANGTHAI = 1
                         AND MANV = ?
                         AND NGAYLAP >= DATEADD(MINUTE, -5, SYSDATETIME())
                         AND NGAYLAP <= SYSDATETIME()
                        THEN 1 ELSE 0
                    END
                    FROM dbo.HOA_DON
                    WHERE MAHD = ?
                """, self.username, invoice_code)
                permission_row = cursor.fetchone()
                self._selected_can_cancel = bool(
                    permission_row and permission_row[0] == 1
                )
            except Exception:
                self._selected_can_cancel = False
            finally:
                cursor.close()

    def cancel_selected_invoice(self):
        """Hủy hóa đơn, hoàn kho và cập nhật trạng thái trong cùng transaction."""
        if not self.can_cancel:
            QMessageBox.warning(
                self, "Không có quyền",
                "Tài khoản của bạn không có quyền hủy hóa đơn."
            )
            return

        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(
                self, "Chưa chọn hóa đơn",
                "Vui lòng chọn hóa đơn cần hủy."
            )
            return

        invoice_item = self.table.item(row, 0)
        if invoice_item is None:
            return
        invoice_code = invoice_item.text().strip()
        owner_code = str(
            invoice_item.data(Qt.ItemDataRole.UserRole) or ""
        ).strip()
        if (
            self.is_cashier
            and not self.is_admin
            and not self.is_manager
            and owner_code.casefold() != self.username.casefold()
        ):
            QMessageBox.warning(
                self, "Không có quyền",
                "Thu ngân chỉ được hủy hóa đơn do chính mình lập."
            )
            return

        status_item = self.table.item(row, 7)
        if status_item is None or status_item.text() != "Đã thanh toán":
            QMessageBox.information(
                self, "Không thể hủy",
                "Hóa đơn này đã bị hủy hoặc không có trạng thái hợp lệ."
            )
            self.update_action_buttons()
            return

        answer = QMessageBox.question(
            self,
            "Xác nhận hủy hóa đơn",
            (
                f"Bạn có chắc chắn muốn hủy hóa đơn {invoice_code}?\n\n"
                "Toàn bộ số lượng sản phẩm trong hóa đơn sẽ được hoàn lại kho.\n"
                "Trạng thái hóa đơn sẽ chuyển thành 0 (Đã hủy).\n"
                "Thu ngân chỉ được hủy hóa đơn của mình trong 5 phút kể từ lúc lập.\n\n"
                "Thao tác này không thể thực hiện lần thứ hai cho cùng hóa đơn."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(
                self, "Thông báo", "Chưa có kết nối database."
            )
            return

        cursor = conn.cursor()
        try:
            # Khóa dòng hóa đơn để ngăn hai thao tác hủy chạy đồng thời.
            cursor.execute("""
                SELECT
                    TRANGTHAI,
                    MANV,
                    CASE
                        WHEN NGAYLAP >= DATEADD(MINUTE, -5, SYSDATETIME())
                         AND NGAYLAP <= SYSDATETIME()
                        THEN 1 ELSE 0
                    END AS WITHIN_FIVE_MINUTES
                FROM dbo.HOA_DON WITH (UPDLOCK, HOLDLOCK)
                WHERE MAHD = ?
            """, invoice_code)
            invoice = cursor.fetchone()
            if invoice is None:
                raise RuntimeError("Không tìm thấy hóa đơn cần hủy.")

            current_status = invoice[0]
            invoice_owner = str(invoice[1] or "").strip()
            if current_status is None or int(current_status) != 1:
                raise RuntimeError(
                    "Hóa đơn đã bị hủy hoặc không còn ở trạng thái có hiệu lực."
                )

            # Phiếu đổi trả cũng thay đổi tồn kho. Khóa hóa đơn ở trên khiến
            # thao tác tạo phiếu đổi trả và hủy hóa đơn được tuần tự hóa.
            cursor.execute("""
                SELECT TOP (1) MAPDT
                FROM dbo.PHIEU_DOI_TRA WITH (UPDLOCK, HOLDLOCK)
                WHERE MAHD = ?
            """, invoice_code)
            self._assert_no_return_vouchers(cursor.fetchone() is not None)

            # Kiểm tra lại chủ sở hữu từ SQL Server trong transaction, không chỉ dựa vào giao diện.
            if (
                self.is_cashier
                and not self.is_admin
                and not self.is_manager
            ):
                if invoice_owner.casefold() != self.username.casefold():
                    raise PermissionError(
                        "Thu ngân chỉ được hủy hóa đơn do chính mình lập."
                    )
                if int(invoice[2] or 0) != 1:
                    raise PermissionError(
                        "Thu ngân chỉ được hủy hóa đơn do mình tạo trong vòng 5 phút kể từ thời điểm lập."
                    )

            # Lấy tổng số lượng theo sản phẩm; giữ khóa chi tiết đến khi commit.
            cursor.execute("""
                SELECT MASP, SUM(ISNULL(SOLUONG, 0)) AS TONG_SOLUONG
                FROM dbo.CHI_TIET_HOA_DON WITH (UPDLOCK, HOLDLOCK)
                WHERE MAHD = ?
                GROUP BY MASP
            """, invoice_code)
            invoice_items = cursor.fetchall()
            if not invoice_items:
                raise RuntimeError(
                    "Hóa đơn không có chi tiết sản phẩm nên không thể hoàn kho."
                )

            # Hoàn lại cả sản phẩm đã xóa mềm; không lọc IS_DELETED ở đây.
            for item in invoice_items:
                product_code = item[0]
                quantity = int(item[1] or 0)
                if quantity <= 0:
                    raise RuntimeError(
                        f"Số lượng hoàn kho không hợp lệ cho sản phẩm {product_code}."
                    )

                cursor.execute("""
                    UPDATE dbo.SAN_PHAM
                    SET SLTON = ISNULL(SLTON, 0) + ?
                    WHERE MASP = ?
                """, quantity, product_code)

                if cursor.rowcount != 1:
                    raise RuntimeError(
                        f"Không tìm thấy sản phẩm {product_code}; toàn bộ thao tác hủy đã được hoàn tác."
                    )

            # Chỉ chuyển trạng thái sau khi hoàn kho thành công.
            cursor.execute("""
                UPDATE dbo.HOA_DON
                SET TRANGTHAI = 0
                WHERE MAHD = ? AND TRANGTHAI = 1
            """, invoice_code)

            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Không thể cập nhật trạng thái hóa đơn; thao tác hoàn kho đã được hoàn tác."
                )

            conn.commit()
            QMessageBox.information(
                self,
                "Hủy hóa đơn thành công",
                f"Đã hủy hóa đơn {invoice_code} và hoàn toàn bộ sản phẩm về kho."
            )
            self.load_invoices()

        except Exception as error:
            conn.rollback()
            QMessageBox.critical(
                self,
                "Không thể hủy hóa đơn",
                f"{error}\n\nKhông có thay đổi nào được lưu; tồn kho và trạng thái hóa đơn đã được hoàn tác."
            )
            self.load_invoices()
        finally:
            cursor.close()

    def open_selected_invoice(self):
        """Mở hóa đơn đang được chọn trong danh sách."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(
                self, "Thông báo", "Vui lòng chọn hóa đơn."
            )
            return
        item = self.table.item(row, 0)
        if item:
            self.open_invoice_detail(row, 0)

    def open_invoice_detail(self, row, column):
        """Hiển thị cửa sổ chi tiết hóa đơn và nội dung in."""
        item = self.table.item(row, 0)
        if item is None:
            return

        invoice_code = item.text()
        try:
            self.update_action_buttons()
            dialog = InvoiceDetailDialog(
                self.db,
                invoice_code,
                self,
                on_cancel=self.cancel_selected_invoice if self._selected_can_cancel else None,
            )
            dialog.exec()
            self.load_invoices()
        except Exception as error:
            QMessageBox.critical(
                self, "Lỗi xem hóa đơn", str(error)
            )

    def open_create_invoice(self):
        """Mở hộp thoại lập hóa đơn mới."""
        if not self.can_create:
            QMessageBox.warning(
                self, "Từ chối truy cập",
                "Tài khoản không có quyền lập hóa đơn."
            )
            return

        try:
            dialog = CreateInvoiceDialog(self.db, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_invoices()
                if dialog.saved_invoice_code:
                    ask = QMessageBox.question(
                        self,
                        "In hóa đơn",
                        f"Đã tạo hóa đơn {dialog.saved_invoice_code}. "
                        "Bạn có muốn in ngay không?",
                        QMessageBox.StandardButton.Yes |
                        QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )
                    if ask == QMessageBox.StandardButton.Yes:
                        try:
                            detail = InvoiceDetailDialog(
                                self.db, dialog.saved_invoice_code, self
                            )
                            detail.print_invoice()
                        except Exception as error:
                            QMessageBox.critical(
                                self, "Lỗi in hóa đơn", str(error)
                            )
        except Exception as error:
            QMessageBox.critical(
                self, "Không thể lập hóa đơn", str(error)
            )




