"""CreateInvoiceDialog: thành phần giao diện nghiệp vụ hóa đơn."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QTableWidget,
    QHeaderView,
    QAbstractItemView,
    QMessageBox,
    QSpinBox,
    QGroupBox,
)
from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table,
    pause_table_sorting,
    resume_table_sorting,
)
from .dung_chung import MONEY_QUANT, Decimal, InvalidOperation, ROUND_HALF_UP, money, as_decimal, date_text, time_text
from ui.permissions import is_admin_account


class CreateInvoiceDialog(QDialog):
    """Hộp thoại lập hóa đơn, quản lý sản phẩm trong giỏ và tính số tiền khách phải trả."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.username = (getattr(db, "username", "") or "").strip()
        self.is_admin = is_admin_account(self.username)
        self.employee = None
        self.active_shift = None
        self.products = {}
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
        """Lấy thông tin nhân viên đăng nhập và ca làm việc đang hoạt động."""
        conn = self.db.get_connection()
        if conn is None:
            raise RuntimeError("Chưa có kết nối SQL Server.")

        cursor = conn.cursor()
        try:
            if self.is_admin:
                cursor.execute("""
                    SELECT MANV, TENNV, VAITRO
                    FROM dbo.NHAN_VIEN
                    WHERE MANV = ?
                """, self.username)
                row = cursor.fetchone()
                self.employee = {
                    "manv": row[0] if row else None,
                    "tennv": (row[1] or row[0]) if row else "Admin",
                    "vaitro": row[2] if row else "Quản trị hệ thống",
                }
                # Admin không bị ràng buộc bởi đăng ký ca; MACA có thể để NULL.
                self.active_shift = None
                return

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
                  AND C.TMCUOICA IS NULL
                ORDER BY C.SOCA
            """, self.username)
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError(
                    "Bạn chưa đăng ký ca đang diễn ra.\n"
                    "Chỉ nhân viên thuộc ca hiện tại mới được lập hóa đơn."
                )

            self.employee = {
                "manv": row[0],
                "tennv": row[1],
                "vaitro": row[2],
            }
            self.active_shift = {
                "maca": row[3],
                "soca": row[4],
                "ngaylam": row[5],
                "tgmo": row[6],
                "tgdong": row[7],
            }
        finally:
            cursor.close()

    def _build_ui(self):
        """Tạo các trường nhập, bảng sản phẩm, giỏ hàng và khu vực thanh toán."""
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        title = QLabel("LẬP HÓA ĐƠN BÁN HÀNG")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        root.addWidget(title)

        info = QGroupBox("Thông tin hóa đơn")
        info_form = QFormLayout(info)
        shift = self.active_shift
        if shift is None:
            shift_text = "Tài khoản Admin – không giới hạn ca làm việc"
        else:
            shift_text = (
                f"Ca {shift['soca']} | Mã ca: {shift['maca']} | "
                f"{date_text(shift['ngaylam'])} | "
                f"{time_text(shift['tgmo'])} - {time_text(shift['tgdong'])}"
            )
        employee_code = self.employee["manv"] or "Tài khoản hệ thống"
        self.employee_label = QLabel(
            f"{self.employee['tennv']} ({employee_code})"
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
            "Mã SP", "Tên sản phẩm", "ĐVT", "Giá bán (đã gồm VAT)",
            "Tồn kho", "VAT (%)"
        ])
        self._configure_table(
            self.product_table,
            stretch_column=1,
            default_sort_column=1
        )
        self.product_table.cellDoubleClicked.connect(
            lambda *_: self.add_selected_product()
        )
        products_layout.addWidget(self.product_table)
        root.addWidget(products_group, 2)

        cart_group = QGroupBox("Sản phẩm trong hóa đơn")
        cart_layout = QVBoxLayout(cart_group)
        self.cart_table = QTableWidget(0, 7)
        self.cart_table.setHorizontalHeaderLabels([
            "Mã SP", "Tên sản phẩm", "SL", "Đơn giá (đã gồm VAT)",
            "VAT (%)", "Thành tiền", ""
        ])
        self._configure_table(
            self.cart_table,
            stretch_column=1,
            default_sort_column=0
        )
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
        self.discount_label = QLabel("0,00")
        self.total_label = QLabel("0,00")
        self.total_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #16A34A;"
        )
        self.cash_input = QLineEdit()
        self.cash_input.setPlaceholderText("Nhập tiền khách đưa")
        self.cash_input.textChanged.connect(self.update_totals)
        self.change_label = QLabel("0,00")
        totals_form.addRow("Tiền hàng (đã gồm VAT):", self.subtotal_label)
        totals_form.addRow("Giảm giá:", self.discount_label)
        totals_form.addRow("Khách cần trả:", self.total_label)
        totals_form.addRow("Tiền khách đưa:", self.cash_input)
        totals_form.addRow("Tiền thừa:", self.change_label)
        bottom.addWidget(totals_group, 2)

        actions = QVBoxLayout()
        actions.addStretch()
        self.save_button = QPushButton("Lưu hóa đơn")
        self.save_button.setProperty("buttonRole", "primary")
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(self.save_invoice)
        self.cancel_button = QPushButton("Đóng")
        self.cancel_button.clicked.connect(self.reject)
        actions.addWidget(self.save_button)
        actions.addWidget(self.cancel_button)
        bottom.addLayout(actions, 1)
        root.addLayout(bottom)

    @staticmethod
    def _configure_table(
            table,
            stretch_column=None,
            default_sort_column=0
    ):
        """Cấu hình cách hiển thị, chọn và sắp xếp bảng sản phẩm."""
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
            default_column=default_sort_column
        )

    @staticmethod
    def _set_cell(table, row, column, value, data=None):
        """Gán nội dung cho ô bảng và áp dụng căn lề phù hợp."""
        item = QTableWidgetItem("" if value is None else str(value))
        if data is not None:
            item.setData(Qt.ItemDataRole.UserRole, data)
        table.setItem(row, column, item)

    def _load_promotions(self):
        """Tải các chương trình khuyến mãi còn hiệu lực để áp dụng cho hóa đơn."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT MAKM, TENKM, TYLEGIAM
                FROM dbo.CHUONG_TRINH_KM
                WHERE NGAYBD <= SYSDATETIME()
                  AND NGAYKT >= SYSDATETIME()
                  AND ISNULL(IS_DELETED, 0) = 0
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
        """Tìm sản phẩm theo từ khóa và cập nhật danh sách kết quả."""
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

            pause_table_sorting(self.product_table)

            self.product_table.setRowCount(0)
            self.products = {}

            for row_index, row in enumerate(rows):
                masp, tensp, dvt, price, stock, vat = row
                self.products[masp] = {
                    "masp": masp,
                    "tensp": tensp,
                    "dvt": dvt,
                    "price": as_decimal(price),
                    "stock": int(stock or 0),
                    "vat": as_decimal(vat),
                }
                self.product_table.insertRow(row_index)
                values = [
                    masp, tensp, dvt, money(price), stock, money(vat)
                ]
                for col, value in enumerate(values):
                    self._set_cell(
                        self.product_table, row_index, col, value,
                        masp if col == 0 else None
                    )
        except Exception as error:
            QMessageBox.critical(self, "Lỗi tải sản phẩm", str(error))
        finally:
            resume_table_sorting(self.product_table)
            cursor.close()

    def add_selected_product(self):
        """Thêm sản phẩm đang chọn vào giỏ hàng hoặc tăng số lượng nếu đã có."""
        row = self.product_table.currentRow()
        if row < 0:
            QMessageBox.information(
                self, "Thông báo", "Vui lòng chọn sản phẩm."
            )
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
        """Cập nhật các dòng trong bảng giỏ hàng theo trạng thái hiện tại."""
        pause_table_sorting(self.cart_table)

        try:
            self.cart_table.setRowCount(0)

            for row_index, (masp, item) in enumerate(self.cart.items()):
                # GIABAN đã gồm VAT nên thành tiền chỉ là đơn giá nhân số lượng.
                line_total = item["price"] * item["quantity"]

                values = [
                    masp,
                    item["tensp"],
                    item["quantity"],
                    money(item["price"]),
                    money(item["vat"]),
                    money(line_total),
                    "Bỏ",
                ]

                self.cart_table.insertRow(row_index)

                for col, value in enumerate(values):
                    self._set_cell(
                        self.cart_table, row_index, col, value,
                        masp if col == 6 else None
                    )

        finally:
            resume_table_sorting(self.cart_table)

    def remove_selected_cart_item(self):
        """Xóa sản phẩm đang chọn khỏi giỏ hàng."""
        row = self.cart_table.currentRow()
        if row < 0:
            return
        item = self.cart_table.item(row, 0)
        if item:
            self.cart.pop(item.text(), None)
            self._refresh_cart()
            self.update_totals()

    def _calculate_totals(self):
        """Tính tiền từ đơn giá đã bao gồm VAT, không cộng VAT lần nữa."""
        subtotal = sum(
            (
                item["price"] * item["quantity"]
                for item in self.cart.values()
            ),
            Decimal("0.00")
        ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

        promotion_code = self.promotion_combo.currentData()
        discount_rate = self.promotions.get(
            promotion_code, Decimal("0")
        )
        discount = (
            subtotal * discount_rate / Decimal("100")
        ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        total = (subtotal - discount).quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP
        )
        return subtotal, discount, total

    def update_totals(self, *_):
        """Hiển thị lại tổng tiền và số tiền khách cần thanh toán."""
        subtotal, discount, total = self._calculate_totals()
        self.subtotal_label.setText(money(subtotal))
        self.discount_label.setText(money(discount))
        self.total_label.setText(money(total))

        try:
            cash_text = (
                self.cash_input.text().strip()
                .replace(",", "").replace(" ", "")
            )
            cash = Decimal(cash_text) if cash_text else Decimal("0")
            change = cash - total
        except InvalidOperation:
            change = Decimal("0") - total

        self.change_label.setText(
            money(max(change, Decimal("0")))
        )

    @staticmethod
    def _parse_cash(text):
        """Chuyển chuỗi tiền khách nhập thành giá trị số hợp lệ."""
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

    @staticmethod
    def _assert_cart_prices_unchanged(
        cursor, cart, promotion_code, expected_discount_rate
    ):
        """Chặn lưu hóa đơn với giá, VAT hoặc khuyến mãi đã thay đổi khi form đang mở."""
        for product_code, item in cart.items():
            cursor.execute("""
                SELECT GIABAN, VAT
                FROM dbo.SAN_PHAM WITH (UPDLOCK, HOLDLOCK)
                WHERE MASP = ?
                  AND ISNULL(IS_DELETED, 0) = 0
            """, product_code)
            current = cursor.fetchone()
            if current is None:
                raise RuntimeError(
                    f"Sản phẩm {product_code} đã bị xóa hoặc ngừng kinh doanh."
                )

            if (
                as_decimal(current[0]) != as_decimal(item["price"])
                or as_decimal(current[1]) != as_decimal(item["vat"])
            ):
                raise RuntimeError(
                    f"Giá bán hoặc VAT của sản phẩm {product_code} đã thay đổi "
                    "trong lúc lập hóa đơn. Hãy đóng biểu mẫu và lập lại hóa đơn."
                )

        if promotion_code:
            cursor.execute("""
                SELECT TYLEGIAM
                FROM dbo.CHUONG_TRINH_KM WITH (UPDLOCK, HOLDLOCK)
                WHERE MAKM = ?
                  AND NGAYBD <= SYSDATETIME()
                  AND NGAYKT >= SYSDATETIME()
                  AND ISNULL(IS_DELETED, 0) = 0
            """, promotion_code)
            promotion = cursor.fetchone()
            if (
                promotion is None
                or as_decimal(promotion[0]) != as_decimal(expected_discount_rate)
            ):
                raise RuntimeError(
                    "Chương trình khuyến mãi đã hết hạn hoặc thay đổi tỷ lệ giảm. "
                    "Hãy tải lại biểu mẫu trước khi thanh toán."
                )

    @staticmethod
    def _assert_active_shift(cursor, employee, shift):
        """Xác thực lại nhân viên và ca ngay trong transaction lưu hóa đơn."""
        employee_code = (employee or {}).get("manv")
        shift_code = (shift or {}).get("maca")
        if not employee_code or shift_code is None:
            raise RuntimeError(
                "Không xác định được nhân viên hoặc ca làm việc hiện tại."
            )

        cursor.execute("""
            SELECT TOP (1) C.MACA
            FROM dbo.NHAN_VIEN NV WITH (UPDLOCK, HOLDLOCK)
            INNER JOIN dbo.LAMCA L WITH (UPDLOCK, HOLDLOCK)
                ON L.MANV = NV.MANV
            INNER JOIN dbo.CA_LAM_VIEC C WITH (UPDLOCK, HOLDLOCK)
                ON C.MACA = L.MACA
            WHERE NV.MANV = ?
              AND C.MACA = ?
              AND CAST(C.NGAYLAM AS date) = CAST(SYSDATETIME() AS date)
              AND CAST(SYSDATETIME() AS time) >= C.TGMO
              AND CAST(SYSDATETIME() AS time) < C.TGDONG
              AND C.TMCUOICA IS NULL
        """, employee_code, shift_code)

        if cursor.fetchone() is None:
            raise RuntimeError(
                "Ca làm việc của bạn đã kết thúc, đã được chốt hoặc "
                "không còn đăng ký hiệu lực. Hóa đơn chưa được lưu."
            )

    def save_invoice(self):
        """Kiểm tra giỏ hàng, ca làm việc và thanh toán trước khi ghi hóa đơn cùng chi tiết vào SQL Server."""
        if not self.cart:
            QMessageBox.warning(
                self, "Thông báo", "Hóa đơn chưa có sản phẩm."
            )
            return

        try:
            cash = self._parse_cash(self.cash_input.text())
        except ValueError as error:
            QMessageBox.warning(
                self, "Thông tin chưa hợp lệ", str(error)
            )
            return

        _, _, total = self._calculate_totals()
        if cash < total:
            QMessageBox.warning(
                self, "Chưa đủ tiền",
                f"Khách cần trả {money(total)} nhưng mới đưa {money(cash)}."
            )
            return

        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(
                self, "Thông báo", "Chưa có kết nối database."
            )
            return

        cursor = conn.cursor()
        invoice_code = None
        try:
            # Admin được phép lập hóa đơn mà không cần đăng ký ca.
            # Các tài khoản khác phải còn thuộc đúng ca tại thời điểm bấm Lưu.
            if not self.is_admin:
                self._assert_active_shift(
                    cursor, self.employee, self.active_shift
                )

            # Recheck giá, VAT và khuyến mãi để tránh áp dụng dữ liệu đã cũ.
            promotion_code = self.promotion_combo.currentData()
            expected_discount_rate = self.promotions.get(
                promotion_code, Decimal("0")
            )
            self._assert_cart_prices_unchanged(
                cursor, self.cart, promotion_code, expected_discount_rate
            )

            # Khóa bảng trong transaction để hạn chế sinh trùng mã hóa đơn.
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
            # Hóa đơn mới mặc định TRANGTHAI = 1 (đã thanh toán/có hiệu lực).
            cursor.execute("""
                INSERT INTO dbo.HOA_DON
                    (MAHD, NGAYLAP, TIENKHACHDUA,
                     TRANGTHAI, MANV, MAKM, MACA)
                VALUES (?, SYSDATETIME(), ?, 1, ?, ?, ?)
            """, (
                invoice_code, cash, self.employee["manv"],
                promotion_code, shift["maca"] if shift else None
            ))

            for masp, item in self.cart.items():
                # Trừ tồn kho có điều kiện để không bán vượt số lượng tồn.
                cursor.execute("""
                    UPDATE dbo.SAN_PHAM
                    SET SLTON = SLTON - ?
                    WHERE MASP = ?
                      AND ISNULL(IS_DELETED, 0) = 0
                      AND SLTON >= ?
                """, (
                    item["quantity"], masp, item["quantity"]
                ))
                if cursor.rowcount != 1:
                    raise RuntimeError(
                        f"Sản phẩm {masp} không còn đủ tồn kho. "
                        "Hóa đơn chưa được lưu."
                    )

                # Lưu đơn giá đã gồm VAT và thuế suất tại thời điểm bán.
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
                f"Đã tạo hóa đơn {invoice_code}.\n"
                f"Tiền thừa: {money(cash - total)}"
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





