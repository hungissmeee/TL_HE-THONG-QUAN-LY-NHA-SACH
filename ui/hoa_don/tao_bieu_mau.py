"""CreateInvoiceDialog: thành phần giao diện nghiệp vụ hóa đơn."""

from PySide6.QtCore import Qt, QStringListModel, QTimer
from PySide6.QtWidgets import (
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
    QGroupBox,
)
from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
)
from ui.product_table import ProductTableWidget
from .dung_chung import MONEY_QUANT, Decimal, InvalidOperation, ROUND_HALF_UP, money, as_decimal, date_text, time_text
from ui.permissions import is_admin_account
from ui.san_pham.tim_kiem import find_matching_product_codes
from core.repositories.hoa_don_repository import HoaDonRepository
from core.services.hoa_don_service import HoaDonService


class CreateInvoiceDialog(QDialog):
    """Hộp thoại lập hóa đơn, quản lý sản phẩm trong giỏ và tính số tiền khách phải trả."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.service = HoaDonService(HoaDonRepository(db))
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
        data = self.service.get_employee_and_active_shift(
            self.username, is_admin=self.is_admin
        )
        self.employee = data["employee"]
        self.active_shift = data["active_shift"]

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

        products_group = QGroupBox("Thêm sản phẩm")
        products_layout = QVBoxLayout(products_group)
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
        self.product_completer.activated.connect(
            self.add_completed_product
        )
        self.product_search.returnPressed.connect(self.add_selected_product)

        search_row.addWidget(self.product_search, 1)
        products_layout.addLayout(search_row)

        search_hint = QLabel(
            "Chọn một kết quả gợi ý hoặc nhập chính xác mã sản phẩm rồi nhấn Enter. "
            "Số lượng được điều chỉnh ngay trong giỏ hàng."
        )
        search_hint.setWordWrap(True)
        search_hint.setStyleSheet("color: #AAB7C8; font-size: 11px;")
        products_layout.addWidget(search_hint)
        root.addWidget(products_group)

        cart_group = QGroupBox("Giỏ hàng")
        cart_layout = QVBoxLayout(cart_group)
        self.cart_table = ProductTableWidget(
            [
                "Mã SP", "Tên sản phẩm", "Số lượng",
                "Đơn giá (đã gồm VAT)", "VAT (%)", "Thành tiền", "Thao tác"
            ],
            stretch_column=1,
            parent=self,
        )
        self.cart_table.setMinimumHeight(170)
        cart_layout.addWidget(self.cart_table)
        root.addWidget(cart_group, 3)

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
    def _set_cell(table, row, column, value, data=None):
        """Gán nội dung cho ô bảng và áp dụng căn lề phù hợp."""
        item = QTableWidgetItem("" if value is None else str(value))
        if data is not None:
            item.setData(Qt.ItemDataRole.UserRole, data)
        table.setItem(row, column, item)

    def _load_promotions(self):
        for code, name, rate in self.service.list_active_promotions():
            self.promotion_combo.addItem(f"{name} ({rate}%)", code)
            self.promotions[code] = as_decimal(rate)

    def search_products(self, *_):
        products = self.service.list_available_products()
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
                f"Tồn: {product['stock']} | Giá: {money(product['price'])}"
            )
        self.product_suggestion_model.setStringList(suggestions)

    def _add_product_to_cart(self, masp):
        """Thêm một sản phẩm vào giỏ; thêm lại cùng mã sẽ tăng số lượng một đơn vị."""
        product = self.products.get(str(masp))
        if product is None:
            QMessageBox.information(
                self, "Không tìm thấy sản phẩm",
                "Sản phẩm không còn trong danh sách kinh doanh."
            )
            return

        current_quantity = int(
            self.cart.get(masp, {}).get("quantity", 0)
        )
        if current_quantity + 1 > product["stock"]:
            QMessageBox.warning(
                self, "Không đủ tồn kho",
                f"{product['tensp']} chỉ còn {product['stock']} sản phẩm."
            )
            return

        if masp in self.cart:
            self.cart[masp]["quantity"] += 1
        else:
            self.cart[masp] = {**product, "quantity": 1}

        self._refresh_cart()
        self.update_totals()
        # QCompleter có thể ghi lại completion sau khi signal activated kết thúc.
        # Đặt clear/focus vào lượt event kế tiếp để nội dung không bị điền lại.
        QTimer.singleShot(50, self._reset_product_search)

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
        """Thêm sản phẩm khi người dùng chọn một gợi ý trong ô tìm kiếm."""
        masp = str(completion or "").split(" | ", 1)[0].strip()
        if masp:
            self._add_product_to_cart(masp)

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
                "Không có sản phẩm còn hàng phù hợp với mã sản phẩm, mã vạch, ISBN hoặc tên.",
            )

    def _refresh_cart(self):
        """Cập nhật giỏ hàng với bộ điều chỉnh số lượng ngay trên từng dòng."""
        self.cart_table.setRowCount(0)
        for row_index, (masp, item) in enumerate(self.cart.items()):
            line_total = item["price"] * item["quantity"]
            self.cart_table.insert_product_row(row_index)

            self._set_cell(self.cart_table, row_index, 0, masp)
            self._set_cell(self.cart_table, row_index, 1, item["tensp"])
            self._set_cell(self.cart_table, row_index, 3, money(item["price"]))
            self._set_cell(self.cart_table, row_index, 4, money(item["vat"]))
            self._set_cell(self.cart_table, row_index, 5, money(line_total))

            quantity = QSpinBox(self.cart_table)
            quantity.setRange(1, max(1, int(item["stock"])))
            quantity.setValue(int(item["quantity"]))
            quantity.setMinimumHeight(34)
            quantity.valueChanged.connect(
                lambda value, code=masp: self._update_cart_quantity(code, value)
            )
            self.cart_table.setCellWidget(row_index, 2, quantity)

            remove_button = QPushButton("Bỏ")
            remove_button.setObjectName("dangerButton")
            remove_button.clicked.connect(
                lambda _checked=False, product_code=masp:
                self._remove_cart_item(product_code)
            )
            self.cart_table.setCellWidget(row_index, 6, remove_button)

    def _update_cart_quantity(self, masp, quantity):
        """Đồng bộ số lượng ở giỏ và cập nhật thành tiền, tổng thanh toán."""
        item = self.cart.get(masp)
        if item is None:
            return
        quantity = int(quantity)
        if quantity < 1 or quantity > int(item["stock"]):
            return
        item["quantity"] = quantity

        for row in range(self.cart_table.rowCount()):
            code_item = self.cart_table.item(row, 0)
            if code_item and code_item.text() == masp:
                amount_item = self.cart_table.item(row, 5)
                if amount_item is not None:
                    amount_item.setText(money(item["price"] * quantity))
                break
        self.update_totals()

    def _remove_cart_item(self, masp):
        """Bỏ một sản phẩm trực tiếp từ giỏ hàng."""
        self.cart.pop(masp, None)
        self._refresh_cart()
        self.update_totals()

    def remove_selected_cart_item(self):
        """Tương thích với thao tác xóa theo dòng đang chọn."""
        row = self.cart_table.currentRow()
        item = self.cart_table.item(row, 0) if row >= 0 else None
        if item is not None:
            self._remove_cart_item(item.text())

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
    def _assert_cart_prices_unchanged(cursor, cart, promotion_code, expected_discount_rate):
        return HoaDonRepository.assert_cart_prices_unchanged(
            cursor, cart, promotion_code, expected_discount_rate
        )

    @staticmethod
    def _assert_active_shift(cursor, employee, shift):
        return HoaDonRepository.assert_active_shift(cursor, employee, shift)

    def save_invoice(self):
        if not self.cart:
            QMessageBox.warning(self, "Thông báo", "Hóa đơn chưa có sản phẩm.")
            return
        try:
            cash = self._parse_cash(self.cash_input.text())
            promotion_code = self.promotion_combo.currentData()
            payload = {
                "employee": self.employee,
                "active_shift": self.active_shift,
                "cart": self.cart,
                "promotion_code": promotion_code,
                "discount_rate": self.promotions.get(promotion_code, Decimal("0")),
                "cash": cash,
            }
            invoice_code = self.service.create_invoice(
                payload, is_admin=self.is_admin
            )
            _, _, total = self._calculate_totals()
            self.saved_invoice_code = invoice_code
            QMessageBox.information(
                self, "Thành công",
                f"Đã tạo hóa đơn {invoice_code}.\n"
                f"Tiền thừa: {money(cash - total)}"
            )
            self.accept()
        except (ValueError, PermissionError) as error:
            QMessageBox.warning(self, "Thông tin chưa hợp lệ", str(error))
        except Exception as error:
            QMessageBox.critical(
                self, "Không thể tạo hóa đơn",
                f"{error}\n\nCác thay đổi trong giao dịch đã được hoàn tác."
            )
