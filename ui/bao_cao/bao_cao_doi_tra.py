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
            "Theo dõi số phiếu đổi trả, hóa đơn gốc, nhân viên xử lý, số lượng hàng hoàn và tiền hoàn.",
            True,
            parent,
        )
        self.add_stat_cards([
            ("count", "Số phiếu đổi trả", "0",
             "Số chứng từ đổi trả trong kỳ", "neutral"),
            ("quantity", "Số lượng sản phẩm hoàn", "0",
             "Tổng số lượng hàng được ghi nhận hoàn", "warning"),
            ("amount", "Tổng tiền đã hoàn", "0 đ",
             "Tổng tiền hoàn trên các phiếu đổi trả", "primary"),
        ])
        self.table = self.make_table([
            "Mã phiếu đổi trả", "Ngày đổi trả", "Mã hóa đơn",
            "Nhân viên", "Lý do", "Số lượng hoàn", "Tiền hoàn"
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
                COALESCE(CT.TONG_SOLUONG, 0),
                COALESCE(PDT.TONG_TIEN_HOAN, 0)
            FROM dbo.PHIEU_DOI_TRA PDT
            LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = PDT.MANV
            OUTER APPLY (
                SELECT SUM(COALESCE(CTDT.SOLUONG, 0)) AS TONG_SOLUONG
                FROM dbo.CHI_TIET_DOI_TRA CTDT
                WHERE CTDT.MAPDT = PDT.MAPDT
            ) CT
            WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
              AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
            ORDER BY PDT.NGAY_DOI_TRA DESC, PDT.MAPDT DESC
        """
        rows = self.fetch_all(sql, (start_date, end_date))
        quantity = sum(int(row[5] or 0) for row in rows)
        amount = sum((row[6] or 0) for row in rows)

        self.set_stat("count", number_text(len(rows)))
        self.set_stat("quantity", number_text(quantity))
        self.set_stat("amount", money_text(amount))
        self.fill_table(self.table, [
            (
                row[0], date_text(row[1]), row[2], row[3], row[4],
                number_text(row[5]), money_text(row[6]),
            )
            for row in rows
        ])
