"""Repository truy vấn dữ liệu cho các báo cáo nhà sách.

Chỉ chứa SQL/read-model. Các trang PySide6 và API Web không tự thực thi SQL.
"""

from core.sql_support import resolve_connection


class BaoCaoRepository:
    def __init__(self, connection_source):
        self.connection_source = connection_source

    def _fetch_all(self, sql, params=()):
        conn = resolve_connection(self.connection_source)
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()

    def _fetch_one(self, sql, params=()):
        rows = self._fetch_all(sql, params)
        return rows[0] if rows else None

    def overview_summary(self, start_date, end_date):
        """Tổng hợp số hóa đơn và doanh thu, làm tròn giảm giá theo từng hóa đơn."""
        return self._fetch_one("""
            WITH InvoiceTotals AS (
                SELECT
                    HD.MAHD,
                    HD.TRANGTHAI,
                    COALESCE(KM.TYLEGIAM, 0) AS TYLEGIAM,
                    COALESCE(SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)), 0)
                        AS TIEN_HANG
                FROM dbo.HOA_DON HD
                LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY HD.MAHD, HD.TRANGTHAI, KM.TYLEGIAM
            )
            SELECT
                COUNT(CASE WHEN TRANGTHAI = 1 THEN 1 END),
                COUNT(CASE WHEN TRANGTHAI = 0 THEN 1 END),
                COALESCE(SUM(CASE WHEN TRANGTHAI = 1
                    THEN TIEN_HANG - ROUND(TIEN_HANG * TYLEGIAM / 100.0, 2)
                    ELSE 0 END), 0)
            FROM InvoiceTotals
        """, (start_date, end_date))

    def overview_refunds(self, start_date, end_date):
        return self._fetch_one("""
            SELECT COALESCE(SUM(TONG_TIEN_HOAN), 0)
            FROM dbo.PHIEU_DOI_TRA
            WHERE NGAY_DOI_TRA >= CONVERT(date, ?)
              AND NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
        """, (start_date, end_date))

    def overview_imports(self, start_date, end_date):
        return self._fetch_one("""
            SELECT COALESCE(SUM(TONGTRIGIA), 0)
            FROM dbo.PHIEU_NHAP
            WHERE NGAYNHAP >= CONVERT(date, ?)
              AND NGAYNHAP < DATEADD(day, 1, CONVERT(date, ?))
              AND ISNULL(TRANGTHAI, 1) = 1
        """, (start_date, end_date))

    def overview_trend(self, start_date, end_date):
        """Doanh thu theo ngày bán và tiền hoàn theo ngày lập phiếu đổi trả."""
        return self._fetch_all("""
            WITH InvoiceTotals AS (
                SELECT
                    HD.MAHD,
                    CAST(HD.NGAYLAP AS date) AS NGAY,
                    HD.TRANGTHAI,
                    COUNT(CT.MASP) AS SO_DONG,
                    COALESCE(SUM(CT.SOLUONG), 0) AS SO_LUONG,
                    COALESCE(SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)), 0)
                        AS TIEN_HANG,
                    COALESCE(KM.TYLEGIAM, 0) AS TYLEGIAM
                FROM dbo.HOA_DON HD
                LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY HD.MAHD, CAST(HD.NGAYLAP AS date),
                         HD.TRANGTHAI, KM.TYLEGIAM
            ),
            SalesByDay AS (
                SELECT
                    NGAY,
                    COUNT(CASE WHEN TRANGTHAI = 1 THEN 1 END) AS SO_HD,
                    SUM(CASE WHEN TRANGTHAI = 1 THEN SO_LUONG ELSE 0 END) AS SO_LUONG,
                    SUM(CASE WHEN TRANGTHAI = 1 THEN
                        TIEN_HANG - ROUND(TIEN_HANG * TYLEGIAM / 100.0, 2)
                        ELSE 0 END) AS DOANH_THU
                FROM InvoiceTotals
                GROUP BY NGAY
            ),
            RefundByDay AS (
                SELECT
                    CAST(NGAY_DOI_TRA AS date) AS NGAY,
                    COALESCE(SUM(TONG_TIEN_HOAN), 0) AS TIEN_HOAN
                FROM dbo.PHIEU_DOI_TRA
                WHERE NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY CAST(NGAY_DOI_TRA AS date)
            )
            SELECT
                COALESCE(S.NGAY, R.NGAY) AS NGAY,
                COALESCE(S.SO_HD, 0) AS SO_HD,
                COALESCE(S.SO_LUONG, 0) AS SO_LUONG,
                COALESCE(S.DOANH_THU, 0) AS DOANH_THU,
                COALESCE(R.TIEN_HOAN, 0) AS TIEN_HOAN,
                COALESCE(S.DOANH_THU, 0) - COALESCE(R.TIEN_HOAN, 0)
                    AS THUAN_THEO_NGAY_PHAT_SINH
            FROM SalesByDay S
            FULL OUTER JOIN RefundByDay R ON R.NGAY = S.NGAY
            ORDER BY NGAY
        """, (start_date, end_date, start_date, end_date))

    def overview_top_products(self, start_date, end_date):
        """Top sản phẩm bán chạy theo số lượng, không phân bổ doanh thu/hoàn."""
        return self._fetch_all("""
            SELECT TOP 10
                SP.MASP,
                COALESCE(SP.TENSP, N''),
                SUM(COALESCE(CT.SOLUONG, 0)) AS SO_LUONG
            FROM dbo.HOA_DON HD
            INNER JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
            INNER JOIN dbo.SAN_PHAM SP ON SP.MASP = CT.MASP
            WHERE HD.TRANGTHAI = 1
              AND HD.NGAYLAP >= CONVERT(date, ?)
              AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
            GROUP BY SP.MASP, SP.TENSP
            ORDER BY SUM(COALESCE(CT.SOLUONG, 0)) DESC, SP.TENSP
        """, (start_date, end_date))

    def revenue_by_period(self, start_date, end_date, period):
        """Doanh số theo kỳ; tiền hoàn và số lượng đổi trả theo ngày xử lý."""
        sales_periods = {
            "day": "CAST(NGAYLAP AS date)",
            "month": "DATEFROMPARTS(YEAR(NGAYLAP), MONTH(NGAYLAP), 1)",
            "year": "DATEFROMPARTS(YEAR(NGAYLAP), 1, 1)",
        }
        return_period = {
            "day": "CAST(NGAY_DOI_TRA AS date)",
            "month": "DATEFROMPARTS(YEAR(NGAY_DOI_TRA), MONTH(NGAY_DOI_TRA), 1)",
            "year": "DATEFROMPARTS(YEAR(NGAY_DOI_TRA), 1, 1)",
        }
        sales_key = sales_periods[period]
        return_key = return_period[period]
        sql = f"""
            WITH InvoiceTotals AS (
                SELECT
                    HD.MAHD, HD.NGAYLAP, HD.TRANGTHAI,
                    COALESCE(KM.TYLEGIAM, 0) AS TYLEGIAM,
                    COALESCE(SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)), 0)
                        AS TIEN_HANG,
                    COALESCE(SUM(COALESCE(CT.SOLUONG, 0)), 0) AS SL_BAN
                FROM dbo.HOA_DON HD
                LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY HD.MAHD, HD.NGAYLAP, HD.TRANGTHAI, KM.TYLEGIAM
            ),
            Sales AS (
                SELECT
                    {sales_key} AS KY,
                    COUNT(CASE WHEN TRANGTHAI = 1 THEN 1 END) AS SO_HD,
                    SUM(CASE WHEN TRANGTHAI = 1 THEN SL_BAN ELSE 0 END) AS SL_BAN,
                    SUM(CASE WHEN TRANGTHAI = 1 THEN TIEN_HANG ELSE 0 END) AS TIEN_HANG,
                    SUM(CASE WHEN TRANGTHAI = 1
                        THEN ROUND(TIEN_HANG * TYLEGIAM / 100.0, 2)
                        ELSE 0 END) AS TIEN_GIAM,
                    SUM(CASE WHEN TRANGTHAI = 1
                        THEN TIEN_HANG - ROUND(TIEN_HANG * TYLEGIAM / 100.0, 2)
                        ELSE 0 END) AS DOANH_SO
                FROM InvoiceTotals
                GROUP BY {sales_key}
            ),
            RefundHeaders AS (
                SELECT
                    {return_key} AS KY,
                    SUM(COALESCE(PDT.TONG_TIEN_HOAN, 0)) AS TIEN_HOAN
                FROM dbo.PHIEU_DOI_TRA PDT
                WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY {return_key}
            ),
            ReturnLines AS (
                SELECT
                    {return_key} AS KY,
                    SUM(COALESCE(CTDT.SOLUONG, 0)) AS SL_DOI_TRA
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY {return_key}
            )
            SELECT
                COALESCE(S.KY, H.KY, L.KY) AS KY,
                COALESCE(S.SO_HD, 0) AS SO_HD,
                COALESCE(S.SL_BAN, 0) AS SL_BAN,
                COALESCE(S.TIEN_HANG, 0) AS TIEN_HANG,
                COALESCE(S.TIEN_GIAM, 0) AS TIEN_GIAM,
                COALESCE(S.DOANH_SO, 0) AS DOANH_SO,
                COALESCE(L.SL_DOI_TRA, 0) AS SL_DOI_TRA,
                COALESCE(H.TIEN_HOAN, 0) AS TIEN_HOAN,
                COALESCE(S.DOANH_SO, 0) - COALESCE(H.TIEN_HOAN, 0)
                    AS DOANH_SO_SAU_HOAN
            FROM Sales S
            FULL OUTER JOIN RefundHeaders H ON H.KY = S.KY
            FULL OUTER JOIN ReturnLines L ON L.KY = COALESCE(S.KY, H.KY)
            ORDER BY KY DESC
        """
        return self._fetch_all(sql, (
            start_date, end_date,
            start_date, end_date,
            start_date, end_date,
        ))

    def promotion_effectiveness(self, start_date, end_date):
        """Hiệu quả khuyến mãi; tiền hoàn gắn theo hóa đơn gốc trong kỳ."""
        return self._fetch_all("""
            WITH InvoiceTotals AS (
                SELECT
                    HD.MAHD, HD.MAKM,
                    COALESCE(KM.TENKM, N'Không áp dụng khuyến mãi') AS TENKM,
                    COALESCE(KM.TYLEGIAM, 0) AS TYLEGIAM,
                    COALESCE(SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)), 0)
                        AS TIEN_HANG
                FROM dbo.HOA_DON HD
                LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.TRANGTHAI = 1
                  AND HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY HD.MAHD, HD.MAKM, KM.TENKM, KM.TYLEGIAM
            ),
            PromotionSales AS (
                SELECT
                    MAKM, TENKM, TYLEGIAM,
                    COUNT(*) AS SO_HD,
                    SUM(TIEN_HANG) AS TIEN_HANG,
                    SUM(ROUND(TIEN_HANG * TYLEGIAM / 100.0, 2)) AS TIEN_GIAM,
                    SUM(TIEN_HANG - ROUND(TIEN_HANG * TYLEGIAM / 100.0, 2))
                        AS DOANH_THU
                FROM InvoiceTotals
                GROUP BY MAKM, TENKM, TYLEGIAM
            ),
            PromotionRefunds AS (
                SELECT
                    I.MAKM,
                    COALESCE(SUM(PDT.TONG_TIEN_HOAN), 0) AS TIEN_HOAN
                FROM InvoiceTotals I
                INNER JOIN dbo.PHIEU_DOI_TRA PDT ON PDT.MAHD = I.MAHD
                GROUP BY I.MAKM
            )
            SELECT
                S.MAKM, S.TENKM, S.TYLEGIAM, S.SO_HD, S.TIEN_HANG,
                S.TIEN_GIAM, S.DOANH_THU, COALESCE(R.TIEN_HOAN, 0),
                S.DOANH_THU - COALESCE(R.TIEN_HOAN, 0)
            FROM PromotionSales S
            LEFT JOIN PromotionRefunds R
                ON ISNULL(R.MAKM, '') = ISNULL(S.MAKM, '')
            ORDER BY S.DOANH_THU DESC, S.TENKM
        """, (start_date, end_date))

    def invoice_report(self, start_date, end_date):
        """Chi tiết hóa đơn; tiền đổi trả là lũy kế theo hóa đơn gốc."""
        return self._fetch_all("""
            WITH InvoiceTotals AS (
                SELECT
                    HD.MAHD, HD.NGAYLAP, HD.MANV, HD.MACA, HD.TIENKHACHDUA,
                    HD.TRANGTHAI, COALESCE(KM.TYLEGIAM, 0) AS TYLEGIAM,
                    COALESCE(SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)), 0)
                        AS TIEN_HANG
                FROM dbo.HOA_DON HD
                LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY HD.MAHD, HD.NGAYLAP, HD.MANV, HD.MACA, HD.TIENKHACHDUA,
                         HD.TRANGTHAI, KM.TYLEGIAM
            ),
            ReturnTotals AS (
                SELECT
                    PDT.MAHD,
                    COUNT(*) AS SO_PHIEU,
                    SUM(COALESCE(PDT.TONG_TIEN_HOAN, 0)) AS TIEN_HOAN
                FROM dbo.PHIEU_DOI_TRA PDT
                GROUP BY PDT.MAHD
            ),
            ReturnQuantities AS (
                SELECT
                    PDT.MAHD,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_HOAN_TIEN,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 1
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_DOI_HANG
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                GROUP BY PDT.MAHD
            )
            SELECT
                I.MAHD, I.NGAYLAP,
                COALESCE(NV.TENNV, I.MANV, N''),
                COALESCE(CONVERT(nvarchar(20), I.MACA), N''),
                I.TIEN_HANG,
                I.TYLEGIAM,
                ROUND(I.TIEN_HANG * I.TYLEGIAM / 100.0, 2) AS TIEN_GIAM,
                I.TIEN_HANG - ROUND(I.TIEN_HANG * I.TYLEGIAM / 100.0, 2)
                    AS THANH_TIEN,
                CASE WHEN I.TRANGTHAI = 1
                    THEN I.TIEN_HANG - ROUND(I.TIEN_HANG * I.TYLEGIAM / 100.0, 2)
                    ELSE 0 END AS DOANH_THU_GHI_NHAN,
                COALESCE(R.SO_PHIEU, 0),
                COALESCE(RQ.SL_HOAN_TIEN, 0),
                COALESCE(RQ.SL_DOI_HANG, 0),
                COALESCE(R.TIEN_HOAN, 0),
                CASE WHEN I.TRANGTHAI = 1
                    THEN I.TIEN_HANG - ROUND(I.TIEN_HANG * I.TYLEGIAM / 100.0, 2)
                         - COALESCE(R.TIEN_HOAN, 0)
                    ELSE 0 END AS DOANH_THU_SAU_HOAN,
                COALESCE(I.TIENKHACHDUA, 0) AS TIEN_KHACH_DUA,
                CASE WHEN I.TIENKHACHDUA IS NOT NULL
                    THEN I.TIENKHACHDUA
                         - (I.TIEN_HANG - ROUND(I.TIEN_HANG * I.TYLEGIAM / 100.0, 2))
                    ELSE NULL END AS TIEN_THUA,
                I.TRANGTHAI
            FROM InvoiceTotals I
            LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = I.MANV
            LEFT JOIN ReturnTotals R ON R.MAHD = I.MAHD
            LEFT JOIN ReturnQuantities RQ ON RQ.MAHD = I.MAHD
            ORDER BY I.NGAYLAP DESC, I.MAHD DESC
        """, (start_date, end_date))

    def import_report(self, start_date, end_date):
        """Báo cáo nhập hàng theo chứng từ, nhà cung cấp và sản phẩm."""
        imports = self._fetch_all("""
            SELECT PN.MAPN, PN.NGAYNHAP,
                COALESCE(PN.LOAIPHIEUNHAP, N''),
                COALESCE(NCC.TENNCC, PN.MANCC, N''),
                COALESCE(PN.SHDNCC, N''),
                COALESCE(NV.TENNV, PN.MANV, N''),
                COALESCE(CT.TONG_SOLUONG, 0),
                COALESCE(PN.TONGTRIGIA, 0)
            FROM dbo.PHIEU_NHAP PN
            LEFT JOIN dbo.NHA_CUNG_CAP NCC ON NCC.MANCC = PN.MANCC
            LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = PN.MANV
            OUTER APPLY (
                SELECT SUM(COALESCE(CTPN.SOLUONG, 0)) AS TONG_SOLUONG
                FROM dbo.CHI_TIET_PHIEU_NHAP CTPN WHERE CTPN.MAPN = PN.MAPN
            ) CT
            WHERE PN.NGAYNHAP >= CONVERT(date, ?)
              AND PN.NGAYNHAP < DATEADD(day, 1, CONVERT(date, ?))
              AND ISNULL(PN.TRANGTHAI, 1) = 1
            ORDER BY PN.NGAYNHAP DESC, PN.MAPN DESC
        """, (start_date, end_date))

        suppliers = self._fetch_all("""
            SELECT
                PN.MANCC,
                COALESCE(NCC.TENNCC, PN.MANCC, N'Không xác định'),
                COALESCE(NCC.SDT, N''),
                COUNT(DISTINCT PN.MAPN),
                COALESCE(SUM(CT.TONG_SOLUONG), 0),
                COALESCE(SUM(PN.TONGTRIGIA), 0)
            FROM dbo.PHIEU_NHAP PN
            LEFT JOIN dbo.NHA_CUNG_CAP NCC ON NCC.MANCC = PN.MANCC
            OUTER APPLY (
                SELECT SUM(COALESCE(CTPN.SOLUONG, 0)) AS TONG_SOLUONG
                FROM dbo.CHI_TIET_PHIEU_NHAP CTPN WHERE CTPN.MAPN = PN.MAPN
            ) CT
            WHERE PN.NGAYNHAP >= CONVERT(date, ?)
              AND PN.NGAYNHAP < DATEADD(day, 1, CONVERT(date, ?))
              AND ISNULL(PN.TRANGTHAI, 1) = 1
            GROUP BY PN.MANCC, NCC.TENNCC, NCC.SDT
            ORDER BY SUM(PN.TONGTRIGIA) DESC, NCC.TENNCC
        """, (start_date, end_date))

        products = self._fetch_all("""
            SELECT
                CT.MASP,
                COALESCE(SP.TENSP, N''),
                COUNT(DISTINCT PN.MAPN) AS SO_PHIEU_NHAP,
                SUM(COALESCE(CT.SOLUONG, 0)) AS SL_NHAP,
                SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0))
                    AS GIA_TRI_NHAP
            FROM dbo.PHIEU_NHAP PN
            INNER JOIN dbo.CHI_TIET_PHIEU_NHAP CT ON CT.MAPN = PN.MAPN
            LEFT JOIN dbo.SAN_PHAM SP ON SP.MASP = CT.MASP
            WHERE PN.NGAYNHAP >= CONVERT(date, ?)
              AND PN.NGAYNHAP < DATEADD(day, 1, CONVERT(date, ?))
              AND ISNULL(PN.TRANGTHAI, 1) = 1
            GROUP BY CT.MASP, SP.TENSP
            ORDER BY SL_NHAP DESC, SP.TENSP
        """, (start_date, end_date))
        return {"imports": imports, "suppliers": suppliers, "products": products}

    def return_report(self, start_date, end_date):
        return self._fetch_all("""
            SELECT
                PDT.MAPDT, PDT.NGAY_DOI_TRA,
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
                FROM dbo.CHI_TIET_DOI_TRA CTDT WHERE CTDT.MAPDT = PDT.MAPDT
            ) CT
            WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
              AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
            ORDER BY PDT.NGAY_DOI_TRA DESC, PDT.MAPDT DESC
        """, (start_date, end_date))

    def inventory_report(self, threshold, status, keyword=""):
        """Ảnh chụp tồn kho hiện tại; KPI không bị thu hẹp theo bộ lọc trạng thái."""
        search_sql = ""
        search_params = []
        if keyword:
            search_sql = " AND (SP.MASP LIKE ? OR SP.TENSP LIKE ?)"
            search_params = [f"%{keyword}%", f"%{keyword}%"]

        row_status_sql = ""
        if status == "low":
            row_status_sql = (
                " AND COALESCE(SP.SLTON, 0) > 0 "
                "AND COALESCE(SP.SLTON, 0) <= ?"
            )
        elif status == "out":
            row_status_sql = " AND COALESCE(SP.SLTON, 0) <= 0"

        summary = self._fetch_one(f"""
            SELECT
                COUNT(*),
                SUM(CASE WHEN COALESCE(SP.SLTON, 0) > 0
                    AND COALESCE(SP.SLTON, 0) <= ? THEN 1 ELSE 0 END),
                SUM(CASE WHEN COALESCE(SP.SLTON, 0) <= 0 THEN 1 ELSE 0 END),
                COALESCE(SUM(COALESCE(SP.GIANHAP, 0) * COALESCE(SP.SLTON, 0)), 0)
            FROM dbo.SAN_PHAM SP
            WHERE COALESCE(SP.IS_DELETED, 0) = 0
            {search_sql}
        """, (threshold, *search_params))

        rows = self._fetch_all(f"""
            SELECT
                SP.MASP, COALESCE(SP.TENSP, N''), COALESCE(SP.DVT, N''),
                COALESCE(SP.SLTON, 0), COALESCE(SP.GIANHAP, 0),
                COALESCE(SP.GIABAN, 0),
                COALESCE(SP.GIANHAP, 0) * COALESCE(SP.SLTON, 0),
                CASE
                    WHEN COALESCE(SP.SLTON, 0) <= 0 THEN N'Hết hàng'
                    WHEN COALESCE(SP.SLTON, 0) <= ? THEN N'Sắp hết'
                    ELSE N'Còn hàng'
                END
            FROM dbo.SAN_PHAM SP
            WHERE COALESCE(SP.IS_DELETED, 0) = 0
              {search_sql}
              {row_status_sql}
            ORDER BY COALESCE(SP.SLTON, 0) ASC, SP.TENSP ASC
        """, (threshold, *search_params, *([threshold] if status == "low" else [])))
        return {"summary": summary, "rows": rows}

    def product_report(self, start_date, end_date, sort, keyword=""):
        """Báo cáo số lượng nhập, bán, hoàn, đổi và tồn kho theo sản phẩm."""
        order_options = {
            "quantity_desc": "COALESCE(S.SL_BAN, 0) DESC, SP.TENSP ASC",
            "quantity_asc": "COALESCE(S.SL_BAN, 0) ASC, SP.TENSP ASC",
            "refund_desc": (
                "COALESCE(R.SL_HOAN_TIEN, 0) DESC, "
                "COALESCE(S.SL_BAN, 0) DESC, SP.TENSP ASC"
            ),
        }
        order_sql = order_options[sort]
        filter_sql = ""
        search_params = []
        if keyword:
            filter_sql = " AND (SP.MASP LIKE ? OR SP.TENSP LIKE ?)"
            search_params = [f"%{keyword}%", f"%{keyword}%"]
        sql = f"""
            WITH Sales AS (
                SELECT CT.MASP,
                    COUNT(DISTINCT HD.MAHD) AS SO_HD,
                    SUM(COALESCE(CT.SOLUONG, 0)) AS SL_BAN
                FROM dbo.HOA_DON HD
                INNER JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                WHERE HD.TRANGTHAI = 1
                  AND HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY CT.MASP
            ),
            Purchases AS (
                SELECT CT.MASP,
                    SUM(COALESCE(CT.SOLUONG, 0)) AS SL_NHAP
                FROM dbo.PHIEU_NHAP PN
                INNER JOIN dbo.CHI_TIET_PHIEU_NHAP CT ON CT.MAPN = PN.MAPN
                WHERE ISNULL(PN.TRANGTHAI, 1) = 1
                  AND PN.NGAYNHAP >= CONVERT(date, ?)
                  AND PN.NGAYNHAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY CT.MASP
            ),
            Returns AS (
                SELECT CTDT.MASP,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_HOAN_TIEN,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 1
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_DOI_HANG,
                    SUM(CASE WHEN CTDT.TINHTRANGHANG = 1
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_NGUYEN_VEN,
                    SUM(CASE WHEN CTDT.TINHTRANGHANG = 0
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_HANG_HONG
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY CTDT.MASP
            )
            SELECT
                ROW_NUMBER() OVER (ORDER BY {order_sql}) AS XEP_HANG,
                SP.MASP, COALESCE(SP.TENSP, N''),
                COALESCE(S.SO_HD, 0), COALESCE(P.SL_NHAP, 0),
                COALESCE(S.SL_BAN, 0),
                COALESCE(R.SL_HOAN_TIEN, 0), COALESCE(R.SL_DOI_HANG, 0),
                COALESCE(R.SL_NGUYEN_VEN, 0), COALESCE(R.SL_HANG_HONG, 0),
                COALESCE(SP.SLTON, 0)
            FROM dbo.SAN_PHAM SP
            LEFT JOIN Sales S ON S.MASP = SP.MASP
            LEFT JOIN Purchases P ON P.MASP = SP.MASP
            LEFT JOIN Returns R ON R.MASP = SP.MASP
            WHERE (
                COALESCE(SP.IS_DELETED, 0) = 0
                OR S.MASP IS NOT NULL OR P.MASP IS NOT NULL OR R.MASP IS NOT NULL
            )
            {filter_sql}
            ORDER BY {order_sql}
        """
        return self._fetch_all(sql, (
            start_date, end_date,
            start_date, end_date,
            start_date, end_date,
            *search_params
        ))

    def stock_movement_report(self, start_date, end_date, keyword=""):
        """Tái dựng nhập–xuất–tồn từ số tồn hiện tại và chứng từ còn hiệu lực."""
        search_sql = ""
        search_params = []
        if keyword:
            search_sql = " AND (SP.MASP LIKE ? OR SP.TENSP LIKE ?)"
            search_params = [f"%{keyword}%", f"%{keyword}%"]
        return self._fetch_all(f"""
            WITH Bounds AS (
                SELECT
                    CONVERT(date, ?) AS START_DATE,
                    DATEADD(day, 1, CONVERT(date, ?)) AS END_EXCLUSIVE
            ),
            Movements AS (
                SELECT
                    CT.MASP, PN.NGAYNHAP AS NGAY,
                    N'PURCHASE' AS LOAI,
                    SUM(COALESCE(CT.SOLUONG, 0)) AS SO_LUONG,
                    SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0))
                        AS GIA_TRI_THUC_TE,
                    SUM(COALESCE(CT.SOLUONG, 0)) AS BIEN_DONG
                FROM dbo.PHIEU_NHAP PN
                INNER JOIN dbo.CHI_TIET_PHIEU_NHAP CT ON CT.MAPN = PN.MAPN
                CROSS JOIN Bounds B
                WHERE ISNULL(PN.TRANGTHAI, 1) = 1
                  AND PN.NGAYNHAP >= B.START_DATE
                  AND PN.NGAYNHAP < SYSDATETIME()
                GROUP BY CT.MASP, PN.NGAYNHAP

                UNION ALL

                SELECT
                    CT.MASP, HD.NGAYLAP AS NGAY,
                    N'SALE' AS LOAI,
                    SUM(COALESCE(CT.SOLUONG, 0)) AS SO_LUONG,
                    SUM(COALESCE(CT.SOLUONG, 0) * COALESCE(SP.GIANHAP, 0))
                        AS GIA_TRI_THUC_TE,
                    -SUM(COALESCE(CT.SOLUONG, 0)) AS BIEN_DONG
                FROM dbo.HOA_DON HD
                INNER JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                INNER JOIN dbo.SAN_PHAM SP ON SP.MASP = CT.MASP
                CROSS JOIN Bounds B
                WHERE HD.TRANGTHAI = 1
                  AND HD.NGAYLAP >= B.START_DATE
                  AND HD.NGAYLAP < SYSDATETIME()
                GROUP BY CT.MASP, HD.NGAYLAP

                UNION ALL

                SELECT
                    CTDT.MASP, PDT.NGAY_DOI_TRA AS NGAY,
                    N'RETURN_IN' AS LOAI,
                    SUM(COALESCE(CTDT.SOLUONG, 0)) AS SO_LUONG,
                    SUM(COALESCE(CTDT.SOLUONG, 0) * COALESCE(SP.GIANHAP, 0))
                        AS GIA_TRI_THUC_TE,
                    SUM(COALESCE(CTDT.SOLUONG, 0)) AS BIEN_DONG
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                INNER JOIN dbo.SAN_PHAM SP ON SP.MASP = CTDT.MASP
                CROSS JOIN Bounds B
                WHERE CTDT.HINH_THUC_XU_LY = 0
                  AND CTDT.TINHTRANGHANG = 1
                  AND PDT.NGAY_DOI_TRA >= B.START_DATE
                  AND PDT.NGAY_DOI_TRA < SYSDATETIME()
                GROUP BY CTDT.MASP, PDT.NGAY_DOI_TRA

                UNION ALL

                SELECT
                    CTDT.MASP, PDT.NGAY_DOI_TRA AS NGAY,
                    N'EXCHANGE_OUT' AS LOAI,
                    SUM(COALESCE(CTDT.SOLUONG, 0)) AS SO_LUONG,
                    SUM(COALESCE(CTDT.SOLUONG, 0) * COALESCE(SP.GIANHAP, 0))
                        AS GIA_TRI_THUC_TE,
                    -SUM(COALESCE(CTDT.SOLUONG, 0)) AS BIEN_DONG
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                INNER JOIN dbo.SAN_PHAM SP ON SP.MASP = CTDT.MASP
                CROSS JOIN Bounds B
                WHERE CTDT.HINH_THUC_XU_LY = 1
                  AND PDT.NGAY_DOI_TRA >= B.START_DATE
                  AND PDT.NGAY_DOI_TRA < SYSDATETIME()
                GROUP BY CTDT.MASP, PDT.NGAY_DOI_TRA
            ),
            MovementSummary AS (
                SELECT
                    M.MASP,
                    SUM(M.BIEN_DONG) AS BIEN_DONG_TU_DAU_KY,
                    SUM(CASE WHEN M.NGAY >= B.END_EXCLUSIVE
                        THEN M.BIEN_DONG ELSE 0 END) AS BIEN_DONG_SAU_KY,
                    SUM(CASE WHEN M.NGAY < B.END_EXCLUSIVE
                              AND M.LOAI = N'PURCHASE'
                        THEN M.SO_LUONG ELSE 0 END) AS SL_NHAP,
                    SUM(CASE WHEN M.NGAY < B.END_EXCLUSIVE
                              AND M.LOAI = N'PURCHASE'
                        THEN M.GIA_TRI_THUC_TE ELSE 0 END) AS GT_NHAP,
                    SUM(CASE WHEN M.NGAY < B.END_EXCLUSIVE
                              AND M.LOAI = N'RETURN_IN'
                        THEN M.SO_LUONG ELSE 0 END) AS SL_KHACH_TRA,
                    SUM(CASE WHEN M.NGAY < B.END_EXCLUSIVE
                              AND M.LOAI = N'RETURN_IN'
                        THEN M.GIA_TRI_THUC_TE ELSE 0 END) AS GT_KHACH_TRA,
                    SUM(CASE WHEN M.NGAY < B.END_EXCLUSIVE
                              AND M.LOAI = N'SALE'
                        THEN M.SO_LUONG ELSE 0 END) AS SL_BAN,
                    SUM(CASE WHEN M.NGAY < B.END_EXCLUSIVE
                              AND M.LOAI = N'EXCHANGE_OUT'
                        THEN M.SO_LUONG ELSE 0 END) AS SL_DOI
                FROM Movements M
                CROSS JOIN Bounds B
                GROUP BY M.MASP
            )
            SELECT
                SP.MASP,
                COALESCE(SP.TENSP, N''),
                COALESCE(SP.DVT, N''),
                COALESCE(SP.SLTON, 0) - COALESCE(M.BIEN_DONG_TU_DAU_KY, 0)
                    AS TON_DAU,
                (COALESCE(SP.SLTON, 0) - COALESCE(M.BIEN_DONG_TU_DAU_KY, 0))
                    * COALESCE(SP.GIANHAP, 0) AS GT_TON_DAU,
                COALESCE(M.SL_NHAP, 0) AS SL_NHAP,
                COALESCE(M.GT_NHAP, 0) AS GT_NHAP,
                COALESCE(M.SL_KHACH_TRA, 0) AS SL_KHACH_TRA,
                COALESCE(M.GT_KHACH_TRA, 0) AS GT_KHACH_TRA,
                COALESCE(M.SL_BAN, 0) AS SL_BAN,
                COALESCE(M.SL_DOI, 0) AS SL_DOI,
                COALESCE(M.SL_BAN, 0) + COALESCE(M.SL_DOI, 0) AS SL_XUAT,
                (COALESCE(M.SL_BAN, 0) + COALESCE(M.SL_DOI, 0))
                    * COALESCE(SP.GIANHAP, 0) AS GT_XUAT,
                COALESCE(SP.SLTON, 0) - COALESCE(M.BIEN_DONG_SAU_KY, 0)
                    AS TON_CUOI,
                (COALESCE(SP.SLTON, 0) - COALESCE(M.BIEN_DONG_SAU_KY, 0))
                    * COALESCE(SP.GIANHAP, 0) AS GT_TON_CUOI
            FROM dbo.SAN_PHAM SP
            LEFT JOIN MovementSummary M ON M.MASP = SP.MASP
            WHERE (COALESCE(SP.IS_DELETED, 0) = 0 OR M.MASP IS NOT NULL)
            {search_sql}
            ORDER BY SP.TENSP, SP.MASP
        """, (start_date, end_date, *search_params))

    def product_report_summary(self, start_date, end_date):
        """Tổng hợp toàn kỳ: số lượng, doanh thu và tổng thu sau hoàn."""
        row = self._fetch_one("""
            WITH InvoiceSubtotals AS (
                SELECT
                    HD.MAHD,
                    COALESCE(KM.TYLEGIAM, 0) AS TYLEGIAM,
                    COALESCE(
                        SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)),
                        0
                    ) AS TIEN_HANG
                FROM dbo.HOA_DON HD
                LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.TRANGTHAI = 1
                  AND HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY HD.MAHD, KM.TYLEGIAM
            ),
            Sales AS (
                SELECT COALESCE(SUM(
                    TIEN_HANG - ROUND(TIEN_HANG * TYLEGIAM / 100.0, 2)
                ), 0) AS DOANH_THU
                FROM InvoiceSubtotals
            ),
            ReturnQuantities AS (
                SELECT
                    COALESCE(SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0
                        THEN CTDT.SOLUONG ELSE 0 END), 0) AS SL_HOAN_TIEN,
                    COALESCE(SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 1
                        THEN CTDT.SOLUONG ELSE 0 END), 0) AS SL_DOI_HANG,
                    COALESCE(SUM(CASE WHEN CTDT.TINHTRANGHANG = 1
                        THEN CTDT.SOLUONG ELSE 0 END), 0) AS SL_NGUYEN_VEN,
                    COALESCE(SUM(CASE WHEN CTDT.TINHTRANGHANG = 0
                        THEN CTDT.SOLUONG ELSE 0 END), 0) AS SL_HANG_HONG
                FROM dbo.PHIEU_DOI_TRA PDT
                LEFT JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
            ),
            Refunds AS (
                SELECT COALESCE(SUM(PDT.TONG_TIEN_HOAN), 0) AS TIEN_HOAN
                FROM dbo.PHIEU_DOI_TRA PDT
                WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
            )
            SELECT
                (SELECT COALESCE(SUM(CT.SOLUONG), 0)
                 FROM dbo.HOA_DON HD
                 INNER JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                 WHERE HD.TRANGTHAI = 1
                   AND HD.NGAYLAP >= CONVERT(date, ?)
                   AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                ) AS SL_BAN,
                RQ.SL_HOAN_TIEN, RQ.SL_DOI_HANG,
                RQ.SL_NGUYEN_VEN, RQ.SL_HANG_HONG,
                S.DOANH_THU, R.TIEN_HOAN,
                S.DOANH_THU - R.TIEN_HOAN AS TONG_THU_SAU_HOAN
            FROM Sales S
            CROSS JOIN ReturnQuantities RQ
            CROSS JOIN Refunds R
        """, (
            start_date, end_date,
            start_date, end_date,
            start_date, end_date,
            start_date, end_date,
        ))
        row = row or (0, 0, 0, 0, 0, 0, 0, 0)
        return {
            "sold": row[0] or 0,
            "refund_quantity": row[1] or 0,
            "exchange_quantity": row[2] or 0,
            "intact_quantity": row[3] or 0,
            "damaged_quantity": row[4] or 0,
            "gross_revenue": row[5] or 0,
            "refund_amount": row[6] or 0,
            "net_revenue": row[7] or 0,
        }

    def shift_report(self, start_date, end_date):
        """Báo cáo ca, số hóa đơn và doanh số theo ca; tách biệt tiền kiểm kê."""
        return self._fetch_all("""
            SELECT
                C.MACA, CAST(C.NGAYLAM AS date), C.SOCA, C.TGMO, C.TGDONG,
                COUNT(DISTINCT L.MANV),
                COALESCE(S.SO_HD, 0), COALESCE(S.DOANH_THU, 0),
                C.TMDAUCA, C.TMCUOICA,
                CASE
                    WHEN C.TGMO IS NULL OR C.TGDONG IS NULL THEN N'Chưa cấu hình giờ'
                    WHEN SYSDATETIME() >= T.END_AT THEN N'Đã kết thúc'
                    WHEN SYSDATETIME() >= T.START_AT THEN N'Đang diễn ra'
                    ELSE N'Chưa bắt đầu'
                END
            FROM dbo.CA_LAM_VIEC C
            CROSS APPLY (
                SELECT
                    DATEADD(
                        SECOND,
                        DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGMO),
                        CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                    ) AS START_AT,
                    DATEADD(
                        SECOND,
                        DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGDONG),
                        DATEADD(
                            DAY, CASE WHEN C.TGDONG <= C.TGMO THEN 1 ELSE 0 END,
                            CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                        )
                    ) AS END_AT
            ) T
            OUTER APPLY (
                SELECT
                    COUNT(H.MAHD) AS SO_HD,
                    COALESCE(SUM(
                        H.TIEN_HANG - ROUND(H.TIEN_HANG * H.TYLEGIAM / 100.0, 2)
                    ), 0) AS DOANH_THU
                FROM (
                    SELECT
                        HD.MAHD,
                        COALESCE(SUM(COALESCE(CT.DONGIA, 0)
                            * COALESCE(CT.SOLUONG, 0)), 0) AS TIEN_HANG,
                        COALESCE(KM.TYLEGIAM, 0) AS TYLEGIAM
                    FROM dbo.HOA_DON HD
                    LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                    LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                    WHERE HD.MACA = C.MACA AND HD.TRANGTHAI = 1
                    GROUP BY HD.MAHD, KM.TYLEGIAM
                ) H
            ) S
            LEFT JOIN dbo.LAMCA L ON L.MACA = C.MACA
            WHERE C.NGAYLAM >= CONVERT(date, ?)
              AND C.NGAYLAM < DATEADD(day, 1, CONVERT(date, ?))
            GROUP BY C.MACA, C.NGAYLAM, C.SOCA, C.TGMO, C.TGDONG,
                     C.TMDAUCA, C.TMCUOICA, T.START_AT, T.END_AT,
                     S.SO_HD, S.DOANH_THU
            ORDER BY C.NGAYLAM DESC, C.SOCA, C.MACA
        """, (start_date, end_date))

    def employee_sales_report(self, start_date, end_date):
        """Bán hàng theo nhân viên lập và đổi trả theo nhân viên xử lý."""
        return self._fetch_all("""
            WITH InvoiceTotals AS (
                SELECT
                    HD.MAHD, HD.MANV,
                    COALESCE(KM.TYLEGIAM, 0) AS TYLEGIAM,
                    COALESCE(SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)), 0)
                        AS TIEN_HANG,
                    COALESCE(SUM(CT.SOLUONG), 0) AS SL_BAN
                FROM dbo.HOA_DON HD
                LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.TRANGTHAI = 1
                  AND HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY HD.MAHD, HD.MANV, KM.TYLEGIAM
            ),
            SalesByEmployee AS (
                SELECT
                    MANV,
                    COUNT(*) AS SO_HOA_DON,
                    SUM(SL_BAN) AS SL_BAN,
                    SUM(TIEN_HANG - ROUND(TIEN_HANG * TYLEGIAM / 100.0, 2))
                        AS DOANH_THU
                FROM InvoiceTotals
                GROUP BY MANV
            ),
            ReturnHeadersByEmployee AS (
                SELECT
                    PDT.MANV,
                    COUNT(*) AS SO_PHIEU_XU_LY,
                    SUM(COALESCE(PDT.TONG_TIEN_HOAN, 0)) AS TIEN_HOAN
                FROM dbo.PHIEU_DOI_TRA PDT
                WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY PDT.MANV
            ),
            ReturnLinesByEmployee AS (
                SELECT
                    PDT.MANV,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_HOAN_TIEN,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 1
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_DOI_HANG
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY PDT.MANV
            )
            SELECT
                COALESCE(NV.MANV, S.MANV, RH.MANV),
                COALESCE(NV.TENNV, N''),
                COALESCE(S.SO_HOA_DON, 0),
                COALESCE(S.SL_BAN, 0),
                COALESCE(S.DOANH_THU, 0),
                COALESCE(RH.SO_PHIEU_XU_LY, 0),
                COALESCE(RL.SL_HOAN_TIEN, 0),
                COALESCE(RL.SL_DOI_HANG, 0),
                COALESCE(RH.TIEN_HOAN, 0)
            FROM SalesByEmployee S
            FULL OUTER JOIN ReturnHeadersByEmployee RH ON RH.MANV = S.MANV
            LEFT JOIN ReturnLinesByEmployee RL
                ON RL.MANV = COALESCE(S.MANV, RH.MANV)
            LEFT JOIN dbo.NHAN_VIEN NV
                ON NV.MANV = COALESCE(S.MANV, RH.MANV)
            ORDER BY COALESCE(S.DOANH_THU, 0) DESC, NV.TENNV
        """, (
            start_date, end_date,
            start_date, end_date,
            start_date, end_date,
        ))


    # ---------------------------------------------------------
    # Báo cáo POS: dữ liệu chứng từ, không phân bổ tiền hoàn theo SKU
    # ---------------------------------------------------------
    def daily_sales_report(self, start_date, end_date, keyword=""):
        """Danh sách hóa đơn trong kỳ, kể cả hóa đơn đã hủy."""
        search_sql = ""
        params = [start_date, end_date]
        if keyword:
            search_sql = """
                AND (
                    HD.MAHD LIKE ? OR NV.TENNV LIKE ?
                    OR HD.MANV LIKE ? OR CONVERT(nvarchar(20), HD.MACA) LIKE ?
                )
            """
            params.extend([f"%{keyword}%"] * 4)
        return self._fetch_all(f"""
            SELECT
                HD.MAHD,
                N'Không lưu thông tin khách hàng' AS KHACH_HANG,
                COALESCE(NV.TENNV, HD.MANV, N''),
                HD.NGAYLAP,
                COALESCE(CONVERT(nvarchar(20), C.SOCA), N''),
                COALESCE(D.SO_LUONG, 0),
                COALESCE(D.TIEN_HANG, 0),
                ROUND(COALESCE(D.TIEN_HANG, 0) * COALESCE(KM.TYLEGIAM, 0) / 100.0, 2),
                CASE WHEN HD.TRANGTHAI = 1
                    THEN COALESCE(D.TIEN_HANG, 0)
                         - ROUND(COALESCE(D.TIEN_HANG, 0)
                           * COALESCE(KM.TYLEGIAM, 0) / 100.0, 2)
                    ELSE 0 END AS DOANH_SO,
                CASE WHEN HD.TRANGTHAI = 1
                    THEN COALESCE(HD.TIENKHACHDUA, 0) ELSE 0 END,
                CASE WHEN HD.TRANGTHAI = 1
                    THEN CASE WHEN COALESCE(HD.TIENKHACHDUA, 0)
                        > COALESCE(D.TIEN_HANG, 0)
                          - ROUND(COALESCE(D.TIEN_HANG, 0)
                            * COALESCE(KM.TYLEGIAM, 0) / 100.0, 2)
                        THEN COALESCE(HD.TIENKHACHDUA, 0)
                          - (COALESCE(D.TIEN_HANG, 0)
                            - ROUND(COALESCE(D.TIEN_HANG, 0)
                              * COALESCE(KM.TYLEGIAM, 0) / 100.0, 2))
                        ELSE 0 END
                    ELSE 0 END AS TIEN_THUA,
                CASE WHEN HD.TRANGTHAI = 1 THEN N'Hợp lệ' ELSE N'Đã hủy' END
            FROM dbo.HOA_DON HD
            LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = HD.MANV
            LEFT JOIN dbo.CA_LAM_VIEC C ON C.MACA = HD.MACA
            LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
            OUTER APPLY (
                SELECT
                    SUM(COALESCE(CT.SOLUONG, 0)) AS SO_LUONG,
                    SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0))
                        AS TIEN_HANG
                FROM dbo.CHI_TIET_HOA_DON CT
                WHERE CT.MAHD = HD.MAHD
            ) D
            WHERE HD.NGAYLAP >= CONVERT(date, ?)
              AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
              {search_sql}
            ORDER BY HD.NGAYLAP DESC, HD.MAHD DESC
        """, tuple(params))

    def sales_by_period_report(self, start_date, end_date, period="day"):
        """Bán hàng theo ngày/tháng/năm; trả hàng theo ngày lập phiếu."""
        sales_periods = {
            "day": "CAST(NGAYLAP AS date)",
            "month": "DATEFROMPARTS(YEAR(NGAYLAP), MONTH(NGAYLAP), 1)",
            "year": "DATEFROMPARTS(YEAR(NGAYLAP), 1, 1)",
        }
        return_periods = {
            "day": "CAST(NGAY_DOI_TRA AS date)",
            "month": "DATEFROMPARTS(YEAR(NGAY_DOI_TRA), MONTH(NGAY_DOI_TRA), 1)",
            "year": "DATEFROMPARTS(YEAR(NGAY_DOI_TRA), 1, 1)",
        }
        sales_key = sales_periods[period]
        return_key = return_periods[period]
        return self._fetch_all(f"""
            WITH InvoiceTotals AS (
                SELECT HD.MAHD, HD.NGAYLAP, HD.TRANGTHAI,
                    COALESCE(KM.TYLEGIAM, 0) AS TYLEGIAM,
                    COALESCE(SUM(COALESCE(CT.DONGIA, 0)
                        * COALESCE(CT.SOLUONG, 0)), 0) AS TIEN_HANG,
                    COALESCE(SUM(COALESCE(CT.SOLUONG, 0)), 0) AS SL_BAN
                FROM dbo.HOA_DON HD
                LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY HD.MAHD, HD.NGAYLAP, HD.TRANGTHAI, KM.TYLEGIAM
            ),
            Sales AS (
                SELECT {sales_key} AS KY,
                    COUNT(CASE WHEN TRANGTHAI = 1 THEN 1 END) AS SO_HOA_DON,
                    SUM(CASE WHEN TRANGTHAI = 1 THEN SL_BAN ELSE 0 END) AS SL_BAN,
                    SUM(CASE WHEN TRANGTHAI = 1 THEN TIEN_HANG ELSE 0 END) AS TIEN_HANG,
                    SUM(CASE WHEN TRANGTHAI = 1
                        THEN ROUND(TIEN_HANG * TYLEGIAM / 100.0, 2)
                        ELSE 0 END) AS TIEN_GIAM,
                    SUM(CASE WHEN TRANGTHAI = 1
                        THEN TIEN_HANG - ROUND(TIEN_HANG * TYLEGIAM / 100.0, 2)
                        ELSE 0 END) AS DOAN_SO
                FROM InvoiceTotals
                GROUP BY {sales_key}
            ),
            ReturnHeaders AS (
                SELECT {return_key} AS KY,
                    SUM(COALESCE(TONG_TIEN_HOAN, 0)) AS TIEN_HOAN
                FROM dbo.PHIEU_DOI_TRA
                WHERE NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY {return_key}
            ),
            ReturnLines AS (
                SELECT {return_key} AS KY,
                    SUM(COALESCE(CTDT.SOLUONG, 0)) AS SL_TRA
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY {return_key}
            )
            SELECT COALESCE(S.KY, H.KY, L.KY) AS KY,
                COALESCE(S.SO_HOA_DON, 0),
                COALESCE(S.SL_BAN, 0),
                COALESCE(S.TIEN_HANG, 0),
                COALESCE(S.TIEN_GIAM, 0),
                COALESCE(S.DOAN_SO, 0),
                COALESCE(L.SL_TRA, 0),
                COALESCE(H.TIEN_HOAN, 0),
                COALESCE(S.DOAN_SO, 0) - COALESCE(H.TIEN_HOAN, 0)
            FROM Sales S
            FULL OUTER JOIN ReturnHeaders H ON H.KY = S.KY
            FULL OUTER JOIN ReturnLines L ON L.KY = COALESCE(S.KY, H.KY)
            ORDER BY KY DESC
        """, (start_date, end_date, start_date, end_date, start_date, end_date))

    def sales_by_employee_report(self, start_date, end_date, keyword=""):
        """Tách doanh số người bán và tiền hoàn của người xử lý phiếu."""
        search_sql = ""
        params = [start_date, end_date, start_date, end_date, start_date, end_date]
        if keyword:
            search_sql = " AND (NV.MANV LIKE ? OR NV.TENNV LIKE ?)"
            params.extend((f"%{keyword}%", f"%{keyword}%"))
        return self._fetch_all(f"""
            WITH InvoiceTotals AS (
                SELECT HD.MAHD, HD.MANV,
                    COALESCE(KM.TYLEGIAM, 0) AS TYLEGIAM,
                    COALESCE(SUM(COALESCE(CT.DONGIA, 0)
                        * COALESCE(CT.SOLUONG, 0)), 0) AS TIEN_HANG,
                    COALESCE(SUM(COALESCE(CT.SOLUONG, 0)), 0) AS SL_BAN
                FROM dbo.HOA_DON HD
                LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.TRANGTHAI = 1
                  AND HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY HD.MAHD, HD.MANV, KM.TYLEGIAM
            ),
            Sales AS (
                SELECT MANV, COUNT(*) AS SO_HD, SUM(SL_BAN) AS SL_BAN,
                    SUM(TIEN_HANG) AS TIEN_HANG,
                    SUM(ROUND(TIEN_HANG * TYLEGIAM / 100.0, 2)) AS TIEN_GIAM,
                    SUM(TIEN_HANG - ROUND(TIEN_HANG * TYLEGIAM / 100.0, 2)) AS DOAN_SO
                FROM InvoiceTotals GROUP BY MANV
            ),
            ReturnHeaders AS (
                SELECT MANV, COUNT(*) AS SO_PHIEU,
                    SUM(COALESCE(TONG_TIEN_HOAN, 0)) AS TIEN_HOAN
                FROM dbo.PHIEU_DOI_TRA
                WHERE NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY MANV
            ),
            ReturnLines AS (
                SELECT PDT.MANV,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_HOAN,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 1
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_DOI
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY PDT.MANV
            )
            SELECT COALESCE(NV.MANV, S.MANV, H.MANV),
                COALESCE(NV.TENNV, N''),
                COALESCE(S.SO_HD, 0), COALESCE(S.SL_BAN, 0),
                COALESCE(S.TIEN_HANG, 0), COALESCE(S.TIEN_GIAM, 0),
                COALESCE(S.DOAN_SO, 0), COALESCE(H.SO_PHIEU, 0),
                COALESCE(L.SL_HOAN, 0), COALESCE(L.SL_DOI, 0),
                COALESCE(H.TIEN_HOAN, 0)
            FROM Sales S
            FULL OUTER JOIN ReturnHeaders H ON H.MANV = S.MANV
            LEFT JOIN ReturnLines L ON L.MANV = COALESCE(S.MANV, H.MANV)
            LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = COALESCE(S.MANV, H.MANV)
            WHERE 1 = 1 {search_sql}
            ORDER BY COALESCE(S.DOAN_SO, 0) DESC, NV.TENNV
        """, tuple(params))

    def product_movement_report(self, start_date, end_date, keyword=""):
        """Số lượng nhập, bán, hoàn, đổi theo sản phẩm trong kỳ."""
        search_sql = ""
        params = [start_date, end_date, start_date, end_date, start_date, end_date]
        if keyword:
            search_sql = " AND (SP.MASP LIKE ? OR SP.TENSP LIKE ?)"
            params.extend((f"%{keyword}%", f"%{keyword}%"))
        return self._fetch_all(f"""
            WITH Sales AS (
                SELECT CT.MASP, COUNT(DISTINCT HD.MAHD) AS SO_HD,
                    SUM(COALESCE(CT.SOLUONG, 0)) AS SL_BAN
                FROM dbo.HOA_DON HD
                INNER JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                WHERE HD.TRANGTHAI = 1
                  AND HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY CT.MASP
            ),
            Purchases AS (
                SELECT CT.MASP, SUM(COALESCE(CT.SOLUONG, 0)) AS SL_NHAP
                FROM dbo.PHIEU_NHAP PN
                INNER JOIN dbo.CHI_TIET_PHIEU_NHAP CT ON CT.MAPN = PN.MAPN
                WHERE ISNULL(PN.TRANGTHAI, 1) = 1
                  AND PN.NGAYNHAP >= CONVERT(date, ?)
                  AND PN.NGAYNHAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY CT.MASP
            ),
            Returns AS (
                SELECT CTDT.MASP,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_HOAN,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 1
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_DOI,
                    SUM(CASE WHEN CTDT.TINHTRANGHANG = 1
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_NGUYEN,
                    SUM(CASE WHEN CTDT.TINHTRANGHANG = 0
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_HONG
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY CTDT.MASP
            )
            SELECT SP.MASP, COALESCE(SP.TENSP, N''),
                COALESCE(S.SO_HD, 0), COALESCE(P.SL_NHAP, 0),
                COALESCE(S.SL_BAN, 0), COALESCE(R.SL_HOAN, 0),
                COALESCE(R.SL_DOI, 0), COALESCE(R.SL_NGUYEN, 0),
                COALESCE(R.SL_HONG, 0), COALESCE(SP.SLTON, 0)
            FROM dbo.SAN_PHAM SP
            LEFT JOIN Sales S ON S.MASP = SP.MASP
            LEFT JOIN Purchases P ON P.MASP = SP.MASP
            LEFT JOIN Returns R ON R.MASP = SP.MASP
            WHERE (COALESCE(SP.IS_DELETED, 0) = 0
                   OR S.MASP IS NOT NULL OR P.MASP IS NOT NULL OR R.MASP IS NOT NULL)
              {search_sql}
            ORDER BY COALESCE(S.SL_BAN, 0) DESC, SP.TENSP
        """, tuple(params))

    def import_detail_report(self, start_date, end_date, keyword=""):
        """Chi tiết từng dòng hàng trên phiếu nhập còn hiệu lực."""
        search_sql = ""
        params = [start_date, end_date]
        if keyword:
            search_sql = """
                AND (
                    PN.MAPN LIKE ? OR CT.MASP LIKE ? OR SP.TENSP LIKE ?
                    OR NCC.TENNCC LIKE ? OR NV.TENNV LIKE ?
                )
            """
            params.extend([f"%{keyword}%"] * 5)
        return self._fetch_all(f"""
            SELECT PN.MAPN, PN.NGAYNHAP, COALESCE(PN.LOAIPHIEUNHAP, N''),
                COALESCE(NCC.TENNCC, PN.MANCC, N''),
                COALESCE(PN.SHDNCC, N''), COALESCE(NV.TENNV, PN.MANV, N''),
                CT.MASP, COALESCE(SP.TENSP, N''),
                COALESCE(CT.SOLUONG, 0), COALESCE(CT.DONGIA, 0),
                COALESCE(CT.SOLUONG, 0) * COALESCE(CT.DONGIA, 0)
            FROM dbo.PHIEU_NHAP PN
            INNER JOIN dbo.CHI_TIET_PHIEU_NHAP CT ON CT.MAPN = PN.MAPN
            LEFT JOIN dbo.SAN_PHAM SP ON SP.MASP = CT.MASP
            LEFT JOIN dbo.NHA_CUNG_CAP NCC ON NCC.MANCC = PN.MANCC
            LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = PN.MANV
            WHERE ISNULL(PN.TRANGTHAI, 1) = 1
              AND PN.NGAYNHAP >= CONVERT(date, ?)
              AND PN.NGAYNHAP < DATEADD(day, 1, CONVERT(date, ?))
              {search_sql}
            ORDER BY PN.NGAYNHAP DESC, PN.MAPN, SP.TENSP
        """, tuple(params))

    def import_supplier_report(self, start_date, end_date, keyword=""):
        """Tổng hợp nhập hàng theo nhà cung cấp."""
        search_sql = ""
        params = [start_date, end_date]
        if keyword:
            search_sql = " AND (NCC.MANCC LIKE ? OR NCC.TENNCC LIKE ?)"
            params.extend((f"%{keyword}%", f"%{keyword}%"))
        return self._fetch_all(f"""
            SELECT PN.MANCC, COALESCE(NCC.TENNCC, PN.MANCC, N''),
                COALESCE(NCC.SDT, N''), COUNT(DISTINCT PN.MAPN),
                COALESCE(SUM(D.SL_NHAP), 0), COALESCE(SUM(PN.TONGTRIGIA), 0)
            FROM dbo.PHIEU_NHAP PN
            LEFT JOIN dbo.NHA_CUNG_CAP NCC ON NCC.MANCC = PN.MANCC
            OUTER APPLY (
                SELECT SUM(COALESCE(CT.SOLUONG, 0)) AS SL_NHAP
                FROM dbo.CHI_TIET_PHIEU_NHAP CT WHERE CT.MAPN = PN.MAPN
            ) D
            WHERE ISNULL(PN.TRANGTHAI, 1) = 1
              AND PN.NGAYNHAP >= CONVERT(date, ?)
              AND PN.NGAYNHAP < DATEADD(day, 1, CONVERT(date, ?))
              {search_sql}
            GROUP BY PN.MANCC, NCC.TENNCC, NCC.SDT
            ORDER BY SUM(PN.TONGTRIGIA) DESC, NCC.TENNCC
        """, tuple(params))

    def return_detail_report(self, start_date, end_date, keyword=""):
        """Danh sách phiếu đổi trả, tổng tiền giữ ở cấp phiếu."""
        search_sql = ""
        params = [start_date, end_date]
        if keyword:
            search_sql = """
                AND (PDT.MAPDT LIKE ? OR PDT.MAHD LIKE ?
                     OR PDT.MANV LIKE ? OR NV.TENNV LIKE ?)
            """
            params.extend([f"%{keyword}%"] * 4)
        return self._fetch_all(f"""
            SELECT PDT.MAPDT, PDT.NGAY_DOI_TRA, COALESCE(PDT.MAHD, N''),
                COALESCE(NV.TENNV, PDT.MANV, N''), COALESCE(PDT.LY_DO, N''),
                COALESCE(D.SO_DONG, 0), COALESCE(D.SL_HOAN, 0),
                COALESCE(D.SL_DOI, 0), COALESCE(D.SL_NGUYEN, 0),
                COALESCE(D.SL_HONG, 0), COALESCE(PDT.TONG_TIEN_HOAN, 0)
            FROM dbo.PHIEU_DOI_TRA PDT
            LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = PDT.MANV
            OUTER APPLY (
                SELECT COUNT(*) AS SO_DONG,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_HOAN,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 1
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_DOI,
                    SUM(CASE WHEN CTDT.TINHTRANGHANG = 1
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_NGUYEN,
                    SUM(CASE WHEN CTDT.TINHTRANGHANG = 0
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_HONG
                FROM dbo.CHI_TIET_DOI_TRA CTDT WHERE CTDT.MAPDT = PDT.MAPDT
            ) D
            WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
              AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
              {search_sql}
            ORDER BY PDT.NGAY_DOI_TRA DESC, PDT.MAPDT DESC
        """, tuple(params))

    def promotion_report(self, start_date, end_date, keyword=""):
        """Hiệu quả khuyến mãi; tiền hoàn được gắn theo hóa đơn gốc."""
        search_sql = ""
        params = [start_date, end_date]
        if keyword:
            search_sql = " AND (KM.MAKM LIKE ? OR KM.TENKM LIKE ?)"
            params.extend((f"%{keyword}%", f"%{keyword}%"))
        return self._fetch_all(f"""
            WITH InvoiceTotals AS (
                SELECT HD.MAHD, HD.MAKM, HD.NGAYLAP,
                    COALESCE(KM.TENKM, N'Không áp dụng') AS TENKM,
                    COALESCE(KM.TYLEGIAM, 0) AS TYLEGIAM,
                    COALESCE(SUM(COALESCE(CT.DONGIA, 0)
                        * COALESCE(CT.SOLUONG, 0)), 0) AS TIEN_HANG
                FROM dbo.HOA_DON HD
                LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.TRANGTHAI = 1
                  AND HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY HD.MAHD, HD.MAKM, HD.NGAYLAP, KM.TENKM, KM.TYLEGIAM
            ),
            Sales AS (
                SELECT MAKM, TENKM, TYLEGIAM, COUNT(*) AS SO_HD,
                    SUM(TIEN_HANG) AS TIEN_HANG,
                    SUM(ROUND(TIEN_HANG * TYLEGIAM / 100.0, 2)) AS TIEN_GIAM,
                    SUM(TIEN_HANG - ROUND(TIEN_HANG * TYLEGIAM / 100.0, 2))
                        AS DOAN_SO
                FROM InvoiceTotals GROUP BY MAKM, TENKM, TYLEGIAM
            ),
            Refunds AS (
                SELECT I.MAKM, SUM(COALESCE(PDT.TONG_TIEN_HOAN, 0)) AS TIEN_HOAN
                FROM InvoiceTotals I
                INNER JOIN dbo.PHIEU_DOI_TRA PDT ON PDT.MAHD = I.MAHD
                GROUP BY I.MAKM
            )
            SELECT S.MAKM, S.TENKM, S.TYLEGIAM, S.SO_HD, S.TIEN_HANG,
                S.TIEN_GIAM, S.DOAN_SO, COALESCE(R.TIEN_HOAN, 0),
                S.DOAN_SO - COALESCE(R.TIEN_HOAN, 0)
            FROM Sales S
            LEFT JOIN Refunds R ON ISNULL(R.MAKM, '') = ISNULL(S.MAKM, '')
            WHERE 1 = 1 {search_sql}
            ORDER BY S.DOAN_SO DESC, S.TENKM
        """, tuple(params))

    def current_inventory_report(self, threshold=5, status="all", keyword=""):
        """Ảnh chụp tồn kho hiện tại; giá trị kho dùng giá nhập hiện lưu."""
        status_sql = ""
        params = []
        if status == "low":
            status_sql = " AND COALESCE(SP.SLTON, 0) > 0 AND SP.SLTON <= ?"
            params.append(threshold)
        elif status == "out":
            status_sql = " AND COALESCE(SP.SLTON, 0) <= 0"
        search_sql = ""
        if keyword:
            search_sql = " AND (SP.MASP LIKE ? OR SP.TENSP LIKE ?)"
            params.extend((f"%{keyword}%", f"%{keyword}%"))
        return self._fetch_all(f"""
            SELECT SP.MASP, COALESCE(SP.TENSP, N''), COALESCE(SP.DVT, N''),
                COALESCE(SP.SLTON, 0), COALESCE(SP.GIANHAP, 0),
                COALESCE(SP.GIABAN, 0),
                COALESCE(SP.SLTON, 0) * COALESCE(SP.GIANHAP, 0),
                CASE WHEN COALESCE(SP.SLTON, 0) <= 0 THEN N'Hết hàng'
                     WHEN COALESCE(SP.SLTON, 0) <= ? THEN N'Sắp hết'
                     ELSE N'Còn hàng' END
            FROM dbo.SAN_PHAM SP
            WHERE COALESCE(SP.IS_DELETED, 0) = 0
              {status_sql}
              {search_sql}
            ORDER BY COALESCE(SP.SLTON, 0), SP.TENSP
        """, (threshold, *params))

    def stock_movement_report(self, start_date, end_date, keyword=""):
        """Nhập–xuất–tồn tái dựng từ chứng từ còn hiệu lực và SLTON hiện tại.

        Tồn đầu/cuối được đối chiếu ngược từ SLTON hiện tại và các biến động
        đã lưu từ ngày bắt đầu đến hiện tại. Giá trị tồn/xuất/trả là ước tính
        theo GIANHAP hiện tại; trị giá nhập NCC lấy đơn giá chứng từ thực tế.
        """
        search_sql = ""
        search_params = []
        if keyword:
            search_sql = " AND (SP.MASP LIKE ? OR SP.TENSP LIKE ?)"
            search_params = [f"%{keyword}%", f"%{keyword}%"]
        return self._fetch_all(f"""
            WITH Bounds AS (
                SELECT CONVERT(date, ?) AS START_DATE,
                       DATEADD(day, 1, CONVERT(date, ?)) AS END_EXCLUSIVE
            ),
            Movements AS (
                SELECT CT.MASP, PN.NGAYNHAP AS NGAY,
                    N'PURCHASE' AS LOAI,
                    SUM(COALESCE(CT.SOLUONG, 0)) AS SL_NHAP,
                    CAST(0 AS BIGINT) AS SL_XUAT,
                    SUM(COALESCE(CT.SOLUONG, 0) * COALESCE(CT.DONGIA, 0))
                        AS GT_NHAP_THUC_TE,
                    CAST(0 AS DECIMAL(18, 2)) AS GT_XUAT_UOC_TINH
                FROM dbo.PHIEU_NHAP PN
                INNER JOIN dbo.CHI_TIET_PHIEU_NHAP CT ON CT.MAPN = PN.MAPN
                CROSS JOIN Bounds B
                WHERE ISNULL(PN.TRANGTHAI, 1) = 1
                  AND PN.NGAYNHAP >= B.START_DATE
                GROUP BY CT.MASP, PN.NGAYNHAP

                UNION ALL

                SELECT CT.MASP, HD.NGAYLAP, N'SALE',
                    CAST(0 AS BIGINT), SUM(COALESCE(CT.SOLUONG, 0)),
                    CAST(0 AS DECIMAL(18, 2)),
                    SUM(COALESCE(CT.SOLUONG, 0) * COALESCE(SP.GIANHAP, 0))
                FROM dbo.HOA_DON HD
                INNER JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                INNER JOIN dbo.SAN_PHAM SP ON SP.MASP = CT.MASP
                CROSS JOIN Bounds B
                WHERE HD.TRANGTHAI = 1 AND HD.NGAYLAP >= B.START_DATE
                GROUP BY CT.MASP, HD.NGAYLAP

                UNION ALL

                SELECT CTDT.MASP, PDT.NGAY_DOI_TRA, N'RETURN_IN',
                    SUM(COALESCE(CTDT.SOLUONG, 0)), CAST(0 AS BIGINT),
                    CAST(0 AS DECIMAL(18, 2)),
                    CAST(0 AS DECIMAL(18, 2))
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                CROSS JOIN Bounds B
                WHERE CTDT.HINH_THUC_XU_LY = 0
                  AND CTDT.TINHTRANGHANG = 1
                  AND PDT.NGAY_DOI_TRA >= B.START_DATE
                GROUP BY CTDT.MASP, PDT.NGAY_DOI_TRA

                UNION ALL

                SELECT CTDT.MASP, PDT.NGAY_DOI_TRA, N'EXCHANGE_OUT',
                    CAST(0 AS BIGINT), SUM(COALESCE(CTDT.SOLUONG, 0)),
                    CAST(0 AS DECIMAL(18, 2)),
                    SUM(COALESCE(CTDT.SOLUONG, 0) * COALESCE(SP.GIANHAP, 0))
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                INNER JOIN dbo.SAN_PHAM SP ON SP.MASP = CTDT.MASP
                CROSS JOIN Bounds B
                WHERE CTDT.HINH_THUC_XU_LY = 1
                  AND PDT.NGAY_DOI_TRA >= B.START_DATE
                GROUP BY CTDT.MASP, PDT.NGAY_DOI_TRA
            ),
            MovementSummary AS (
                SELECT M.MASP,
                    SUM(M.SL_NHAP - M.SL_XUAT) AS NET_FROM_START,
                    SUM(CASE WHEN M.NGAY >= B.END_EXCLUSIVE
                        THEN M.SL_NHAP - M.SL_XUAT ELSE 0 END) AS NET_AFTER_END,
                    SUM(CASE WHEN M.NGAY >= B.START_DATE
                              AND M.NGAY < B.END_EXCLUSIVE
                              AND M.LOAI = N'PURCHASE'
                        THEN M.SL_NHAP ELSE 0 END) AS SL_NHAP_NCC,
                    SUM(CASE WHEN M.NGAY >= B.START_DATE
                              AND M.NGAY < B.END_EXCLUSIVE
                              AND M.LOAI = N'PURCHASE'
                        THEN M.GT_NHAP_THUC_TE ELSE 0 END) AS GT_NHAP_NCC,
                    SUM(CASE WHEN M.NGAY >= B.START_DATE
                              AND M.NGAY < B.END_EXCLUSIVE
                              AND M.LOAI = N'RETURN_IN'
                        THEN M.SL_NHAP ELSE 0 END) AS SL_KHACH_TRA,
                    SUM(CASE WHEN M.NGAY >= B.START_DATE
                              AND M.NGAY < B.END_EXCLUSIVE
                              AND M.LOAI = N'SALE'
                        THEN M.SL_XUAT ELSE 0 END) AS SL_BAN,
                    SUM(CASE WHEN M.NGAY >= B.START_DATE
                              AND M.NGAY < B.END_EXCLUSIVE
                              AND M.LOAI = N'SALE'
                        THEN M.GT_XUAT_UOC_TINH ELSE 0 END) AS GT_BAN_UOC_TINH,
                    SUM(CASE WHEN M.NGAY >= B.START_DATE
                              AND M.NGAY < B.END_EXCLUSIVE
                              AND M.LOAI = N'EXCHANGE_OUT'
                        THEN M.SL_XUAT ELSE 0 END) AS SL_DOI_HANG,
                    SUM(CASE WHEN M.NGAY >= B.START_DATE
                              AND M.NGAY < B.END_EXCLUSIVE
                              AND M.LOAI = N'EXCHANGE_OUT'
                        THEN M.GT_XUAT_UOC_TINH ELSE 0 END) AS GT_DOI_UOC_TINH
                FROM Movements M CROSS JOIN Bounds B
                GROUP BY M.MASP
            )
            SELECT SP.MASP, COALESCE(SP.TENSP, N''), COALESCE(SP.DVT, N''),
                COALESCE(SP.SLTON, 0) - COALESCE(M.NET_FROM_START, 0)
                    AS TON_DAU,
                (COALESCE(SP.SLTON, 0) - COALESCE(M.NET_FROM_START, 0))
                    * COALESCE(SP.GIANHAP, 0) AS GT_TON_DAU_UOC_TINH,
                COALESCE(M.SL_NHAP_NCC, 0), COALESCE(M.GT_NHAP_NCC, 0),
                COALESCE(M.SL_KHACH_TRA, 0),
                COALESCE(M.SL_KHACH_TRA, 0) * COALESCE(SP.GIANHAP, 0),
                COALESCE(M.SL_BAN, 0), COALESCE(M.GT_BAN_UOC_TINH, 0),
                COALESCE(M.SL_DOI_HANG, 0), COALESCE(M.GT_DOI_UOC_TINH, 0),
                COALESCE(SP.SLTON, 0) - COALESCE(M.NET_AFTER_END, 0),
                (COALESCE(SP.SLTON, 0) - COALESCE(M.NET_AFTER_END, 0))
                    * COALESCE(SP.GIANHAP, 0)
            FROM dbo.SAN_PHAM SP
            LEFT JOIN MovementSummary M ON M.MASP = SP.MASP
            WHERE COALESCE(SP.IS_DELETED, 0) = 0 OR M.MASP IS NOT NULL
              {search_sql}
            ORDER BY SP.TENSP, SP.MASP
        """, (start_date, end_date, *search_params))

    def stock_card_report(self, start_date, end_date, keyword=""):
        """Thẻ kho theo chứng từ với tồn chạy được tái dựng từ SLTON hiện tại."""
        search_sql = ""
        search_params = []
        if keyword:
            search_sql = " AND (SP.MASP LIKE ? OR SP.TENSP LIKE ?)"
            search_params = [f"%{keyword}%", f"%{keyword}%"]
        return self._fetch_all(f"""
            WITH Bounds AS (
                SELECT CONVERT(date, ?) AS START_DATE,
                       DATEADD(day, 1, CONVERT(date, ?)) AS END_EXCLUSIVE
            ),
            Movements AS (
                SELECT CT.MASP, PN.NGAYNHAP AS NGAY, PN.MAPN AS CHUNG_TU,
                    N'Nhập nhà cung cấp' AS LOAI,
                    SUM(COALESCE(CT.SOLUONG, 0)) AS SL_NHAP,
                    CAST(0 AS BIGINT) AS SL_XUAT
                FROM dbo.PHIEU_NHAP PN
                INNER JOIN dbo.CHI_TIET_PHIEU_NHAP CT ON CT.MAPN = PN.MAPN
                WHERE ISNULL(PN.TRANGTHAI, 1) = 1
                GROUP BY CT.MASP, PN.NGAYNHAP, PN.MAPN

                UNION ALL
                SELECT CT.MASP, HD.NGAYLAP, HD.MAHD, N'Bán hàng',
                    CAST(0 AS BIGINT), SUM(COALESCE(CT.SOLUONG, 0))
                FROM dbo.HOA_DON HD
                INNER JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                WHERE HD.TRANGTHAI = 1
                GROUP BY CT.MASP, HD.NGAYLAP, HD.MAHD

                UNION ALL
                SELECT CTDT.MASP, PDT.NGAY_DOI_TRA, PDT.MAPDT, N'Khách trả hàng nguyên vẹn',
                    SUM(COALESCE(CTDT.SOLUONG, 0)), CAST(0 AS BIGINT)
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                WHERE CTDT.HINH_THUC_XU_LY = 0 AND CTDT.TINHTRANGHANG = 1
                GROUP BY CTDT.MASP, PDT.NGAY_DOI_TRA, PDT.MAPDT

                UNION ALL
                SELECT CTDT.MASP, PDT.NGAY_DOI_TRA, PDT.MAPDT, N'Xuất hàng đổi',
                    CAST(0 AS BIGINT), SUM(COALESCE(CTDT.SOLUONG, 0))
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                WHERE CTDT.HINH_THUC_XU_LY = 1
                GROUP BY CTDT.MASP, PDT.NGAY_DOI_TRA, PDT.MAPDT
            ),
            Opening AS (
                SELECT SP.MASP,
                    COALESCE(SP.SLTON, 0) - COALESCE(SUM(
                        CASE WHEN M.NGAY >= B.START_DATE
                            THEN M.SL_NHAP - M.SL_XUAT ELSE 0 END
                    ), 0) AS TON_DAU
                FROM dbo.SAN_PHAM SP
                CROSS JOIN Bounds B
                LEFT JOIN Movements M ON M.MASP = SP.MASP
                GROUP BY SP.MASP, SP.SLTON
            ),
            PeriodMovements AS (
                SELECT M.MASP, M.NGAY, M.CHUNG_TU, M.LOAI, M.SL_NHAP, M.SL_XUAT
                FROM Movements M CROSS JOIN Bounds B
                WHERE M.NGAY >= B.START_DATE AND M.NGAY < B.END_EXCLUSIVE
            )
            SELECT P.NGAY, P.LOAI, P.CHUNG_TU, P.MASP,
                COALESCE(SP.TENSP, N''), P.SL_NHAP, P.SL_XUAT,
                O.TON_DAU + SUM(P.SL_NHAP - P.SL_XUAT) OVER (
                    PARTITION BY P.MASP ORDER BY P.NGAY, P.CHUNG_TU, P.LOAI
                    ROWS UNBOUNDED PRECEDING
                ) AS TON_SAU_GIAO_DICH
            FROM PeriodMovements P
            INNER JOIN Opening O ON O.MASP = P.MASP
            LEFT JOIN dbo.SAN_PHAM SP ON SP.MASP = P.MASP
            WHERE 1 = 1 {search_sql}
            ORDER BY P.MASP, P.NGAY, P.CHUNG_TU, P.LOAI
        """, (start_date, end_date, *search_params))
