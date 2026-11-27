"""Báo cáo tồn kho hiện tại."""

from PySide6.QtWidgets import QLabel, QHBoxLayout, QComboBox, QSpinBox, QLineEdit

from ui.bao_cao.bao_cao_co_so import ReportBasePage, money_text, number_text


class InventoryReportPage(ReportBasePage):
    """Thống kê số lượng và giá trị tồn kho."""
    """Báo cáo số lượng và giá trị hàng tồn kho."""
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
        """Truy vấn số lượng và giá trị tồn kho theo bộ lọc đang chọn."""
        threshold = self.threshold_spin.value()
        filter_key = self.status_combo.currentData()
        keyword = self.search_input.text().strip()

        where_extra = ""
        params = [threshold]
        if filter_key == "low":
            where_extra += " AND COALESCE(SLTON, 0) > 0 AND COALESCE(SLTON, 0) <= ?"
            params.append(threshold)
        elif filter_key == "out":
            where_extra += " AND COALESCE(SLTON, 0) <= 0"

        if keyword:
            where_extra += " AND (MASP LIKE ? OR TENSP LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        summary_sql = """
            SELECT
                COUNT(*),
                SUM(CASE WHEN COALESCE(SLTON, 0) > 0 AND COALESCE(SLTON, 0) <= ? THEN 1 ELSE 0 END),
                SUM(CASE WHEN COALESCE(SLTON, 0) <= 0 THEN 1 ELSE 0 END),
                COALESCE(SUM(COALESCE(GIANHAP, 0) * COALESCE(SLTON, 0)), 0)
            FROM dbo.SAN_PHAM
            WHERE COALESCE(IS_DELETED, 0) = 0
        """
        summary = self.fetch_one(summary_sql, (threshold,))
        self.set_stat("products", number_text(summary[0]))
        self.set_stat("low", number_text(summary[1]))
        self.set_stat("out", number_text(summary[2]))
        self.set_stat("value", money_text(summary[3]))

        sql = f"""
            SELECT
                MASP,
                COALESCE(TENSP, N''),
                COALESCE(DVT, N''),
                COALESCE(SLTON, 0),
                COALESCE(GIANHAP, 0),
                COALESCE(GIABAN, 0),
                COALESCE(GIANHAP, 0) * COALESCE(SLTON, 0) AS GIATRI_TON,
                CASE
                    WHEN COALESCE(SLTON, 0) <= 0 THEN N'Hết hàng'
                    WHEN COALESCE(SLTON, 0) <= ? THEN N'Sắp hết'
                    ELSE N'Còn hàng'
                END AS TINH_TRANG
            FROM dbo.SAN_PHAM
            WHERE COALESCE(IS_DELETED, 0) = 0
            {where_extra}
            ORDER BY COALESCE(SLTON, 0) ASC, TENSP ASC
        """
        rows = self.fetch_all(sql, tuple(params))
        self.fill_table(self.table, [
            (
                row[0], row[1], row[2], number_text(row[3]),
                money_text(row[4]), money_text(row[5]), money_text(row[6]), row[7],
            )
            for row in rows
        ])
