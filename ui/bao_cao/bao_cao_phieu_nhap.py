"""Báo cáo phiếu nhập hàng."""

from PySide6.QtWidgets import QLabel

from ui.bao_cao.bao_cao_co_so import (
    ReportBasePage, money_text, number_text, date_text,
)


class ImportReportPage(ReportBasePage):
    """Hiển thị số liệu tổng hợp từ các phiếu nhập."""
    def __init__(self, db, parent=None):
        super().__init__(
            db,
            "Báo cáo nhập hàng",
            "Tra cứu toàn bộ phiếu nhập theo nhà cung cấp và nhân viên; số lượng và trị giá thực nhập chỉ tính phiếu còn hiệu lực.",
            True,
            parent,
        )
        self.add_stat_cards([
            ("count", "Số phiếu nhập hợp lệ", "0",
             "Chỉ tính phiếu chưa bị hủy", "neutral"),
            ("quantity", "Số lượng thực nhập", "0",
             "Tổng số lượng của các phiếu còn hiệu lực", "positive"),
            ("amount", "Tổng trị giá thực nhập", "0 đ",
             "Không bao gồm phiếu nhập đã hủy", "primary"),
        ], primary_key="amount")
        self.table = self.make_table([
            "Mã phiếu nhập", "Ngày nhập", "Loại phiếu", "Nhà cung cấp",
            "Số HĐ nhà cung cấp", "Nhân viên lập", "Số lượng nhập", "Tổng trị giá"
        ])
        self.content_layout.addWidget(self.table)
        self.register_export_table("Chi tiet phieu nhap", self.table)

        supplier_title = QLabel("Tổng hợp nhập hàng theo nhà cung cấp")
        supplier_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.content_layout.addWidget(supplier_title)
        supplier_note = QLabel(
            "Chỉ tổng hợp các phiếu nhập còn hiệu lực trong khoảng thời gian đã chọn."
        )
        supplier_note.setStyleSheet("color: #8291A5; font-size: 10px;")
        self.content_layout.addWidget(supplier_note)
        self.supplier_table = self.make_table([
            "Mã NCC", "Nhà cung cấp", "Số điện thoại",
            "Số phiếu nhập", "Số lượng nhập", "Tổng trị giá",
        ])
        self.content_layout.addWidget(self.supplier_table)
        self.register_export_table(
            "Nhap hang theo nha cung cap", self.supplier_table
        )

    def load_report(self):
        start_date, end_date = self.date_parameters()
        data = self.service.import_report(start_date, end_date)
        rows = data["imports"]
        suppliers = data["suppliers"]
        quantity = sum(int(row[6] or 0) for row in rows)
        amount = sum((row[7] or 0) for row in rows)

        self.set_stat("count", number_text(len(rows)))
        self.set_stat("quantity", number_text(quantity))
        self.set_stat("amount", money_text(amount))

        self.fill_table(self.table, [
            (
                row[0], date_text(row[1]), row[2], row[3], row[4], row[5],
                number_text(row[6]), money_text(row[7]),
            )
            for row in rows
        ])
        self.fill_table(self.supplier_table, [
            (
                row[0] or "", row[1], row[2],
                number_text(row[3]), number_text(row[4]), money_text(row[5]),
            )
            for row in suppliers
        ])
