"""Báo cáo phiếu đổi trả và tiền hoàn lại."""

from ui.bao_cao.bao_cao_co_so import (
    ReportBasePage, money_text, number_text, date_text,
)


class ReturnReportPage(ReportBasePage):
    """Hiển thị dữ liệu đổi trả để theo dõi số lượng và giá trị giao dịch."""
    def __init__(self, db, parent=None):
        super().__init__(
            db,
            "Báo cáo đổi trả",
            "Phân biệt số lượng hoàn tiền, đổi sản phẩm, tình trạng hàng và khoản tiền thực tế hoàn cho khách.",
            True,
            parent,
        )
        self.add_stat_cards([
            ("count", "Số phiếu đổi trả", "0",
             "Số chứng từ được lập trong kỳ", "neutral"),
            ("refund_qty", "SL hoàn tiền", "0",
             "Hàng xử lý theo hình thức hoàn tiền", "warning"),
            ("exchange_qty", "SL đổi sản phẩm", "0",
             "Hàng xử lý theo hình thức đổi cùng mã", "positive"),
            ("intact_qty", "SL hàng nguyên vẹn", "0",
             "Hàng trả về còn nguyên vẹn", "neutral"),
            ("damaged_qty", "SL hàng hỏng", "0",
             "Hàng được ghi nhận đã hỏng", "negative"),
            ("amount", "Tổng tiền đã hoàn", "0 đ",
             "Tiền thực tế hoàn cho khách; đổi hàng không cộng vào đây", "primary"),
        ], primary_key="amount")
        self.table = self.make_table([
            "Mã phiếu", "Ngày xử lý", "Hóa đơn gốc", "Nhân viên",
            "Lý do", "SL hoàn tiền", "SL đổi hàng", "SL nguyên vẹn",
            "SL hàng hỏng", "Tổng tiền hoàn"
        ])
        self.content_layout.addWidget(self.table)
        self.register_export_table("Bao cao doi tra", self.table)

    def load_report(self):
        start_date, end_date = self.date_parameters()
        sql = """
            SELECT
                PDT.MAPDT,
                PDT.NGAY_DOI_TRA,
                COALESCE(PDT.MAHD, N''),
                COALESCE(NV.TENNV, PDT.MANV, N''),
                COALESCE(PDT.LY_DO, N''),
                COALESCE(CT.SL_HOAN_TIEN, 0),
                COALESCE(CT.SL_DOI_HANG, 0),
                COALESCE(CT.SL_NGUYEN_VEN, 0),
                COALESCE(CT.SL_HANG_HONG, 0),
                COALESCE(PDT.TONG_TIEN_HOAN, 0)
            FROM dbo.PHIEU_DOI_TRA PDT
            LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = PDT.MANV
            OUTER APPLY (
                SELECT
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_HOAN_TIEN,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 1
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_DOI_HANG,
                    SUM(CASE WHEN CTDT.TINHTRANGHANG = 1
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_NGUYEN_VEN,
                    SUM(CASE WHEN CTDT.TINHTRANGHANG = 0
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_HANG_HONG
                FROM dbo.CHI_TIET_DOI_TRA CTDT
                WHERE CTDT.MAPDT = PDT.MAPDT
            ) CT
            WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
              AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
            ORDER BY PDT.NGAY_DOI_TRA DESC, PDT.MAPDT DESC
        """
        rows = self.fetch_all(sql, (start_date, end_date))
        refund_quantity = sum(int(row[5] or 0) for row in rows)
        exchange_quantity = sum(int(row[6] or 0) for row in rows)
        intact_quantity = sum(int(row[7] or 0) for row in rows)
        damaged_quantity = sum(int(row[8] or 0) for row in rows)
        refund_amount = sum((row[9] or 0) for row in rows)

        self.set_stat("count", number_text(len(rows)))
        self.set_stat("refund_qty", number_text(refund_quantity))
        self.set_stat("exchange_qty", number_text(exchange_quantity))
        self.set_stat("intact_qty", number_text(intact_quantity))
        self.set_stat("damaged_qty", number_text(damaged_quantity))
        self.set_stat("amount", money_text(refund_amount))
        self.fill_table(self.table, [
            (
                row[0], date_text(row[1]), row[2], row[3], row[4],
                number_text(row[5]), number_text(row[6]),
                number_text(row[7]), number_text(row[8]), money_text(row[9]),
            )
            for row in rows
        ])
