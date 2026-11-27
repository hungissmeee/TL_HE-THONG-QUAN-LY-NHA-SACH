"""Báo cáo doanh thu theo ngày, tháng hoặc năm."""

from PySide6.QtWidgets import QLabel, QHBoxLayout, QComboBox

from ui.bao_cao.bao_cao_co_so import (
    ReportBasePage, ReportLineChart, money_text, number_text, date_text,
)


class RevenueReportPage(ReportBasePage):
    """Hiển thị doanh thu theo bộ lọc thời gian được chọn."""
    PERIODS = {
        "Ngày": "CAST(HD.NGAYLAP AS date)",
        "Tháng": "DATEFROMPARTS(YEAR(HD.NGAYLAP), MONTH(HD.NGAYLAP), 1)",
        "Năm": "DATEFROMPARTS(YEAR(HD.NGAYLAP), 1, 1)",
    }
    REFUND_PERIODS = {
        "Ngày": "CAST(PDT.NGAY_DOI_TRA AS date)",
        "Tháng": "DATEFROMPARTS(YEAR(PDT.NGAY_DOI_TRA), MONTH(PDT.NGAY_DOI_TRA), 1)",
        "Năm": "DATEFROMPARTS(YEAR(PDT.NGAY_DOI_TRA), 1, 1)",
    }

    def __init__(self, db, parent=None):
        super().__init__(
            db,
            "Báo cáo doanh thu",
            "Doanh thu được nhóm theo ngày lập hóa đơn; tiền hoàn được nhóm theo ngày xử lý phiếu đổi trả.",
            True,
            parent,
        )

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Tổng hợp theo:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Ngày", "Tháng", "Năm"])
        controls.addWidget(self.period_combo)
        controls.addStretch(1)
        self.content_layout.addLayout(controls)

        self.add_stat_cards([
            ("gross", "Tiền hàng trước khuyến mãi", "0 đ",
             "Giá trị hàng hóa trước khi giảm", "neutral"),
            ("discount", "Tiền giảm khuyến mãi", "0 đ",
             "Số tiền được giảm từ chương trình khuyến mãi", "warning"),
            ("revenue", "Doanh thu hợp lệ", "0 đ",
             "Tiền hàng sau khuyến mãi, chưa trừ hoàn trả", "positive"),
            ("refund", "Tiền hoàn trả", "0 đ",
             "Tổng tiền hoàn theo phiếu đổi trả", "warning"),
            ("net", "Doanh thu sau hoàn", "0 đ",
             "Doanh thu hợp lệ trừ tiền hoàn", "primary"),
            ("count", "Hóa đơn hợp lệ", "0",
             "Số hóa đơn được ghi nhận doanh thu", "positive"),
        ], primary_key="net")
        self.chart = ReportLineChart(
            "Xu hướng doanh thu và doanh thu sau hoàn",
            [
                ("Doanh thu bán hàng", 0, "#60A5FA"),
                ("Doanh thu sau hoàn theo ngày", 1, "#34D399"),
            ],
        )
        self.content_layout.addWidget(self.chart)

        note = QLabel(
            "Doanh thu bán hàng tính theo ngày lập hóa đơn. Tiền hoàn tính "
            "theo ngày lập phiếu đổi trả; doanh thu sau hoàn trong kỳ bằng "
            "doanh thu bán hàng trong kỳ trừ tiền hoàn phát sinh trong kỳ."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #8291A5; font-size: 10px;")
        self.content_layout.addWidget(note)

        self.table = self.make_table([
            "Kỳ", "Số hóa đơn", "Tiền hàng", "Giảm khuyến mãi",
            "Doanh thu bán hàng", "Tiền hoàn phát sinh", "Doanh thu sau hoàn"
        ])
        self.content_layout.addWidget(self.table)
        self.register_export_table("Bao cao doanh thu theo ky", self.table)

        promotion_title = QLabel("Hiệu quả chương trình khuyến mãi")
        promotion_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.content_layout.addWidget(promotion_title)
        promotion_note = QLabel(
            "Phân nhóm theo ngày lập hóa đơn. Tiền hoàn ở bảng này là lũy kế "
            "của các hóa đơn thuộc kỳ, kể cả phiếu đổi trả được lập sau kỳ."
        )
        promotion_note.setWordWrap(True)
        promotion_note.setStyleSheet("color: #8291A5; font-size: 10px;")
        self.content_layout.addWidget(promotion_note)
        self.promotion_table = self.make_table([
            "Mã khuyến mãi", "Tên chương trình", "Tỷ lệ giảm",
            "Số hóa đơn", "Tiền hàng", "Tiền giảm",
            "Doanh thu sau giảm", "Tiền hoàn", "Doanh thu sau hoàn",
        ])
        self.content_layout.addWidget(self.promotion_table)
        self.register_export_table(
            "Hieu qua khuyen mai", self.promotion_table
        )

    def load_report(self):
        start_date, end_date = self.date_parameters()
        period_name = self.period_combo.currentText()
        period_key = {"Ngày": "day", "Tháng": "month", "Năm": "year"}[period_name]
        rows = self.service.revenue_by_period(start_date, end_date, period_key)

        gross_total = sum((row[2] or 0) for row in rows)
        discount_total = sum((row[3] or 0) for row in rows)
        sales_total = sum((row[4] or 0) for row in rows)
        refund_total = sum((row[5] or 0) for row in rows)
        invoice_total = sum(int(row[1] or 0) for row in rows)

        self.set_stat("gross", money_text(gross_total))
        self.set_stat("discount", money_text(discount_total))
        self.set_stat("revenue", money_text(sales_total))
        self.set_stat("refund", money_text(refund_total))
        self.set_stat("net", money_text(sales_total - refund_total))
        self.set_stat("count", number_text(invoice_total))

        chart_rows = []
        display_rows = []
        for row in rows:
            period = row[0]
            if hasattr(period, "strftime"):
                period_label = period.strftime("%d/%m/%Y")
                if period_name == "Tháng":
                    period_label = period.strftime("%m/%Y")
                elif period_name == "Năm":
                    period_label = period.strftime("%Y")
            else:
                period_label = str(period or "")

            chart_rows.append((period_label, row[4] or 0, row[6] or 0))
            display_rows.append((
                period_label,
                number_text(row[1]),
                money_text(row[2]),
                money_text(row[3]),
                money_text(row[4]),
                money_text(row[5]),
                money_text(row[6]),
            ))

        self.chart.set_data(list(reversed(chart_rows)))
        self.fill_table(self.table, display_rows)

        promotion_rows = self.service.promotion_effectiveness(start_date, end_date)
        self.fill_table(self.promotion_table, [
            (
                row[0] or "—",
                row[1],
                f"{float(row[2] or 0):.2f}%",
                number_text(row[3]),
                money_text(row[4]),
                money_text(row[5]),
                money_text(row[6]),
                money_text(row[7]),
                money_text(row[8]),
            )
            for row in promotion_rows
        ])
