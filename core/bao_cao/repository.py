"""Read-model truy vấn cho trung tâm báo cáo POS nhà sách."""

from core.sql_support import resolve_connection


class BaoCaoRepository:
    """Chỉ truy vấn dữ liệu báo cáo; không chứa logic giao diện."""

    def __init__(self, connection_source):
        self.connection_source = connection_source

    def _fetch_all(self, sql, params=()):
        connection = resolve_connection(self.connection_source)
        cursor = connection.cursor()
        try:
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()

    def _fetch_one(self, sql, params=()):
        rows = self._fetch_all(sql, params)
        return rows[0] if rows else None

    def employees(self):
        return self._fetch_all("""
            SELECT MANV, COALESCE(TENNV, N'')
            FROM dbo.NHAN_VIEN
            ORDER BY TENNV, MANV
        """)

    def daily_sales_report(self, start_date, end_date, employee_code=None, keyword=""):
        search_sql = ""
        employee_sql = ""
        params = [start_date, end_date]
        if employee_code:
            employee_sql = " AND HD.MANV = ?"
            params.append(employee_code)
        if keyword:
            search_sql = """
                AND (I.MAHD LIKE ? OR I.TENNV LIKE ?
                     OR I.MANV LIKE ? OR CONVERT(nvarchar(20), I.MACA) LIKE ?)
            """
            params.extend([f"%{keyword}%"] * 4)
        return self._fetch_all(f"""
            WITH InvoiceLines AS (
                SELECT HD.MAHD, HD.NGAYLAP, HD.MANV, HD.MACA,
                    HD.TIENKHACHDUA, HD.TRANGTHAI,
                    COALESCE(NV.TENNV, HD.MANV, N'') AS TENNV,
                    C.SOCA,
                    COUNT(CT.MASP) AS SO_DONG,
                    COALESCE(SUM(CT.SOLUONG), 0) AS SO_LUONG,
                    COALESCE(SUM(COALESCE(CT.DONGIA, 0)
                        * COALESCE(CT.SOLUONG, 0)), 0) AS TIEN_HANG,
                    COALESCE(KM.TYLEGIAM, 0) AS TYLEGIAM
                FROM dbo.HOA_DON HD
                LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = HD.MANV
                LEFT JOIN dbo.CA_LAM_VIEC C ON C.MACA = HD.MACA
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                  {employee_sql}
                GROUP BY HD.MAHD, HD.NGAYLAP, HD.MANV, HD.MACA,
                         HD.TIENKHACHDUA, HD.TRANGTHAI, NV.TENNV,
                         C.SOCA, KM.TYLEGIAM
            ),
            ReturnHeaders AS (
                SELECT MAHD, COUNT(*) AS SO_PHIEU_TRA,
                    SUM(COALESCE(TONG_TIEN_HOAN, 0)) AS TIEN_HOAN
                FROM dbo.PHIEU_DOI_TRA GROUP BY MAHD
            ),
            ReturnLines AS (
                SELECT PDT.MAHD,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_HOAN_TIEN,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 1
                        THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS SL_DOI_HANG
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                GROUP BY PDT.MAHD
            )
            SELECT I.MAHD, N'Khách lẻ' AS KHACH_HANG, I.TENNV, I.NGAYLAP,
                CASE WHEN I.SOCA IS NULL THEN N'—' ELSE CONCAT(N'Ca ', I.SOCA) END,
                I.SO_DONG, I.SO_LUONG, I.TIEN_HANG,
                ROUND(I.TIEN_HANG * I.TYLEGIAM / 100.0, 2) AS TIEN_GIAM,
                CASE WHEN I.TRANGTHAI = 1
                    THEN I.TIEN_HANG - ROUND(I.TIEN_HANG * I.TYLEGIAM / 100.0, 2)
                    ELSE 0 END AS DOAN_SO,
                COALESCE(RH.SO_PHIEU_TRA, 0), COALESCE(RL.SL_HOAN_TIEN, 0),
                COALESCE(RL.SL_DOI_HANG, 0), COALESCE(RH.TIEN_HOAN, 0),
                CASE WHEN I.TRANGTHAI = 1
                    THEN I.TIEN_HANG - ROUND(I.TIEN_HANG * I.TYLEGIAM / 100.0, 2)
                         - COALESCE(RH.TIEN_HOAN, 0) ELSE 0 END AS CON_LAI_SAU_HOAN,
                COALESCE(I.TIENKHACHDUA, 0),
                CASE WHEN I.TRANGTHAI = 1
                    THEN CASE WHEN COALESCE(I.TIENKHACHDUA, 0) >
                        I.TIEN_HANG - ROUND(I.TIEN_HANG * I.TYLEGIAM / 100.0, 2)
                        THEN COALESCE(I.TIENKHACHDUA, 0)
                          - (I.TIEN_HANG - ROUND(I.TIEN_HANG * I.TYLEGIAM / 100.0, 2))
                        ELSE 0 END ELSE 0 END AS TIEN_THUA,
                CASE WHEN I.TRANGTHAI = 1 THEN N'Hợp lệ' ELSE N'Đã hủy' END
            FROM InvoiceLines I
            LEFT JOIN ReturnHeaders RH ON RH.MAHD = I.MAHD
            LEFT JOIN ReturnLines RL ON RL.MAHD = I.MAHD
            WHERE 1 = 1 {search_sql}
            ORDER BY I.NGAYLAP DESC, I.MAHD DESC
        """, tuple(params))

    def sales_by_period_report(self, start_date, end_date, period="day"):
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
        sales_key, return_key = sales_periods[period], return_periods[period]
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
                        THEN ROUND(TIEN_HANG * TYLEGIAM / 100.0, 2) ELSE 0 END) AS TIEN_GIAM,
                    SUM(CASE WHEN TRANGTHAI = 1
                        THEN TIEN_HANG - ROUND(TIEN_HANG * TYLEGIAM / 100.0, 2)
                        ELSE 0 END) AS DOAN_SO
                FROM InvoiceTotals GROUP BY {sales_key}
            ),
            ReturnHeaders AS (
                SELECT {return_key} AS KY, COUNT(*) AS SO_PHIEU_TRA,
                    SUM(COALESCE(TONG_TIEN_HOAN, 0)) AS TIEN_HOAN
                FROM dbo.PHIEU_DOI_TRA
                WHERE NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY {return_key}
            ),
            ReturnLines AS (
                SELECT {return_key} AS KY, SUM(COALESCE(CTDT.SOLUONG, 0)) AS SL_TRA
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY {return_key}
            )
            SELECT COALESCE(S.KY, H.KY, L.KY), COALESCE(S.SO_HOA_DON, 0),
                COALESCE(S.SL_BAN, 0), COALESCE(S.TIEN_HANG, 0),
                COALESCE(S.TIEN_GIAM, 0), COALESCE(S.DOAN_SO, 0),
                COALESCE(H.SO_PHIEU_TRA, 0), COALESCE(L.SL_TRA, 0),
                COALESCE(H.TIEN_HOAN, 0),
                COALESCE(S.DOAN_SO, 0) - COALESCE(H.TIEN_HOAN, 0)
            FROM Sales S
            FULL OUTER JOIN ReturnHeaders H ON H.KY = S.KY
            FULL OUTER JOIN ReturnLines L ON L.KY = COALESCE(S.KY, H.KY)
            ORDER BY 1
        """, (start_date, end_date, start_date, end_date, start_date, end_date))

    def sales_by_employee_report(self, start_date, end_date, keyword=""):
        search_sql = ""
        params = [start_date, end_date, start_date, end_date, start_date, end_date]
        if keyword:
            search_sql = " AND (NV.MANV LIKE ? OR NV.TENNV LIKE ?)"
            params.extend((f"%{keyword}%", f"%{keyword}%"))
        return self._fetch_all(f"""
            WITH InvoiceTotals AS (
                SELECT HD.MAHD, HD.MANV, COALESCE(KM.TYLEGIAM, 0) AS TYLEGIAM,
                    COALESCE(SUM(COALESCE(CT.DONGIA, 0)
                        * COALESCE(CT.SOLUONG, 0)), 0) AS TIEN_HANG,
                    COALESCE(SUM(CT.SOLUONG), 0) AS SL_BAN
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
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0 THEN CTDT.SOLUONG ELSE 0 END) AS SL_HOAN,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 1 THEN CTDT.SOLUONG ELSE 0 END) AS SL_DOI
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY PDT.MANV
            )
            SELECT COALESCE(NV.MANV, S.MANV, H.MANV), COALESCE(NV.TENNV, N''),
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

    def sales_by_product_report(self, start_date, end_date, keyword=""):
        search_sql = ""
        params = [start_date, end_date, start_date, end_date]
        if keyword:
            search_sql = " AND (SP.MASP LIKE ? OR SP.TENSP LIKE ? OR SP.BARCODE LIKE ?)"
            params.extend([f"%{keyword}%"] * 3)
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
            Returns AS (
                SELECT CTDT.MASP,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0 THEN CTDT.SOLUONG ELSE 0 END) AS SL_HOAN,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 1 THEN CTDT.SOLUONG ELSE 0 END) AS SL_DOI
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY CTDT.MASP
            )
            SELECT SP.MASP, COALESCE(SP.BARCODE, N''), COALESCE(BK.ISBN, N''),
                COALESCE(SP.TENSP, N''), COALESCE(SP.DVT, N''),
                COALESCE(S.SO_HD, 0), COALESCE(S.SL_BAN, 0),
                COALESCE(R.SL_HOAN, 0), COALESCE(R.SL_DOI, 0),
                COALESCE(SP.SLTON, 0)
            FROM dbo.SAN_PHAM SP
            LEFT JOIN Sales S ON S.MASP = SP.MASP
            LEFT JOIN Returns R ON R.MASP = SP.MASP
            LEFT JOIN dbo.SACH BK ON BK.MASP = SP.MASP
            WHERE (COALESCE(SP.IS_DELETED, 0) = 0
                   OR S.MASP IS NOT NULL OR R.MASP IS NOT NULL)
              {search_sql}
            ORDER BY COALESCE(S.SL_BAN, 0) DESC, SP.TENSP
        """, tuple(params))

    def promotion_report(self, start_date, end_date, keyword=""):
        search_sql = ""
        params = [start_date, end_date]
        if keyword:
            search_sql = " AND (KM.MAKM LIKE ? OR KM.TENKM LIKE ?)"
            params.extend((f"%{keyword}%", f"%{keyword}%"))
        return self._fetch_all(f"""
            WITH InvoiceTotals AS (
                SELECT HD.MAHD, HD.MAKM,
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
                GROUP BY HD.MAHD, HD.MAKM, KM.TENKM, KM.TYLEGIAM
            ),
            Returns AS (
                SELECT MAHD, COUNT(*) AS SO_PHIEU_TRA,
                    SUM(COALESCE(TONG_TIEN_HOAN, 0)) AS TIEN_HOAN
                FROM dbo.PHIEU_DOI_TRA GROUP BY MAHD
            ),
            Sales AS (
                SELECT I.MAKM, I.TENKM, I.TYLEGIAM, COUNT(*) AS SO_HD,
                    SUM(I.TIEN_HANG) AS TIEN_HANG,
                    SUM(ROUND(I.TIEN_HANG * I.TYLEGIAM / 100.0, 2)) AS TIEN_GIAM,
                    SUM(I.TIEN_HANG - ROUND(I.TIEN_HANG * I.TYLEGIAM / 100.0, 2)) AS DOAN_SO,
                    SUM(COALESCE(R.SO_PHIEU_TRA, 0)) AS SO_PHIEU_TRA,
                    SUM(COALESCE(R.TIEN_HOAN, 0)) AS TIEN_HOAN
                FROM InvoiceTotals I
                LEFT JOIN Returns R ON R.MAHD = I.MAHD
                GROUP BY I.MAKM, I.TENKM, I.TYLEGIAM
            )
            SELECT S.MAKM, S.TENKM, S.TYLEGIAM, S.SO_HD, S.TIEN_HANG,
                S.TIEN_GIAM, S.DOAN_SO, S.SO_PHIEU_TRA, S.TIEN_HOAN,
                S.DOAN_SO - S.TIEN_HOAN
            FROM Sales S
            LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = S.MAKM
            WHERE 1 = 1 {search_sql}
            ORDER BY S.DOAN_SO DESC, S.TENKM
        """, tuple(params))

    def return_detail_report(self, start_date, end_date, keyword=""):
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
                COALESCE(NV.TENNV, N''), COALESCE(PDT.LY_DO, N''),
                COALESCE(D.SO_DONG, 0), COALESCE(D.SL_HOAN, 0),
                COALESCE(D.SL_DOI, 0), COALESCE(D.SL_NGUYEN, 0),
                COALESCE(D.SL_HONG, 0), COALESCE(PDT.TONG_TIEN_HOAN, 0)
            FROM dbo.PHIEU_DOI_TRA PDT
            LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = PDT.MANV
            OUTER APPLY (
                SELECT COUNT(*) AS SO_DONG,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0 THEN CTDT.SOLUONG ELSE 0 END) AS SL_HOAN,
                    SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 1 THEN CTDT.SOLUONG ELSE 0 END) AS SL_DOI,
                    SUM(CASE WHEN CTDT.TINHTRANGHANG = 1 THEN CTDT.SOLUONG ELSE 0 END) AS SL_NGUYEN,
                    SUM(CASE WHEN CTDT.TINHTRANGHANG = 0 THEN CTDT.SOLUONG ELSE 0 END) AS SL_HONG
                FROM dbo.CHI_TIET_DOI_TRA CTDT WHERE CTDT.MAPDT = PDT.MAPDT
            ) D
            WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
              AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
              {search_sql}
            ORDER BY PDT.NGAY_DOI_TRA DESC, PDT.MAPDT DESC
        """, tuple(params))

    def import_detail_report(self, start_date, end_date, keyword=""):
        search_sql = ""
        params = [start_date, end_date]
        if keyword:
            search_sql = """
                AND (PN.MAPN LIKE ? OR CT.MASP LIKE ? OR SP.TENSP LIKE ?
                     OR NCC.TENNCC LIKE ? OR NV.TENNV LIKE ?)
            """
            params.extend([f"%{keyword}%"] * 5)
        return self._fetch_all(f"""
            SELECT PN.MAPN, PN.NGAYNHAP, COALESCE(PN.LOAIPHIEUNHAP, N''),
                COALESCE(NCC.TENNCC, PN.MANCC, N''), COALESCE(PN.SHDNCC, N''),
                COALESCE(NV.TENNV, PN.MANV, N''), CT.MASP, COALESCE(SP.TENSP, N''),
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
        search_sql = ""
        params = [start_date, end_date]
        if keyword:
            search_sql = " AND (NCC.MANCC LIKE ? OR NCC.TENNCC LIKE ?)"
            params.extend((f"%{keyword}%", f"%{keyword}%"))
        return self._fetch_all(f"""
            SELECT PN.MANCC, COALESCE(NCC.TENNCC, PN.MANCC, N''),
                COALESCE(NCC.SDT, N''), COUNT(*) AS SO_PHIEU_NHAP,
                COALESCE(SUM(D.SO_LUONG), 0), COALESCE(SUM(PN.TONGTRIGIA), 0)
            FROM dbo.PHIEU_NHAP PN
            LEFT JOIN dbo.NHA_CUNG_CAP NCC ON NCC.MANCC = PN.MANCC
            OUTER APPLY (
                SELECT SUM(COALESCE(CT.SOLUONG, 0)) AS SO_LUONG
                FROM dbo.CHI_TIET_PHIEU_NHAP CT WHERE CT.MAPN = PN.MAPN
            ) D
            WHERE ISNULL(PN.TRANGTHAI, 1) = 1
              AND PN.NGAYNHAP >= CONVERT(date, ?)
              AND PN.NGAYNHAP < DATEADD(day, 1, CONVERT(date, ?))
              {search_sql}
            GROUP BY PN.MANCC, NCC.TENNCC, NCC.SDT
            ORDER BY SUM(PN.TONGTRIGIA) DESC, NCC.TENNCC
        """, tuple(params))

    def current_inventory_report(self, threshold=5, status="all", keyword=""):
        status_sql = ""
        params = [threshold]
        if status == "low":
            status_sql = " AND COALESCE(SP.SLTON, 0) > 0 AND SP.SLTON <= ?"
            params.append(threshold)
        elif status == "out":
            status_sql = " AND COALESCE(SP.SLTON, 0) <= 0"
        search_sql = ""
        if keyword:
            search_sql = " AND (SP.MASP LIKE ? OR SP.TENSP LIKE ? OR SP.BARCODE LIKE ?)"
            params.extend([f"%{keyword}%"] * 3)
        return self._fetch_all(f"""
            SELECT SP.MASP, COALESCE(SP.BARCODE, N''),
                COALESCE(SP.TENSP, N''), COALESCE(SP.DVT, N''),
                COALESCE(SP.SLTON, 0), COALESCE(SP.GIANHAP, 0),
                COALESCE(SP.GIABAN, 0),
                COALESCE(SP.SLTON, 0) * COALESCE(SP.GIANHAP, 0),
                CASE WHEN COALESCE(SP.SLTON, 0) <= 0 THEN N'Hết hàng'
                     WHEN SP.SLTON <= ? THEN N'Sắp hết' ELSE N'Còn hàng' END
            FROM dbo.SAN_PHAM SP
            WHERE COALESCE(SP.IS_DELETED, 0) = 0
              {status_sql}
              {search_sql}
            ORDER BY COALESCE(SP.SLTON, 0), SP.TENSP
        """, tuple(params))

    @staticmethod
    def _stock_movements_cte():
        return """
            WITH Bounds AS (
                SELECT CONVERT(date, ?) AS START_DATE,
                       DATEADD(day, 1, CONVERT(date, ?)) AS END_EXCLUSIVE
            ),
            Movements AS (
                SELECT CT.MASP, PN.NGAYNHAP AS NGAY, PN.MAPN AS CHUNG_TU,
                    N'Nhập nhà cung cấp' AS LOAI,
                    SUM(COALESCE(CT.SOLUONG, 0)) AS SL_NHAP,
                    SUM(COALESCE(CT.SOLUONG, 0) * COALESCE(CT.DONGIA, 0)) AS GT_NHAP,
                    CAST(0 AS BIGINT) AS SL_XUAT,
                    CAST(0 AS DECIMAL(18, 2)) AS GT_XUAT
                FROM dbo.PHIEU_NHAP PN
                INNER JOIN dbo.CHI_TIET_PHIEU_NHAP CT ON CT.MAPN = PN.MAPN
                WHERE ISNULL(PN.TRANGTHAI, 1) = 1
                GROUP BY CT.MASP, PN.NGAYNHAP, PN.MAPN

                UNION ALL

                SELECT CT.MASP, HD.NGAYLAP, HD.MAHD, N'Bán hàng',
                    CAST(0 AS BIGINT), CAST(0 AS DECIMAL(18, 2)),
                    SUM(COALESCE(CT.SOLUONG, 0)),
                    SUM(COALESCE(CT.SOLUONG, 0) * COALESCE(SP.GIANHAP, 0))
                FROM dbo.HOA_DON HD
                INNER JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                INNER JOIN dbo.SAN_PHAM SP ON SP.MASP = CT.MASP
                WHERE HD.TRANGTHAI = 1
                GROUP BY CT.MASP, HD.NGAYLAP, HD.MAHD

                UNION ALL

                SELECT CTDT.MASP, PDT.NGAY_DOI_TRA, PDT.MAPDT,
                    N'Khách trả nhập lại',
                    SUM(COALESCE(CTDT.SOLUONG, 0)),
                    SUM(COALESCE(CTDT.SOLUONG, 0) * COALESCE(SP.GIANHAP, 0)),
                    CAST(0 AS BIGINT), CAST(0 AS DECIMAL(18, 2))
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                INNER JOIN dbo.SAN_PHAM SP ON SP.MASP = CTDT.MASP
                WHERE CTDT.HINH_THUC_XU_LY = 0 AND CTDT.TINHTRANGHANG = 1
                GROUP BY CTDT.MASP, PDT.NGAY_DOI_TRA, PDT.MAPDT

                UNION ALL

                SELECT CTDT.MASP, PDT.NGAY_DOI_TRA, PDT.MAPDT,
                    N'Xuất đổi hàng', CAST(0 AS BIGINT),
                    CAST(0 AS DECIMAL(18, 2)),
                    SUM(COALESCE(CTDT.SOLUONG, 0)),
                    SUM(COALESCE(CTDT.SOLUONG, 0) * COALESCE(SP.GIANHAP, 0))
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                INNER JOIN dbo.SAN_PHAM SP ON SP.MASP = CTDT.MASP
                WHERE CTDT.HINH_THUC_XU_LY = 1
                GROUP BY CTDT.MASP, PDT.NGAY_DOI_TRA, PDT.MAPDT
            )
        """

    def stock_movement_report(self, start_date, end_date, keyword=""):
        search_sql = ""
        params = [start_date, end_date]
        if keyword:
            search_sql = " AND (SP.MASP LIKE ? OR SP.TENSP LIKE ? OR SP.BARCODE LIKE ?)"
            params.extend([f"%{keyword}%"] * 3)
        sql = self._stock_movements_cte() + f"""
            , MovementSummary AS (
                SELECT M.MASP,
                    SUM(CASE WHEN M.NGAY >= B.START_DATE
                        THEN M.SL_NHAP - M.SL_XUAT ELSE 0 END) AS NET_FROM_START,
                    SUM(CASE WHEN M.NGAY >= B.END_EXCLUSIVE
                        THEN M.SL_NHAP - M.SL_XUAT ELSE 0 END) AS NET_AFTER_END,
                    SUM(CASE WHEN M.NGAY >= B.START_DATE AND M.NGAY < B.END_EXCLUSIVE
                              AND M.LOAI = N'Nhập nhà cung cấp'
                        THEN M.SL_NHAP ELSE 0 END) AS SL_NHAP,
                    SUM(CASE WHEN M.NGAY >= B.START_DATE AND M.NGAY < B.END_EXCLUSIVE
                              AND M.LOAI = N'Khách trả nhập lại'
                        THEN M.SL_NHAP ELSE 0 END) AS SL_KHACH_TRA,
                    SUM(CASE WHEN M.NGAY >= B.START_DATE AND M.NGAY < B.END_EXCLUSIVE
                              AND M.LOAI = N'Bán hàng'
                        THEN M.SL_XUAT ELSE 0 END) AS SL_BAN,
                    SUM(CASE WHEN M.NGAY >= B.START_DATE AND M.NGAY < B.END_EXCLUSIVE
                              AND M.LOAI = N'Xuất đổi hàng'
                        THEN M.SL_XUAT ELSE 0 END) AS SL_DOI
                FROM Movements M CROSS JOIN Bounds B
                GROUP BY M.MASP
            ),
            ImportValues AS (
                SELECT CT.MASP,
                    SUM(COALESCE(CT.SOLUONG, 0) * COALESCE(CT.DONGIA, 0)) AS GT_NHAP
                FROM dbo.PHIEU_NHAP PN
                INNER JOIN dbo.CHI_TIET_PHIEU_NHAP CT ON CT.MAPN = PN.MAPN
                CROSS JOIN Bounds B
                WHERE ISNULL(PN.TRANGTHAI, 1) = 1
                  AND PN.NGAYNHAP >= B.START_DATE
                  AND PN.NGAYNHAP < B.END_EXCLUSIVE
                GROUP BY CT.MASP
            )
            SELECT SP.MASP, COALESCE(SP.TENSP, N''), COALESCE(SP.DVT, N''),
                COALESCE(SP.SLTON, 0) - COALESCE(M.NET_FROM_START, 0),
                (COALESCE(SP.SLTON, 0) - COALESCE(M.NET_FROM_START, 0))
                    * COALESCE(SP.GIANHAP, 0),
                COALESCE(M.SL_NHAP, 0), COALESCE(I.GT_NHAP, 0),
                COALESCE(M.SL_KHACH_TRA, 0),
                COALESCE(M.SL_KHACH_TRA, 0) * COALESCE(SP.GIANHAP, 0),
                COALESCE(M.SL_BAN, 0),
                COALESCE(M.SL_BAN, 0) * COALESCE(SP.GIANHAP, 0),
                COALESCE(M.SL_DOI, 0),
                COALESCE(M.SL_DOI, 0) * COALESCE(SP.GIANHAP, 0),
                COALESCE(SP.SLTON, 0) - COALESCE(M.NET_AFTER_END, 0),
                (COALESCE(SP.SLTON, 0) - COALESCE(M.NET_AFTER_END, 0))
                    * COALESCE(SP.GIANHAP, 0)
            FROM dbo.SAN_PHAM SP
            LEFT JOIN MovementSummary M ON M.MASP = SP.MASP
            LEFT JOIN ImportValues I ON I.MASP = SP.MASP
            WHERE COALESCE(SP.IS_DELETED, 0) = 0 OR M.MASP IS NOT NULL
            {search_sql}
            ORDER BY SP.TENSP, SP.MASP
        """
        return self._fetch_all(sql, tuple(params))

    def stock_card_report(self, start_date, end_date, keyword=""):
        search_sql = ""
        params = [start_date, end_date]
        if keyword:
            search_sql = " AND (SP.MASP LIKE ? OR SP.TENSP LIKE ? OR SP.BARCODE LIKE ?)"
            params.extend([f"%{keyword}%"] * 3)
        sql = self._stock_movements_cte() + f"""
            , Opening AS (
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
                SELECT M.*
                FROM Movements M CROSS JOIN Bounds B
                WHERE M.NGAY >= B.START_DATE AND M.NGAY < B.END_EXCLUSIVE
            )
            SELECT P.NGAY, P.LOAI, P.CHUNG_TU, P.MASP,
                COALESCE(SP.TENSP, N''), O.TON_DAU,
                P.SL_NHAP, P.GT_NHAP, P.SL_XUAT, P.GT_XUAT,
                O.TON_DAU + SUM(P.SL_NHAP - P.SL_XUAT) OVER (
                    PARTITION BY P.MASP
                    ORDER BY P.NGAY, P.CHUNG_TU, P.LOAI
                    ROWS UNBOUNDED PRECEDING
                )
            FROM PeriodMovements P
            INNER JOIN Opening O ON O.MASP = P.MASP
            INNER JOIN dbo.SAN_PHAM SP ON SP.MASP = P.MASP
            WHERE 1 = 1 {search_sql}
            ORDER BY P.MASP, P.NGAY, P.CHUNG_TU, P.LOAI
        """
        return self._fetch_all(sql, tuple(params))

    def shift_report(self, start_date, end_date):
        return self._fetch_all("""
            WITH InvoiceTotals AS (
                SELECT HD.MAHD, HD.MACA,
                    COALESCE(SUM(CT.SOLUONG), 0) AS SL_BAN,
                    COALESCE(SUM(COALESCE(CT.DONGIA, 0)
                        * COALESCE(CT.SOLUONG, 0)), 0) AS TIEN_HANG,
                    COALESCE(KM.TYLEGIAM, 0) AS TYLEGIAM
                FROM dbo.HOA_DON HD
                LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.TRANGTHAI = 1
                  AND HD.NGAYLAP >= CONVERT(date, ?)
                  AND HD.NGAYLAP < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY HD.MAHD, HD.MACA, KM.TYLEGIAM
            ),
            Sales AS (
                SELECT MACA, COUNT(*) AS SO_HD, SUM(SL_BAN) AS SL_BAN,
                    SUM(TIEN_HANG - ROUND(TIEN_HANG * TYLEGIAM / 100.0, 2)) AS DOAN_SO
                FROM InvoiceTotals GROUP BY MACA
            ),
            Employees AS (
                SELECT MACA, COUNT(*) AS LUOT_NHAN_VIEN
                FROM dbo.LAMCA GROUP BY MACA
            ),
            Returns AS (
                SELECT HD.MACA, COUNT(DISTINCT PDT.MAPDT) AS SO_PHIEU_TRA,
                    SUM(COALESCE(PDT.TONG_TIEN_HOAN, 0)) AS TIEN_HOAN
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.HOA_DON HD ON HD.MAHD = PDT.MAHD
                WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
                GROUP BY HD.MACA
            )
            SELECT C.MACA, CAST(C.NGAYLAM AS date), C.SOCA, C.TGMO, C.TGDONG,
                COALESCE(E.LUOT_NHAN_VIEN, 0), COALESCE(S.SO_HD, 0),
                COALESCE(S.SL_BAN, 0), COALESCE(S.DOAN_SO, 0),
                COALESCE(R.SO_PHIEU_TRA, 0), COALESCE(R.TIEN_HOAN, 0),
                COALESCE(C.TMDAUCA, 0), C.TMCUOICA,
                CASE WHEN C.TMCUOICA IS NULL THEN N'Chưa chốt' ELSE N'Đã chốt' END
            FROM dbo.CA_LAM_VIEC C
            LEFT JOIN Sales S ON S.MACA = C.MACA
            LEFT JOIN Employees E ON E.MACA = C.MACA
            LEFT JOIN Returns R ON R.MACA = C.MACA
            WHERE C.NGAYLAM >= CONVERT(date, ?)
              AND C.NGAYLAM < DATEADD(day, 1, CONVERT(date, ?))
            ORDER BY C.NGAYLAM DESC, C.SOCA, C.MACA
        """, (start_date, end_date, start_date, end_date))
