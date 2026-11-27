"""Repository truy vấn dữ liệu cho các báo cáo nhà sách.

Chỉ chứa SQL/read-model. Các trang PySide6 và API Web không tự thực thi SQL.
"""

from core.sql_support import resolve_connection


class BaoCaoRepository:
    def __init__(self, connection_source):
        self.connection_source = connection_source

    def fetch_all(self, sql, params=()):
        conn = resolve_connection(self.connection_source)
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()

    def fetch_one(self, sql, params=()):
        rows = self.fetch_all(sql, params)
        return rows[0] if rows else None

    def overview_summary(self, start_date, end_date):
        return self.fetch_one("""
            SELECT
                COUNT(DISTINCT CASE WHEN HD.TRANGTHAI = 1 THEN HD.MAHD END),
                COUNT(DISTINCT CASE WHEN HD.TRANGTHAI = 0 THEN HD.MAHD END),
                COALESCE(SUM(CASE WHEN HD.TRANGTHAI = 1 THEN
                    COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)
                    * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0)
                    ELSE 0 END), 0)
            FROM dbo.HOA_DON HD
            LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
            LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
            WHERE HD.NGAYLAP >= CONVERT(date, ?)
              AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
        """, (start_date, end_date))

    def overview_refunds(self, start_date, end_date):
        return self.fetch_one("""
            SELECT COALESCE(SUM(TONG_TIEN_HOAN), 0)
            FROM dbo.PHIEU_DOI_TRA
            WHERE NGAY_DOI_TRA >= CONVERT(date, ?)
              AND NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
        """, (start_date, end_date))

    def overview_imports(self, start_date, end_date):
        return self.fetch_one("""
            SELECT COALESCE(SUM(TONGTRIGIA), 0)
            FROM dbo.PHIEU_NHAP
            WHERE NGAYNHAP >= CONVERT(date, ?)
              AND NGAYNHAP < DATEADD(day, 1, CONVERT(date, ?))
              AND ISNULL(TRANGTHAI, 1) = 1
        """, (start_date, end_date))

    def overview_trend(self, start_date, end_date):
        return self.fetch_all("""
            WITH SalesByDay AS (
                SELECT
                    CAST(HD.NGAYLAP AS date) AS NGAY,
                    COUNT(DISTINCT HD.MAHD) AS SO_HD,
                    COALESCE(SUM(CT.SOLUONG), 0) AS SO_LUONG,
                    COALESCE(SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)
                        * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0)), 0) AS DOANH_THU
                FROM dbo.HOA_DON HD
                INNER JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.TRANGTHAI = 1
                  AND HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY CAST(HD.NGAYLAP AS date)
            ),
            RefundByDay AS (
                SELECT
                    CAST(PDT.NGAY_DOI_TRA AS date) AS NGAY,
                    COALESCE(SUM(PDT.TONG_TIEN_HOAN), 0) AS TIEN_HOAN
                FROM dbo.PHIEU_DOI_TRA PDT
                WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY CAST(PDT.NGAY_DOI_TRA AS date)
            )
            SELECT
                COALESCE(S.NGAY, R.NGAY) AS NGAY,
                COALESCE(S.SO_HD, 0) AS SO_HD,
                COALESCE(S.SO_LUONG, 0) AS SO_LUONG,
                COALESCE(S.DOANH_THU, 0) AS DOANH_THU,
                COALESCE(R.TIEN_HOAN, 0) AS TIEN_HOAN,
                COALESCE(S.DOANH_THU, 0) - COALESCE(R.TIEN_HOAN, 0)
                    AS DOANH_THU_SAU_HOAN
            FROM SalesByDay S
            FULL OUTER JOIN RefundByDay R ON R.NGAY = S.NGAY
            ORDER BY NGAY
        """, (start_date, end_date, start_date, end_date))

    def overview_top_products(self, start_date, end_date):
        return self.fetch_all("""
            SELECT TOP 10
                SP.MASP,
                COALESCE(SP.TENSP, N''),
                SUM(COALESCE(CT.SOLUONG, 0)) AS SO_LUONG,
                SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)
                    * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0)) AS DOANH_THU
            FROM dbo.HOA_DON HD
            INNER JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
            INNER JOIN dbo.SAN_PHAM SP ON SP.MASP = CT.MASP
            LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
            WHERE HD.TRANGTHAI = 1
              AND HD.NGAYLAP >= CONVERT(date, ?)
              AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
            GROUP BY SP.MASP, SP.TENSP
            ORDER BY SUM(COALESCE(CT.SOLUONG, 0)) DESC, DOANH_THU DESC
        """, (start_date, end_date))

    def revenue_by_period(self, start_date, end_date, period):
        sales_periods = {
            "day": "CAST(HD.NGAYLAP AS date)",
            "month": "DATEFROMPARTS(YEAR(HD.NGAYLAP), MONTH(HD.NGAYLAP), 1)",
            "year": "DATEFROMPARTS(YEAR(HD.NGAYLAP), 1, 1)",
        }
        refund_periods = {
            "day": "CAST(PDT.NGAY_DOI_TRA AS date)",
            "month": "DATEFROMPARTS(YEAR(PDT.NGAY_DOI_TRA), MONTH(PDT.NGAY_DOI_TRA), 1)",
            "year": "DATEFROMPARTS(YEAR(PDT.NGAY_DOI_TRA), 1, 1)",
        }
        sales_period = sales_periods[period]
        refund_period = refund_periods[period]
        sql = f"""
            WITH Sales AS (
                SELECT
                    {sales_period} AS KY,
                    COUNT(DISTINCT HD.MAHD) AS SO_HD,
                    SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)) AS TIEN_HANG,
                    SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)
                        * COALESCE(KM.TYLEGIAM, 0) / 100.0) AS TIEN_GIAM,
                    SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)
                        * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0)) AS DOANH_THU
                FROM dbo.HOA_DON HD
                LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.TRANGTHAI = 1
                  AND HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY {sales_period}
            ),
            Refunds AS (
                SELECT
                    {refund_period} AS KY,
                    SUM(COALESCE(PDT.TONG_TIEN_HOAN, 0)) AS TIEN_HOAN
                FROM dbo.PHIEU_DOI_TRA PDT
                WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY {refund_period}
            )
            SELECT
                COALESCE(S.KY, R.KY) AS KY,
                COALESCE(S.SO_HD, 0),
                COALESCE(S.TIEN_HANG, 0),
                COALESCE(S.TIEN_GIAM, 0),
                COALESCE(S.DOANH_THU, 0),
                COALESCE(R.TIEN_HOAN, 0),
                COALESCE(S.DOANH_THU, 0) - COALESCE(R.TIEN_HOAN, 0)
                    AS DOANH_THU_SAU_HOAN
            FROM Sales S
            FULL OUTER JOIN Refunds R ON R.KY = S.KY
            ORDER BY KY DESC
        """
        return self.fetch_all(sql, (start_date, end_date, start_date, end_date))

    def promotion_effectiveness(self, start_date, end_date):
        return self.fetch_all("""
            WITH PromotionSales AS (
                SELECT
                    HD.MAKM,
                    COALESCE(KM.TENKM, N'Không áp dụng khuyến mãi') AS TENKM,
                    COALESCE(KM.TYLEGIAM, 0) AS TYLEGIAM,
                    COUNT(DISTINCT HD.MAHD) AS SO_HD,
                    COALESCE(SUM(CT.DONGIA * CT.SOLUONG), 0) AS TIEN_HANG,
                    COALESCE(SUM(CT.DONGIA * CT.SOLUONG
                        * COALESCE(KM.TYLEGIAM, 0) / 100.0), 0) AS TIEN_GIAM,
                    COALESCE(SUM(CT.DONGIA * CT.SOLUONG
                        * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0)), 0) AS DOANH_THU
                FROM dbo.HOA_DON HD
                LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.TRANGTHAI = 1
                  AND HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY HD.MAKM, KM.TENKM, KM.TYLEGIAM
            ),
            PromotionRefunds AS (
                SELECT
                    HD.MAKM,
                    COALESCE(SUM(PDT.TONG_TIEN_HOAN), 0) AS TIEN_HOAN
                FROM dbo.HOA_DON HD
                INNER JOIN dbo.PHIEU_DOI_TRA PDT ON PDT.MAHD = HD.MAHD
                WHERE HD.TRANGTHAI = 1
                  AND HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY HD.MAKM
            )
            SELECT
                S.MAKM, S.TENKM, S.TYLEGIAM, S.SO_HD, S.TIEN_HANG,
                S.TIEN_GIAM, S.DOANH_THU, COALESCE(R.TIEN_HOAN, 0),
                S.DOANH_THU - COALESCE(R.TIEN_HOAN, 0)
            FROM PromotionSales S
            LEFT JOIN PromotionRefunds R
                ON ISNULL(R.MAKM, '') = ISNULL(S.MAKM, '')
            ORDER BY S.DOANH_THU DESC, S.TENKM
        """, (start_date, end_date, start_date, end_date))

    def invoice_report(self, start_date, end_date):
        return self.fetch_all("""
            SELECT
                HD.MAHD, HD.NGAYLAP,
                COALESCE(NV.TENNV, HD.MANV, N''),
                COALESCE(CONVERT(nvarchar(20), HD.MACA), N''),
                COALESCE(S.TIEN_HANG, 0),
                COALESCE(KM.TYLEGIAM, 0),
                COALESCE(S.TIEN_HANG, 0) * COALESCE(KM.TYLEGIAM, 0) / 100.0,
                COALESCE(S.TIEN_HANG, 0) * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0),
                CASE WHEN HD.TRANGTHAI = 1
                    THEN COALESCE(S.TIEN_HANG, 0)
                        * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0)
                    ELSE 0 END,
                COALESCE(R.SO_PHIEU, 0),
                COALESCE(RX.SL_HOAN_TIEN, 0),
                COALESCE(RX.SL_DOI_HANG, 0),
                COALESCE(R.TIEN_HOAN, 0),
                CASE WHEN HD.TRANGTHAI = 1
                    THEN COALESCE(S.TIEN_HANG, 0)
                        * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0)
                        - COALESCE(R.TIEN_HOAN, 0)
                    ELSE 0 END,
                COALESCE(HD.TIENKHACHDUA, 0),
                HD.TRANGTHAI
            FROM dbo.HOA_DON HD
            LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = HD.MANV
            LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
            OUTER APPLY (
                SELECT SUM(COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)) AS TIEN_HANG
                FROM dbo.CHI_TIET_HOA_DON CT WHERE CT.MAHD = HD.MAHD
            ) S
            OUTER APPLY (
                SELECT COUNT(*) AS SO_PHIEU,
                       COALESCE(SUM(PDT.TONG_TIEN_HOAN), 0) AS TIEN_HOAN
                FROM dbo.PHIEU_DOI_TRA PDT WHERE PDT.MAHD = HD.MAHD
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
        """, (start_date, end_date))

    def import_report(self, start_date, end_date):
        rows = self.fetch_all("""
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
        suppliers = self.fetch_all("""
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
        return {"imports": rows, "suppliers": suppliers}

    def return_report(self, start_date, end_date):
        return self.fetch_all("""
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
        where_extra = ""
        filter_params = []
        if status == "low":
            where_extra += (
                " AND COALESCE(SP.SLTON, 0) > 0 "
                "AND COALESCE(SP.SLTON, 0) <= ?"
            )
            filter_params.append(threshold)
        elif status == "out":
            where_extra += " AND COALESCE(SP.SLTON, 0) <= 0"
        if keyword:
            where_extra += " AND (SP.MASP LIKE ? OR SP.TENSP LIKE ?)"
            filter_params.extend([f"%{keyword}%", f"%{keyword}%"])

        summary = self.fetch_one(f"""
            SELECT
                COUNT(*),
                SUM(CASE WHEN COALESCE(SP.SLTON, 0) > 0
                    AND COALESCE(SP.SLTON, 0) <= ? THEN 1 ELSE 0 END),
                SUM(CASE WHEN COALESCE(SP.SLTON, 0) <= 0 THEN 1 ELSE 0 END),
                COALESCE(SUM(COALESCE(SP.GIANHAP, 0) * COALESCE(SP.SLTON, 0)), 0)
            FROM dbo.SAN_PHAM SP
            WHERE COALESCE(SP.IS_DELETED, 0) = 0
            {where_extra}
        """, (threshold, *filter_params))
        rows = self.fetch_all(f"""
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
            {where_extra}
            ORDER BY COALESCE(SP.SLTON, 0) ASC, SP.TENSP ASC
        """, (threshold, *filter_params))
        return {"summary": summary, "rows": rows}

    def product_report(self, start_date, end_date, sort, keyword=""):
        order_options = {
            "quantity_desc": (
                "COALESCE(S.SL_BAN, 0) DESC, "
                "(COALESCE(S.DOANH_THU, 0) - COALESCE(R.TIEN_HOAN, 0)) DESC, SP.TENSP ASC"
            ),
            "quantity_asc": (
                "COALESCE(S.SL_BAN, 0) ASC, "
                "(COALESCE(S.DOANH_THU, 0) - COALESCE(R.TIEN_HOAN, 0)) ASC, SP.TENSP ASC"
            ),
            "revenue_desc": (
                "(COALESCE(S.DOANH_THU, 0) - COALESCE(R.TIEN_HOAN, 0)) DESC, "
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
                SELECT CTDT.MASP,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_HOAN_TIEN,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 1
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_DOI_HANG,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0
                        THEN COALESCE(CTDT.DONGIAHOAN, 0) * COALESCE(CTDT.SOLUONG, 0)
                        ELSE 0 END) AS TIEN_HOAN
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY CTDT.MASP
            )
            SELECT
                ROW_NUMBER() OVER (ORDER BY {order_sql}) AS XEP_HANG,
                SP.MASP, COALESCE(SP.TENSP, N''),
                COALESCE(S.SO_HD, 0), COALESCE(S.SL_BAN, 0),
                COALESCE(R.SL_HOAN_TIEN, 0), COALESCE(R.SL_DOI_HANG, 0),
                COALESCE(S.TIEN_HANG, 0), COALESCE(S.TIEN_GIAM, 0),
                COALESCE(S.DOANH_THU, 0), COALESCE(R.TIEN_HOAN, 0),
                COALESCE(S.DOANH_THU, 0) - COALESCE(R.TIEN_HOAN, 0),
                COALESCE(SP.SLTON, 0)
            FROM dbo.SAN_PHAM SP
            LEFT JOIN Sales S ON S.MASP = SP.MASP
            LEFT JOIN Returns R ON R.MASP = SP.MASP
            WHERE COALESCE(SP.IS_DELETED, 0) = 0
            {filter_sql}
            ORDER BY {order_sql}
        """
        return self.fetch_all(sql, (
            start_date, end_date, start_date, end_date, *search_params
        ))

    def shift_report(self, start_date, end_date):
        return self.fetch_all("""
            SELECT
                C.MACA, CAST(C.NGAYLAM AS date), C.SOCA, C.TGMO, C.TGDONG,
                COUNT(DISTINCT L.MANV), C.TMDAUCA, C.TMCUOICA,
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
            LEFT JOIN dbo.LAMCA L ON L.MACA = C.MACA
            WHERE C.NGAYLAM >= CONVERT(date, ?)
              AND C.NGAYLAM < DATEADD(day, 1, CONVERT(date, ?))
            GROUP BY C.MACA, C.NGAYLAM, C.SOCA, C.TGMO, C.TGDONG,
                     C.TMDAUCA, C.TMCUOICA, T.START_AT, T.END_AT
            ORDER BY C.NGAYLAM DESC, C.SOCA, C.MACA
        """, (start_date, end_date))
