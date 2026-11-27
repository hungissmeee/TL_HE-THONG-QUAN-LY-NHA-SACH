"""Báo cáo tồn kho hiện tại."""

from PySide6.QtWidgets import QLabel, QHBoxLayout, QComboBox, QSpinBox, QLineEdit

from ui.bao_cao.bao_cao_co_so import ReportBasePage, money_text, number_text


class InventoryReportPage(ReportBasePage):
    """Báo cáo số lượng, tình trạng và giá trị tồn kho ước tính."""
    def __init__(self, db, parent=None):
        super().__init__(
            db,
            "Báo cáo tồn kho",
            "Kiểm tra lượng tồn, sản phẩm sắp hết/hết hàng và giá trị tồn kho ước tính theo giá nhập hiện tại.",
            use_date_filter=False,
            parent=parent,
        )

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Tình trạng:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("Tất cả", "all")
        self.status_combo.addItem("Sắp hết hàng", "low")
        self.status_combo.addItem("Hết hàng", "out")
        controls.addWidget(self.status_combo)

        controls.addWidget(QLabel("Ngưỡng sắp hết:"))
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(1, 100000)
        self.threshold_spin.setValue(5)
        controls.addWidget(self.threshold_spin)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm mã hoặc tên sản phẩm...")
        self.search_input.setMinimumWidth(220)
        controls.addWidget(self.search_input)
        self.content_layout.addLayout(controls)

        self.add_stat_cards([
            ("products", "Tổng số sản phẩm", "0",
             "Số mặt hàng chưa bị xóa", "neutral"),
            ("low", "Sản phẩm sắp hết", "0",
             "Tồn kho lớn hơn 0 và không vượt ngưỡng", "warning"),
            ("out", "Sản phẩm hết hàng", "0",
             "Số mặt hàng có tồn kho bằng hoặc dưới 0", "negative"),
            ("value", "Giá trị tồn ước tính", "0 đ",
             "Tồn kho nhân với giá nhập hiện tại", "primary"),
        ], primary_key="value")

        self.table = self.make_table([
            "Mã sản phẩm", "Tên sản phẩm", "Đơn vị tính", "Số lượng tồn",
            "Giá nhập hiện tại", "Giá bán", "Giá trị tồn", "Tình trạng"
        ])
        self.content_layout.addWidget(self.table)
        self.register_export_table("Bao cao ton kho", self.table)

        self.status_combo.currentIndexChanged.connect(lambda *_: self.refresh_data())
        self.threshold_spin.valueChanged.connect(lambda *_: self.refresh_data())
        self.search_input.returnPressed.connect(self.refresh_data)

    def load_report(self):
        threshold = self.threshold_spin.value()
        filter_key = self.status_combo.currentData()
        keyword = self.search_input.text().strip()
        data = self.service.inventory_report(threshold, filter_key, keyword)
        summary = data["summary"]
        rows = data["rows"]

        self.set_stat("products", number_text(summary[0]))
        self.set_stat("low", number_text(summary[1]))
        self.set_stat("out", number_text(summary[2]))
        self.set_stat("value", money_text(summary[3]))

        self.fill_table(self.table, [
            (
                row[0], row[1], row[2], number_text(row[3]),
                money_text(row[4]), money_text(row[5]), money_text(row[6]), row[7],
            )
            for row in rows
        ])
