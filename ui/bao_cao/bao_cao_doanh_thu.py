"""Báo cáo doanh thu theo ngày, tháng hoặc năm."""

from PySide6.QtWidgets import QLabel, QHBoxLayout, QComboBox

from ui.bao_cao.bao_cao_co_so import (
    ReportBasePage, ReportLineChart, money_text, number_text,
)


class RevenueReportPage(ReportBasePage):
    """Theo dõi doanh số, tiền hoàn và hiệu quả bán hàng theo nhân viên."""

    def __init__(self, db, parent=None):
        super().__init__(
            db,
            "Báo cáo doanh thu",
            "Doanh số bán được nhóm theo ngày lập hóa đơn; tiền hoàn được nhóm "
            "theo ngày lập phiếu đổi trả.",
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
             "Giá trị hàng hóa trên hóa đơn hợp lệ trước giảm giá", "neutral"),
            ("discount", "Tiền giảm khuyến mãi", "0 đ",
             "Tiền giảm được làm tròn riêng theo từng hóa đơn", "warning"),
            ("revenue", "Doanh số bán hàng", "0 đ",
             "Tổng tiền hóa đơn hợp lệ sau khuyến mãi", "positive"),
            ("refund", "Tiền hoàn phát sinh", "0 đ",
             "Tổng tiền trên phiếu đổi trả được lập trong kỳ", "warning"),
            ("net", "Doanh số sau hoàn trong kỳ", "0 đ",
             "Doanh số bán trong kỳ trừ tiền hoàn phát sinh trong cùng kỳ", "primary"),
            ("count", "Hóa đơn hợp lệ", "0",
             "Số hóa đơn được ghi nhận doanh số", "positive"),
        ], primary_key="net")

        self.chart = ReportLineChart(
            "Doanh số bán và chênh lệch sau hoàn theo kỳ",
            [
                ("Doanh số bán hàng", 0, "#60A5FA"),
                ("Chênh lệch bán - hoàn", 1, "#34D399"),
            ],
        )
        self.content_layout.addWidget(self.chart)

        note = QLabel(
            "Doanh số bán được nhóm theo ngày lập hóa đơn; tiền hoàn được nhóm "
            "theo ngày lập phiếu đổi trả. Chỉ tiêu chênh lệch trong mỗi kỳ là "
            "doanh số bán trong kỳ trừ tiền hoàn phát sinh trong cùng kỳ; "
            "không phải báo cáo dòng tiền hay lợi nhuận kế toán."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #8291A5; font-size: 10px;")
        self.content_layout.addWidget(note)

        self.table = self.make_table([
            "Kỳ", "Số hóa đơn", "Tiền hàng", "Giảm khuyến mãi",
            "Doanh số bán hàng", "Tiền hoàn phát sinh",
            "Chênh lệch bán - hoàn",
        ])
        self.content_layout.addWidget(self.table)
        self.register_export_table("Bao cao doanh so theo ky", self.table)

        promotion_title = QLabel("Hiệu quả chương trình khuyến mãi")
        promotion_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.content_layout.addWidget(promotion_title)
        promotion_note = QLabel(
            "Phân nhóm theo hóa đơn gốc trong kỳ. Tiền hoàn được cộng lũy kế "
            "theo những hóa đơn đó, kể cả phiếu đổi trả phát sinh sau kỳ bán."
        )
        promotion_note.setWordWrap(True)
        promotion_note.setStyleSheet("color: #8291A5; font-size: 10px;")
        self.content_layout.addWidget(promotion_note)
        self.promotion_table = self.make_table([
            "Mã khuyến mãi", "Tên chương trình", "Tỷ lệ giảm",
            "Số hóa đơn", "Tiền hàng", "Tiền giảm",
            "Doanh số sau giảm", "Tiền hoàn lũy kế", "Còn lại sau hoàn",
        ])
        self.content_layout.addWidget(self.promotion_table)
        self.register_export_table("Hieu qua khuyen mai", self.promotion_table)

        employee_title = QLabel("Bán hàng và xử lý đổi trả theo nhân viên")
        employee_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.content_layout.addWidget(employee_title)
        employee_note = QLabel(
            "Doanh số thuộc nhân viên lập hóa đơn. Phiếu đổi trả và tiền hoàn "
            "thuộc nhân viên trực tiếp xử lý phiếu, không gán ngược cho người bán."
        )
        employee_note.setWordWrap(True)
        employee_note.setStyleSheet("color: #8291A5; font-size: 10px;")
        self.content_layout.addWidget(employee_note)
        self.employee_table = self.make_table([
            "Mã NV", "Nhân viên", "Hóa đơn bán", "SL bán", "Doanh số",
            "Phiếu đổi trả xử lý", "SL hoàn tiền", "SL đổi hàng", "Tiền đã hoàn",
        ])
        self.content_layout.addWidget(self.employee_table)
        self.register_export_table("Ban hang theo nhan vien", self.employee_table)

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

        employee_rows = self.service.employee_sales_report(start_date, end_date)
        self.fill_table(self.employee_table, [
            (
                row[0] or "",
                row[1],
                number_text(row[2]),
                number_text(row[3]),
                money_text(row[4]),
                number_text(row[5]),
                number_text(row[6]),
                number_text(row[7]),
                money_text(row[8]),
            )
            for row in employee_rows
        ])
