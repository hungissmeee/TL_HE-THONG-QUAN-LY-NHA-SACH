from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html import escape

from PySide6.QtCore import Qt, QDateTime, QTimer, QSizeF, QMarginsF
from PySide6.QtGui import QTextDocument, QPageSize, QPageLayout
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtWidgets import (
    QWidget, QDialog, QLabel, QPushButton, QLineEdit, QComboBox,
    QVBoxLayout, QHBoxLayout, QFormLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox,
    QSpinBox, QGroupBox, QDoubleSpinBox
)


MONEY_QUANT = Decimal("0.01")


def money(value):
    try:
        amount = Decimal(str(value or 0)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        amount = Decimal("0.00")
    return f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def as_decimal(value):
    return Decimal(str(value or 0)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def date_text(value):
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y %H:%M:%S") if hasattr(value, "hour") else value.strftime("%d/%m/%Y")
    return str(value)


def time_text(value):
    if value is None:
        return ""
    return value.strftime("%H:%M") if hasattr(value, "strftime") else str(value)[:5]


class CreateInvoiceDialog(QDialog):
    """Lập hóa đơn tiền mặt; dùng ca hiện tại của nhân viên đăng nhập."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.username = (getattr(db, "username", "") or "").strip()
        self.employee = None
        self.active_shift = None
        self.products = []
        self.cart = {}
        self.promotions = {}
        self.saved_invoice_code = None

        self.setWindowTitle("Lập hóa đơn")
        self.resize(1100, 760)
        self.setMinimumSize(900, 650)

        self._load_employee_and_active_shift()
        self._build_ui()
        self._load_promotions()
        self.search_products()
        self.update_totals()

    def _load_employee_and_active_shift(self):
        conn = self.db.get_connection()
        if conn is None:
            raise RuntimeError("Chưa có kết nối SQL Server.")

        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT TOP 1
                    NV.MANV, NV.TENNV, NV.VAITRO,
                    C.MACA, C.SOCA, C.NGAYLAM, C.TGMO, C.TGDONG
                FROM dbo.NHAN_VIEN NV
                INNER JOIN dbo.LAMCA L ON L.MANV = NV.MANV
                INNER JOIN dbo.CA_LAM_VIEC C ON C.MACA = L.MACA
                WHERE NV.MANV = ?
                  AND CAST(C.NGAYLAM AS date) = CAST(SYSDATETIME() AS date)
                  AND CAST(SYSDATETIME() AS time) >= C.TGMO
                  AND CAST(SYSDATETIME() AS time) < C.TGDONG
                ORDER BY C.SOCA
            """, self.username)
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError(
                    "Bạn chưa đăng ký ca đang diễn ra.\n"
                    "Chỉ nhân viên thuộc ca hiện tại mới được lập hóa đơn."
                )
            self.employee = {
                "manv": row[0], "tennv": row[1], "vaitro": row[2],
            }
            self.active_shift = {
                "maca": row[3], "soca": row[4], "ngaylam": row[5],
                "tgmo": row[6], "tgdong": row[7],
            }
        finally:
            cursor.close()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        title = QLabel("LẬP HÓA ĐƠN BÁN HÀNG")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        root.addWidget(title)

        info = QGroupBox("Thông tin hóa đơn")
        info_form = QFormLayout(info)
        shift = self.active_shift
        shift_text = (
            f"Ca {shift['soca']} | Mã ca: {shift['maca']} | "
            f"{date_text(shift['ngaylam'])} | "
            f"{time_text(shift['tgmo'])} - {time_text(shift['tgdong'])}"
        )
        self.employee_label = QLabel(
            f"{self.employee['tennv']} ({self.employee['manv']})"
        )
        self.shift_label = QLabel(shift_text)
        self.promotion_combo = QComboBox()
        self.promotion_combo.addItem("Không áp dụng khuyến mãi", None)
        self.promotion_combo.currentIndexChanged.connect(self.update_totals)
        info_form.addRow("Nhân viên:", self.employee_label)
        info_form.addRow("Ca làm việc:", self.shift_label)
        info_form.addRow("Khuyến mãi:", self.promotion_combo)
        root.addWidget(info)

        products_group = QGroupBox("Chọn sản phẩm")
        products_layout = QVBoxLayout(products_group)
        search_row = QHBoxLayout()
        self.product_search = QLineEdit()
        self.product_search.setPlaceholderText("Tìm theo mã hoặc tên sản phẩm...")
        self.product_search.textChanged.connect(self.search_products)
        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 999999)
        self.quantity_input.setValue(1)
        self.add_product_button = QPushButton("Thêm vào hóa đơn")
        self.add_product_button.clicked.connect(self.add_selected_product)
        search_row.addWidget(self.product_search, 1)
        search_row.addWidget(QLabel("Số lượng:"))
        search_row.addWidget(self.quantity_input)
        search_row.addWidget(self.add_product_button)
        products_layout.addLayout(search_row)

        self.product_table = QTableWidget(0, 6)
        self.product_table.setHorizontalHeaderLabels([
            "Mã SP", "Tên sản phẩm", "ĐVT", "Giá bán", "Tồn kho", "VAT (%)"
        ])
        self._configure_table(self.product_table, stretch_column=1)
        self.product_table.cellDoubleClicked.connect(lambda *_: self.add_selected_product())
        products_layout.addWidget(self.product_table)
        root.addWidget(products_group, 2)

        cart_group = QGroupBox("Sản phẩm trong hóa đơn")
        cart_layout = QVBoxLayout(cart_group)
        self.cart_table = QTableWidget(0, 7)
        self.cart_table.setHorizontalHeaderLabels([
            "Mã SP", "Tên sản phẩm", "SL", "Đơn giá", "VAT (%)", "Thành tiền", ""
        ])
        self._configure_table(self.cart_table, stretch_column=1)
        cart_layout.addWidget(self.cart_table)
        remove_row = QHBoxLayout()
        remove_row.addStretch()
        self.remove_item_button = QPushButton("Bỏ sản phẩm đã chọn")
        self.remove_item_button.clicked.connect(self.remove_selected_cart_item)
        remove_row.addWidget(self.remove_item_button)
        cart_layout.addLayout(remove_row)
        root.addWidget(cart_group, 2)

        bottom = QHBoxLayout()
        totals_group = QGroupBox("Thanh toán")
        totals_form = QFormLayout(totals_group)
        self.subtotal_label = QLabel("0,00")
        self.vat_label = QLabel("0,00")
        self.discount_label = QLabel("0,00")
        self.total_label = QLabel("0,00")
        self.total_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #16A34A;")
        self.cash_input = QLineEdit()
        self.cash_input.setPlaceholderText("Nhập tiền khách đưa")
        self.cash_input.textChanged.connect(self.update_totals)
        self.change_label = QLabel("0,00")
        totals_form.addRow("Tiền hàng:", self.subtotal_label)
        totals_form.addRow("Tổng VAT:", self.vat_label)
        totals_form.addRow("Giảm giá:", self.discount_label)
        totals_form.addRow("Khách cần trả:", self.total_label)
        totals_form.addRow("Tiền khách đưa:", self.cash_input)
        totals_form.addRow("Tiền thừa:", self.change_label)
        bottom.addWidget(totals_group, 2)

        actions = QVBoxLayout()
        actions.addStretch()
        self.save_button = QPushButton("Lưu hóa đơn")
        self.save_button.clicked.connect(self.save_invoice)
        self.cancel_button = QPushButton("Đóng")
        self.cancel_button.clicked.connect(self.reject)
        actions.addWidget(self.save_button)
        actions.addWidget(self.cancel_button)
        bottom.addLayout(actions, 1)
        root.addLayout(bottom)

    @staticmethod
    def _configure_table(table, stretch_column=None):
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        if stretch_column is not None:
            header.setSectionResizeMode(stretch_column, QHeaderView.ResizeMode.Stretch)

    @staticmethod
    def _set_cell(table, row, column, value, data=None):
        item = QTableWidgetItem("" if value is None else str(value))
        if data is not None:
            item.setData(Qt.ItemDataRole.UserRole, data)
        table.setItem(row, column, item)

    def _load_promotions(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT MAKM, TENKM, TYLEGIAM
                FROM dbo.CHUONG_TRINH_KM
                WHERE NGAYBD <= SYSDATETIME()
                  AND NGAYKT >= SYSDATETIME()
                ORDER BY TENKM
            """)
            for row in cursor.fetchall():
                self.promotion_combo.addItem(
                    f"{row[1]} ({row[2]}%)", row[0]
                )
                self.promotions[row[0]] = as_decimal(row[2])
        finally:
            cursor.close()

    def search_products(self, *_):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        keyword = self.product_search.text().strip()
        try:
            cursor.execute("""
                SELECT MASP, TENSP, DVT, GIABAN, SLTON, VAT
                FROM dbo.SAN_PHAM
                WHERE ISNULL(IS_DELETED, 0) = 0
                  AND ISNULL(SLTON, 0) > 0
                  AND (MASP LIKE ? OR TENSP LIKE ?)
                ORDER BY TENSP
            """, (f"%{keyword}%", f"%{keyword}%"))
            rows = cursor.fetchall()
            self.product_table.setRowCount(0)
            self.products = {}
            for row_index, row in enumerate(rows):
                masp, tensp, dvt, price, stock, vat = row
                self.products[masp] = {
                    "masp": masp, "tensp": tensp, "dvt": dvt,
                    "price": as_decimal(price), "stock": int(stock or 0),
                    "vat": as_decimal(vat),
                }
                self.product_table.insertRow(row_index)
                values = [masp, tensp, dvt, money(price), stock, money(vat)]
                for col, value in enumerate(values):
                    self._set_cell(self.product_table, row_index, col, value,
                                   masp if col == 0 else None)
        except Exception as error:
            QMessageBox.critical(self, "Lỗi tải sản phẩm", str(error))
        finally:
            cursor.close()

    def add_selected_product(self):
        row = self.product_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Thông báo", "Vui lòng chọn sản phẩm.")
            return
        item = self.product_table.item(row, 0)
        if item is None:
            return
        masp = item.text()
        product = self.products.get(masp)
        if not product:
            return
        quantity = self.quantity_input.value()
        current_quantity = self.cart.get(masp, {}).get("quantity", 0)
        if current_quantity + quantity > product["stock"]:
            QMessageBox.warning(
                self, "Không đủ tồn kho",
                f"Sản phẩm {masp} chỉ còn {product['stock']} sản phẩm."
            )
            return
        if masp in self.cart:
            self.cart[masp]["quantity"] += quantity
        else:
            self.cart[masp] = {**product, "quantity": quantity}
        self._refresh_cart()
        self.update_totals()

    def _refresh_cart(self):
        self.cart_table.setRowCount(0)
        for row_index, (masp, item) in enumerate(self.cart.items()):
            self.cart_table.insertRow(row_index)
            base = item["price"] * item["quantity"]
            line_total = base * (Decimal("1") + item["vat"] / Decimal("100"))
            values = [
                masp, item["tensp"], item["quantity"], money(item["price"]),
                money(item["vat"]), money(line_total), "Bỏ"
            ]
            for col, value in enumerate(values):
                self._set_cell(self.cart_table, row_index, col, value, masp if col == 6 else None)

    def remove_selected_cart_item(self):
        row = self.cart_table.currentRow()
        if row < 0:
            return
        item = self.cart_table.item(row, 0)
        if item:
            self.cart.pop(item.text(), None)
            self._refresh_cart()
            self.update_totals()

    def _calculate_totals(self):
        subtotal = Decimal("0.00")
        vat_total = Decimal("0.00")
        for item in self.cart.values():
            base = item["price"] * item["quantity"]
            vat_amount = base * item["vat"] / Decimal("100")
            subtotal += base
            vat_total += vat_amount
        before_discount = (subtotal + vat_total).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        promotion_code = self.promotion_combo.currentData()
        discount_rate = self.promotions.get(promotion_code, Decimal("0"))
        discount = (before_discount * discount_rate / Decimal("100")).quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP
        )
        total = (before_discount - discount).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        return subtotal, vat_total, discount, total

    def update_totals(self, *_):
        subtotal, vat_total, discount, total = self._calculate_totals()
        self.subtotal_label.setText(money(subtotal))
        self.vat_label.setText(money(vat_total))
        self.discount_label.setText(money(discount))
        self.total_label.setText(money(total))
        try:
            cash_text = self.cash_input.text().strip().replace(",", "").replace(" ", "")
            cash = Decimal(cash_text) if cash_text else Decimal("0")
            change = cash - total
        except InvalidOperation:
            change = Decimal("0") - total
        self.change_label.setText(money(max(change, Decimal("0"))))

    @staticmethod
    def _parse_cash(text):
        normalized = text.strip().replace(",", "").replace(" ", "")
        if not normalized:
            raise ValueError("Vui lòng nhập số tiền khách đưa.")
        try:
            value = Decimal(normalized)
        except InvalidOperation:
            raise ValueError("Tiền khách đưa phải là số hợp lệ.")
        if not value.is_finite() or value < 0:
            raise ValueError("Tiền khách đưa không hợp lệ.")
        return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    def save_invoice(self):
        if not self.cart:
            QMessageBox.warning(self, "Thông báo", "Hóa đơn chưa có sản phẩm.")
            return
        try:
            cash = self._parse_cash(self.cash_input.text())
        except ValueError as error:
            QMessageBox.warning(self, "Thông tin chưa hợp lệ", str(error))
            return

        _, _, _, total = self._calculate_totals()
        if cash < total:
            QMessageBox.warning(
                self, "Chưa đủ tiền",
                f"Khách cần trả {money(total)} nhưng mới đưa {money(cash)}."
            )
            return

        conn = self.db.get_connection()
        cursor = conn.cursor()
        invoice_code = None
        try:
            # Khóa bảng trong transaction khi lấy số tiếp theo để hạn chế trùng mã.
            cursor.execute("""
                SELECT COALESCE(
                    MAX(TRY_CONVERT(BIGINT, SUBSTRING(MAHD, 3, 18))), 0
                )
                FROM dbo.HOA_DON WITH (TABLOCKX, HOLDLOCK)
                WHERE UPPER(LEFT(MAHD, 2)) = 'HD'
                  AND TRY_CONVERT(BIGINT, SUBSTRING(MAHD, 3, 18)) IS NOT NULL
            """)
            last_number = int(cursor.fetchone()[0] or 0)
            invoice_code = f"HD{last_number + 1:06d}"

            promotion_code = self.promotion_combo.currentData()
            shift = self.active_shift

            # TRANGTHAI được gán 1 theo giả định hóa đơn đã hoàn tất thanh toán.
            cursor.execute("""
                INSERT INTO dbo.HOA_DON
                    (MAHD, NGAYLAP, TIENKHACHDUA,
                     TRANGTHAI, MANV, MAKM, MACA)
                VALUES (?, SYSDATETIME(), ?, 1, ?, ?, ?)
            """, (
                invoice_code, cash, self.username,
                promotion_code, shift["maca"]
            ))

            for masp, item in self.cart.items():
                # Trừ tồn kho có điều kiện để tránh bán vượt số lượng tồn.
                cursor.execute("""
                    UPDATE dbo.SAN_PHAM
                    SET SLTON = SLTON - ?
                    WHERE MASP = ?
                      AND ISNULL(IS_DELETED, 0) = 0
                      AND SLTON >= ?
                """, (item["quantity"], masp, item["quantity"]))
                if cursor.rowcount != 1:
                    raise RuntimeError(
                        f"Sản phẩm {masp} không còn đủ tồn kho. Hóa đơn chưa được lưu."
                    )

                cursor.execute("""
                    INSERT INTO dbo.CHI_TIET_HOA_DON
                        (MAHD, MASP, DONGIA, SOLUONG, VAT)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    invoice_code, masp, item["price"],
                    item["quantity"], item["vat"]
                ))

            conn.commit()
            self.saved_invoice_code = invoice_code
            QMessageBox.information(
                self, "Thành công",
                f"Đã tạo hóa đơn {invoice_code}.\nTiền thừa: {money(cash - total)}"
            )
            self.accept()

        except Exception as error:
            conn.rollback()
            QMessageBox.critical(
                self, "Không thể tạo hóa đơn",
                f"{error}\n\nCác thay đổi trong giao dịch đã được hoàn tác."
            )
        finally:
            cursor.close()


class InvoiceDetailDialog(QDialog):
    def __init__(self, db, invoice_code, parent=None):
        super().__init__(parent)
        self.db = db
        self.invoice_code = invoice_code
        self.setWindowTitle(f"Chi tiết hóa đơn {invoice_code}")
        self.resize(900, 650)
        self.setMinimumSize(760, 540)
        self.header, self.items = self._load_invoice()
        self._build_ui()

    def _load_invoice(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    HD.MAHD, HD.NGAYLAP, HD.TIENKHACHDUA,
                    HD.TRANGTHAI, HD.MANV, NV.TENNV, NV.VAITRO,
                    HD.MACA, C.SOCA, C.NGAYLAM, C.TGMO, C.TGDONG,
                    HD.MAKM, KM.TENKM, KM.TYLEGIAM
                FROM dbo.HOA_DON HD
                LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = HD.MANV
                LEFT JOIN dbo.CA_LAM_VIEC C ON C.MACA = HD.MACA
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.MAHD = ?
            """, self.invoice_code)
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("Không tìm thấy hóa đơn.")
            header = {
                "mahd": row[0], "ngaylap": row[1],
                "cash": as_decimal(row[2]), "status": row[3],
                "manv": row[4], "tennv": row[5], "vaitro": row[6],
                "maca": row[7], "soca": row[8], "ngaylam": row[9],
                "tgmo": row[10], "tgdong": row[11], "makm": row[12],
                "tenkm": row[13], "discount_rate": as_decimal(row[14]),
            }

            cursor.execute("""
                SELECT CT.MASP, SP.TENSP, SP.DVT,
                       CT.DONGIA, CT.SOLUONG, CT.VAT
                FROM dbo.CHI_TIET_HOA_DON CT
                LEFT JOIN dbo.SAN_PHAM SP ON SP.MASP = CT.MASP
                WHERE CT.MAHD = ?
                ORDER BY CT.MASP
            """, self.invoice_code)
            items = []
            for item in cursor.fetchall():
                price = as_decimal(item[3])
                quantity = int(item[4] or 0)
                vat = as_decimal(item[5])
                base = price * quantity
                vat_amount = (base * vat / Decimal("100")).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
                items.append({
                    "masp": item[0], "tensp": item[1] or "(Sản phẩm đã ngừng lưu thông)",
                    "dvt": item[2], "price": price, "quantity": quantity,
                    "vat": vat, "base": base, "vat_amount": vat_amount,
                    "line_total": base + vat_amount,
                })
            return header, items
        finally:
            cursor.close()

    def _totals(self):
        subtotal = sum((item["base"] for item in self.items), Decimal("0"))
        vat_total = sum((item["vat_amount"] for item in self.items), Decimal("0"))
        before_discount = subtotal + vat_total
        discount = (before_discount * self.header["discount_rate"] / Decimal("100")).quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP
        )
        total = (before_discount - discount).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        change = self.header["cash"] - total
        return subtotal, vat_total, discount, total, change

    def _build_ui(self):
        root = QVBoxLayout(self)
        title = QLabel(f"HÓA ĐƠN BÁN HÀNG - {self.header['mahd']}")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        root.addWidget(title)

        info = QGroupBox("Thông tin hóa đơn")
        form = QFormLayout(info)
        shift_text = (
            f"Ca {self.header['soca']} | Mã ca: {self.header['maca']} | "
            f"{date_text(self.header['ngaylam'])} | "
            f"{time_text(self.header['tgmo'])} - {time_text(self.header['tgdong'])}"
        ) if self.header["maca"] is not None else "Không có thông tin ca"
        form.addRow("Mã hóa đơn:", QLabel(str(self.header["mahd"])))
        form.addRow("Ngày, giờ lập:", QLabel(date_text(self.header["ngaylap"])))
        form.addRow("Nhân viên:", QLabel(f"{self.header['tennv'] or ''} ({self.header['manv'] or ''})"))
        form.addRow("Vai trò:", QLabel(str(self.header["vaitro"] or "")))
        form.addRow("Ca làm việc:", QLabel(shift_text))
        if self.header["makm"]:
            form.addRow("Khuyến mãi:", QLabel(
                f"{self.header['tenkm'] or self.header['makm']} ({money(self.header['discount_rate'])}%)"
            ))
        root.addWidget(info)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Mã SP", "Tên sản phẩm", "ĐVT", "Số lượng",
            "Đơn giá", "VAT (%)", "Thành tiền"
        ])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i, item in enumerate(self.items):
            self.table.insertRow(i)
            values = [item["masp"], item["tensp"], item["dvt"], item["quantity"],
                      money(item["price"]), money(item["vat"]), money(item["line_total"])]
            for col, value in enumerate(values):
                self.table.setItem(i, col, QTableWidgetItem(str(value or "")))
        root.addWidget(self.table, 1)

        subtotal, vat_total, discount, total, change = self._totals()
        summary = QGroupBox("Thanh toán")
        summary_form = QFormLayout(summary)
        summary_form.addRow("Tiền hàng:", QLabel(money(subtotal)))
        summary_form.addRow("Tổng VAT:", QLabel(money(vat_total)))
        summary_form.addRow("Giảm giá:", QLabel(money(discount)))
        total_label = QLabel(money(total))
        total_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #16A34A;")
        summary_form.addRow("Tổng thanh toán:", total_label)
        summary_form.addRow("Tiền khách đưa:", QLabel(money(self.header["cash"])))
        summary_form.addRow("Tiền thừa:", QLabel(money(change)))
        root.addWidget(summary)

        buttons = QHBoxLayout()
        buttons.addStretch()
        print_button = QPushButton("In hóa đơn")
        print_button.clicked.connect(self.print_invoice)
        close_button = QPushButton("Đóng")
        close_button.clicked.connect(self.accept)
        buttons.addWidget(print_button)
        buttons.addWidget(close_button)
        root.addLayout(buttons)

    def _build_print_html(self):
        """Tạo mẫu hóa đơn nhiệt 80 mm với các cột cố định, thẳng hàng."""
        h = self.header
        subtotal, vat_total, discount, total, change = self._totals()

        shift_text = (
            f"Ca {h['soca']} | Mã ca: {h['maca']}<br>"
            f"Ngày ca: {date_text(h['ngaylam'])}<br>"
            f"Giờ ca: {time_text(h['tgmo'])} - {time_text(h['tgdong'])}"
        ) if h["maca"] is not None else "Không có thông tin ca"

        # Dùng MỘT bảng duy nhất cho toàn bộ mặt hàng. Nếu tạo một bảng
        # riêng cho từng sản phẩm, Qt có thể tự chia độ rộng cột khác nhau.
        item_rows = []
        for item in self.items:
            item_rows.append(
                "<tr class='item-name-row'>"
                "<td colspan='2'>"
                f"<div class='item-name'>{escape(str(item['tensp'] or ''))}</div>"
                f"<div class='item-code'>Mã: {escape(str(item['masp'] or ''))}"
                f" | ĐVT: {escape(str(item['dvt'] or ''))}</div>"
                f"<div class='item-vat'>VAT: {money(item['vat'])}%</div>"
                "</td></tr>"
                "<tr class='item-price-row'>"
                f"<td class='qty-price' width='68%'>{item['quantity']} x {money(item['price'])}</td>"
                f"<td class='amount right' width='32%'>{money(item['line_total'])}</td>"
                "</tr>"
            )
        items_html = "".join(item_rows) or (
            "<tr><td colspan='2' class='center'>Không có sản phẩm</td></tr>"
        )

        promo = ""
        if h["makm"]:
            promo = (
                "<p><b>Khuyến mãi:</b> "
                f"{escape(str(h['tenkm'] or h['makm']))} "
                f"({money(h['discount_rate'])}%)</p>"
            )

        return f"""
        <!DOCTYPE html>
        <html><head><meta charset='utf-8'>
        <style>
            body {{
                font-family: Arial, sans-serif;
                font-size: 8pt;
                color: #111;
                margin: 0;
                padding: 0;
            }}
            .center {{ text-align: center; }}
            h1 {{ font-size: 15pt; margin: 0 0 2px 0; text-align: center; }}
            h2 {{ font-size: 10pt; margin: 5px 0; text-align: center; }}
            p {{ margin: 3px 0; line-height: 1.2; }}
            .company {{ text-align: center; font-size: 7.5pt; margin-bottom: 5px; }}
            .meta {{ margin: 6px 0; line-height: 1.3; }}
            .dash {{ border-top: 1px dashed #333; margin: 6px 0; }}

            /* Bảng sản phẩm có độ rộng 2 cột cố định */
            table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
            .items {{ width: 100%; table-layout: fixed; }}
            .items td {{ padding: 1px 0; vertical-align: top; border: none; }}
            .item-name-row td {{ padding-top: 5px; }}
            .item-name {{ font-weight: bold; font-size: 8.5pt; word-wrap: break-word; }}
            .item-code, .item-vat {{ font-size: 7pt; color: #333; }}
            .item-price-row td {{ padding-bottom: 4px; border-bottom: 1px dashed #999; }}
            .qty-price {{ width: 68%; text-align: left; }}
            .amount {{ width: 32%; text-align: right; white-space: nowrap; }}
            .right {{ text-align: right; }}

            /* Bảng tổng tiền cũng dùng tỷ lệ cột cố định */
            .summary {{ width: 100%; table-layout: fixed; }}
            .summary td {{ border: none; padding: 2px 0; vertical-align: top; }}
            .summary td:first-child {{ width: 68%; text-align: left; }}
            .summary td:last-child {{ width: 32%; text-align: right; white-space: nowrap; }}
            .total td {{ border-top: 1px solid #222; padding-top: 5px; font-size: 9pt; font-weight: bold; }}
            .thanks {{ text-align: center; margin-top: 9px; font-weight: bold; }}
            .small {{ text-align: center; font-size: 7pt; margin-top: 3px; }}
        </style></head><body>
            <h1>BOOKHUB</h1>
            <div class='company'>HỆ THỐNG QUẢN LÝ NHÀ SÁCH</div>
            <h2>HÓA ĐƠN BÁN HÀNG</h2>
            <div class='meta'>
                <p><b>Mã hóa đơn:</b> {escape(str(h['mahd']))}</p>
                <p><b>Ngày, giờ lập:</b> {escape(date_text(h['ngaylap']))}</p>
                <p><b>Nhân viên:</b> {escape(str(h['tennv'] or ''))}</p>
                <p><b>Mã nhân viên:</b> {escape(str(h['manv'] or ''))}</p>
                <p><b>Vai trò:</b> {escape(str(h['vaitro'] or ''))}</p>
                <p><b>Ca làm việc:</b><br>{shift_text}</p>
            </div>
            {promo}
            <div class='dash'></div>
            <p><b>CHI TIẾT SẢN PHẨM</b></p>
            <table class='items' width='100%' cellspacing='0' cellpadding='0'>
                <colgroup><col width='68%'><col width='32%'></colgroup>
                {items_html}
            </table>
            <div class='dash'></div>
            <table class='summary' width='100%' cellspacing='0' cellpadding='0'>
                <colgroup><col width='68%'><col width='32%'></colgroup>
                <tr><td>Tiền hàng</td><td>{money(subtotal)}</td></tr>
                <tr><td>Tổng VAT</td><td>{money(vat_total)}</td></tr>
                <tr><td>Giảm giá</td><td>-{money(discount)}</td></tr>
                <tr class='total'><td>TỔNG THANH TOÁN</td><td>{money(total)}</td></tr>
                <tr><td>Tiền khách đưa</td><td>{money(h['cash'])}</td></tr>
                <tr><td>Tiền thừa</td><td>{money(change)}</td></tr>
            </table>
            <div class='dash'></div>
            <p class='thanks'>Cảm ơn quý khách!</p>
            <p class='small'>Hẹn gặp lại quý khách.</p>
        </body></html>
        """

    def print_invoice(self):
        """In hóa đơn trên giấy in nhiệt cuộn 80 mm, chiều dài tự theo nội dung."""
        paper_width_mm = 80.0
        margin_mm = 3.0
        printable_width_pt = (paper_width_mm - 2 * margin_mm) * 72.0 / 25.4

        document = QTextDocument()
        document.setDocumentMargin(0)
        document.setHtml(self._build_print_html())
        document.setTextWidth(printable_width_pt)

        # Đọc chiều cao sau khi Qt bố trí nội dung theo đúng bề rộng in.
        # Không gọi adjustSize() vì thao tác đó có thể làm thay đổi lại chiều rộng.
        content_height_pt = max(
            document.documentLayout().documentSize().height(), 80.0
        )
        content_height_mm = content_height_pt * 25.4 / 72.0
        paper_height_mm = content_height_mm + 2 * margin_mm + 2.0

        page_size = QPageSize(
            QSizeF(paper_width_mm, paper_height_mm),
            QPageSize.Unit.Millimeter,
            "BookHub Receipt 80mm",
            QPageSize.SizeMatchPolicy.ExactMatch
        )
        margins = QMarginsF(margin_mm, margin_mm, margin_mm, margin_mm)

        # QTextDocument sử dụng kích thước vùng in tính theo point
        document.setPageSize(QSizeF(printable_width_pt, content_height_pt + 1.0))

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(page_size)
        printer.setPageMargins(margins, QPageLayout.Unit.Millimeter)

        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("In hóa đơn - giấy nhiệt 80 mm")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # Áp dụng lại khổ cuộn sau khi người dùng chọn máy in trong hộp thoại
        printer.setPageSize(page_size)
        printer.setPageMargins(margins, QPageLayout.Unit.Millimeter)
        document.print_(printer)


class InvoiceWindow(QWidget):
    """Trang danh sách, lập, xem và in hóa đơn."""

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.username = (getattr(db, "username", "") or "").strip()
        self.employee_role = self._get_employee_role()
        self.can_create = (
            self.username.casefold() == "admin"
            or self.employee_role.casefold() in {"quản lý", "thu ngân"}
        )
        self._build_ui()
        self.load_invoices()

    def _get_employee_role(self):
        conn = self.db.get_connection()
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

        search = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm mã hóa đơn, mã nhân viên hoặc tên nhân viên...")
        self.search_input.returnPressed.connect(self.load_invoices)
        search_button = QPushButton("Tìm kiếm")
        search_button.clicked.connect(self.load_invoices)
        clear_button = QPushButton("Xóa tìm kiếm")
        clear_button.clicked.connect(self.clear_search)
        search.addWidget(self.search_input, 1)
        search.addWidget(search_button)
        search.addWidget(clear_button)
        root.addLayout(search)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Mã hóa đơn", "Ngày lập", "Nhân viên", "Mã ca",
            "Số ca", "Tổng thanh toán", "Tiền khách đưa"
        ])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(self.open_invoice_detail)
        root.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        self.total_label = QLabel("Tổng số hóa đơn: 0")
        bottom.addWidget(self.total_label)
        bottom.addStretch()
        detail_button = QPushButton("Xem chi tiết / In hóa đơn")
        detail_button.clicked.connect(self.open_selected_invoice)
        bottom.addWidget(detail_button)
        root.addLayout(bottom)

    def clear_search(self):
        self.search_input.clear()
        self.load_invoices()

    def load_invoices(self):
        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối database.")
            return
        cursor = conn.cursor()
        keyword = self.search_input.text().strip()
        sql = """
            SELECT
                HD.MAHD, HD.NGAYLAP, HD.MANV, NV.TENNV,
                HD.MACA, C.SOCA, HD.TIENKHACHDUA,
                COALESCE(SUM(
                    CT.DONGIA * CT.SOLUONG *
                    (1 + COALESCE(CT.VAT, 0) / 100.0)
                ), 0) * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0) AS TOTAL_AMOUNT
            FROM dbo.HOA_DON HD
            LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = HD.MANV
            LEFT JOIN dbo.CA_LAM_VIEC C ON C.MACA = HD.MACA
            LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
            LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
        """
        params = []
        if keyword:
            sql += " WHERE (HD.MAHD LIKE ? OR HD.MANV LIKE ? OR NV.TENNV LIKE ?)"
            like = f"%{keyword}%"
            params.extend([like, like, like])
        sql += """
            GROUP BY HD.MAHD, HD.NGAYLAP, HD.MANV, NV.TENNV,
                     HD.MACA, C.SOCA, HD.TIENKHACHDUA,
                     KM.TYLEGIAM
            ORDER BY HD.NGAYLAP DESC, HD.MAHD DESC
        """
        try:
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
            self.table.setRowCount(0)
            for i, row in enumerate(rows):
                self.table.insertRow(i)
                values = [
                    row[0], date_text(row[1]),
                    f"{row[3] or ''} ({row[2] or ''})",
                    row[4], row[5], money(row[7]), money(row[6])
                ]
                for col, value in enumerate(values):
                    self.table.setItem(i, col, QTableWidgetItem(str(value or "")))
            self.total_label.setText(f"Tổng số hóa đơn: {len(rows)}")
        except Exception as error:
            QMessageBox.critical(self, "Lỗi tải hóa đơn", str(error))
        finally:
            cursor.close()

    def open_selected_invoice(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Thông báo", "Vui lòng chọn hóa đơn.")
            return
        item = self.table.item(row, 0)
        if item:
            self.open_invoice_detail(row, 0)

    def open_invoice_detail(self, row, column):
        item = self.table.item(row, 0)
        if item is None:
            return
        invoice_code = item.text()
        try:
            dialog = InvoiceDetailDialog(self.db, invoice_code, self)
            dialog.exec()
        except Exception as error:
            QMessageBox.critical(self, "Lỗi xem hóa đơn", str(error))

    def open_create_invoice(self):
        if not self.can_create:
            QMessageBox.warning(self, "Từ chối truy cập", "Tài khoản không có quyền lập hóa đơn.")
            return
        try:
            dialog = CreateInvoiceDialog(self.db, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_invoices()
                if dialog.saved_invoice_code:
                    ask = QMessageBox.question(
                        self, "In hóa đơn",
                        f"Đã tạo hóa đơn {dialog.saved_invoice_code}. Bạn có muốn in ngay không?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )
                    if ask == QMessageBox.StandardButton.Yes:
                        try:
                            detail = InvoiceDetailDialog(self.db, dialog.saved_invoice_code, self)
                            detail.print_invoice()
                        except Exception as error:
                            QMessageBox.critical(self, "Lỗi in hóa đơn", str(error))
        except Exception as error:
            QMessageBox.critical(self, "Không thể lập hóa đơn", str(error))
