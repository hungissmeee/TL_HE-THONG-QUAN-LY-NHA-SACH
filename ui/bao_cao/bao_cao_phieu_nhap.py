"""Báo cáo phiếu nhập hàng."""

from ui.bao_cao.bao_cao_co_so import (
    ReportBasePage, money_text, number_text, date_text,
)


class ImportReportPage(ReportBasePage):
    """Hiển thị số liệu tổng hợp từ các phiếu nhập."""
    def __init__(self, db, parent=None):
        super().__init__(
            db,
            "Báo cáo nhập hàng",
            "Tra cứu toàn bộ phiếu nhập theo nhà cung cấp và nhân viên; số lượng và trị giá thực nhập chỉ tính phiếu còn hiệu lực.",
            True,
            parent,
        )
        self.add_stat_cards([
            ("total", "Tổng số phiếu", "0",
             "Bao gồm cả phiếu đã hủy để đối chiếu", "neutral"),
            ("active", "Phiếu còn hiệu lực", "0",
             "Được tính vào số lượng và trị giá nhập thực tế", "positive"),
            ("cancelled", "Phiếu đã hủy", "0",
             "Không được tính vào nhập hàng thực tế", "negative"),
            ("quantity", "Số lượng thực nhập", "0",
             "Chỉ cộng chi tiết của phiếu còn hiệu lực", "neutral"),
            ("amount", "Tổng trị giá thực nhập", "0 đ",
             "Chỉ cộng phiếu nhập còn hiệu lực", "primary"),
        ], primary_key="amount")
        self.table = self.make_table([
            "Mã phiếu nhập", "Ngày nhập", "Loại phiếu", "Nhà cung cấp",
            "Số HĐ nhà cung cấp", "Nhân viên lập", "Số lượng theo phiếu",
            "Tổng trị giá", "Trạng thái"
        ])
        self.content_layout.addWidget(self.table)
        self.register_export_table("Bao cao nhap hang", self.table)

    def load_report(self):
        start_date, end_date = self.date_parameters()
        sql = """
            SELECT
                PN.MAPN,
                PN.NGAYNHAP,
                COALESCE(PN.LOAIPHIEUNHAP, N''),
                COALESCE(NCC.TENNCC, PN.MANCC, N''),
                COALESCE(PN.SHDNCC, N''),
                COALESCE(NV.TENNV, PN.MANV, N''),
                COALESCE(CT.TONG_SOLUONG, 0),
                COALESCE(PN.TONGTRIGIA, 0),
                ISNULL(PN.TRANGTHAI, 1) AS TRANGTHAI
            FROM dbo.PHIEU_NHAP PN
            LEFT JOIN dbo.NHA_CUNG_CAP NCC ON NCC.MANCC = PN.MANCC
            LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = PN.MANV
            OUTER APPLY (
                SELECT SUM(COALESCE(CTPN.SOLUONG, 0)) AS TONG_SOLUONG
                FROM dbo.CHI_TIET_PHIEU_NHAP CTPN
                WHERE CTPN.MAPN = PN.MAPN
            ) CT
            WHERE PN.NGAYNHAP >= CONVERT(date, ?)
              AND PN.NGAYNHAP < DATEADD(day, 1, CONVERT(date, ?))
            ORDER BY PN.NGAYNHAP DESC, PN.MAPN DESC
        """
        rows = self.fetch_all(sql, (start_date, end_date))
        active_rows = [row for row in rows if int(row[8] or 0) == 1]
        cancelled_rows = [row for row in rows if int(row[8] or 0) == 0]
        quantity = sum(int(row[6] or 0) for row in active_rows)
        amount = sum((row[7] or 0) for row in active_rows)

        self.set_stat("total", number_text(len(rows)))
        self.set_stat("active", number_text(len(active_rows)))
        self.set_stat("cancelled", number_text(len(cancelled_rows)))
        self.set_stat("quantity", number_text(quantity))
        self.set_stat("amount", money_text(amount))

        self.fill_table(self.table, [
            (
                row[0], date_text(row[1]), row[2], row[3], row[4], row[5],
                number_text(row[6]), money_text(row[7]),
                "Có hiệu lực" if int(row[8] or 0) == 1 else "Đã hủy",
            )
            for row in rows
        ])
