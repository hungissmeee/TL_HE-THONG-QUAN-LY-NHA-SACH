"""Repository SQL cho nghiệp vụ phiếu nhập kho."""

from core.sql_support import resolve_connection


class PhieuNhapRepository:
    """Truy vấn và giao dịch phiếu nhập, không phụ thuộc PySide6."""

    def __init__(self, connection_source):
        self.connection_source = connection_source

    def _connection(self):
        return resolve_connection(self.connection_source)

    def get_employee(self, username, is_admin=False):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT MANV, TENNV, VAITRO
                FROM dbo.NHAN_VIEN WHERE MANV = ?
            """, username)
            row = cursor.fetchone()
            if row is None and not is_admin:
                raise LookupError(
                    "Tài khoản đăng nhập chưa có hồ sơ tương ứng trong NHAN_VIEN."
                )
            return {
                "manv": row[0] if row else None,
                "tennv": (row[1] or row[0]) if row else "Admin",
                "vaitro": (row[2] or "") if row else "Quản lý",
            }
        finally:
            cursor.close()

    def list_suppliers_for_import(self):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT MANCC, TENNCC FROM dbo.NHA_CUNG_CAP
                WHERE ISNULL(IS_DELETED, 0) = 0
                ORDER BY TENNCC, MANCC
            """)
            return [(str(r[0]), str(r[1] or "")) for r in cursor.fetchall()]
        finally:
            cursor.close()

    def list_products_for_import(self):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT SP.MASP, SP.TENSP, SP.DVT, SP.GIANHAP,
                       SP.SLTON, SP.VAT, SP.BARCODE, S.ISBN
                FROM dbo.SAN_PHAM SP
                LEFT JOIN dbo.SACH S ON S.MASP = SP.MASP
                WHERE ISNULL(SP.IS_DELETED, 0) = 0
                ORDER BY SP.TENSP, SP.MASP
            """)
            keys = ("masp", "tensp", "dvt", "price", "stock", "vat", "barcode", "isbn")
            return [dict(zip(keys, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def list_imports(self, start_date, end_date, keyword=""):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            sql = """
                SELECT PN.MAPN, PN.NGAYNHAP, PN.MANV, NV.TENNV,
                       PN.MANCC, NCC.TENNCC, PN.LOAIPHIEUNHAP,
                       PN.SHDNCC, PN.TONGTRIGIA, ISNULL(PN.TRANGTHAI, 1)
                FROM dbo.PHIEU_NHAP PN
                LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = PN.MANV
                LEFT JOIN dbo.NHA_CUNG_CAP NCC ON NCC.MANCC = PN.MANCC
                WHERE PN.NGAYNHAP >= ?
                  AND PN.NGAYNHAP < DATEADD(DAY, 1, CAST(? AS date))
            """
            params = [start_date, end_date]
            keyword = str(keyword or "").strip()
            if keyword:
                like = f"%{keyword}%"
                sql += """
                    AND (PN.MAPN LIKE ? OR PN.SHDNCC LIKE ? OR PN.MANV LIKE ?
                         OR NV.TENNV LIKE ? OR PN.MANCC LIKE ? OR NCC.TENNCC LIKE ?)
                """
                params.extend([like] * 6)
            sql += " ORDER BY PN.NGAYNHAP DESC, PN.MAPN DESC"
            cursor.execute(sql, *params)
            return [tuple(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_import_detail(self, import_code):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT PN.MAPN, PN.NGAYNHAP, PN.LOAIPHIEUNHAP, PN.SHDNCC,
                       PN.TONGTRIGIA, PN.MANV, NV.TENNV, PN.MANCC,
                       NCC.TENNCC, NCC.SDT, NCC.DIACHI, NCC.MST, PN.TRANGTHAI
                FROM dbo.PHIEU_NHAP PN
                LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = PN.MANV
                LEFT JOIN dbo.NHA_CUNG_CAP NCC ON NCC.MANCC = PN.MANCC
                WHERE PN.MAPN = ?
            """, import_code)
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Không tìm thấy phiếu nhập.")
            header = dict(zip(
                ("mapn", "ngaynhap", "loai", "shdncc", "total", "manv",
                 "tennv", "mancc", "tenncc", "sdt", "diachi", "mst", "status"),
                row
            ))
            cursor.execute("""
                SELECT CT.MASP, SP.TENSP, SP.DVT, CT.SOLUONG, CT.DONGIA, CT.VAT
                FROM dbo.CHI_TIET_PHIEU_NHAP CT
                LEFT JOIN dbo.SAN_PHAM SP ON SP.MASP = CT.MASP
                WHERE CT.MAPN = ?
                ORDER BY SP.TENSP, CT.MASP
            """, import_code)
            items = [
                dict(zip(("masp", "tensp", "dvt", "quantity", "price", "vat"), detail))
                for detail in cursor.fetchall()
            ]
            return {"header": header, "items": items}
        finally:
            cursor.close()

    @staticmethod
    def _next_import_code(cursor):
        cursor.execute("""
            SELECT COALESCE(MAX(TRY_CONVERT(BIGINT, SUBSTRING(MAPN, 3, 18))), 0)
            FROM dbo.PHIEU_NHAP WITH (TABLOCKX, HOLDLOCK)
            WHERE UPPER(LEFT(MAPN, 2)) = 'PN'
              AND TRY_CONVERT(BIGINT, SUBSTRING(MAPN, 3, 18)) IS NOT NULL
        """)
        code = f"PN{int(cursor.fetchone()[0] or 0) + 1:06d}"
        if len(code) > 20:
            raise ValueError("Đã vượt giới hạn độ dài mã phiếu nhập.")
        return code

    def create_import(self, payload):
        """Tạo phiếu, chi tiết, cập nhật tồn và giá nhập bình quân trong một transaction."""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            supplier_code = payload["supplier_code"]
            supplier_invoice = payload.get("supplier_invoice")
            if supplier_invoice:
                cursor.execute("""
                    SELECT 1 FROM dbo.PHIEU_NHAP WITH (UPDLOCK, HOLDLOCK)
                    WHERE MANCC = ? AND SHDNCC = ? AND ISNULL(TRANGTHAI, 1) = 1
                """, supplier_code, supplier_invoice)
                if cursor.fetchone():
                    raise ValueError(
                        "Số hóa đơn nhà cung cấp này đã được ghi nhận cho nhà cung cấp đã chọn."
                    )
            import_code = self._next_import_code(cursor)
            cursor.execute("""
                INSERT INTO dbo.PHIEU_NHAP
                    (MAPN, NGAYNHAP, LOAIPHIEUNHAP, SHDNCC,
                     TONGTRIGIA, MANV, MANCC, TRANGTHAI)
                VALUES (?, SYSDATETIME(), ?, ?, ?, ?, ?, 1)
            """, import_code, payload["import_type"], supplier_invoice,
                 payload["total"], payload["employee_code"], supplier_code)

            for item in payload["items"]:
                code = item["product_code"]
                quantity = item["quantity"]
                price = item["price"]
                cursor.execute("""
                    UPDATE dbo.SAN_PHAM
                    SET GIANHAP = CAST((
                        CAST(ISNULL(SLTON, 0) AS DECIMAL(18, 2))
                        * CAST(ISNULL(GIANHAP, 0) AS DECIMAL(18, 2))
                        + CAST(? AS DECIMAL(18, 2)) * CAST(? AS DECIMAL(10, 0))
                    ) / NULLIF(
                        CAST(ISNULL(SLTON, 0) AS DECIMAL(18, 2))
                        + CAST(? AS DECIMAL(18, 2)), 0
                    ) AS DECIMAL(15, 2)),
                    SLTON = ISNULL(SLTON, 0) + ?
                    WHERE MASP = ? AND ISNULL(IS_DELETED, 0) = 0
                """, price, quantity, quantity, quantity, code)
                if cursor.rowcount != 1:
                    raise LookupError(
                        f"Không tìm thấy sản phẩm {code} hoặc sản phẩm đã ngừng sử dụng."
                    )
                cursor.execute("""
                    INSERT INTO dbo.CHI_TIET_PHIEU_NHAP
                        (MAPN, MASP, DONGIA, SOLUONG, VAT)
                    VALUES (?, ?, ?, ?, ?)
                """, import_code, code, price, quantity, item["vat"])
            conn.commit()
            return import_code
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def cancel_import(self, import_code, username, role, is_admin=False):
        """Hủy phiếu và hoàn tác tồn kho/giá nhập trong cùng transaction."""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT TRANGTHAI, MANV,
                       CASE WHEN NGAYNHAP >= DATEADD(MINUTE, -5, SYSDATETIME())
                                  AND NGAYNHAP <= SYSDATETIME()
                            THEN 1 ELSE 0 END
                FROM dbo.PHIEU_NHAP WITH (UPDLOCK, HOLDLOCK)
                WHERE MAPN = ?
            """, import_code)
            header = cursor.fetchone()
            if header is None:
                raise LookupError("Không tìm thấy phiếu nhập.")
            if int(header[0] or 0) != 1:
                raise ValueError("Phiếu nhập đã bị hủy trước đó.")
            role = str(role or "").strip().casefold()
            admin = bool(is_admin) or str(username or "").strip().casefold() == "admin"
            manager = role == "quản lý"
            warehouse = role == "nhân viên kho"
            if not (admin or manager or warehouse):
                raise PermissionError("Tài khoản không có quyền hủy phiếu nhập.")
            if warehouse and not (admin or manager):
                if str(header[1] or "").casefold() != str(username or "").casefold():
                    raise PermissionError("Nhân viên kho chỉ được hủy phiếu do mình lập.")
                if int(header[2] or 0) != 1:
                    raise PermissionError("Chỉ được hủy phiếu do mình lập trong vòng 5 phút.")

            cursor.execute("""
                SELECT MASP, SUM(ISNULL(SOLUONG, 0))
                FROM dbo.CHI_TIET_PHIEU_NHAP WITH (UPDLOCK, HOLDLOCK)
                WHERE MAPN = ? GROUP BY MASP
            """, import_code)
            details = cursor.fetchall()
            if not details:
                raise ValueError("Phiếu nhập không có chi tiết sản phẩm.")
            for detail in details:
                product_code, quantity = str(detail[0]), int(detail[1] or 0)
                if quantity <= 0:
                    raise ValueError(f"Số lượng nhập của {product_code} không hợp lệ.")
                cursor.execute("""
                    UPDATE dbo.SAN_PHAM SET SLTON = SLTON - ?
                    WHERE MASP = ? AND ISNULL(SLTON, 0) >= ?
                """, quantity, product_code, quantity)
                if cursor.rowcount != 1:
                    raise ValueError(
                        f"Không thể hủy phiếu vì tồn kho {product_code} không còn đủ "
                        f"{quantity} sản phẩm để hoàn tác."
                    )
            cursor.execute("""
                UPDATE dbo.PHIEU_NHAP SET TRANGTHAI = 0
                WHERE MAPN = ? AND TRANGTHAI = 1
            """, import_code)
            if cursor.rowcount != 1:
                raise RuntimeError("Không thể cập nhật trạng thái phiếu nhập.")
            for detail in details:
                product_code = str(detail[0])
                cursor.execute("""
                    UPDATE SP
                    SET GIANHAP = CAST(COALESCE(T.AVG_COST, 0) AS DECIMAL(15, 2))
                    FROM dbo.SAN_PHAM SP
                    OUTER APPLY (
                        SELECT SUM(CT.DONGIA * CT.SOLUONG)
                               / NULLIF(SUM(CT.SOLUONG), 0) AS AVG_COST
                        FROM dbo.CHI_TIET_PHIEU_NHAP CT
                        INNER JOIN dbo.PHIEU_NHAP PN ON PN.MAPN = CT.MAPN
                        WHERE CT.MASP = SP.MASP AND ISNULL(PN.TRANGTHAI, 1) = 1
                    ) T WHERE SP.MASP = ?
                """, product_code)
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
