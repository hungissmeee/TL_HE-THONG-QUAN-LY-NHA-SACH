"""CreateImportDialog: thành phần giao diện nghiệp vụ phiếu nhập."""

from PySide6.QtWidgets import (
    QWidget,
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
    QDoubleSpinBox,
    QGroupBox,
)
from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table,
    pause_table_sorting,
    resume_table_sorting,
)
from .dung_chung import MONEY_QUANT, Decimal, ROUND_HALF_UP, money, as_decimal
from .tao_nha_cung_cap import CreateSupplierDialog
from ui.permissions import is_admin_account


class CreateImportDialog(QDialog):
    """Hộp thoại lập phiếu nhập, quản lý nhà cung cấp, sản phẩm và số lượng nhập."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.username = (getattr(db, "username", "") or "").strip()
        self.is_admin = is_admin_account(self.username)
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
        """Lấy thông tin nhân viên lập phiếu nhập từ tài khoản hiện tại."""
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
            if row is None and not self.is_admin:
                raise RuntimeError(
                    "Tài khoản đăng nhập chưa có hồ sơ tương ứng trong NHAN_VIEN."
                )
            self.employee = {
                "manv": row[0] if row else None,
                "tennv": (row[1] or row[0]) if row else "Admin",
                "vaitro": (row[2] or "") if row else "Quản lý",
            }
        finally:
            cursor.close()

    def _build_ui(self):
        """Tạo biểu mẫu chọn nhà cung cấp, sản phẩm và số lượng nhập."""
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(9)

        title = QLabel("LẬP PHIẾU NHẬP KHO")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        root.addWidget(title)

        info_box = QGroupBox("Thông tin phiếu nhập")
        info_form = QFormLayout(info_box)
        employee_code = self.employee["manv"] or "Tài khoản hệ thống"
        self.employee_label = QLabel(
            f"{self.employee['tennv']} ({employee_code})"
        )
        self.supplier_combo = QComboBox()
        self.supplier_combo.setMinimumWidth(300)
        supplier_row = QHBoxLayout()
        supplier_row.addWidget(self.supplier_combo, 1)
        self.add_supplier_button = QPushButton("+ Nhà cung cấp")
        can_add_supplier = (
            self.is_admin
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
        """Cấu hình bảng sản phẩm và giỏ hàng trong phiếu nhập."""
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
        """Gán giá trị cho ô bảng với căn lề phù hợp."""
        table.setItem(row, column, QTableWidgetItem(
            "" if value is None else str(value)
        ))

    def load_suppliers(self, selected_code=None):
        """Tải nhà cung cấp đang hoạt động để chọn cho phiếu nhập."""
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
        """Mở hộp thoại thêm nhanh nhà cung cấp và cập nhật danh sách lựa chọn."""
        dialog = CreateSupplierDialog(self.db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved_supplier:
            self.load_suppliers(dialog.saved_supplier[0])

    def search_products(self, *_):
        """Tìm sản phẩm có thể nhập kho theo từ khóa."""
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
        """Đưa sản phẩm được chọn vào khu vực nhập số lượng và đơn giá."""
        item = self.product_table.item(row, 0)
        if item is None:
            return
        product = self.products.get(item.text())
        if product:
            self.price_input.setValue(float(product["price"]))

    def add_selected_product(self):
        """Thêm sản phẩm được chọn vào danh sách chi tiết phiếu nhập."""
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
        """Cập nhật bảng các sản phẩm dự kiến nhập."""
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
        """Xóa sản phẩm đang chọn khỏi chi tiết phiếu nhập."""
        row = self.cart_table.currentRow()
        if row < 0:
            return
        item = self.cart_table.item(row, 0)
        if item:
            self.cart.pop(item.text(), None)
            self.refresh_cart()
            self.update_total()

    def calculate_total(self):
        """Tính tổng trị giá các dòng hàng trong phiếu nhập."""
        return sum(
            (item["price"] * item["quantity"] for item in self.cart.values()),
            Decimal("0.00")
        ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    def update_total(self):
        """Cập nhật tổng tiền phiếu nhập trên giao diện."""
        self.total_label.setText(money(self.calculate_total()))

    def _next_import_code(self, cursor):
        """Sinh mã phiếu nhập tiếp theo theo quy tắc hiện có."""
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
        """Kiểm tra dữ liệu và ghi phiếu nhập cùng chi tiết, bảo đảm cập nhật tồn kho trong giao dịch."""
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
                self.employee["manv"],
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





