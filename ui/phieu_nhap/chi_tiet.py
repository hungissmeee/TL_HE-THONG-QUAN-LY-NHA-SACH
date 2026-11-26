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
)
from ui.sap_xep_bang import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table,
)
from .dung_chung import Decimal, money, as_decimal, date_text


class ImportDetailDialog(QDialog):
    """Hiển thị thông tin chung, hàng hóa và nội dung in của phiếu nhập."""
    """Hộp thoại xem và in chi tiết phiếu nhập."""
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





