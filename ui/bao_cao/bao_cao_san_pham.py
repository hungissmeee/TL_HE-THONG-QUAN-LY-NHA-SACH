"""Báo cáo hiệu quả bán hàng theo sản phẩm."""

from PySide6.QtWidgets import QLabel, QHBoxLayout, QComboBox, QLineEdit

from ui.bao_cao.bao_cao_co_so import ReportBasePage, money_text, number_text


class ProductReportPage(ReportBasePage):
    """Thống kê sản phẩm theo các tiêu chí báo cáo."""
    def __init__(self, db, parent=None):
        super().__init__(
            db,
            "Báo cáo sản phẩm",
            "Phân tích số lượng bán, số hóa đơn có sản phẩm, doanh thu sau khuyến mãi và tồn kho hiện tại.",
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
            ("sold", "TỔNG SỐ LƯỢNG ĐÃ BÁN", "0"),
            ("revenue", "TỔNG DOANH THU SẢN PHẨM", "0 đ"),
            ("active", "SẢN PHẨM CÓ PHÁT SINH BÁN", "0"),
        ])

        self.table = self.make_table([
            "Xếp hạng", "Mã sản phẩm", "Tên sản phẩm", "Số hóa đơn",
            "Số lượng bán", "Tiền hàng", "Doanh thu sau KM", "Tồn kho"
        ])
        self.content_layout.addWidget(self.table)
        self.register_export_table("Bao cao san pham", self.table)

        self.sort_combo.currentIndexChanged.connect(lambda *_: self.refresh_data())
        self.search_input.returnPressed.connect(self.refresh_data)

    def load_report(self):
        start_date, end_date = self.date_parameters()
        search = self.search_input.text().strip()
        filter_sql = ""
        params = [start_date, end_date]
        if search:
            filter_sql = " AND (SP.MASP LIKE ? OR SP.TENSP LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        order_options = {
            "quantity_desc": "COALESCE(S.SL_BAN, 0) DESC, COALESCE(S.DOANH_THU, 0) DESC, SP.TENSP ASC",
            "quantity_asc": "COALESCE(S.SL_BAN, 0) ASC, COALESCE(S.DOANH_THU, 0) ASC, SP.TENSP ASC",
            "revenue_desc": "COALESCE(S.DOANH_THU, 0) DESC, COALESCE(S.SL_BAN, 0) DESC, SP.TENSP ASC",
        }
        order_sql = order_options.get(
            self.sort_combo.currentData(),
            order_options["quantity_desc"],
        )

        sql = f"""
            WITH Sales AS (
                SELECT
                    CT.MASP,
                    COUNT(DISTINCT HD.MAHD) AS SO_HD,
                    SUM(COALESCE(CT.SOLUONG, 0)) AS SL_BAN,
                    SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)) AS TIEN_HANG,
                    SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)
                        * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0)) AS DOANH_THU
                FROM dbo.HOA_DON HD
                INNER JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.TRANGTHAI = 1
                  AND HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY CT.MASP
            )
            SELECT
                ROW_NUMBER() OVER (ORDER BY {order_sql}) AS XEP_HANG,
                SP.MASP,
                COALESCE(SP.TENSP, N''),
                COALESCE(S.SO_HD, 0),
                COALESCE(S.SL_BAN, 0),
                COALESCE(S.TIEN_HANG, 0),
                COALESCE(S.DOANH_THU, 0),
                COALESCE(SP.SLTON, 0),
                COALESCE(S.SL_BAN, 0) AS SL_BAN_SORT,
                COALESCE(S.DOANH_THU, 0) AS DOANH_THU_SORT
            FROM dbo.SAN_PHAM SP
            LEFT JOIN Sales S ON S.MASP = SP.MASP
            WHERE COALESCE(SP.IS_DELETED, 0) = 0
            {filter_sql}
            ORDER BY {order_sql}
        """
        rows = self.fetch_all(sql, tuple(params))

        total_sold = sum(int(row[4] or 0) for row in rows)
        total_revenue = sum((row[6] or 0) for row in rows)
        active_products = sum(1 for row in rows if int(row[4] or 0) > 0)
        self.set_stat("sold", number_text(total_sold))
        self.set_stat("revenue", money_text(total_revenue))
        self.set_stat("active", number_text(active_products))

        self.fill_table(self.table, [
            (
                number_text(row[0]), row[1], row[2], number_text(row[3]),
                number_text(row[4]), money_text(row[5]), money_text(row[6]),
                number_text(row[7]),
            )
            for row in rows
        ])
