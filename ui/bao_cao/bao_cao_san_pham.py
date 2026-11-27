"""Báo cáo hiệu quả bán hàng theo sản phẩm."""

from PySide6.QtWidgets import QLabel, QHBoxLayout, QComboBox, QLineEdit

from ui.bao_cao.bao_cao_co_so import ReportBasePage, money_text, number_text


class ProductReportPage(ReportBasePage):
    """Thống kê sản phẩm theo các tiêu chí báo cáo."""
    def __init__(self, db, parent=None):
        super().__init__(
            db,
            "Báo cáo sản phẩm",
            "Lượng bán nhóm theo ngày lập hóa đơn; lượng và tiền hoàn nhóm theo ngày xử lý phiếu đổi trả. Tồn kho là số hiện tại.",
            True,
            parent,
        )
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Sắp xếp:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Bán chạy nhất", "quantity_desc")
        self.sort_combo.addItem("Bán chậm nhất", "quantity_asc")
        self.sort_combo.addItem("Doanh thu cao nhất", "revenue_desc")
        controls.addWidget(self.sort_combo)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm mã hoặc tên sản phẩm...")
        self.search_input.setMinimumWidth(220)
        controls.addWidget(self.search_input)
        self.content_layout.addLayout(controls)

        self.add_stat_cards([
            ("sold", "Số lượng đã bán", "0",
             "Tổng lượng xuất trên hóa đơn hợp lệ", "neutral"),
            ("refund", "Tiền hoàn theo sản phẩm", "0 đ",
             "Chỉ gồm dòng xử lý hoàn tiền", "warning"),
            ("active", "Sản phẩm có phát sinh bán", "0",
             "Số mã hàng có phát sinh bán", "neutral"),
            ("net", "Doanh thu sản phẩm sau hoàn", "0 đ",
             "Doanh thu sau khuyến mãi trừ tiền hoàn theo sản phẩm", "primary"),
        ], primary_key="net")

        self.table = self.make_table([
            "Xếp hạng", "Mã sản phẩm", "Tên sản phẩm", "Số hóa đơn",
            "SL đã bán", "SL hoàn tiền", "SL đổi hàng", "Tiền hàng",
            "Giảm khuyến mãi", "Doanh thu sau KM", "Tiền hoàn",
            "Doanh thu sau hoàn", "Tồn kho hiện tại"
        ])
        self.content_layout.addWidget(self.table)
        self.register_export_table("Bao cao san pham", self.table)

        self.sort_combo.currentIndexChanged.connect(lambda *_: self.refresh_data())
        self.search_input.returnPressed.connect(self.refresh_data)

    def load_report(self):
        start_date, end_date = self.date_parameters()
        sort_key = self.sort_combo.currentData()
        search = self.search_input.text().strip()
        rows = self.service.product_report(start_date, end_date, sort_key, search)

        total_sold = sum(int(row[4] or 0) for row in rows)
        total_refund = sum((row[10] or 0) for row in rows)
        net_revenue = sum((row[11] or 0) for row in rows)
        active_products = sum(1 for row in rows if int(row[4] or 0) > 0)

        self.set_stat("sold", number_text(total_sold))
        self.set_stat("refund", money_text(total_refund))
        self.set_stat("active", number_text(active_products))
        self.set_stat("net", money_text(net_revenue))

        self.fill_table(self.table, [
            (
                number_text(row[0]), row[1], row[2],
                number_text(row[3]), number_text(row[4]),
                number_text(row[5]), number_text(row[6]),
                money_text(row[7]), money_text(row[8]),
                money_text(row[9]), money_text(row[10]),
                money_text(row[11]), number_text(row[12]),
            )
            for row in rows
        ])
