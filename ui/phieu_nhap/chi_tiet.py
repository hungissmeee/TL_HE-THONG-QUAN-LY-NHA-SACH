"""ImportDetailDialog: thành phần giao diện nghiệp vụ phiếu nhập."""

from html import escape
from PySide6.QtCore import (
    Qt,
    QMarginsF,
)
from PySide6.QtGui import (
    QTextDocument,
    QPageSize,
    QPageLayout,
)
from PySide6.QtPrintSupport import (
    QPrinter,
    QPrintDialog,
)
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QTableWidget,
    QHeaderView,
    QAbstractItemView,
    QGroupBox,
    QComboBox,
    QLineEdit,
    QMessageBox,
)
from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table,
)
from .dung_chung import Decimal, money, as_decimal, date_text
from core.phieu_nhap.repository import PhieuNhapRepository
from core.phieu_nhap.service import PhieuNhapService


class ImportDetailDialog(QDialog):
    """Hiển thị thông tin chung, hàng hóa và nội dung in của phiếu nhập."""
    """Chi tiết và in phiếu nhập khổ A4."""

    def __init__(
        self, db, import_code, parent=None, on_cancel=None,
        can_edit=False, can_edit_header=None, has_later_stock_movement=False
    ):
        super().__init__(parent)
        self.db = db
        self.service = PhieuNhapService(PhieuNhapRepository(db))
        self.import_code = import_code
        self.on_cancel = on_cancel
        self.can_edit = bool(can_edit)
        self.can_edit_header = bool(can_edit if can_edit_header is None else can_edit_header)
        self.has_later_stock_movement = bool(has_later_stock_movement)
        self.username = (getattr(db, "username", "") or "").strip()
        self.is_admin = self.username.casefold() == "admin"
        self.employee = self.service.get_employee(self.username, self.is_admin)
        self.header = None
        self.items = []
        self._load_import()
        self.setWindowTitle(f"Chi tiết phiếu nhập {import_code}")
        self.resize(900, 650)
        self._build_ui()

    def _load_import(self):
        data = self.service.get_import_detail(
            self.import_code, self.username, self.is_admin
        )
        self.header = data["header"]
        self.has_later_stock_movement = bool(
            self.header.get("has_later_stock_movement")
        )
        self.header["total"] = as_decimal(self.header.get("total"))
        self.header["status"] = int(self.header.get("status") or 0)
        for detail in data["items"]:
            quantity = int(detail.get("quantity") or 0)
            price = as_decimal(detail.get("price"))
            self.items.append({
                "masp": detail.get("masp"),
                "tensp": detail.get("tensp") or "",
                "dvt": detail.get("dvt") or "",
                "quantity": quantity,
                "price": price,
                "vat": as_decimal(detail.get("vat")),
                "amount": price * quantity,
            })

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
        if h.get("history_check_incomplete"):
            warning_text = (
                "Tài khoản hiện tại không có quyền xem lịch sử đổi trả trong SQL Server. "
                "Chỉ được sửa thông tin chung; quản lý hoặc Admin cần kiểm tra và xử lý chi tiết/hủy phiếu."
            )
        elif self.has_later_stock_movement:
            warning_text = (
                "Có ít nhất một sản phẩm trong phiếu đã phát sinh giao dịch kho sau ngày nhập. "
                "Hệ thống khóa chỉnh sửa chi tiết và hủy toàn bộ phiếu để bảo toàn lịch sử tồn kho."
            )
        else:
            warning_text = ""
        if warning_text:
            warning = QLabel(warning_text)
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #B45309;")
            root.addWidget(warning)

        if self.can_edit_header and h["status"] == 1:
            header_edit = QGroupBox("Chỉnh sửa thông tin chung")
            header_form = QFormLayout(header_edit)
            self.supplier_combo = QComboBox()
            current_supplier = str(h.get("mancc") or "")
            supplier_rows = self.service.list_suppliers_for_import()
            supplier_codes = set()
            for code, name in supplier_rows:
                self.supplier_combo.addItem(f"{name} ({code})", code)
                supplier_codes.add(code)
            if current_supplier and current_supplier not in supplier_codes:
                self.supplier_combo.addItem(
                    f"{h.get('tenncc') or current_supplier} ({current_supplier}) - không hoạt động",
                    current_supplier,
                )
            current_index = self.supplier_combo.findData(current_supplier)
            if current_index >= 0:
                self.supplier_combo.setCurrentIndex(current_index)
            self.supplier_invoice_input = QLineEdit(str(h.get("shdncc") or ""))
            self.supplier_invoice_input.setMaxLength(50)
            self.supplier_invoice_input.setPlaceholderText(
                "Số hóa đơn/chứng từ của nhà cung cấp (nếu có)"
            )
            header_form.addRow("Nhà cung cấp:", self.supplier_combo)
            header_form.addRow("Số HĐ nhà cung cấp:", self.supplier_invoice_input)
            save_header_button = QPushButton("Lưu thông tin chung")
            save_header_button.clicked.connect(self.save_import_header)
            header_form.addRow(save_header_button)
            root.addWidget(header_edit)

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
        if (
            self.can_edit and self.header["status"] == 1
            and not self.has_later_stock_movement
        ):
            edit_details_button = QPushButton("Sửa chi tiết hàng hóa")
            edit_details_button.clicked.connect(self.edit_import_details)
            buttons.addWidget(edit_details_button)
        if (
            self.on_cancel is not None and self.header["status"] == 1
            and not self.has_later_stock_movement
        ):
            cancel_button = QPushButton("Hủy phiếu nhập")
            cancel_button.setObjectName("dangerButton")
            cancel_button.clicked.connect(self.cancel_import)
            buttons.addWidget(cancel_button)

        print_button = QPushButton("In phiếu nhập")
        print_button.clicked.connect(self.print_import)
        close_button = QPushButton("Đóng")
        close_button.clicked.connect(self.reject)
        buttons.addWidget(print_button)
        buttons.addWidget(close_button)
        root.addLayout(buttons)

    def save_import_header(self):
        """Chỉ cập nhật nhà cung cấp và số hóa đơn NCC."""
        supplier_code = self.supplier_combo.currentData()
        if not supplier_code:
            QMessageBox.warning(
                self, "Thiếu nhà cung cấp",
                "Vui lòng chọn nhà cung cấp hợp lệ."
            )
            return
        try:
            self.service.update_import_header(
                self.import_code, supplier_code,
                self.supplier_invoice_input.text(),
                self.username, self.employee.get("vaitro"),
                is_admin=self.is_admin,
            )
            QMessageBox.information(
                self, "Cập nhật thành công",
                "Thông tin nhà cung cấp và số hóa đơn đã được cập nhật. "
                "Ngày nhập, nhân viên lập, loại phiếu và mã phiếu được giữ nguyên."
            )
            self.accept()
        except (ValueError, LookupError, PermissionError) as error:
            QMessageBox.warning(self, "Không thể cập nhật thông tin", str(error))
        except Exception as error:
            QMessageBox.critical(
                self, "Lỗi cập nhật thông tin",
                f"{error}\n\nMọi thay đổi đã được hoàn tác."
            )

    def edit_import_details(self):
        """Mở màn hình sửa hàng hóa nếu phiếu chưa có giao dịch kho phát sinh sau."""
        from .tao_bieu_mau import EditImportDialog

        dialog = EditImportDialog(
            self.db,
            {"header": self.header, "items": self.items},
            self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.accept()

    def cancel_import(self):
        """Gọi quy trình hủy phiếu nhập có kiểm tra quyền và cập nhật tồn kho."""
        if self.on_cancel is None or self.has_later_stock_movement:
            return
        callback = self.on_cancel
        self.accept()
        callback()

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
          <h1>HỆ THỐNG QUẢN LÝ NHÀ SÁCH</h1>
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





