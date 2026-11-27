"""Báo cáo hiệu quả bán hàng theo sản phẩm."""

from PySide6.QtWidgets import QLabel, QHBoxLayout, QComboBox, QLineEdit

from ui.bao_cao.bao_cao_co_so import ReportBasePage, money_text, number_text


class ProductReportPage(ReportBasePage):
    """Thống kê sản phẩm theo các tiêu chí báo cáo."""
    def __init__(self, db, parent=None):
        super().__init__(
            db,
            "Báo cáo sản phẩm",
            "Phân tích lượng bán, lượng đổi/trả, tiền hoàn và doanh thu ròng theo sản phẩm. Tồn kho là số hiện tại.",
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
        search = self.search_input.text().strip()
        filter_sql = ""
        order_options = {
            "quantity_desc": (
                "COALESCE(S.SL_BAN, 0) DESC, "
                "(COALESCE(S.DOANH_THU, 0) - COALESCE(R.TIEN_HOAN, 0)) DESC, "
                "SP.TENSP ASC"
            ),
            "quantity_asc": (
                "COALESCE(S.SL_BAN, 0) ASC, "
                "(COALESCE(S.DOANH_THU, 0) - COALESCE(R.TIEN_HOAN, 0)) ASC, "
                "SP.TENSP ASC"
            ),
            "revenue_desc": (
                "(COALESCE(S.DOANH_THU, 0) - COALESCE(R.TIEN_HOAN, 0)) DESC, "
                "COALESCE(S.SL_BAN, 0) DESC, SP.TENSP ASC"
            ),
        }
        order_sql = order_options.get(
            self.sort_combo.currentData(),
            order_options["quantity_desc"],
        )

        sales_params = [start_date, end_date]
        return_params = [start_date, end_date]
        if search:
            filter_sql = " AND (SP.MASP LIKE ? OR SP.TENSP LIKE ?)"
            search_params = [f"%{search}%", f"%{search}%"]
        else:
            search_params = []

        sql = f"""
            WITH Sales AS (
                SELECT
                    CT.MASP,
                    COUNT(DISTINCT HD.MAHD) AS SO_HD,
                    SUM(COALESCE(CT.SOLUONG, 0)) AS SL_BAN,
                    SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)) AS TIEN_HANG,
                    SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)
                        * COALESCE(KM.TYLEGIAM, 0) / 100.0) AS TIEN_GIAM,
                    SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)
                        * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0)) AS DOANH_THU
                FROM dbo.HOA_DON HD
                INNER JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.TRANGTHAI = 1
                  AND HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY CT.MASP
            ),
            Returns AS (
                SELECT
                    CTDT.MASP,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_HOAN_TIEN,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 1
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_DOI_HANG,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0
                        THEN COALESCE(CTDT.DONGIAHOAN, 0)
                           * COALESCE(CTDT.SOLUONG, 0)
                        ELSE 0 END) AS TIEN_HOAN
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY CTDT.MASP
            )
            SELECT
                ROW_NUMBER() OVER (ORDER BY {order_sql}) AS XEP_HANG,
                SP.MASP,
                COALESCE(SP.TENSP, N''),
                COALESCE(S.SO_HD, 0),
                COALESCE(S.SL_BAN, 0),
                COALESCE(R.SL_HOAN_TIEN, 0),
                COALESCE(R.SL_DOI_HANG, 0),
                COALESCE(S.TIEN_HANG, 0),
                COALESCE(S.TIEN_GIAM, 0),
                COALESCE(S.DOANH_THU, 0),
                COALESCE(R.TIEN_HOAN, 0),
                COALESCE(S.DOANH_THU, 0) - COALESCE(R.TIEN_HOAN, 0),
                COALESCE(SP.SLTON, 0)
            FROM dbo.SAN_PHAM SP
            LEFT JOIN Sales S ON S.MASP = SP.MASP
            LEFT JOIN Returns R ON R.MASP = SP.MASP
            WHERE COALESCE(SP.IS_DELETED, 0) = 0
            {filter_sql}
            ORDER BY {order_sql}
        """
        params = [*sales_params, *return_params, *search_params]
        rows = self.fetch_all(sql, tuple(params))

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
