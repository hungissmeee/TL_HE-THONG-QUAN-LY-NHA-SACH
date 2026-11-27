"""Báo cáo chi tiết hóa đơn bán hàng."""

from ui.bao_cao.bao_cao_co_so import (
    ReportBasePage, money_text, number_text, date_text,
)


class InvoiceReportPage(ReportBasePage):
    """Hiển thị số liệu tổng hợp từ hóa đơn bán hàng."""
    def __init__(self, db, parent=None):
        super().__init__(
            db,
            "Báo cáo hóa đơn",
            "Tiền hoàn và số lượng đổi/trả được cộng lũy kế theo hóa đơn gốc, không phụ thuộc ngày lập phiếu đổi trả. Hóa đơn hủy vẫn được giữ để tra cứu.",
            True,
            parent,
        )
        self.add_stat_cards([
            ("total", "Tổng số hóa đơn", "0",
             "Tất cả hóa đơn trong kỳ", "neutral"),
            ("valid", "Hóa đơn hợp lệ", "0",
             "Được ghi nhận doanh thu", "positive"),
            ("cancelled", "Hóa đơn đã hủy", "0",
             "Không ghi nhận doanh thu", "negative"),
            ("revenue", "Doanh thu trước hoàn", "0 đ",
             "Hóa đơn hợp lệ sau khuyến mãi", "positive"),
            ("refund", "Tiền đã hoàn", "0 đ",
             "Tổng tiền hoàn gắn với các hóa đơn trong kỳ", "warning"),
            ("net", "Doanh thu sau hoàn", "0 đ",
             "Doanh thu hợp lệ trừ tiền hoàn lũy kế", "primary"),
        ], primary_key="net")
        self.table = self.make_table([
            "Mã hóa đơn", "Ngày lập", "Nhân viên", "Mã ca",
            "Tiền hàng", "Tỷ lệ giảm", "Tiền giảm", "Thành tiền",
            "Doanh thu ghi nhận", "Số phiếu đổi trả", "SL hoàn tiền",
            "SL đổi hàng", "Tiền đã hoàn", "Doanh thu sau hoàn",
            "Khách đưa", "Trạng thái"
        ])
        self.content_layout.addWidget(self.table)
        self.register_export_table("Bao cao hoa don", self.table)

    def load_report(self):
        start_date, end_date = self.date_parameters()
        sql = """
            SELECT
                HD.MAHD,
                HD.NGAYLAP,
                COALESCE(NV.TENNV, HD.MANV, N''),
                COALESCE(CONVERT(nvarchar(20), HD.MACA), N''),
                COALESCE(S.TIEN_HANG, 0) AS TIEN_HANG,
                COALESCE(KM.TYLEGIAM, 0) AS TYLE_GIAM,
                COALESCE(S.TIEN_HANG, 0) * COALESCE(KM.TYLEGIAM, 0) / 100.0 AS TIEN_GIAM,
                COALESCE(S.TIEN_HANG, 0)
                    * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0) AS THANH_TIEN,
                CASE WHEN HD.TRANGTHAI = 1
                    THEN COALESCE(S.TIEN_HANG, 0)
                        * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0)
                    ELSE 0 END AS DOANH_THU_GHI_NHAN,
                COALESCE(R.SO_PHIEU, 0),
                COALESCE(RX.SL_HOAN_TIEN, 0),
                COALESCE(RX.SL_DOI_HANG, 0),
                COALESCE(R.TIEN_HOAN, 0),
                CASE WHEN HD.TRANGTHAI = 1
                    THEN COALESCE(S.TIEN_HANG, 0)
                        * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0)
                        - COALESCE(R.TIEN_HOAN, 0)
                    ELSE 0 END AS DOANH_THU_SAU_HOAN,
                COALESCE(HD.TIENKHACHDUA, 0),
                HD.TRANGTHAI
            FROM dbo.HOA_DON HD
            LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = HD.MANV
            LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
            OUTER APPLY (
                SELECT SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)) AS TIEN_HANG
                FROM dbo.CHI_TIET_HOA_DON CT
                WHERE CT.MAHD = HD.MAHD
            ) S
            OUTER APPLY (
                SELECT
                    COUNT(*) AS SO_PHIEU,
                    COALESCE(SUM(PDT.TONG_TIEN_HOAN), 0) AS TIEN_HOAN
                FROM dbo.PHIEU_DOI_TRA PDT
                WHERE PDT.MAHD = HD.MAHD
            ) R
            OUTER APPLY (
                SELECT
                    COALESCE(SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0
                        THEN CTDT.SOLUONG ELSE 0 END), 0) AS SL_HOAN_TIEN,
                    COALESCE(SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 1
                        THEN CTDT.SOLUONG ELSE 0 END), 0) AS SL_DOI_HANG
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                WHERE PDT.MAHD = HD.MAHD
            ) RX
            WHERE HD.NGAYLAP >= CONVERT(date, ?)
              AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
            ORDER BY HD.NGAYLAP DESC, HD.MAHD DESC
        """
        rows = self.fetch_all(sql, (start_date, end_date))

        total_count = len(rows)
        valid_rows = [row for row in rows if row[15] is True or row[15] == 1]
        cancelled_count = sum(
            1 for row in rows if row[15] is False or row[15] == 0
        )
        gross_revenue = sum((row[8] or 0) for row in valid_rows)
        refund_total = sum((row[12] or 0) for row in rows)
        net_revenue = sum((row[13] or 0) for row in rows)

        self.set_stat("total", number_text(total_count))
        self.set_stat("valid", number_text(len(valid_rows)))
        self.set_stat("cancelled", number_text(cancelled_count))
        self.set_stat("revenue", money_text(gross_revenue))
        self.set_stat("refund", money_text(refund_total))
        self.set_stat("net", money_text(net_revenue))

        display = []
        for row in rows:
            status = "Đã thanh toán" if row[15] is True or row[15] == 1 else (
                "Đã hủy" if row[15] is False or row[15] == 0 else "Không xác định"
            )
            display.append((
                row[0], date_text(row[1]), row[2], row[3],
                money_text(row[4]), f"{float(row[5] or 0):.2f}%",
                money_text(row[6]), money_text(row[7]),
                money_text(row[8]), number_text(row[9]),
                number_text(row[10]), number_text(row[11]),
                money_text(row[12]), money_text(row[13]),
                money_text(row[14]), status,
            ))
        self.fill_table(self.table, display)
