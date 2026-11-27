"""Hộp thoại lập phiếu đổi trả."""

from decimal import Decimal, ROUND_HALF_UP

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFormLayout, QGroupBox, QComboBox, QCompleter, QLineEdit, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox,
)

from .dung_chung import MONEY_QUANT, as_decimal, date_text, money
from ui.permissions import is_admin_account


class CreateReturnDialog(QDialog):
    """Lập phiếu hoàn tiền hoặc đổi sản phẩm từ một hóa đơn hợp lệ."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.username = (getattr(db, "username", "") or "").strip()
        self.is_admin = is_admin_account(self.username)
        self.employee_code = None if self.is_admin else self.username
        self.row_controls = {}
        self.invoice_discount = Decimal("0.00")

        self.setWindowTitle("Lập phiếu đổi trả")
        self.resize(1120, 720)
        self.setMinimumSize(980, 620)
        self._ensure_manager()
        self._build_ui()
        self._load_eligible_invoices()

    def _ensure_manager(self, cursor=None):
        """Cho phép admin hoặc kiểm tra cả SQL role và hồ sơ của Quản lý."""
        own_cursor = cursor is None
        conn = self.db.get_connection()
        if conn is None:
            raise RuntimeError("Chưa có kết nối SQL Server.")
        cursor = cursor or conn.cursor()
        try:
            if self.is_admin:
                # Tài khoản hệ thống có thể không có hồ sơ NHAN_VIEN.
                cursor.execute(
                    "SELECT MANV FROM dbo.NHAN_VIEN WHERE MANV = ?",
                    self.username,
                )
                employee = cursor.fetchone()
                self.employee_code = employee[0] if employee else None
                return

            cursor.execute("""
                SELECT CASE
                    WHEN IS_ROLEMEMBER(N'rl_QuanLy') = 1
                     AND EXISTS (
                         SELECT 1 FROM dbo.NHAN_VIEN
                         WHERE MANV = ? AND VAITRO = N'Quản lý'
                     )
                    THEN 1 ELSE 0
                END
            """, self.username)
            row = cursor.fetchone()
            if row is None or int(row[0] or 0) != 1:
                raise PermissionError(
                    "Chỉ tài khoản thuộc vai trò Quản lý được xử lý đổi trả."
                )
        finally:
            if own_cursor:
                cursor.close()

    def _build_ui(self):
        """Tạo giao diện chọn hóa đơn, sản phẩm và hình thức xử lý."""
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        title = QLabel("LẬP PHIẾU ĐỔI TRẢ")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        root.addWidget(title)

        invoice_group = QGroupBox("Hóa đơn gốc")
        invoice_form = QFormLayout(invoice_group)
        self.invoice_combo = QComboBox()
        self.invoice_combo.setEditable(True)
        self.invoice_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.invoice_combo.setMaxVisibleItems(15)
        self.invoice_combo.lineEdit().setPlaceholderText(
            "Nhập mã hóa đơn để tìm..."
        )
        self.invoice_combo.setToolTip(
            "Nhập mã hóa đơn hoặc một phần mã để tìm trong các hóa đơn hợp lệ."
        )
        completer = self.invoice_combo.completer()
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.invoice_combo.currentIndexChanged.connect(self.load_invoice_items)
        self.invoice_combo.lineEdit().editingFinished.connect(
            self._select_typed_invoice
        )
        self.invoice_info = QLabel("Chọn hóa đơn trong ngày để xem sản phẩm.")
        self.invoice_info.setWordWrap(True)
        invoice_form.addRow("Mã hóa đơn:", self.invoice_combo)
        invoice_form.addRow("Thông tin:", self.invoice_info)
        root.addWidget(invoice_group)

        reason_group = QGroupBox("Thông tin xử lý")
        reason_form = QFormLayout(reason_group)
        self.reason_input = QLineEdit()
        self.reason_input.setMaxLength(255)
        self.reason_input.setPlaceholderText("Nhập lý do khách yêu cầu đổi hoặc trả...")
        reason_form.addRow("Lý do:", self.reason_input)
        root.addWidget(reason_group)

        items_group = QGroupBox("Sản phẩm trong hóa đơn")
        items_layout = QVBoxLayout(items_group)
        hint = QLabel(
            "Hàng nguyên vẹn chỉ được hoàn tiền. Đổi sản phẩm chỉ áp dụng "
            "với hàng đã hỏng và đổi đúng sản phẩm cùng mã."
        )
        hint.setWordWrap(True)
        items_layout.addWidget(hint)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "Mã SP", "Tên sản phẩm", "Đã mua", "Đã xử lý",
            "Còn được xử lý", "Số lượng", "Tình trạng hàng",
            "Hình thức xử lý", "Tiền hoàn"
        ])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.table.setHorizontalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        # Dùng cùng cách co giãn cột như bảng giỏ hàng hóa đơn/phiếu nhập.
        # Các cột điều khiển được chừa riêng không gian cho nút và mũi tên.
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        # Giữ cột tên sản phẩm đủ rộng; khi thiếu chỗ, bảng cuộn ngang
        # thay vì co cột và cắt nội dung.
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 210)
        control_column_widths = {
            5: 116,  # Số lượng: chừa chỗ cho hai nút tăng/giảm
            6: 202,  # Tình trạng hàng: hiển thị đủ "Còn nguyên vẹn"
            7: 242,  # Hình thức xử lý: hiển thị đủ lựa chọn dài nhất
        }
        for column, width in control_column_widths.items():
            header.setSectionResizeMode(
                column, QHeaderView.ResizeMode.Fixed
            )
            self.table.setColumnWidth(column, width)

        items_layout.addWidget(self.table, 1)
        root.addWidget(items_group, 1)

        bottom = QHBoxLayout()
        self.total_label = QLabel("Tổng tiền hoàn: 0,00 đ")
        self.total_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #16A34A;"
        )
        bottom.addWidget(self.total_label)
        bottom.addStretch()
        self.save_button = QPushButton("Lưu phiếu đổi trả")
        self.save_button.setProperty("buttonRole", "primary")
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(self.save_return)
        close_button = QPushButton("Đóng")
        close_button.clicked.connect(self.reject)
        bottom.addWidget(self.save_button)
        bottom.addWidget(close_button)
        root.addLayout(bottom)

    @staticmethod
    def _find_invoice_index(invoice_combo, typed_text):
        """Tìm chỉ số hóa đơn từ mã hoặc nội dung đầy đủ người dùng đã nhập."""
        keyword = str(typed_text or "").strip().casefold()
        if not keyword:
            return -1

        for index in range(invoice_combo.count()):
            code = str(invoice_combo.itemData(index) or "").strip().casefold()
            label = invoice_combo.itemText(index).strip().casefold()
            if keyword == code or keyword == label:
                return index
        return -1

    def _select_typed_invoice(self):
        """Chọn hóa đơn khi người dùng nhập chính xác mã hoặc nội dung hóa đơn."""
        typed_text = self.invoice_combo.currentText().strip()
        index = self._find_invoice_index(self.invoice_combo, typed_text)
        if index >= 0:
            self.invoice_combo.setCurrentIndex(index)
            return

        self.invoice_combo.setCurrentIndex(-1)
        self.table.setRowCount(0)
        self.row_controls.clear()
        self.invoice_info.setText(
            "Không tìm thấy hóa đơn phù hợp. Hãy chọn một kết quả trong danh sách."
        )
        self.save_button.setEnabled(False)
        self.update_totals()

    @staticmethod
    def _parse_quantity_input(text):
        """Đọc số lượng từ ô nhập dạng chữ số; ô trống được xem là 0."""
        value = str(text or "").strip()
        if not value:
            return 0
        try:
            quantity = int(value)
        except (TypeError, ValueError):
            raise ValueError("Số lượng phải là số nguyên không âm.")
        if quantity < 0:
            raise ValueError("Số lượng phải là số nguyên không âm.")
        return quantity

    def _load_eligible_invoices(self):
        """Chỉ liệt kê hóa đơn có hiệu lực được lập trong ngày hiện tại."""
        cursor = self.db.get_connection().cursor()
        try:
            cursor.execute("""
                SELECT MAHD, NGAYLAP
                FROM dbo.HOA_DON
                WHERE ISNULL(TRANGTHAI, 0) = 1
                  AND NGAYLAP >= CONVERT(date, SYSDATETIME())
                  AND NGAYLAP < DATEADD(day, 1, CONVERT(date, SYSDATETIME()))
                ORDER BY NGAYLAP DESC, MAHD DESC
            """)
            rows = cursor.fetchall()
            self.invoice_combo.blockSignals(True)
            self.invoice_combo.clear()
            for row in rows:
                code = str(row[0])
                self.invoice_combo.addItem(f"{code} | {date_text(row[1])}", code)
            self.invoice_combo.blockSignals(False)

            if not rows:
                self.invoice_combo.addItem(
                    "Không có hóa đơn đủ điều kiện trong hôm nay", None
                )
                self.invoice_combo.setEnabled(False)
                self.save_button.setEnabled(False)
                self.invoice_info.setText(
                    "Chỉ được đổi trả trong cùng ngày lập hóa đơn. "
                    "Hiện không có hóa đơn hợp lệ."
                )
                return
            self.load_invoice_items()
        finally:
            cursor.close()

    def load_invoice_items(self, *_):
        """Tải số lượng đã mua, số lượng đã xử lý và lượng còn có thể đổi trả."""
        invoice_code = self.invoice_combo.currentData()
        self.table.setRowCount(0)
        self.row_controls.clear()
        if not invoice_code:
            self.update_totals()
            return

        cursor = self.db.get_connection().cursor()
        try:
            cursor.execute("""
                SELECT HD.NGAYLAP, ISNULL(KM.TYLEGIAM, 0)
                FROM dbo.HOA_DON HD
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.MAHD = ?
                  AND ISNULL(HD.TRANGTHAI, 0) = 1
                  AND CAST(HD.NGAYLAP AS date) = CAST(SYSDATETIME() AS date)
            """, invoice_code)
            header = cursor.fetchone()
            if header is None:
                self.invoice_info.setText("Hóa đơn không còn đủ điều kiện đổi trả.")
                self.save_button.setEnabled(False)
                return

            discount_rate = as_decimal(header[1])
            self.invoice_discount = discount_rate
            self.invoice_info.setText(
                f"Ngày lập: {date_text(header[0])} | "
                f"Giảm giá hóa đơn: {money(discount_rate)}%"
            )

            cursor.execute("""
                SELECT
                    CT.MASP,
                    COALESCE(SP.TENSP, N'(Sản phẩm không còn trong danh mục)'),
                    COALESCE(SP.DVT, N''),
                    COALESCE(CT.SOLUONG, 0),
                    COALESCE(R.DA_XU_LY, 0),
                    COALESCE(CT.DONGIA, 0),
                    COALESCE(CT.VAT, 0)
                FROM dbo.CHI_TIET_HOA_DON CT
                LEFT JOIN dbo.SAN_PHAM SP ON SP.MASP = CT.MASP
                OUTER APPLY (
                    SELECT SUM(COALESCE(CTDT.SOLUONG, 0)) AS DA_XU_LY
                    FROM dbo.PHIEU_DOI_TRA PDT
                    INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                    WHERE PDT.MAHD = CT.MAHD AND CTDT.MASP = CT.MASP
                ) R
                WHERE CT.MAHD = ?
                ORDER BY CT.MASP
            """, invoice_code)

            for data in cursor.fetchall():
                masp = str(data[0])
                purchased = int(data[3] or 0)
                processed = int(data[4] or 0)
                remaining = max(purchased - processed, 0)
                net_price = (
                    as_decimal(data[5]) * (Decimal("100") - discount_rate)
                    / Decimal("100")
                ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

                row = self.table.rowCount()
                self.table.insertRow(row)
                values = [
                    masp, str(data[1] or ""), purchased, processed,
                    remaining, "", "", "", money(0)
                ]
                for column, value in enumerate(values):
                    cell_item = QTableWidgetItem(str(value))
                    cell_item.setToolTip(str(value))
                    self.table.setItem(row, column, cell_item)

                # Giữ nguyên mẫu dùng trong hóa đơn và phiếu nhập:
                # tạo control với bảng làm parent, gắn trực tiếp vào cell,
                # chiều cao control 34 px và chiều cao dòng 44 px.
                quantity = QSpinBox(self.table)
                quantity.setRange(0, remaining)
                quantity.setValue(0)
                quantity.setMinimumHeight(34)
                quantity.setToolTip(
                    f"Chỉ nhập số nguyên từ 0 đến {remaining}. "
                    f"Đơn vị tính: {data[2] or 'Không xác định'}"
                )
                self.table.setCellWidget(row, 5, quantity)

                condition = QComboBox(self.table)
                condition.addItem("Còn nguyên vẹn", 1)
                condition.addItem("Đã hỏng", 0)
                condition.setMinimumHeight(34)
                condition.setMinimumContentsLength(14)
                condition.setSizeAdjustPolicy(
                    QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
                )
                condition.setToolTip("Chọn tình trạng thực tế của hàng khách trả.")
                self.table.setCellWidget(row, 6, condition)

                action = QComboBox(self.table)
                action.addItem("Hoàn tiền", 0)
                action.addItem("Đổi sản phẩm cùng mã", 1)
                action.setMinimumHeight(34)
                action.setMinimumContentsLength(22)
                action.setSizeAdjustPolicy(
                    QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
                )
                action.setToolTip(
                    "Chọn hoàn tiền hoặc đổi sản phẩm cùng mã. "
                    "Chỉ hàng đã hỏng mới được đổi."
                )
                self.table.setCellWidget(row, 7, action)

                # Bảng đổi trả có thêm ba cột điều khiển và stylesheet ô
                # có padding dọc; chừa thêm khoảng trống để nút không chạm mép.
                self.table.setRowHeight(row, 50)
                self.row_controls[masp] = {
                    "row": row,
                    "quantity": quantity,
                    "remaining": remaining,
                    "condition": condition,
                    "action": action,
                    "net_price": net_price,
                }
                quantity.valueChanged.connect(self.update_totals)
                condition.currentIndexChanged.connect(self.update_totals)
                action.currentIndexChanged.connect(self.update_totals)

            self.save_button.setEnabled(bool(self.row_controls))
            self.update_totals()
        finally:
            cursor.close()

    def update_totals(self, *_):
        """Tính tiền hoàn dự kiến; dòng đổi sản phẩm không hoàn tiền."""
        total = Decimal("0.00")
        for controls in self.row_controls.values():
            quantity = int(controls["quantity"].value())
            condition = controls["condition"].currentData()
            action = controls["action"].currentData()
            amount_item = self.table.item(controls["row"], 8)

            if quantity > 0 and action == 1 and condition != 0:
                amount_item.setText("Không hợp lệ")
                amount_item.setToolTip(
                    "Chỉ được đổi sản phẩm khi hàng khách trả đã hỏng."
                )
                continue

            amount = controls["net_price"] * quantity if action == 0 else Decimal("0")
            amount = amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            total += amount
            amount_item.setText(money(amount))
            amount_item.setToolTip(f"Tiền hoàn dự kiến: {money(amount)}")
        self.total_label.setText(f"Tổng tiền hoàn: {money(total)} đ")

    def save_return(self):
        """Ghi phiếu, chi tiết và biến động tồn kho trong cùng transaction."""
        invoice_code = self.invoice_combo.currentData()
        reason = self.reason_input.text().strip()
        if not invoice_code:
            QMessageBox.warning(self, "Thiếu hóa đơn", "Vui lòng chọn hóa đơn hợp lệ.")
            return
        if not reason:
            QMessageBox.warning(self, "Thiếu lý do", "Vui lòng nhập lý do đổi trả.")
            self.reason_input.setFocus()
            return

        selected = []
        for masp, controls in self.row_controls.items():
            try:
                quantity = int(controls["quantity"].value())
            except ValueError as error:
                QMessageBox.warning(self, "Số lượng không hợp lệ", str(error))
                controls["quantity"].setFocus()
                return
            if quantity > controls["remaining"]:
                QMessageBox.warning(
                    self, "Số lượng vượt giới hạn",
                    f"Sản phẩm {masp} chỉ còn {controls['remaining']} sản phẩm có thể xử lý."
                )
                controls["quantity"].setFocus()
                return
            if quantity <= 0:
                continue
            condition = int(controls["condition"].currentData())
            action = int(controls["action"].currentData())
            if action == 1 and condition != 0:
                QMessageBox.warning(
                    self, "Không hợp lệ",
                    f"Sản phẩm {masp}: chỉ được đổi sản phẩm khi hàng trả đã hỏng."
                )
                return
            selected.append((masp, quantity, condition, action))

        if not selected:
            QMessageBox.warning(
                self, "Chưa chọn sản phẩm", "Vui lòng chọn số lượng cần đổi hoặc trả."
            )
            return

        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối SQL Server.")
            return

        cursor = conn.cursor()
        try:
            self._ensure_manager(cursor)

            # Khóa hóa đơn để tuần tự hóa các phiếu và ngăn trả vượt số lượng đã mua.
            cursor.execute("""
                SELECT HD.NGAYLAP, HD.TRANGTHAI, ISNULL(KM.TYLEGIAM, 0)
                FROM dbo.HOA_DON HD WITH (UPDLOCK, HOLDLOCK)
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.MAHD = ?
            """, invoice_code)
            invoice = cursor.fetchone()
            if invoice is None or int(invoice[1] or 0) != 1:
                raise RuntimeError("Hóa đơn không tồn tại hoặc đã bị hủy.")

            cursor.execute("""
                SELECT CASE WHEN CAST(? AS date) = CAST(SYSDATETIME() AS date)
                            THEN 1 ELSE 0 END
            """, invoice[0])
            if int(cursor.fetchone()[0] or 0) != 1:
                raise RuntimeError("Chỉ được đổi trả trong cùng ngày lập hóa đơn.")

            discount_rate = as_decimal(invoice[2])
            verified_lines = []
            total_refund = Decimal("0.00")

            for masp, quantity, condition, action in selected:
                cursor.execute("""
                    SELECT COALESCE(SOLUONG, 0), COALESCE(DONGIA, 0), COALESCE(VAT, 0)
                    FROM dbo.CHI_TIET_HOA_DON WITH (UPDLOCK, HOLDLOCK)
                    WHERE MAHD = ? AND MASP = ?
                """, invoice_code, masp)
                sold_line = cursor.fetchone()
                if sold_line is None:
                    raise RuntimeError(f"Sản phẩm {masp} không thuộc hóa đơn gốc.")

                purchased = int(sold_line[0] or 0)
                original_price = as_decimal(sold_line[1])
                vat = as_decimal(sold_line[2])

                cursor.execute("""
                    SELECT COALESCE(SUM(CTDT.SOLUONG), 0)
                    FROM dbo.PHIEU_DOI_TRA PDT WITH (UPDLOCK, HOLDLOCK)
                    INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                    WHERE PDT.MAHD = ? AND CTDT.MASP = ?
                """, invoice_code, masp)
                processed = int(cursor.fetchone()[0] or 0)
                remaining = purchased - processed
                if quantity > remaining:
                    raise RuntimeError(
                        f"Sản phẩm {masp} chỉ còn {max(remaining, 0)} sản phẩm có thể xử lý."
                    )
                if action == 1 and condition != 0:
                    raise RuntimeError(
                        f"Sản phẩm {masp}: chỉ được đổi sản phẩm khi hàng trả đã hỏng."
                    )

                net_price = (
                    original_price * (Decimal("100") - discount_rate)
                    / Decimal("100")
                ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

                if action == 1:
                    # Khách đổi hàng hỏng lấy sản phẩm mới cùng mã: xuất hàng mới.
                    cursor.execute("""
                        UPDATE dbo.SAN_PHAM
                        SET SLTON = SLTON - ?
                        WHERE MASP = ?
                          AND ISNULL(IS_DELETED, 0) = 0
                          AND ISNULL(SLTON, 0) >= ?
                    """, quantity, masp, quantity)
                    if cursor.rowcount != 1:
                        raise RuntimeError(f"Sản phẩm {masp} không đủ tồn kho để đổi.")
                    refund_unit_price = Decimal("0.00")
                else:
                    # Chỉ hàng nguyên vẹn được nhập lại tồn kho bán được.
                    if condition == 1:
                        cursor.execute("""
                            UPDATE dbo.SAN_PHAM
                            SET SLTON = ISNULL(SLTON, 0) + ?
                            WHERE MASP = ?
                        """, quantity, masp)
                        if cursor.rowcount != 1:
                            raise RuntimeError(f"Không tìm thấy sản phẩm {masp}.")
                    refund_unit_price = net_price
                    total_refund += net_price * quantity

                verified_lines.append((
                    masp, quantity, refund_unit_price, vat, condition, action
                ))

            total_refund = total_refund.quantize(
                MONEY_QUANT, rounding=ROUND_HALF_UP
            )

            cursor.execute("""
                SELECT COALESCE(
                    MAX(TRY_CONVERT(BIGINT, SUBSTRING(MAPDT, 4, 18))), 0
                )
                FROM dbo.PHIEU_DOI_TRA WITH (TABLOCKX, HOLDLOCK)
                WHERE UPPER(LEFT(MAPDT, 3)) = 'PDT'
                  AND TRY_CONVERT(BIGINT, SUBSTRING(MAPDT, 4, 18)) IS NOT NULL
            """)
            return_code = f"PDT{int(cursor.fetchone()[0] or 0) + 1:06d}"

            cursor.execute("""
                INSERT INTO dbo.PHIEU_DOI_TRA
                    (MAPDT, NGAY_DOI_TRA, LY_DO, TONG_TIEN_HOAN, MAHD, MANV)
                VALUES (?, SYSDATETIME(), ?, ?, ?, ?)
            """, return_code, reason, total_refund, invoice_code, self.employee_code)

            for line in verified_lines:
                cursor.execute("""
                    INSERT INTO dbo.CHI_TIET_DOI_TRA
                        (MASP, MAPDT, SOLUONG, DONGIAHOAN, VAT,
                         TINHTRANGHANG, HINH_THUC_XU_LY)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, line[0], return_code, line[1], line[2], line[3], line[4], line[5])

            conn.commit()
            QMessageBox.information(
                self, "Thành công",
                f"Đã lập phiếu đổi trả {return_code}.\n"
                f"Hóa đơn: {invoice_code}\n"
                f"Tổng tiền hoàn: {money(total_refund)} đ"
            )
            self.accept()
        except Exception as error:
            conn.rollback()
            QMessageBox.critical(
                self, "Không thể lập phiếu đổi trả",
                f"{error}\n\nMọi thay đổi trong giao dịch đã được hoàn tác."
            )
        finally:
            cursor.close()
