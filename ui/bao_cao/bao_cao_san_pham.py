"""Báo cáo số lượng bán, hoàn và đổi theo từng sản phẩm."""

from PySide6.QtWidgets import QLabel, QHBoxLayout, QComboBox, QLineEdit

from ui.bao_cao.bao_cao_co_so import ReportBasePage, money_text, number_text


class ProductReportPage(ReportBasePage):
    """Thống kê biến động số lượng theo sản phẩm trong kỳ báo cáo."""

    def __init__(self, db, parent=None):
        super().__init__(
            db,
            "Báo cáo sản phẩm",
            "Bảng tập trung vào số lượng bán, hoàn tiền, đổi hàng và tình trạng hàng trả. "
            "Tổng thu sau hoàn được tính chung cho toàn kỳ, không phân bổ xuống từng sản phẩm.",
            True,
            parent,
        )
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Sắp xếp:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Bán nhiều nhất", "quantity_desc")
        self.sort_combo.addItem("Bán ít nhất", "quantity_asc")
        self.sort_combo.addItem("Hoàn tiền nhiều nhất", "refund_desc")
        controls.addWidget(self.sort_combo)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm mã hoặc tên sản phẩm...")
        self.search_input.setMinimumWidth(220)
        controls.addWidget(self.search_input)
        self.content_layout.addLayout(controls)

        self.add_stat_cards([
            ("sold", "Số lượng đã bán", "0",
             "Tổng số lượng trên hóa đơn hợp lệ trong kỳ", "neutral"),
            ("refund", "Số lượng hoàn tiền", "0",
             "Số lượng trả theo hình thức hoàn tiền", "warning"),
            ("exchange", "Số lượng đổi hàng", "0",
             "Số lượng xử lý theo hình thức đổi hàng", "neutral"),
            ("intact", "Số lượng hàng nguyên vẹn", "0",
             "Hàng trả lại còn nguyên vẹn", "positive"),
            ("damaged", "Số lượng hàng hỏng", "0",
             "Hàng trả lại được ghi nhận đã hỏng", "negative"),
            ("net", "TỔNG THU SAU HOÀN", "0 đ",
             "Doanh thu hóa đơn hợp lệ trừ tổng tiền hoàn trong kỳ", "primary"),
        ], primary_key="net")

        self.table = self.make_table([
            "Xếp hạng", "Mã sản phẩm", "Tên sản phẩm", "Số hóa đơn",
            "SL đã bán", "SL hoàn tiền", "SL đổi hàng",
            "SL nguyên vẹn", "SL hàng hỏng", "Tồn kho hiện tại",
        ])
        self.content_layout.addWidget(self.table)
        self.register_export_table("Bao cao san pham", self.table)

        self.sort_combo.currentIndexChanged.connect(lambda *_: self.refresh_data())
        self.search_input.returnPressed.connect(self.refresh_data)

    def load_report(self):
        start_date, end_date = self.date_parameters()
        sort_key = self.sort_combo.currentData()
        search = self.search_input.text().strip()

        # KPI luôn tính trên toàn bộ kỳ, không thay đổi theo từ khóa sản phẩm.
        summary = self.service.product_report_summary(start_date, end_date)
        self.set_stat("sold", number_text(summary["sold"]))
        self.set_stat("refund", number_text(summary["refund_quantity"]))
        self.set_stat("exchange", number_text(summary["exchange_quantity"]))
        self.set_stat("intact", number_text(summary["intact_quantity"]))
        self.set_stat("damaged", number_text(summary["damaged_quantity"]))
        self.set_stat("net", money_text(summary["net_revenue"]))

        # Bảng chỉ chứa số lượng; không phân bổ tiền hoàn theo SKU.
        rows = self.service.product_report(start_date, end_date, sort_key, search)
        self.fill_table(self.table, [
            (
                number_text(row[0]), row[1], row[2],
                number_text(row[3]), number_text(row[4]),
                number_text(row[5]), number_text(row[6]),
                number_text(row[7]), number_text(row[8]),
                number_text(row[9]),
            )
            for row in rows
        ])
