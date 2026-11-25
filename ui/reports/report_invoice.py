"""Báo cáo chi tiết hóa đơn bán hàng."""

from ui.reports.report_base import (
    ReportBasePage, money_text, number_text, date_text,
)


class InvoiceReportPage(ReportBasePage):
    def __init__(self, db, parent=None):
        super().__init__(
            db,
            "Báo cáo hóa đơn",
            "Tra cứu hóa đơn theo thời gian, nhân viên, ca làm việc và trạng thái. Hóa đơn hủy vẫn hiển thị để đối chiếu nhưng không ghi nhận doanh thu.",
            True,
            parent,
        )
        self.add_stat_cards([
            ("total", "TỔNG SỐ HÓA ĐƠN", "0"),
            ("valid", "HÓA ĐƠN HỢP LỆ", "0"),
            ("cancelled", "HÓA ĐƠN ĐÃ HỦY", "0"),
            ("revenue", "DOANH THU ĐƯỢC GHI NHẬN", "0 đ"),
        ])
        self.table = self.make_table([
            "Mã hóa đơn", "Ngày lập", "Nhân viên", "Mã ca",
            "Tiền hàng", "Tỷ lệ giảm", "Tiền giảm", "Thành tiền",
            "Doanh thu ghi nhận", "Khách đưa", "Trạng thái"
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
                COALESCE(S.TIEN_HANG, 0) * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0) AS THANH_TIEN,
                CASE WHEN HD.TRANGTHAI = 1
                    THEN COALESCE(S.TIEN_HANG, 0) * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0)
                    ELSE 0 END AS DOANH_THU_GHI_NHAN,
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
            WHERE HD.NGAYLAP >= CONVERT(date, ?)
              AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
            ORDER BY HD.NGAYLAP DESC, HD.MAHD DESC
        """
        rows = self.fetch_all(sql, (start_date, end_date))

        total_count = len(rows)
        valid_count = sum(1 for row in rows if row[10] is True or row[10] == 1)
        cancelled_count = sum(1 for row in rows if row[10] is False or row[10] == 0)
        revenue = sum((row[8] or 0) for row in rows)

        self.set_stat("total", number_text(total_count))
        self.set_stat("valid", number_text(valid_count))
        self.set_stat("cancelled", number_text(cancelled_count))
        self.set_stat("revenue", money_text(revenue))

        display = []
        for row in rows:
            status = "Đã thanh toán" if row[10] is True or row[10] == 1 else (
                "Đã hủy" if row[10] is False or row[10] == 0 else "Không xác định"
            )
            display.append((
                row[0], date_text(row[1]), row[2], row[3],
                money_text(row[4]), f"{float(row[5] or 0):.2f}%",
                money_text(row[6]), money_text(row[7]),
                money_text(row[8]), money_text(row[9]), status,
            ))
        self.fill_table(self.table, display)
