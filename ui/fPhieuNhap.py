from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html import escape

from PySide6.QtCore import Qt, QDate, QSizeF, QMarginsF, QTimer
from PySide6.QtGui import QTextDocument, QPageSize, QPageLayout
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtWidgets import (
    QWidget, QDialog, QLabel, QPushButton, QLineEdit, QComboBox,
    QVBoxLayout, QHBoxLayout, QFormLayout, QTableWidget, QHeaderView, QAbstractItemView, QMessageBox,
    QSpinBox, QDoubleSpinBox, QGroupBox, QDateEdit
)

from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table,
    pause_table_sorting,
    resume_table_sorting,
)


MONEY_QUANT = Decimal("0.01")


def money(value):
    try:
        amount = Decimal(str(value or 0)).quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP
        )
    except (InvalidOperation, ValueError, TypeError):
        amount = Decimal("0.00")
    return f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def as_decimal(value):
    try:
        return Decimal(str(value or 0)).quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP
        )
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")


def date_text(value):
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y %H:%M:%S")
    return str(value)


class CreateSupplierDialog(QDialog):
    """Thêm nhanh nhà cung cấp để có thể lập phiếu nhập."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.saved_supplier = None
        self.setWindowTitle("Thêm nhà cung cấp")
        self.setMinimumWidth(460)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        title = QLabel("THÊM NHÀ CUNG CẤP")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        root.addWidget(title)

        form_box = QGroupBox("Thông tin nhà cung cấp")
        form = QFormLayout(form_box)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Tên nhà cung cấp")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Số điện thoại")
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Địa chỉ")
        self.tax_input = QLineEdit()
        self.tax_input.setPlaceholderText("Mã số thuế (nếu có)")
        form.addRow("Tên nhà cung cấp *:", self.name_input)
        form.addRow("Số điện thoại:", self.phone_input)
        form.addRow("Địa chỉ:", self.address_input)
        form.addRow("Mã số thuế:", self.tax_input)
        root.addWidget(form_box)

        buttons = QHBoxLayout()
        buttons.addStretch()
        save = QPushButton("Lưu nhà cung cấp")
        save.clicked.connect(self.save_supplier)
        close = QPushButton("Đóng")
        close.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(close)
        root.addLayout(buttons)

    def save_supplier(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên nhà cung cấp.")
            return

        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối SQL Server.")
            return

        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT COALESCE(
                    MAX(TRY_CONVERT(BIGINT, SUBSTRING(MANCC, 4, 17))), 0
                )
                FROM dbo.NHA_CUNG_CAP WITH (TABLOCKX, HOLDLOCK)
                WHERE UPPER(LEFT(MANCC, 3)) = 'NCC'
                  AND TRY_CONVERT(BIGINT, SUBSTRING(MANCC, 4, 17)) IS NOT NULL
            """)
            next_number = int(cursor.fetchone()[0] or 0) + 1
            code = f"NCC{next_number:03d}"
            cursor.execute("""
                INSERT INTO dbo.NHA_CUNG_CAP
                    (MANCC, SDT, TENNCC, DIACHI, MST, IS_DELETED)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (
                code,
                self.phone_input.text().strip() or None,
                name,
                self.address_input.text().strip() or None,
                self.tax_input.text().strip() or None,
            ))
            conn.commit()
            self.saved_supplier = (code, name)
            QMessageBox.information(
                self, "Thành công", f"Đã thêm nhà cung cấp {code} - {name}."
            )
            self.accept()
        except Exception as error:
            conn.rollback()
            QMessageBox.critical(self, "Không thể thêm nhà cung cấp", str(error))
        finally:
            cursor.close()


class CreateImportDialog(QDialog):
    """Lập phiếu nhập; đơn giá nhập được nhập theo giá đã gồm VAT."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.username = (getattr(db, "username", "") or "").strip()
        self.employee = None
        self.suppliers = {}
        self.products = {}
        self.cart = {}
        self.saved_import_code = None

        self.setWindowTitle("Lập phiếu nhập")
        self.resize(1120, 780)
        self.setMinimumSize(940, 680)

        self._load_employee()
        self._build_ui()
        self.load_suppliers()
        self.search_products()
        self.update_total()

    def _load_employee(self):
        conn = self.db.get_connection()
        if conn is None:
            raise RuntimeError("Chưa có kết nối SQL Server.")
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT MANV, TENNV, VAITRO
                FROM dbo.NHAN_VIEN
                WHERE MANV = ?
            """, self.username)
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError(
                    "Tài khoản đăng nhập chưa có hồ sơ tương ứng trong NHAN_VIEN."
                )
            self.employee = {
                "manv": row[0],
                "tennv": row[1] or row[0],
                "vaitro": row[2] or "",
            }
        finally:
            cursor.close()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(9)

        title = QLabel("LẬP PHIẾU NHẬP KHO")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        root.addWidget(title)

        info_box = QGroupBox("Thông tin phiếu nhập")
        info_form = QFormLayout(info_box)
        self.employee_label = QLabel(
            f"{self.employee['tennv']} ({self.employee['manv']})"
        )
        self.supplier_combo = QComboBox()
        self.supplier_combo.setMinimumWidth(300)
        supplier_row = QHBoxLayout()
        supplier_row.addWidget(self.supplier_combo, 1)
        self.add_supplier_button = QPushButton("+ Nhà cung cấp")
        can_add_supplier = (
            self.username.casefold() == "admin"
            or self.employee["vaitro"].casefold() == "quản lý"
        )
        self.add_supplier_button.setVisible(can_add_supplier)
        self.add_supplier_button.clicked.connect(self.add_supplier)
        supplier_row.addWidget(self.add_supplier_button)
        supplier_widget = QWidget()
        supplier_widget.setLayout(supplier_row)

        self.import_type_combo = QComboBox()
        self.import_type_combo.addItems([
            "Nhập mua", "Nhập bổ sung", "Nhập khác"
        ])
        self.supplier_invoice_input = QLineEdit()
        self.supplier_invoice_input.setPlaceholderText(
            "Số hóa đơn/chứng từ của nhà cung cấp (nếu có)"
        )
        info_form.addRow("Nhân viên lập:", self.employee_label)
        info_form.addRow("Nhà cung cấp:", supplier_widget)
        info_form.addRow("Loại phiếu nhập:", self.import_type_combo)
        info_form.addRow("Số HĐ nhà cung cấp:", self.supplier_invoice_input)
        root.addWidget(info_box)

        product_box = QGroupBox("Chọn sản phẩm nhập kho")
        product_layout = QVBoxLayout(product_box)
        search_row = QHBoxLayout()
        self.product_search = QLineEdit()
        self.product_search.setPlaceholderText("Tìm theo mã hoặc tên sản phẩm...")
        self.product_search.textChanged.connect(self.search_products)
        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 999999)
        self.quantity_input.setValue(1)
        self.price_input = QDoubleSpinBox()
        self.price_input.setDecimals(2)
        self.price_input.setRange(0, 999999999999.99)
        self.price_input.setGroupSeparatorShown(True)
        self.price_input.setSuffix(" đ")
        self.price_input.setToolTip("Đơn giá nhập đã bao gồm VAT.")
        self.add_product_button = QPushButton("Thêm vào phiếu")
        self.add_product_button.clicked.connect(self.add_selected_product)
        search_row.addWidget(self.product_search, 2)
        search_row.addWidget(QLabel("Số lượng:"))
        search_row.addWidget(self.quantity_input)
        search_row.addWidget(QLabel("Đơn giá nhập:"))
        search_row.addWidget(self.price_input, 1)
        search_row.addWidget(self.add_product_button)
        product_layout.addLayout(search_row)

        self.product_table = QTableWidget(0, 6)
        self.product_table.setHorizontalHeaderLabels([
            "Mã SP", "Tên sản phẩm", "ĐVT", "Giá nhập hiện tại",
            "Tồn kho", "VAT (%)"
        ])
        self._configure_table(
            self.product_table,
            stretch_column=1,
            default_sort_column=1
        )
        self.product_table.cellClicked.connect(self.select_product_row)
        self.product_table.cellDoubleClicked.connect(
            lambda *_: self.add_selected_product()
        )
        product_layout.addWidget(self.product_table)
        root.addWidget(product_box, 2)

        cart_box = QGroupBox("Sản phẩm trong phiếu nhập")
        cart_layout = QVBoxLayout(cart_box)
        self.cart_table = QTableWidget(0, 7)
        self.cart_table.setHorizontalHeaderLabels([
            "Mã SP", "Tên sản phẩm", "ĐVT", "Số lượng",
            "Đơn giá (đã gồm VAT)", "VAT (%)", "Thành tiền"
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
        root.addWidget(cart_box, 2)

        bottom = QHBoxLayout()
        total_box = QGroupBox("Tổng giá trị phiếu nhập")
        total_layout = QFormLayout(total_box)
        self.total_label = QLabel("0,00")
        self.total_label.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #16A34A;"
        )
        total_layout.addRow("Tổng tiền hàng (đã gồm VAT):", self.total_label)
        total_layout.addRow(
            "Ghi chú:",
            QLabel("VAT được lưu để tham chiếu; không cộng lại vào đơn giá.")
        )
        bottom.addWidget(total_box, 2)

        actions = QVBoxLayout()
        actions.addStretch()
        self.save_button = QPushButton("Lưu phiếu nhập")
        self.save_button.clicked.connect(self.save_import)
        close_button = QPushButton("Đóng")
        close_button.clicked.connect(self.reject)
        actions.addWidget(self.save_button)
        actions.addWidget(close_button)
        bottom.addLayout(actions, 1)
        root.addLayout(bottom)

    @staticmethod
    def _configure_table(
            table,
            stretch_column=None,
            default_sort_column=0
    ):
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
    def _set_cell(table, row, column, value):
        table.setItem(row, column, QTableWidgetItem(
            "" if value is None else str(value)
        ))

    def load_suppliers(self, selected_code=None):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT MANCC, TENNCC
                FROM dbo.NHA_CUNG_CAP
                WHERE ISNULL(IS_DELETED, 0) = 0
                ORDER BY TENNCC, MANCC
            """)
            rows = cursor.fetchall()
            self.supplier_combo.clear()
            self.suppliers = {}
            for row in rows:
                code, name = str(row[0]), str(row[1] or "")
                self.suppliers[code] = name
                self.supplier_combo.addItem(f"{name} ({code})", code)
            if selected_code:
                index = self.supplier_combo.findData(selected_code)
                if index >= 0:
                    self.supplier_combo.setCurrentIndex(index)
            if not rows:
                self.supplier_combo.addItem("Chưa có nhà cung cấp", None)
        finally:
            cursor.close()

    def add_supplier(self):
        dialog = CreateSupplierDialog(self.db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved_supplier:
            self.load_suppliers(dialog.saved_supplier[0])

    def search_products(self, *_):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        keyword = self.product_search.text().strip()
        try:
            cursor.execute("""
                SELECT MASP, TENSP, DVT, GIANHAP, SLTON, VAT
                FROM dbo.SAN_PHAM
                WHERE ISNULL(IS_DELETED, 0) = 0
                  AND (MASP LIKE ? OR TENSP LIKE ?)
                ORDER BY TENSP, MASP
            """, (f"%{keyword}%", f"%{keyword}%"))
            rows = cursor.fetchall()

            pause_table_sorting(self.product_table)

            self.product_table.setRowCount(0)
            self.products = {}
            for index, row in enumerate(rows):
                code, name, unit, cost, stock, vat = row
                self.products[str(code)] = {
                    "masp": str(code),
                    "tensp": str(name or ""),
                    "dvt": str(unit or ""),
                    "price": as_decimal(cost),
                    "stock": int(stock or 0),
                    "vat": as_decimal(vat),
                }
                self.product_table.insertRow(index)
                values = [
                    code, name, unit, money(cost), int(stock or 0),
                    money(vat)
                ]
                for column, value in enumerate(values):
                    self._set_cell(self.product_table, index, column, value)
        except Exception as error:
            QMessageBox.critical(self, "Lỗi tải sản phẩm", str(error))
        finally:
            resume_table_sorting(self.product_table)
            cursor.close()

    def select_product_row(self, row, column):
        item = self.product_table.item(row, 0)
        if item is None:
            return
        product = self.products.get(item.text())
        if product:
            self.price_input.setValue(float(product["price"]))

    def add_selected_product(self):
        row = self.product_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Chưa chọn sản phẩm", "Vui lòng chọn sản phẩm cần nhập.")
            return
        item = self.product_table.item(row, 0)
        if item is None:
            return
        code = item.text().strip()
        product = self.products.get(code)
        if not product:
            return

        quantity = int(self.quantity_input.value())
        unit_price = as_decimal(self.price_input.value())
        if unit_price <= 0:
            QMessageBox.warning(
                self, "Đơn giá không hợp lệ",
                "Vui lòng nhập đơn giá nhập lớn hơn 0."
            )
            return

        if code in self.cart:
            old = self.cart[code]
            old_quantity = int(old["quantity"])
            new_quantity = old_quantity + quantity
            # Bảng chi tiết có khóa chính (MAPN, MASP), gộp cùng mã SP thành một dòng.
            total_cost = old["price"] * old_quantity + unit_price * quantity
            old["price"] = (total_cost / Decimal(new_quantity)).quantize(
                MONEY_QUANT, rounding=ROUND_HALF_UP
            )
            old["quantity"] = new_quantity
        else:
            self.cart[code] = {
                **product,
                "price": unit_price,
                "quantity": quantity,
            }

        self.refresh_cart()
        self.update_total()

    def refresh_cart(self):
        pause_table_sorting(self.cart_table)

        try:
            self.cart_table.setRowCount(0)

            for index, (code, item) in enumerate(self.cart.items()):
                amount = item["price"] * item["quantity"]

                self.cart_table.insertRow(index)

                values = [
                    code,
                    item["tensp"],
                    item["dvt"],
                    item["quantity"],
                    money(item["price"]),
                    money(item["vat"]),
                    money(amount)
                ]

                for column, value in enumerate(values):
                    self._set_cell(
                        self.cart_table, index, column, value
                    )

        finally:
            resume_table_sorting(self.cart_table)

    def remove_selected_cart_item(self):
        row = self.cart_table.currentRow()
        if row < 0:
            return
        item = self.cart_table.item(row, 0)
        if item:
            self.cart.pop(item.text(), None)
            self.refresh_cart()
            self.update_total()

    def calculate_total(self):
        return sum(
            (item["price"] * item["quantity"] for item in self.cart.values()),
            Decimal("0.00")
        ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    def update_total(self):
        self.total_label.setText(money(self.calculate_total()))

    def _next_import_code(self, cursor):
        cursor.execute("""
            SELECT COALESCE(
                MAX(TRY_CONVERT(BIGINT, SUBSTRING(MAPN, 3, 18))), 0
            )
            FROM dbo.PHIEU_NHAP WITH (TABLOCKX, HOLDLOCK)
            WHERE UPPER(LEFT(MAPN, 2)) = 'PN'
              AND TRY_CONVERT(BIGINT, SUBSTRING(MAPN, 3, 18)) IS NOT NULL
        """)
        next_number = int(cursor.fetchone()[0] or 0) + 1
        code = f"PN{next_number:06d}"
        if len(code) > 20:
            raise ValueError("Đã vượt giới hạn độ dài mã phiếu nhập.")
        return code

    def save_import(self):
        supplier_code = self.supplier_combo.currentData()
        if not supplier_code:
            QMessageBox.warning(
                self, "Thiếu nhà cung cấp",
                "Vui lòng thêm hoặc chọn nhà cung cấp trước khi lập phiếu nhập."
            )
            return
        if not self.cart:
            QMessageBox.warning(
                self, "Chưa có sản phẩm", "Phiếu nhập chưa có sản phẩm nào."
            )
            return

        supplier_invoice = self.supplier_invoice_input.text().strip() or None
        total = self.calculate_total()
        answer = QMessageBox.question(
            self,
            "Xác nhận lập phiếu nhập",
            f"Nhà cung cấp: {self.suppliers.get(supplier_code, '')}\n"
            f"Số mặt hàng: {len(self.cart)}\n"
            f"Tổng giá trị: {money(total)} đồng\n\n"
            "Khi lưu, tồn kho và giá nhập bình quân sẽ được cập nhật. Tiếp tục?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối SQL Server.")
            return
        cursor = conn.cursor()
        try:
            if supplier_invoice:
                cursor.execute("""
                    SELECT 1
                    FROM dbo.PHIEU_NHAP WITH (UPDLOCK, HOLDLOCK)
                    WHERE MANCC = ? AND SHDNCC = ?
                      AND ISNULL(TRANGTHAI, 1) = 1
                """, supplier_code, supplier_invoice)
                if cursor.fetchone():
                    raise ValueError(
                        "Số hóa đơn nhà cung cấp này đã được ghi nhận cho nhà cung cấp đã chọn."
                    )

            import_code = self._next_import_code(cursor)
            cursor.execute("""
                INSERT INTO dbo.PHIEU_NHAP
                    (MAPN, NGAYNHAP, LOAIPHIEUNHAP, SHDNCC,
                     TONGTRIGIA, MANV, MANCC, TRANGTHAI)
                VALUES (?, SYSDATETIME(), ?, ?, ?, ?, ?, 1)
            """, (
                import_code,
                self.import_type_combo.currentText(),
                supplier_invoice,
                total,
                self.username,
                supplier_code,
            ))

            for code, item in self.cart.items():
                quantity = int(item["quantity"])
                price = item["price"]

                # GIANHAP được cập nhật theo giá nhập bình quân gia quyền,
                # với đơn giá đã gồm VAT để thống nhất với cách lưu GIABAN.
                cursor.execute("""
                    UPDATE dbo.SAN_PHAM
                    SET
                        GIANHAP = CAST(
                            (
                                CAST(ISNULL(SLTON, 0) AS DECIMAL(18, 2))
                                * CAST(ISNULL(GIANHAP, 0) AS DECIMAL(18, 2))
                                + CAST(? AS DECIMAL(18, 2))
                                  * CAST(? AS DECIMAL(10, 0))
                            )
                            / NULLIF(
                                CAST(ISNULL(SLTON, 0) AS DECIMAL(18, 2))
                                + CAST(? AS DECIMAL(18, 2)), 0
                            )
                            AS DECIMAL(15, 2)
                        ),
                        SLTON = ISNULL(SLTON, 0) + ?
                    WHERE MASP = ?
                      AND ISNULL(IS_DELETED, 0) = 0
                """, (price, quantity, quantity, quantity, code))
                if cursor.rowcount != 1:
                    raise RuntimeError(
                        f"Không tìm thấy sản phẩm {code} hoặc sản phẩm đã bị ngừng sử dụng."
                    )

                cursor.execute("""
                    INSERT INTO dbo.CHI_TIET_PHIEU_NHAP
                        (MAPN, MASP, DONGIA, SOLUONG, VAT)
                    VALUES (?, ?, ?, ?, ?)
                """, (import_code, code, price, quantity, item["vat"]))

            conn.commit()
            self.saved_import_code = import_code
            QMessageBox.information(
                self, "Lập phiếu nhập thành công",
                f"Đã tạo phiếu nhập {import_code}.\n"
                f"Tổng giá trị: {money(total)} đồng.\n"
                "Tồn kho và giá nhập bình quân đã được cập nhật."
            )
            self.accept()
        except ValueError as error:
            conn.rollback()
            QMessageBox.warning(self, "Thông tin chưa hợp lệ", str(error))
        except Exception as error:
            conn.rollback()
            message = str(error)
            if "permission" in message.lower() or "denied" in message.lower():
                message += (
                    "\n\nTài khoản cần quyền SELECT/INSERT trên PHIEU_NHAP, "
                    "CHI_TIET_PHIEU_NHAP và quyền UPDATE cột SLTON, GIANHAP "
                    "trên SAN_PHAM."
                )
            QMessageBox.critical(
                self, "Không thể lập phiếu nhập",
                f"{message}\n\nGiao dịch đã được hoàn tác; tồn kho không bị cập nhật dở dang."
            )
        finally:
            cursor.close()


class ImportDetailDialog(QDialog):
    """Chi tiết và in phiếu nhập khổ A4."""

    def __init__(self, db, import_code, parent=None):
        super().__init__(parent)
        self.db = db
        self.import_code = import_code
        self.header = None
        self.items = []
        self._load_import()
        self.setWindowTitle(f"Chi tiết phiếu nhập {import_code}")
        self.resize(900, 650)
        self._build_ui()

    def _load_import(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    PN.MAPN, PN.NGAYNHAP, PN.LOAIPHIEUNHAP, PN.SHDNCC,
                    PN.TONGTRIGIA, PN.MANV, NV.TENNV,
                    PN.MANCC, NCC.TENNCC, NCC.SDT, NCC.DIACHI, NCC.MST,
                    PN.TRANGTHAI
                FROM dbo.PHIEU_NHAP PN
                LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = PN.MANV
                LEFT JOIN dbo.NHA_CUNG_CAP NCC ON NCC.MANCC = PN.MANCC
                WHERE PN.MAPN = ?
            """, self.import_code)
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("Không tìm thấy phiếu nhập.")
            self.header = {
                "mapn": row[0], "ngaynhap": row[1], "loai": row[2],
                "shdncc": row[3], "total": as_decimal(row[4]),
                "manv": row[5], "tennv": row[6], "mancc": row[7],
                "tenncc": row[8], "sdt": row[9], "diachi": row[10],
                "mst": row[11], "status": int(row[12] or 0),
            }

            cursor.execute("""
                SELECT CT.MASP, SP.TENSP, SP.DVT,
                       CT.SOLUONG, CT.DONGIA, CT.VAT
                FROM dbo.CHI_TIET_PHIEU_NHAP CT
                LEFT JOIN dbo.SAN_PHAM SP ON SP.MASP = CT.MASP
                WHERE CT.MAPN = ?
                ORDER BY SP.TENSP, CT.MASP
            """, self.import_code)
            for detail in cursor.fetchall():
                quantity = int(detail[3] or 0)
                price = as_decimal(detail[4])
                self.items.append({
                    "masp": detail[0], "tensp": detail[1] or "",
                    "dvt": detail[2] or "", "quantity": quantity,
                    "price": price, "vat": as_decimal(detail[5]),
                    "amount": price * quantity,
                })
        finally:
            cursor.close()

    def _build_ui(self):
        root = QVBoxLayout(self)
        title = QLabel("CHI TIẾT PHIẾU NHẬP")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        root.addWidget(title)

        info = QGroupBox("Thông tin phiếu nhập")
        form = QFormLayout(info)
        h = self.header
        status_text = "Đã hủy" if h["status"] == 0 else "Có hiệu lực"
        form.addRow("Mã phiếu nhập:", QLabel(str(h["mapn"])))
        form.addRow("Ngày nhập:", QLabel(date_text(h["ngaynhap"])))
        form.addRow("Loại phiếu:", QLabel(str(h["loai"] or "")))
        form.addRow("Nhà cung cấp:", QLabel(
            f"{h['tenncc'] or ''} ({h['mancc'] or ''})"
        ))
        form.addRow("Số HĐ nhà cung cấp:", QLabel(str(h["shdncc"] or "Không có")))
        form.addRow("Nhân viên lập:", QLabel(
            f"{h['tennv'] or ''} ({h['manv'] or ''})"
        ))
        form.addRow("Trạng thái:", QLabel(status_text))
        root.addWidget(info)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Mã SP", "Tên sản phẩm", "ĐVT", "Số lượng",
            "Đơn giá (đã gồm VAT)", "VAT (%)", "Thành tiền"
        ])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        for index, item in enumerate(self.items):
            self.table.insertRow(index)
            values = [
                item["masp"], item["tensp"], item["dvt"],
                item["quantity"], money(item["price"]),
                money(item["vat"]), money(item["amount"])
            ]
            for column, value in enumerate(values):
                self.table.setItem(index, column, QTableWidgetItem(str(value or "")))
        prepare_sortable_table(self.table)
        root.addWidget(self.table, 1)

        total = sum((item["amount"] for item in self.items), Decimal("0.00"))
        total_label = QLabel(money(total))
        total_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #16A34A;")
        summary = QGroupBox("Tổng giá trị")
        summary_form = QFormLayout(summary)
        summary_form.addRow("Tổng tiền hàng (đã gồm VAT):", total_label)
        root.addWidget(summary)

        buttons = QHBoxLayout()
        buttons.addStretch()
        print_button = QPushButton("In phiếu nhập")
        print_button.clicked.connect(self.print_import)
        close_button = QPushButton("Đóng")
        close_button.clicked.connect(self.accept)
        buttons.addWidget(print_button)
        buttons.addWidget(close_button)
        root.addLayout(buttons)

    def _build_print_html(self):
        h = self.header
        total = sum((item["amount"] for item in self.items), Decimal("0.00"))
        status = "ĐÃ HỦY" if h["status"] == 0 else "CÓ HIỆU LỰC"
        item_rows = []
        for index, item in enumerate(self.items, 1):
            item_rows.append(
                "<tr>"
                f"<td>{index}</td>"
                f"<td>{escape(str(item['masp'] or ''))}</td>"
                f"<td>{escape(str(item['tensp'] or ''))}</td>"
                f"<td class='right'>{item['quantity']}</td>"
                f"<td class='right'>{money(item['price'])}</td>"
                f"<td class='right'>{money(item['vat'])}%</td>"
                f"<td class='right'>{money(item['amount'])}</td>"
                "</tr>"
            )
        rows_html = "".join(item_rows) or "<tr><td colspan='7'>Không có chi tiết</td></tr>"
        return f"""
        <!DOCTYPE html><html><head><meta charset='utf-8'>
        <style>
          body {{ font-family: Arial, sans-serif; color: #111; font-size: 10pt; }}
          h1 {{ text-align: center; font-size: 20pt; margin-bottom: 2px; }}
          h2 {{ text-align: center; font-size: 14pt; margin-top: 8px; }}
          .center {{ text-align: center; }}
          .meta {{ line-height: 1.55; margin: 18px 0; }}
          table {{ width: 100%; border-collapse: collapse; margin-top: 14px; }}
          th, td {{ border: 1px solid #555; padding: 6px; }}
          th {{ background: #eee; }}
          .right {{ text-align: right; }}
          .total {{ text-align: right; font-weight: bold; font-size: 13pt; margin-top: 14px; }}
          .sign {{ margin-top: 55px; display: flex; justify-content: space-between; }}
        </style></head><body>
          <h1>BOOKHUB</h1>
          <div class='center'>HỆ THỐNG QUẢN LÝ NHÀ SÁCH</div>
          <h2>PHIẾU NHẬP KHO</h2>
          <div class='meta'>
            <b>Mã phiếu:</b> {escape(str(h['mapn']))}<br>
            <b>Ngày nhập:</b> {escape(date_text(h['ngaynhap']))}<br>
            <b>Loại phiếu:</b> {escape(str(h['loai'] or ''))}<br>
            <b>Nhà cung cấp:</b> {escape(str(h['tenncc'] or ''))} ({escape(str(h['mancc'] or ''))})<br>
            <b>Địa chỉ NCC:</b> {escape(str(h['diachi'] or ''))}<br>
            <b>MST:</b> {escape(str(h['mst'] or ''))}<br>
            <b>Số HĐ NCC:</b> {escape(str(h['shdncc'] or 'Không có'))}<br>
            <b>Nhân viên lập:</b> {escape(str(h['tennv'] or ''))} ({escape(str(h['manv'] or ''))})<br>
            <b>Trạng thái:</b> {status}
          </div>
          <p><b>CHI TIẾT SẢN PHẨM</b> — Đơn giá đã bao gồm VAT.</p>
          <table><thead><tr><th>STT</th><th>Mã SP</th><th>Sản phẩm</th><th>SL</th><th>Đơn giá</th><th>VAT</th><th>Thành tiền</th></tr></thead>
          <tbody>{rows_html}</tbody></table>
          <p class='total'>TỔNG GIÁ TRỊ: {money(total)} đồng</p>
          <div class='sign'><span>Người giao hàng</span><span>Người nhận hàng</span><span>Người lập phiếu</span></div>
        </body></html>
        """

    def print_import(self):
        document = QTextDocument()
        document.setHtml(self._build_print_html())
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageMargins(QMarginsF(12, 12, 12, 12), QPageLayout.Unit.Millimeter)
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("In phiếu nhập")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        document.print_(printer)


class ImportWindow(QWidget):
    """Danh sách, tìm kiếm, lập, xem/in và hủy phiếu nhập."""

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.username = (getattr(db, "username", "") or "").strip()
        self.employee_role = self._get_employee_role()
        self.is_admin = self.username.casefold() == "admin"
        self.is_manager = self.employee_role.casefold() == "quản lý"
        self.is_warehouse = self.employee_role.casefold() == "nhân viên kho"
        self.can_create = self.is_admin or self.is_manager or self.is_warehouse
        self.can_cancel = self.is_admin or self.is_manager or self.is_warehouse
        self._build_ui()
        self.load_imports()

        # Khóa nút hủy của Nhân viên kho sau khi hết giới hạn 5 phút.
        self._cancel_permission_timer = QTimer(self)
        self._cancel_permission_timer.setInterval(5000)
        self._cancel_permission_timer.timeout.connect(self.update_action_buttons)
        self._cancel_permission_timer.start()

    def _get_employee_role(self):
        if self.username.casefold() == "admin":
            return "Quản lý"
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
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(10)

        top = QHBoxLayout()
        title = QLabel("QUẢN LÝ PHIẾU NHẬP")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        top.addWidget(title)
        top.addStretch()
        self.create_button = QPushButton("+ Lập phiếu nhập")
        self.create_button.setVisible(self.can_create)
        self.create_button.clicked.connect(self.open_create_import)
        top.addWidget(self.create_button)
        refresh_button = QPushButton("Làm mới")
        refresh_button.clicked.connect(self.load_imports)
        top.addWidget(refresh_button)
        root.addLayout(top)

        filters = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Tìm mã phiếu, số HĐ NCC, nhà cung cấp hoặc nhân viên..."
        )
        self.search_input.returnPressed.connect(self.load_imports)
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("dd/MM/yyyy")
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("dd/MM/yyyy")
        self.to_date.setDate(QDate.currentDate())
        search_button = QPushButton("Tìm kiếm")
        search_button.clicked.connect(self.load_imports)
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

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "Mã phiếu", "Ngày nhập", "Nhà cung cấp", "Nhân viên lập",
            "Loại phiếu", "Số HĐ NCC", "Tổng giá trị", "Trạng thái"
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
        self.table.cellDoubleClicked.connect(self.open_import_detail)
        self.table.itemSelectionChanged.connect(self.update_action_buttons)
        root.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        self.total_label = QLabel("Tổng số phiếu nhập: 0")
        bottom.addWidget(self.total_label)
        bottom.addStretch()
        detail_button = QPushButton("Xem chi tiết / In phiếu")
        detail_button.clicked.connect(self.open_selected_import)
        bottom.addWidget(detail_button)
        self.cancel_button = QPushButton("Hủy phiếu nhập")
        self.cancel_button.setVisible(self.can_cancel)
        self.cancel_button.setEnabled(False)
        self.cancel_button.setStyleSheet("""
            QPushButton:enabled { background-color: #A83232; color: white; }
            QPushButton:disabled { color: #888888; }
        """)
        self.cancel_button.clicked.connect(self.cancel_selected_import)
        bottom.addWidget(self.cancel_button)
        root.addLayout(bottom)

    def clear_filters(self):
        self.search_input.clear()
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.to_date.setDate(QDate.currentDate())
        self.load_imports()

    def load_imports(self):
        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối SQL Server.")
            return
        if self.from_date.date() > self.to_date.date():
            QMessageBox.warning(self, "Khoảng ngày không hợp lệ", "Ngày bắt đầu không được lớn hơn ngày kết thúc.")
            return

        cursor = conn.cursor()
        keyword = self.search_input.text().strip()
        sql = """
            SELECT
                PN.MAPN, PN.NGAYNHAP, PN.MANV, NV.TENNV,
                PN.MANCC, NCC.TENNCC, PN.LOAIPHIEUNHAP,
                PN.SHDNCC, PN.TONGTRIGIA, ISNULL(PN.TRANGTHAI, 1)
            FROM dbo.PHIEU_NHAP PN
            LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = PN.MANV
            LEFT JOIN dbo.NHA_CUNG_CAP NCC ON NCC.MANCC = PN.MANCC
            WHERE PN.NGAYNHAP >= ?
              AND PN.NGAYNHAP < DATEADD(DAY, 1, CAST(? AS date))
        """
        params = [
            self.from_date.date().toString("yyyy-MM-dd"),
            self.to_date.date().toString("yyyy-MM-dd"),
        ]
        if keyword:
            like = f"%{keyword}%"
            sql += """ AND (
                PN.MAPN LIKE ? OR PN.SHDNCC LIKE ? OR PN.MANV LIKE ?
                OR NV.TENNV LIKE ? OR PN.MANCC LIKE ? OR NCC.TENNCC LIKE ?
            )"""
            params.extend([like] * 6)
        sql += " ORDER BY PN.NGAYNHAP DESC, PN.MAPN DESC"

        try:
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()

            pause_table_sorting(self.table)

            self.table.setRowCount(0)
            for index, row in enumerate(rows):
                self.table.insertRow(index)
                status = "Có hiệu lực" if int(row[9] or 0) == 1 else "Đã hủy"
                supplier = f"{row[5] or ''} ({row[4] or ''})"
                employee = f"{row[3] or ''} ({row[2] or ''})"
                values = [
                    row[0], date_text(row[1]), supplier, employee,
                    row[6], row[7], money(row[8]), status
                ]
                for column, value in enumerate(values):
                    item = QTableWidgetItem(str(value or ""))
                    if column == 0:
                        item.setData(Qt.ItemDataRole.UserRole, str(row[2] or "").strip())
                        item.setData(Qt.ItemDataRole.UserRole + 1, row[9])
                        item.setData(Qt.ItemDataRole.UserRole + 2, row[1])
                    self.table.setItem(index, column, item)
            self.total_label.setText(f"Tổng số phiếu nhập: {len(rows)}")
            self.update_action_buttons()
        except Exception as error:
            QMessageBox.critical(self, "Lỗi tải phiếu nhập", str(error))
        finally:
            resume_table_sorting(self.table)
            cursor.close()

    def update_action_buttons(self):
        if not self.can_cancel:
            self.cancel_button.setEnabled(False)
            return
        row = self.table.currentRow()
        if row < 0:
            self.cancel_button.setEnabled(False)
            return
        code_item = self.table.item(row, 0)
        if code_item is None:
            self.cancel_button.setEnabled(False)
            return
        status = int(code_item.data(Qt.ItemDataRole.UserRole + 1) or 0)
        if status != 1:
            self.cancel_button.setEnabled(False)
            return
        if self.is_admin or self.is_manager:
            self.cancel_button.setEnabled(True)
            return

        owner = str(code_item.data(Qt.ItemDataRole.UserRole) or "")
        can_cancel = self.is_warehouse and owner.casefold() == self.username.casefold()
        if can_cancel:
            conn = self.db.get_connection()
            cursor = None
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT CASE WHEN NGAYNHAP >= DATEADD(MINUTE, -5, SYSDATETIME())
                                     AND NGAYNHAP <= SYSDATETIME()
                                THEN 1 ELSE 0 END
                    FROM dbo.PHIEU_NHAP WHERE MAPN = ? AND MANV = ?
                      AND ISNULL(TRANGTHAI, 1) = 1
                """, self.table.item(row, 0).text(), self.username)
                result = cursor.fetchone()
                can_cancel = bool(result and result[0] == 1)
            except Exception:
                can_cancel = False
            finally:
                if cursor is not None:
                    cursor.close()
        self.cancel_button.setEnabled(can_cancel)

    def cancel_selected_import(self):
        if not self.can_cancel:
            QMessageBox.warning(
                self, "Không có quyền", "Tài khoản của bạn không có quyền hủy phiếu nhập."
            )
            return
        row = self.table.currentRow()
        if row < 0:
            return
        code_item = self.table.item(row, 0)
        if code_item is None:
            return
        import_code = code_item.text().strip()
        owner = str(code_item.data(Qt.ItemDataRole.UserRole) or "")
        if self.is_warehouse and not (self.is_admin or self.is_manager):
            if owner.casefold() != self.username.casefold():
                QMessageBox.warning(self, "Không có quyền", "Nhân viên kho chỉ được hủy phiếu do mình lập.")
                return

        answer = QMessageBox.question(
            self, "Xác nhận hủy phiếu nhập",
            f"Bạn có chắc chắn muốn hủy phiếu nhập {import_code}?\n\n"
            "Hệ thống sẽ trừ lại số lượng đã nhập khỏi tồn kho.\n"
            "Không thể hủy nếu tồn kho hiện tại không đủ số lượng để hoàn tác.\n"
            "Phiếu nhập vẫn được giữ lại trong lịch sử với trạng thái Đã hủy.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT TRANGTHAI, MANV,
                       CASE WHEN NGAYNHAP >= DATEADD(MINUTE, -5, SYSDATETIME())
                                  AND NGAYNHAP <= SYSDATETIME()
                            THEN 1 ELSE 0 END
                FROM dbo.PHIEU_NHAP WITH (UPDLOCK, HOLDLOCK)
                WHERE MAPN = ?
            """, import_code)
            header = cursor.fetchone()
            if header is None:
                raise RuntimeError("Không tìm thấy phiếu nhập.")
            if int(header[0] or 0) != 1:
                raise RuntimeError("Phiếu nhập đã bị hủy trước đó.")

            if self.is_warehouse and not (self.is_admin or self.is_manager):
                if str(header[1] or "").casefold() != self.username.casefold():
                    raise PermissionError("Nhân viên kho chỉ được hủy phiếu do mình lập.")
                if int(header[2] or 0) != 1:
                    raise PermissionError("Chỉ được hủy phiếu do mình lập trong vòng 5 phút.")

            cursor.execute("""
                SELECT MASP, SUM(ISNULL(SOLUONG, 0))
                FROM dbo.CHI_TIET_PHIEU_NHAP WITH (UPDLOCK, HOLDLOCK)
                WHERE MAPN = ?
                GROUP BY MASP
            """, import_code)
            details = cursor.fetchall()
            if not details:
                raise RuntimeError("Phiếu nhập không có chi tiết sản phẩm.")

            for detail in details:
                product_code = str(detail[0])
                quantity = int(detail[1] or 0)
                if quantity <= 0:
                    raise RuntimeError(f"Số lượng nhập của {product_code} không hợp lệ.")
                cursor.execute("""
                    UPDATE dbo.SAN_PHAM
                    SET SLTON = SLTON - ?
                    WHERE MASP = ? AND ISNULL(SLTON, 0) >= ?
                """, quantity, product_code, quantity)
                if cursor.rowcount != 1:
                    raise RuntimeError(
                        f"Không thể hủy phiếu vì tồn kho {product_code} không còn đủ "
                        f"{quantity} sản phẩm để hoàn tác. Hãy kiểm tra các giao dịch liên quan."
                    )

            cursor.execute("""
                UPDATE dbo.PHIEU_NHAP
                SET TRANGTHAI = 0
                WHERE MAPN = ? AND TRANGTHAI = 1
            """, import_code)
            if cursor.rowcount != 1:
                raise RuntimeError("Không thể cập nhật trạng thái phiếu nhập.")

            # Tính lại GIANHAP theo bình quân gia quyền của các phiếu nhập còn hiệu lực.
            for detail in details:
                product_code = str(detail[0])
                cursor.execute("""
                    UPDATE SP
                    SET GIANHAP = CAST(COALESCE(T.AVG_COST, 0) AS DECIMAL(15, 2))
                    FROM dbo.SAN_PHAM SP
                    OUTER APPLY (
                        SELECT SUM(CT.DONGIA * CT.SOLUONG)
                               / NULLIF(SUM(CT.SOLUONG), 0) AS AVG_COST
                        FROM dbo.CHI_TIET_PHIEU_NHAP CT
                        INNER JOIN dbo.PHIEU_NHAP PN ON PN.MAPN = CT.MAPN
                        WHERE CT.MASP = SP.MASP
                          AND ISNULL(PN.TRANGTHAI, 1) = 1
                    ) T
                    WHERE SP.MASP = ?
                """, product_code)

            conn.commit()
            QMessageBox.information(
                self, "Đã hủy phiếu nhập",
                f"Phiếu {import_code} đã được hủy và tồn kho đã được hoàn tác."
            )
            self.load_imports()
        except Exception as error:
            conn.rollback()
            QMessageBox.critical(
                self, "Không thể hủy phiếu nhập",
                f"{error}\n\nMọi thay đổi đã được hoàn tác."
            )
            self.load_imports()
        finally:
            cursor.close()

    def open_selected_import(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Chưa chọn phiếu", "Vui lòng chọn phiếu nhập.")
            return
        item = self.table.item(row, 0)
        if item:
            self.open_import_detail(row, 0)

    def open_import_detail(self, row, column):
        item = self.table.item(row, 0)
        if item is None:
            return
        try:
            dialog = ImportDetailDialog(self.db, item.text(), self)
            dialog.exec()
        except Exception as error:
            QMessageBox.critical(self, "Lỗi xem phiếu nhập", str(error))

    def open_create_import(self):
        if not self.can_create:
            QMessageBox.warning(self, "Không có quyền", "Tài khoản không có quyền lập phiếu nhập.")
            return
        try:
            dialog = CreateImportDialog(self.db, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_imports()
                if dialog.saved_import_code:
                    answer = QMessageBox.question(
                        self, "In phiếu nhập",
                        f"Đã tạo phiếu nhập {dialog.saved_import_code}. Bạn có muốn in ngay không?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )
                    if answer == QMessageBox.StandardButton.Yes:
                        detail = ImportDetailDialog(
                            self.db, dialog.saved_import_code, self
                        )
                        detail.print_import()
        except Exception as error:
            QMessageBox.critical(self, "Không thể lập phiếu nhập", str(error))
