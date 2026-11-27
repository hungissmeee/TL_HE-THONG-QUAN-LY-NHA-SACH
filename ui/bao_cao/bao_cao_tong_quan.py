"""Trang tổng quan các chỉ số hoạt động của nhà sách."""

from PySide6.QtWidgets import QLabel, QVBoxLayout

from decimal import Decimal

from ui.bao_cao.bao_cao_co_so import (
    ReportBasePage, ReportLineChart, money_text, number_text, date_text,
)


class OverviewReportPage(ReportBasePage):
    """Tổng hợp các chỉ số quan trọng của hoạt động nhà sách."""
    def __init__(self, db, parent=None):
        super().__init__(
            db,
            "Tổng quan báo cáo",
            "Tổng hợp doanh thu, hoàn trả, hóa đơn và nhập hàng trong khoảng thời gian đã chọn.",
            use_date_filter=True,
            parent=parent,
        )

        # Nhóm tài chính giúp phân biệt doanh thu, tiền hoàn và kết quả sau hoàn.
        self.add_stat_cards(
            [
                (
                    "revenue", "Doanh thu bán hàng", "0 đ",
                    "Tổng tiền hóa đơn hợp lệ sau khuyến mãi", "positive",
                ),
                (
                    "refund", "Tiền đã hoàn", "0 đ",
                    "Tổng tiền ghi nhận trên phiếu đổi trả", "warning",
                ),
                (
                    "net", "Doanh thu sau hoàn", "0 đ",
                    "Doanh thu bán hàng trừ tiền đã hoàn", "primary",
                ),
            ],
            section_title="Kết quả bán hàng",
            section_description="Các khoản thu và hoàn trong khoảng thời gian đang chọn.",
            primary_key="net",
        )

        # Nhóm chứng từ và nhập hàng được tách riêng để tránh trộn với doanh thu.
        self.add_stat_cards(
            [
                (
                    "valid_invoices", "Hóa đơn hợp lệ", "0",
                    "Được ghi nhận vào doanh thu", "positive",
                ),
                (
                    "cancelled_invoices", "Hóa đơn đã hủy", "0",
                    "Không được tính vào doanh thu", "negative",
                ),
                (
                    "imports", "Giá trị nhập hàng", "0 đ",
                    "Tổng trị giá phiếu nhập còn hiệu lực trong kỳ", "violet",
                ),
            ],
            section_title="Chứng từ và nhập hàng",
            section_description="Số lượng hóa đơn theo trạng thái và giá trị hàng đã nhập.",
        )

        trend_title = QLabel("Xu hướng bán hàng và hoàn trả")
        trend_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.content_layout.addWidget(trend_title)

        self.trend_chart = ReportLineChart(
            "Doanh thu theo ngày phát sinh",
            [
                ("Doanh thu bán hàng", 0, "#60A5FA"),
                ("Doanh thu sau hoàn theo ngày", 1, "#34D399"),
            ],
        )
        self.content_layout.addWidget(self.trend_chart)

        trend_note = QLabel(
            "Doanh thu bán hàng theo ngày lập hóa đơn; tiền hoàn theo ngày "
            "lập phiếu đổi trả. Số âm thể hiện ngày có tiền hoàn lớn hơn "
            "doanh thu bán hàng phát sinh trong ngày."
        )
        trend_note.setWordWrap(True)
        trend_note.setStyleSheet("color: #8291A5; font-size: 10px;")
        self.content_layout.addWidget(trend_note)

        self.trend_table = self.make_table([
            "Ngày", "Số hóa đơn", "Số lượng bán",
            "Doanh thu bán hàng", "Tiền hoàn", "Doanh thu sau hoàn"
        ])
        self.content_layout.addWidget(self.trend_table)
        self.register_export_table("Doanh thu theo ngày", self.trend_table)

        products_title = QLabel("10 sản phẩm bán chạy")
        products_title.setStyleSheet("font-weight: bold;")
        self.content_layout.addWidget(products_title)
        self.top_products_table = self.make_table([
            "Mã sản phẩm", "Tên sản phẩm", "Số lượng bán", "Doanh thu sau khuyến mãi"
        ])
        self.content_layout.addWidget(self.top_products_table)
        self.register_export_table("Top sản phẩm bán chạy", self.top_products_table)

    def load_report(self):
        """Tải các chỉ số tổng quan thông qua report service."""
        start_date, end_date = self.date_parameters()
        summary = self.service.overview_summary(start_date, end_date)
        refund_row = self.service.overview_refunds(start_date, end_date)
        import_row = self.service.overview_imports(start_date, end_date)

        revenue = summary[2] or 0
        refund = refund_row[0] if refund_row else 0
        net = Decimal(str(revenue or 0)) - Decimal(str(refund or 0))

        self.set_stat("revenue", money_text(revenue))
        self.set_stat("refund", money_text(refund))
        self.set_stat("net", money_text(net))
        self.set_stat("valid_invoices", number_text(summary[0]))
        self.set_stat("cancelled_invoices", number_text(summary[1]))
        self.set_stat("imports", money_text(import_row[0] if import_row else 0))

        trend_rows = self.service.overview_trend(start_date, end_date)
        self.trend_chart.set_data([
            (
                date_text(row[0], include_time=False),
                row[3] or 0,
                row[5] or 0,
            )
            for row in trend_rows
        ])
        self.fill_table(self.trend_table, [
            (
                date_text(row[0], include_time=False),
                number_text(row[1]),
                number_text(row[2]),
                money_text(row[3]),
                money_text(row[4]),
                money_text(row[5]),
            )
            for row in trend_rows
        ])

        top_rows = self.service.overview_top_products(start_date, end_date)
        self.fill_table(self.top_products_table, [
            (row[0], row[1], number_text(row[2]), money_text(row[3]))
            for row in top_rows
        ])
