"""Báo cáo chi tiết hóa đơn bán hàng."""

from ui.bao_cao.bao_cao_co_so import (
    ReportBasePage, money_text, number_text, date_text,
)


class InvoiceReportPage(ReportBasePage):
    """Hiển thị số liệu tổng hợp từ hóa đơn bán hàng."""
    def __init__(self, db, parent=None):
        super().__init__(
            db,
            "Báo cáo hóa đơn",
            "Tiền hoàn và số lượng đổi/trả được cộng lũy kế theo hóa đơn gốc, không phụ thuộc ngày lập phiếu đổi trả. Hóa đơn hủy vẫn được giữ để tra cứu.",
            True,
            parent,
        )
        self.add_stat_cards([
            ("total", "Tổng số hóa đơn", "0",
             "Tất cả hóa đơn trong kỳ", "neutral"),
            ("valid", "Hóa đơn hợp lệ", "0",
             "Được ghi nhận doanh thu", "positive"),
            ("cancelled", "Hóa đơn đã hủy", "0",
             "Không ghi nhận doanh thu", "negative"),
            ("revenue", "Doanh thu trước hoàn", "0 đ",
             "Hóa đơn hợp lệ sau khuyến mãi", "positive"),
            ("refund", "Tiền đã hoàn", "0 đ",
             "Tổng tiền hoàn gắn với các hóa đơn trong kỳ", "warning"),
            ("net", "Doanh thu sau hoàn", "0 đ",
             "Doanh thu hợp lệ trừ tiền hoàn lũy kế", "primary"),
        ], primary_key="net")
        self.table = self.make_table([
            "Mã hóa đơn", "Ngày lập", "Nhân viên", "Mã ca",
            "Tiền hàng", "Tỷ lệ giảm", "Tiền giảm", "Thành tiền",
            "Doanh thu ghi nhận", "Số phiếu đổi trả", "SL hoàn tiền",
            "SL đổi hàng", "Tiền đã hoàn", "Doanh thu sau hoàn",
            "Khách đưa", "Tiền thừa", "Trạng thái"
        ])
        self.content_layout.addWidget(self.table)
        self.register_export_table("Bao cao hoa don", self.table)

    def load_report(self):
        start_date, end_date = self.date_parameters()
        rows = self.service.invoice_report(start_date, end_date)

        total_count = len(rows)
        valid_rows = [row for row in rows if row[16] is True or row[16] == 1]
        cancelled_count = sum(
            1 for row in rows if row[16] is False or row[16] == 0
        )
        gross_revenue = sum((row[8] or 0) for row in valid_rows)
        refund_total = sum((row[12] or 0) for row in rows)
        net_revenue = sum((row[13] or 0) for row in rows)

        self.set_stat("total", number_text(total_count))
        self.set_stat("valid", number_text(len(valid_rows)))
        self.set_stat("cancelled", number_text(cancelled_count))
        self.set_stat("revenue", money_text(gross_revenue))
        self.set_stat("refund", money_text(refund_total))
        self.set_stat("net", money_text(net_revenue))

        display = []
        for row in rows:
            status = "Đã thanh toán" if row[16] is True or row[16] == 1 else (
                "Đã hủy" if row[16] is False or row[16] == 0 else "Không xác định"
            )
            display.append((
                row[0], date_text(row[1]), row[2], row[3],
                money_text(row[4]), f"{float(row[5] or 0):.2f}%",
                money_text(row[6]), money_text(row[7]),
                money_text(row[8]), number_text(row[9]),
                number_text(row[10]), number_text(row[11]),
                money_text(row[12]), money_text(row[13]),
                money_text(row[14]), money_text(row[15]), status,
            ))
        self.fill_table(self.table, display)
