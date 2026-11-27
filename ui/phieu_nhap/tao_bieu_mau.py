"""CreateImportDialog: thành phần giao diện nghiệp vụ phiếu nhập."""

from PySide6.QtCore import Qt, QLocale, QStringListModel, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QDialog,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QCompleter,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QMessageBox,
    QSpinBox,
    QDoubleSpinBox,
    QGroupBox,
)
from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
)
from ui.product_table import ProductTableWidget
from .dung_chung import MONEY_QUANT, Decimal, ROUND_HALF_UP, money, as_decimal
from .tao_nha_cung_cap import CreateSupplierDialog
from ui.permissions import is_admin_account
from ui.san_pham.tim_kiem import find_matching_product_codes
from core.phieu_nhap.repository import PhieuNhapRepository
from core.phieu_nhap.service import PhieuNhapService


class CreateImportDialog(QDialog):
    """Hộp thoại lập phiếu nhập, quản lý nhà cung cấp, sản phẩm và số lượng nhập."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.service = PhieuNhapService(PhieuNhapRepository(db))
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
        self.employee = self.service.get_employee(self.username, self.is_admin)

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
        self.supplier_combo.setEditable(True)
        self.supplier_combo.setInsertPolicy(
            QComboBox.InsertPolicy.NoInsert
        )
        self.supplier_combo.lineEdit().setPlaceholderText(
            "Nhập mã hoặc tên nhà cung cấp để tìm..."
        )
        supplier_completer = self.supplier_combo.completer()
        supplier_completer.setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
        )
        supplier_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        supplier_completer.setCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )
        self.supplier_combo.setToolTip(
            "Có thể gõ một phần mã hoặc tên nhà cung cấp rồi chọn kết quả."
        )
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

        product_box = QGroupBox("Thêm sản phẩm nhập kho")
        product_layout = QVBoxLayout(product_box)
        search_row = QHBoxLayout()

        self.product_search = QLineEdit()
        self.product_search.setPlaceholderText(
            "Nhập mã hoặc tên sản phẩm, sau đó chọn gợi ý..."
        )
        self.product_search.setMinimumHeight(42)
        self.product_suggestion_model = QStringListModel(self)
        self.product_completer = QCompleter(self.product_suggestion_model, self)
        self.product_completer.setCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )
        self.product_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.product_completer.setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
        )
        self.product_search.setCompleter(self.product_completer)
        self.product_completer.activated.connect(self.add_completed_product)
        self.product_search.returnPressed.connect(self.add_selected_product)

        search_row.addWidget(self.product_search, 1)
        product_layout.addLayout(search_row)

        search_hint = QLabel(
            "Chọn kết quả gợi ý hoặc nhập chính xác mã sản phẩm rồi nhấn Enter. "
            "Số lượng và đơn giá nhập được chỉnh ngay trong giỏ hàng."
        )
        search_hint.setWordWrap(True)
        search_hint.setStyleSheet("color: #AAB7C8; font-size: 11px;")
        product_layout.addWidget(search_hint)
        root.addWidget(product_box)

        cart_box = QGroupBox("Sản phẩm trong phiếu nhập")
        cart_layout = QVBoxLayout(cart_box)
        self.cart_table = ProductTableWidget(
            [
                "Mã SP", "Tên sản phẩm", "ĐVT", "Số lượng",
                "Đơn giá nhập (đã gồm VAT)", "VAT (%)", "Thành tiền", "Thao tác"
            ],
            stretch_column=1,
            parent=self,
        )
        cart_layout.addWidget(self.cart_table)
        root.addWidget(cart_box, 3)

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
        self.save_button.setProperty("buttonRole", "primary")
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(self.save_import)
        close_button = QPushButton("Đóng")
        close_button.clicked.connect(self.reject)
        actions.addWidget(self.save_button)
        actions.addWidget(close_button)
        bottom.addLayout(actions, 1)
        root.addLayout(bottom)

    @staticmethod
    def _set_cell(table, row, column, value):
        """Gán giá trị cho ô bảng với căn lề phù hợp."""
        table.setItem(row, column, QTableWidgetItem(
            "" if value is None else str(value)
        ))

    def _selected_supplier_code(self):
        """Chỉ trả mã khi nội dung ô nhập khớp một nhà cung cấp trong danh sách."""
        typed_text = self.supplier_combo.currentText().strip()
        if not typed_text:
            return None

        index = self.supplier_combo.findText(
            typed_text,
            Qt.MatchFlag.MatchFixedString,
        )
        if index < 0:
            return None

        code = self.supplier_combo.itemData(index)
        return str(code).strip() if code else None

    def load_suppliers(self, selected_code=None):
        rows = self.service.list_suppliers_for_import()
        self.supplier_combo.clear()
        self.suppliers = {}
        for code, name in rows:
            self.suppliers[code] = name
            self.supplier_combo.addItem(f"{name} ({code})", code)
        if selected_code:
            index = self.supplier_combo.findData(selected_code)
            if index >= 0:
                self.supplier_combo.setCurrentIndex(index)
        if not rows:
            self.supplier_combo.addItem("Chưa có nhà cung cấp", None)

    def add_supplier(self):
        """Mở hộp thoại thêm nhanh nhà cung cấp và cập nhật danh sách lựa chọn."""
        dialog = CreateSupplierDialog(self.db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved_supplier:
            self.load_suppliers(dialog.saved_supplier[0])

    def search_products(self, *_):
        products = self.service.list_products_for_import()
        self.products = {}
        suggestions = []
        for product in products:
            code = str(product["masp"])
            product["masp"] = code
            product["tensp"] = str(product["tensp"] or "")
            product["dvt"] = str(product["dvt"] or "")
            product["price"] = as_decimal(product["price"])
            product["stock"] = int(product["stock"] or 0)
            product["vat"] = as_decimal(product["vat"])
            product["barcode"] = str(product["barcode"] or "").strip()
            product["isbn"] = str(product["isbn"] or "").strip()
            self.products[code] = product
            suggestions.append(
                f"{code} | {product['tensp']} | "
                f"Mã vạch: {product['barcode'] or '—'} | "
                f"ISBN: {product['isbn'] or '—'} | "
                f"Giá nhập hiện tại: {money(product['price'])}"
            )
        self.product_suggestion_model.setStringList(suggestions)

    def _reset_product_search(self):
        """Đóng gợi ý, xóa nội dung và trả focus về ô tìm kiếm."""
        self.product_completer.popup().hide()
        self.product_search.blockSignals(True)
        try:
            self.product_search.clear()
        finally:
            self.product_search.blockSignals(False)
        self.product_search.setFocus(Qt.FocusReason.OtherFocusReason)
        self.product_search.setCursorPosition(0)

    def add_completed_product(self, completion):
        """Thêm sản phẩm khi người dùng chọn một gợi ý."""
        code = str(completion or "").split(" | ", 1)[0].strip()
        if code:
            self._add_product_to_cart(code)

    def add_selected_product(self):
        """Thêm sản phẩm theo mã sản phẩm, mã vạch, ISBN hoặc tên."""
        matches = find_matching_product_codes(
            self.products,
            self.product_search.text(),
        )
        if len(matches) == 1:
            self._add_product_to_cart(matches[0])
        elif matches:
            QMessageBox.information(
                self,
                "Chọn sản phẩm",
                "Có nhiều sản phẩm phù hợp. Hãy chọn một kết quả trong danh sách gợi ý.",
            )
            self.product_search.setFocus()
        else:
            QMessageBox.information(
                self,
                "Không tìm thấy",
                "Không có sản phẩm phù hợp với mã sản phẩm, mã vạch, ISBN hoặc tên.",
            )

    def _add_product_to_cart(self, code):
        """Thêm sản phẩm vào giỏ; thêm lại cùng mã sẽ tăng số lượng."""
        product = self.products.get(str(code))
        if product is None:
            return

        if code in self.cart:
            self.cart[code]["quantity"] += 1
        else:
            self.cart[code] = {
                **product,
                "price": product["price"],
                "quantity": 1,
            }

        self.refresh_cart()
        self.update_total()
        # QCompleter có thể ghi lại completion sau khi signal activated kết thúc.
        # Đặt clear/focus vào lượt event kế tiếp để nội dung không bị điền lại.
        QTimer.singleShot(50, self._reset_product_search)

    def refresh_cart(self):
        """Cập nhật giỏ hàng với số lượng và đơn giá chỉnh ngay trên từng dòng."""
        self.cart_table.setRowCount(0)

        for index, (code, item) in enumerate(self.cart.items()):
            self.cart_table.insert_product_row(index)
            self._set_cell(self.cart_table, index, 0, code)
            self._set_cell(self.cart_table, index, 1, item["tensp"])
            self._set_cell(self.cart_table, index, 2, item["dvt"])
            self._set_cell(self.cart_table, index, 5, money(item["vat"]))

            quantity = QSpinBox(self.cart_table)
            quantity.setRange(1, 999999)
            quantity.setValue(int(item["quantity"]))
            quantity.setMinimumHeight(34)
            quantity.valueChanged.connect(
                lambda value, product_code=code:
                self._update_cart_quantity(product_code, value)
            )
            self.cart_table.setCellWidget(index, 3, quantity)

            price = QDoubleSpinBox(self.cart_table)
            price.setLocale(QLocale.c())
            price.setGroupSeparatorShown(False)
            price.setDecimals(2)
            price.setRange(0, 999999999999.99)
            price.setSuffix(" đ")
            price.setValue(float(item["price"]))
            price.setMinimumHeight(34)
            price.valueChanged.connect(
                lambda value, product_code=code:
                self._update_cart_price(product_code, value)
            )
            self.cart_table.setCellWidget(index, 4, price)

            self._set_cell(
                self.cart_table, index, 6,
                money(item["price"] * item["quantity"])
            )

            remove_button = QPushButton("Bỏ")
            remove_button.setObjectName("dangerButton")
            remove_button.clicked.connect(
                lambda _checked=False, product_code=code:
                self._remove_cart_item(product_code)
            )
            self.cart_table.setCellWidget(index, 7, remove_button)

    def _update_cart_quantity(self, code, quantity):
        """Cập nhật số lượng và thành tiền của một mặt hàng trong giỏ."""
        item = self.cart.get(code)
        if item is None:
            return
        item["quantity"] = int(quantity)
        self._update_cart_line_total(code)
        self.update_total()

    def _update_cart_price(self, code, price):
        """Cập nhật đơn giá nhập đã gồm VAT ngay tại dòng giỏ hàng."""
        item = self.cart.get(code)
        if item is None:
            return
        item["price"] = as_decimal(price)
        self._update_cart_line_total(code)
        self.update_total()

    def _update_cart_line_total(self, code):
        item = self.cart.get(code)
        if item is None:
            return
        for row in range(self.cart_table.rowCount()):
            code_item = self.cart_table.item(row, 0)
            if code_item and code_item.text() == code:
                amount_item = self.cart_table.item(row, 6)
                if amount_item is not None:
                    amount_item.setText(
                        money(item["price"] * item["quantity"])
                    )
                break

    def _remove_cart_item(self, code):
        """Bỏ trực tiếp sản phẩm khỏi giỏ."""
        self.cart.pop(code, None)
        self.refresh_cart()
        self.update_total()

    def remove_selected_cart_item(self):
        """Tương thích với lệnh xóa theo dòng đang chọn."""
        row = self.cart_table.currentRow()
        item = self.cart_table.item(row, 0) if row >= 0 else None
        if item is not None:
            self._remove_cart_item(item.text())

    def calculate_total(self):
        """Tính tổng trị giá các dòng hàng trong phiếu nhập."""
        return sum(
            (item["price"] * item["quantity"] for item in self.cart.values()),
            Decimal("0.00")
        ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    def update_total(self):
        """Cập nhật tổng tiền phiếu nhập trên giao diện."""
        self.total_label.setText(money(self.calculate_total()))

    def save_import(self):
        supplier_code = self._selected_supplier_code()
        if not supplier_code:
            QMessageBox.warning(self, "Thiếu nhà cung cấp", "Vui lòng chọn nhà cung cấp.")
            return
        if not self.cart:
            QMessageBox.warning(self, "Chưa có sản phẩm", "Phiếu nhập chưa có sản phẩm nào.")
            return
        total = self.calculate_total()
        answer = QMessageBox.question(
            self, "Xác nhận lập phiếu nhập",
            f"Nhà cung cấp: {self.suppliers.get(supplier_code, '')}\n"
            f"Số mặt hàng: {len(self.cart)}\n"
            f"Tổng giá trị: {money(total)} đồng\n\n"
            "Khi lưu, tồn kho và giá nhập bình quân sẽ được cập nhật. Tiếp tục?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        payload = {
            "supplier_code": supplier_code,
            "supplier_invoice": self.supplier_invoice_input.text().strip() or None,
            "employee_code": self.employee.get("manv"),
            "is_admin": self.is_admin,
            "import_type": self.import_type_combo.currentText(),
            "items": [
                {
                    "product_code": code,
                    "quantity": item["quantity"],
                    "price": item["price"],
                    "vat": item["vat"],
                }
                for code, item in self.cart.items()
            ],
        }
        try:
            import_code = self.service.create_import(payload)
            self.saved_import_code = import_code
            QMessageBox.information(
                self, "Lập phiếu nhập thành công",
                f"Đã tạo phiếu nhập {import_code}.\n"
                f"Tổng giá trị: {money(total)} đồng.\n"
                "Tồn kho và giá nhập bình quân đã được cập nhật.",
            )
            self.accept()
        except (ValueError, LookupError) as error:
            QMessageBox.warning(self, "Thông tin chưa hợp lệ", str(error))
        except Exception as error:
            QMessageBox.critical(
                self, "Không thể lập phiếu nhập",
                f"{error}\n\nGiao dịch đã được hoàn tác; tồn kho không bị cập nhật dở dang.",
            )
