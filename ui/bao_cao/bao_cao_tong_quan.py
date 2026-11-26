"""Trang tổng quan các chỉ số hoạt động của nhà sách."""

from PySide6.QtWidgets import QLabel, QVBoxLayout

from decimal import Decimal

from giao_dien.bao_cao.bao_cao_co_so import (
    ReportBasePage, money_text, number_text, date_text,
)


class OverviewReportPage(ReportBasePage):
    """Báo cáo tổng quan tình hình hoạt động nhà sách."""
    def __init__(self, db, parent=None):
        super().__init__(
            db,
            "Tổng quan báo cáo",
            "Tổng hợp doanh thu, hoàn trả, hóa đơn và nhập hàng trong khoảng thời gian đã chọn.",
            use_date_filter=True,
            parent=parent,
        )

        self.add_stat_cards([
            ("revenue", "DOANH THU BÁN HÀNG", "0 đ"),
            ("refund", "TIỀN ĐÃ HOÀN", "0 đ"),
            ("net", "DOANH THU SAU HOÀN", "0 đ"),
            ("valid_invoices", "HÓA ĐƠN HỢP LỆ", "0"),
            ("cancelled_invoices", "HÓA ĐƠN ĐÃ HỦY", "0"),
            ("imports", "GIÁ TRỊ NHẬP HÀNG", "0 đ"),
        ])

        trend_title = QLabel("DOANH THU THEO NGÀY")
        trend_title.setStyleSheet("font-weight: bold;")
        self.content_layout.addWidget(trend_title)
        self.trend_table = self.make_table([
            "Ngày", "Số hóa đơn", "Số lượng bán", "Doanh thu"
        ])
        self.content_layout.addWidget(self.trend_table)
        self.register_export_table("Doanh thu theo ngày", self.trend_table)

        products_title = QLabel("TOP 10 SẢN PHẨM BÁN CHẠY")
        products_title.setStyleSheet("font-weight: bold;")
        self.content_layout.addWidget(products_title)
        self.top_products_table = self.make_table([
            "Mã sản phẩm", "Tên sản phẩm", "Số lượng bán", "Doanh thu sau khuyến mãi"
        ])
        self.content_layout.addWidget(self.top_products_table)
        self.register_export_table("Top sản phẩm bán chạy", self.top_products_table)

    def load_report(self):
        start_date, end_date = self.date_parameters()

        summary_sql = """
            SELECT
                COUNT(DISTINCT CASE WHEN HD.TRANGTHAI = 1 THEN HD.MAHD END),
                COUNT(DISTINCT CASE WHEN HD.TRANGTHAI = 0 THEN HD.MAHD END),
                COALESCE(SUM(CASE WHEN HD.TRANGTHAI = 1 THEN
                    COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)
                    * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0)
                    ELSE 0 END), 0)
            FROM dbo.HOA_DON HD
            LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
            LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
            WHERE HD.NGAYLAP >= CONVERT(date, ?)
              AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
        """
        summary = self.fetch_one(summary_sql, (start_date, end_date))

        refund_sql = """
            SELECT COALESCE(SUM(TONG_TIEN_HOAN), 0)
            FROM dbo.PHIEU_DOI_TRA
            WHERE NGAY_DOI_TRA >= CONVERT(date, ?)
              AND NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
        """
        refund_row = self.fetch_one(refund_sql, (start_date, end_date))

        import_sql = """
            SELECT COALESCE(SUM(TONGTRIGIA), 0)
            FROM dbo.PHIEU_NHAP
            WHERE NGAYNHAP >= CONVERT(date, ?)
              AND NGAYNHAP < DATEADD(day, 1, CONVERT(date, ?))
        """
        import_row = self.fetch_one(import_sql, (start_date, end_date))

        revenue = summary[2] or 0
        refund = refund_row[0] if refund_row else 0
        net = Decimal(str(revenue or 0)) - Decimal(str(refund or 0))

        self.set_stat("revenue", money_text(revenue))
        self.set_stat("refund", money_text(refund))
        self.set_stat("net", money_text(net))
        self.set_stat("valid_invoices", number_text(summary[0]))
        self.set_stat("cancelled_invoices", number_text(summary[1]))
        self.set_stat("imports", money_text(import_row[0] if import_row else 0))

        trend_sql = """
            SELECT
                CAST(HD.NGAYLAP AS date) AS NGAY,
                COUNT(DISTINCT HD.MAHD) AS SO_HD,
                COALESCE(SUM(CT.SOLUONG), 0) AS SO_LUONG,
                COALESCE(SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)
                    * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0)), 0) AS DOANH_THU
            FROM dbo.HOA_DON HD
            INNER JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
            LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
            WHERE HD.TRANGTHAI = 1
              AND HD.NGAYLAP >= CONVERT(date, ?)
              AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
            GROUP BY CAST(HD.NGAYLAP AS date)
            ORDER BY NGAY DESC
        """
        trend_rows = self.fetch_all(trend_sql, (start_date, end_date))
        self.fill_table(self.trend_table, [
            (
                date_text(row[0], include_time=False),
                number_text(row[1]),
                number_text(row[2]),
                money_text(row[3]),
            )
            for row in trend_rows
        ])

        top_sql = """
            SELECT TOP 10
                SP.MASP,
                COALESCE(SP.TENSP, N''),
                SUM(COALESCE(CT.SOLUONG, 0)) AS SO_LUONG,
                SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)
                    * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0)) AS DOANH_THU
            FROM dbo.HOA_DON HD
            INNER JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
            INNER JOIN dbo.SAN_PHAM SP ON SP.MASP = CT.MASP
            LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
            WHERE HD.TRANGTHAI = 1
              AND HD.NGAYLAP >= CONVERT(date, ?)
              AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
            GROUP BY SP.MASP, SP.TENSP
            ORDER BY SUM(COALESCE(CT.SOLUONG, 0)) DESC, DOANH_THU DESC
        """
        top_rows = self.fetch_all(top_sql, (start_date, end_date))
        self.fill_table(self.top_products_table, [
            (row[0], row[1], number_text(row[2]), money_text(row[3]))
            for row in top_rows
        ])
