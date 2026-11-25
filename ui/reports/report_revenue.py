"""Báo cáo doanh thu theo ngày, tháng hoặc năm."""

from PySide6.QtWidgets import QLabel, QHBoxLayout, QComboBox

from ui.reports.report_base import ReportBasePage, money_text, number_text, date_text


class RevenueReportPage(ReportBasePage):
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
            "Theo dõi tiền hàng, tiền giảm khuyến mãi, doanh thu hợp lệ và tiền hoàn trả theo kỳ.",
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
            ("gross", "TIỀN HÀNG TRƯỚC KHUYẾN MÃI", "0 đ"),
            ("discount", "TIỀN GIẢM KHUYẾN MÃI", "0 đ"),
            ("revenue", "DOANH THU HỢP LỆ", "0 đ"),
            ("refund", "TIỀN HOÀN TRẢ", "0 đ"),
            ("net", "DOANH THU SAU HOÀN", "0 đ"),
            ("count", "SỐ HÓA ĐƠN HỢP LỆ", "0"),
        ])
        self.table = self.make_table([
            "Kỳ", "Số hóa đơn", "Tiền hàng", "Giảm khuyến mãi",
            "Doanh thu", "Tiền hoàn", "Doanh thu sau hoàn"
        ])
        self.content_layout.addWidget(self.table)
        self.register_export_table("Bao cao doanh thu", self.table)

    def load_report(self):
        start_date, end_date = self.date_parameters()
        period_name = self.period_combo.currentText()
        sales_period = self.PERIODS[period_name]
        refund_period = self.REFUND_PERIODS[period_name]

        sql = f"""
            WITH Sales AS (
                SELECT
                    {sales_period} AS KY,
                    COUNT(DISTINCT HD.MAHD) AS SO_HD,
                    SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)) AS TIEN_HANG,
                    SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)
                        * COALESCE(KM.TYLEGIAM, 0) / 100.0) AS TIEN_GIAM,
                    SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)
                        * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0)) AS DOANH_THU
                FROM dbo.HOA_DON HD
                LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.TRANGTHAI = 1
                  AND HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY {sales_period}
            ), Refunds AS (
                SELECT
                    {refund_period} AS KY,
                    SUM(COALESCE(PDT.TONG_TIEN_HOAN, 0)) AS TIEN_HOAN
                FROM dbo.PHIEU_DOI_TRA PDT
                WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY {refund_period}
            )
            SELECT
                COALESCE(S.KY, R.KY) AS KY,
                COALESCE(S.SO_HD, 0),
                COALESCE(S.TIEN_HANG, 0),
                COALESCE(S.TIEN_GIAM, 0),
                COALESCE(S.DOANH_THU, 0),
                COALESCE(R.TIEN_HOAN, 0),
                COALESCE(S.DOANH_THU, 0) - COALESCE(R.TIEN_HOAN, 0) AS DOANH_THU_SAU_HOAN
            FROM Sales S
            FULL OUTER JOIN Refunds R ON R.KY = S.KY
            ORDER BY KY DESC
        """
        rows = self.fetch_all(sql, (start_date, end_date, start_date, end_date))

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
            display_rows.append((
                period_label,
                number_text(row[1]),
                money_text(row[2]),
                money_text(row[3]),
                money_text(row[4]),
                money_text(row[5]),
                money_text(row[6]),
            ))
        self.fill_table(self.table, display_rows)
