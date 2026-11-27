"""Hộp thoại lập phiếu đổi trả."""

from decimal import Decimal, ROUND_HALF_UP

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFormLayout, QGroupBox, QComboBox, QCompleter, QLineEdit,
    QTableWidgetItem, QMessageBox, QSpinBox,
)

from .dung_chung import MONEY_QUANT, as_decimal, date_text, money
from ui.permissions import is_admin_account
from ui.product_table import ProductTableWidget
from core.doi_tra.repository import ReturnRepository
from core.doi_tra.service import ReturnService


class CreateReturnDialog(QDialog):
    """Lập phiếu hoàn tiền hoặc đổi sản phẩm từ một hóa đơn hợp lệ."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.service = ReturnService(ReturnRepository(db))
        self.username = (getattr(db, "username", "") or "").strip()
        self.is_admin = is_admin_account(self.username)
        self.employee_code = None if self.is_admin else self.username
        self.row_controls = {}
        self.invoice_discount = Decimal("0.00")

        self.setWindowTitle("Lập phiếu đổi trả")
        # Đồng bộ kích thước với biểu mẫu phiếu nhập; vùng bảng có thêm không gian.
        self.resize(1120, 780)
        self.setMinimumSize(980, 680)
        self._ensure_manager()
        self._build_ui()
        self._load_eligible_invoices()

    def _ensure_manager(self, cursor=None):
        """Ủy quyền xác thực vai trò cho Repository."""
        if cursor is not None:
            return ReturnRepository.ensure_manager(
                cursor, self.username, self.is_admin
            )
        conn = self.db.get_connection()
        if conn is None:
            raise RuntimeError("Chưa có kết nối SQL Server.")
        cursor = conn.cursor()
        try:
            self.employee_code = ReturnRepository.ensure_manager(
                cursor, self.username, self.is_admin
            )
        finally:
            cursor.close()

    def _build_ui(self):
        """Tạo giao diện chọn hóa đơn, sản phẩm và hình thức xử lý."""
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(9)

        title = QLabel("LẬP PHIẾU ĐỔI TRẢ")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        root.addWidget(title)

        invoice_group = QGroupBox("Hóa đơn gốc")
        invoice_form = QFormLayout(invoice_group)
        self.invoice_combo = QComboBox()
        self._configure_invoice_selector(self.invoice_combo)
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

        self.table = ProductTableWidget(
            [
                "Mã SP", "Tên sản phẩm", "Đã mua", "Đã xử lý",
                "Còn được xử lý", "Số lượng", "Tình trạng hàng",
                "Hình thức xử lý", "Tiền hoàn"
            ],
            stretch_column=1,
            fixed_column_widths={5: 100},
            parent=self,
        )
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
    def _configure_invoice_selector(combo):
        """Cấu hình ô tìm hóa đơn như combobox tìm kiếm của phiếu nhập.

        Giữ số dòng xổ xuống mặc định của Qt, không ép popup cao hơn màn hình.
        """
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.lineEdit().setPlaceholderText("Nhập mã hóa đơn để tìm...")
        combo.setToolTip(
            "Nhập mã hóa đơn hoặc một phần mã để tìm trong các hóa đơn hợp lệ."
        )
        completer = combo.completer()
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

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
        """Tải hóa đơn đủ điều kiện qua Service."""
        rows = self.service.list_eligible_invoices()
        self.invoice_combo.blockSignals(True)
        self.invoice_combo.clear()
        for code, invoice_date in rows:
            self.invoice_combo.addItem(f"{code} | {date_text(invoice_date)}", code)
        self.invoice_combo.blockSignals(False)
        if not rows:
            self.invoice_combo.addItem("Không có hóa đơn đủ điều kiện trong hôm nay", None)
            self.invoice_combo.setEnabled(False)
            self.save_button.setEnabled(False)
            self.invoice_info.setText("Chỉ được đổi trả trong cùng ngày lập hóa đơn. Hiện không có hóa đơn hợp lệ.")
            return
        self.load_invoice_items()

    def load_invoice_items(self, *_):
        invoice_code = self.invoice_combo.currentData()
        self.table.setRowCount(0)
        self.row_controls.clear()
        if not invoice_code:
            self.update_totals()
            return
        data = self.service.get_invoice_items(invoice_code)
        self.invoice_discount = data["discount_rate"]
        self.invoice_info.setText(
            f"Ngày lập: {date_text(data['invoice_date'])} | "
            f"Giảm giá hóa đơn: {money(self.invoice_discount)}%"
        )
        for product in data["items"]:
            masp = product["product_code"]
            remaining = product["remaining"]
            row = self.table.insert_product_row()
            values = [
                masp, product["product_name"], product["purchased"],
                product["processed"], remaining, "", "", "", money(0)
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
            quantity = QSpinBox(self.table)
            quantity.setRange(0, remaining)
            quantity.setAlignment(Qt.AlignmentFlag.AlignCenter)
            quantity.setMinimumHeight(34)
            quantity.setToolTip(f"Chọn từ 0 đến {remaining}. Đơn vị: {product['unit'] or 'Không xác định'}")
            condition = QComboBox()
            condition.addItem("Còn nguyên vẹn", 1)
            condition.addItem("Đã hỏng", 0)
            action = QComboBox()
            action.addItem("Hoàn tiền", 0)
            action.addItem("Đổi sản phẩm cùng mã", 1)
            self.table.setCellWidget(row, 5, quantity)
            self.table.setCellWidget(row, 6, condition)
            self.table.setCellWidget(row, 7, action)
            self.row_controls[masp] = {
                "row": row, "quantity": quantity, "remaining": remaining,
                "condition": condition, "action": action,
                "net_price": product["net_price"],
            }
            quantity.valueChanged.connect(self.update_totals)
            condition.currentIndexChanged.connect(self.update_totals)
            action.currentIndexChanged.connect(self.update_totals)
        self.save_button.setEnabled(bool(self.row_controls))
        self.update_totals()

    def update_totals(self, *_):
        """Tính tiền hoàn dự kiến; dòng đổi sản phẩm không hoàn tiền."""
        total = Decimal("0.00")
        for controls in self.row_controls.values():
            quantity = self._parse_quantity_input(
                str(controls["quantity"].value())
            )
            condition = controls["condition"].currentData()
            action = controls["action"].currentData()
            amount_item = self.table.item(controls["row"], 8)

            if quantity > 0 and action == 1 and condition != 0:
                amount_item.setText("Chỉ đổi hàng đã hỏng")
                continue

            amount = controls["net_price"] * quantity if action == 0 else Decimal("0")
            amount = amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            total += amount
            amount_item.setText(money(amount))
        self.total_label.setText(f"Tổng tiền hoàn: {money(total)} đ")

    def save_return(self):
        selected = []
        for product_code, controls in self.row_controls.items():
            quantity = self._parse_quantity_input(str(controls["quantity"].value()))
            if quantity <= 0:
                continue
            selected.append({
                "product_code": product_code,
                "quantity": quantity,
                "condition": int(controls["condition"].currentData()),
                "action": int(controls["action"].currentData()),
            })
        try:
            deleted_products = self.service.get_deleted_products_to_restore(selected)
            confirmed_restore_codes = []
            if deleted_products:
                product_lines = "\n".join(
                    f"• {item['product_name']} ({item['product_code']})"
                    for item in deleted_products
                )
                answer = QMessageBox.question(
                    self,
                    "Xác nhận khôi phục sản phẩm",
                    "Các sản phẩm sau đã bị xóa mềm khỏi danh mục:\n\n"
                    f"{product_lines}\n\n"
                    "Hoàn hàng sẽ khôi phục các sản phẩm này, đưa chúng trở lại danh mục "
                    "đang hoạt động và cộng số lượng hàng nhận lại vào tồn kho.\n\n"
                    "Bạn có chắc chắn muốn tiếp tục?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return
                confirmed_restore_codes = [
                    item["product_code"] for item in deleted_products
                ]

            result = self.service.create_return(
                {
                    "invoice_code": self.invoice_combo.currentData(),
                    "reason": self.reason_input.text(),
                    "items": selected,
                },
                self.username,
                is_admin=self.is_admin,
                confirmed_restore_codes=confirmed_restore_codes,
            )
            success_message = (
                f"Đã lập phiếu đổi trả {result['return_code']}.\n"
                f"Hóa đơn: {result['invoice_code']}\n"
                f"Tổng tiền hoàn: {money(result['total_refund'])} đ"
            )
            restored_codes = set(result.get("restored_products") or [])
            if restored_codes:
                restored_names = [
                    f"{item['product_name']} ({item['product_code']})"
                    for item in deleted_products
                    if item["product_code"] in restored_codes
                ]
                success_message += (
                    "\n\nĐã khôi phục sản phẩm:\n"
                    + "\n".join(restored_names)
                )
            QMessageBox.information(self, "Thành công", success_message)
            self.accept()
        except (ValueError, PermissionError) as error:
            QMessageBox.warning(self, "Không thể lập phiếu đổi trả", str(error))
        except Exception as error:
            QMessageBox.critical(
                self, "Không thể lập phiếu đổi trả",
                f"{error}\n\nMọi thay đổi trong giao dịch đã được hoàn tác."
            )
