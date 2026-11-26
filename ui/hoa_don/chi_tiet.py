"""InvoiceDetailDialog: thành phần giao diện nghiệp vụ hóa đơn."""

from html import escape
from PySide6.QtCore import (
    QSizeF,
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
)
from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table,
)
from .dung_chung import MONEY_QUANT, Decimal, ROUND_HALF_UP, money, as_decimal, date_text, time_text


class InvoiceDetailDialog(QDialog):
    """Hiển thị thông tin, chi tiết sản phẩm và nội dung in của hóa đơn."""
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
                "mahd": row[0],
                "ngaylap": row[1],
                "cash": as_decimal(row[2]),
                "status": row[3],
                "manv": row[4],
                "tennv": row[5],
                "vaitro": row[6],
                "maca": row[7],
                "soca": row[8],
                "ngaylam": row[9],
                "tgmo": row[10],
                "tgdong": row[11],
                "makm": row[12],
                "tenkm": row[13],
                "discount_rate": as_decimal(row[14]),
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
                # DONGIA đã gồm VAT: không tính thêm VAT vào thành tiền.
                line_total = (price * quantity).quantize(
                    MONEY_QUANT, rounding=ROUND_HALF_UP
                )
                items.append({
                    "masp": item[0],
                    "tensp": item[1] or "(Sản phẩm đã ngừng lưu thông)",
                    "dvt": item[2],
                    "price": price,
                    "quantity": quantity,
                    "vat": vat,
                    "line_total": line_total,
                })
            return header, items
        finally:
            cursor.close()

    def _totals(self):
        # Tổng tiền hàng đã bao gồm VAT.
        subtotal = sum(
            (item["line_total"] for item in self.items),
            Decimal("0.00")
        ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        discount = (
            subtotal * self.header["discount_rate"] / Decimal("100")
        ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        total = (subtotal - discount).quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP
        )
        change = self.header["cash"] - total
        return subtotal, discount, total, change

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
        form.addRow(
            "Nhân viên:",
            QLabel(f"{self.header['tennv'] or ''} ({self.header['manv'] or ''})")
        )
        form.addRow("Vai trò:", QLabel(str(self.header["vaitro"] or "")))
        form.addRow("Ca làm việc:", QLabel(shift_text))
        status = self.header["status"]
        status_text = "Đã hủy" if status == 0 else (
            "Đã thanh toán" if status == 1 else "Không xác định"
        )
        form.addRow("Trạng thái:", QLabel(status_text))
        if self.header["makm"]:
            form.addRow(
                "Khuyến mãi:",
                QLabel(
                    f"{self.header['tenkm'] or self.header['makm']} "
                    f"({money(self.header['discount_rate'])}%)"
                )
            )
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

        for i, item in enumerate(self.items):
            self.table.insertRow(i)
            values = [
                item["masp"], item["tensp"], item["dvt"],
                item["quantity"], money(item["price"]),
                money(item["vat"]), money(item["line_total"])
            ]
            for col, value in enumerate(values):
                self.table.setItem(
                    i, col, QTableWidgetItem(str(value or ""))
                )

        prepare_sortable_table(self.table)

        root.addWidget(self.table, 1)

        subtotal, discount, total, change = self._totals()
        summary = QGroupBox("Thanh toán")
        summary_form = QFormLayout(summary)
        summary_form.addRow(
            "Tiền hàng (đã gồm VAT):", QLabel(money(subtotal))
        )
        summary_form.addRow("Giảm giá:", QLabel(money(discount)))
        total_label = QLabel(money(total))
        total_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #16A34A;"
        )
        summary_form.addRow("Tổng thanh toán:", total_label)
        summary_form.addRow(
            "Tiền khách đưa:", QLabel(money(self.header["cash"]))
        )
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
        """Tạo mẫu hóa đơn nhiệt 80 mm, đơn giá đã bao gồm VAT."""
        h = self.header
        subtotal, discount, total, change = self._totals()

        shift_text = (
            f"Ca {h['soca']} | Mã ca: {h['maca']}<br>"
            f"Ngày ca: {date_text(h['ngaylam'])}<br>"
            f"Giờ ca: {time_text(h['tgmo'])} - {time_text(h['tgdong'])}"
        ) if h["maca"] is not None else "Không có thông tin ca"
        status_text = "ĐÃ HỦY" if h["status"] == 0 else (
            "ĐÃ THANH TOÁN" if h["status"] == 1 else "KHÔNG XÁC ĐỊNH"
        )

        item_rows = []
        for item in self.items:
            item_rows.append(
                "<tr class='item-name-row'>"
                "<td colspan='2'>"
                f"<div class='item-name'>{escape(str(item['tensp'] or ''))}</div>"
                f"<div class='item-code'>Mã: {escape(str(item['masp'] or ''))}"
                f" | ĐVT: {escape(str(item['dvt'] or ''))}</div>"
                f"<div class='item-vat'>VAT: {money(item['vat'])}% (đã gồm trong đơn giá)</div>"
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
            body {{ font-family: Arial, sans-serif; font-size: 8pt; color: #111; margin: 0; padding: 0; }}
            .center {{ text-align: center; }}
            h1 {{ font-size: 15pt; margin: 0 0 2px 0; text-align: center; }}
            h2 {{ font-size: 10pt; margin: 5px 0; text-align: center; }}
            p {{ margin: 3px 0; line-height: 1.2; }}
            .company {{ text-align: center; font-size: 7.5pt; margin-bottom: 5px; }}
            .meta {{ margin: 6px 0; line-height: 1.3; }}
            .dash {{ border-top: 1px dashed #333; margin: 6px 0; }}
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
            .summary {{ width: 100%; table-layout: fixed; }}
            .summary td {{ border: none; padding: 2px 0; vertical-align: top; }}
            .summary td:first-child {{ width: 68%; text-align: left; }}
            .summary td:last-child {{ width: 32%; text-align: right; white-space: nowrap; }}
            .total td {{ border-top: 1px solid #222; padding-top: 5px; font-size: 9pt; font-weight: bold; }}
            .thanks {{ text-align: center; margin-top: 9px; font-weight: bold; }}
            .small {{ text-align: center; font-size: 7pt; margin-top: 3px; }}
        </style></head><body>
            <h1>HỆ THỐNG QUẢN LÝ NHÀ SÁCH</h1>
            <h2>HÓA ĐƠN BÁN HÀNG</h2>
            <div class='meta'>
                <p><b>Mã hóa đơn:</b> {escape(str(h['mahd']))}</p>
                <p><b>Ngày, giờ lập:</b> {escape(date_text(h['ngaylap']))}</p>
                <p><b>Nhân viên:</b> {escape(str(h['tennv'] or ''))}</p>
                <p><b>Mã nhân viên:</b> {escape(str(h['manv'] or ''))}</p>
                <p><b>Vai trò:</b> {escape(str(h['vaitro'] or ''))}</p>
                <p><b>Trạng thái:</b> {status_text}</p>
                <p><b>Ca làm việc:</b><br>{shift_text}</p>
            </div>
            {promo}
            <div class='dash'></div>
            <p><b>CHI TIẾT SẢN PHẨM</b></p>
            <p>Đơn giá đã bao gồm VAT.</p>
            <table class='items' width='100%' cellspacing='0' cellpadding='0'>
                <colgroup><col width='68%'><col width='32%'></colgroup>
                {items_html}
            </table>
            <div class='dash'></div>
            <table class='summary' width='100%' cellspacing='0' cellpadding='0'>
                <colgroup><col width='68%'><col width='32%'></colgroup>
                <tr><td>Tiền hàng (đã gồm VAT)</td><td>{money(subtotal)}</td></tr>
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

        content_height_pt = max(
            document.documentLayout().documentSize().height(), 80.0
        )
        content_height_mm = content_height_pt * 25.4 / 72.0
        paper_height_mm = content_height_mm + 2 * margin_mm + 2.0

        page_size = QPageSize(
            QSizeF(paper_width_mm, paper_height_mm),
            QPageSize.Unit.Millimeter,
            "Hệ thống quản lý nhà sách - Hóa đơn 80mm",
            QPageSize.SizeMatchPolicy.ExactMatch
        )
        margins = QMarginsF(margin_mm, margin_mm, margin_mm, margin_mm)
        document.setPageSize(
            QSizeF(printable_width_pt, content_height_pt + 1.0)
        )

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(page_size)
        printer.setPageMargins(margins, QPageLayout.Unit.Millimeter)

        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("In hóa đơn - giấy nhiệt 80 mm")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        printer.setPageSize(page_size)
        printer.setPageMargins(margins, QPageLayout.Unit.Millimeter)
        document.print_(printer)





