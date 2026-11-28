"""Repository SQL và transaction cho nghiệp vụ hóa đơn bán hàng."""

from decimal import Decimal

from core.sql_support import resolve_connection, restore_and_activate_product


class HoaDonRepository:
    """Truy vấn, xác thực và ghi nhận hóa đơn; độc lập với PySide6."""

    def __init__(self, connection_source):
        self.connection_source = connection_source

    def _connection(self):
        return resolve_connection(self.connection_source)

    def get_employee_and_active_shift(self, username, is_admin=False):
        """Lấy hồ sơ nhân viên và ca hiện tại; Admin được phép không có hồ sơ/ca."""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            if is_admin:
                cursor.execute("""
                    SELECT MANV, TENNV, VAITRO
                    FROM dbo.NHAN_VIEN WHERE MANV = ?
                """, username)
                row = cursor.fetchone()
                return {
                    "employee": {
                        "manv": row[0] if row else None,
                        "tennv": (row[1] or row[0]) if row else "Admin",
                        "vaitro": row[2] if row else "Quản trị hệ thống",
                    },
                    "active_shift": None,
                }

            cursor.execute("""
                SELECT TOP 1
                    NV.MANV, NV.TENNV, NV.VAITRO,
                    C.MACA, C.SOCA, C.NGAYLAM, C.TGMO, C.TGDONG
                FROM dbo.NHAN_VIEN NV
                INNER JOIN dbo.LAMCA L ON L.MANV = NV.MANV
                INNER JOIN dbo.CA_LAM_VIEC C ON C.MACA = L.MACA
                WHERE NV.MANV = ?
                  AND CAST(C.NGAYLAM AS date) = CAST(SYSDATETIME() AS date)
                  AND CAST(SYSDATETIME() AS time) >= C.TGMO
                  AND CAST(SYSDATETIME() AS time) < C.TGDONG
                  AND C.TMCUOICA IS NULL
                ORDER BY C.SOCA
            """, username)
            row = cursor.fetchone()
            if row is None:
                raise PermissionError(
                    "Bạn chưa đăng ký ca đang diễn ra. Chỉ nhân viên thuộc ca hiện tại mới được lập hóa đơn."
                )
            return {
                "employee": {"manv": row[0], "tennv": row[1], "vaitro": row[2]},
                "active_shift": {
                    "maca": row[3], "soca": row[4], "ngaylam": row[5],
                    "tgmo": row[6], "tgdong": row[7],
                },
            }
        finally:
            cursor.close()

    def get_employee_role(self, username):
        if str(username or "").strip().casefold() == "admin":
            return ""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT VAITRO FROM dbo.NHAN_VIEN WHERE MANV = ?",
                username,
            )
            row = cursor.fetchone()
            return str(row[0] or "").strip() if row else ""
        finally:
            cursor.close()

    def list_active_promotions(self):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT MAKM, TENKM, TYLEGIAM
                FROM dbo.CHUONG_TRINH_KM
                WHERE NGAYBD <= SYSDATETIME()
                  AND NGAYKT >= SYSDATETIME()
                  AND ISNULL(IS_DELETED, 0) = 0
                ORDER BY TENKM
            """)
            return [tuple(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def list_available_products(self):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT SP.MASP, SP.TENSP, SP.DVT, SP.GIABAN,
                       SP.SLTON, SP.VAT, SP.BARCODE, S.ISBN
                FROM dbo.SAN_PHAM SP
                LEFT JOIN dbo.SACH S ON S.MASP = SP.MASP
                WHERE ISNULL(SP.IS_DELETED, 0) = 0
                  AND ISNULL(SP.SLTON, 0) > 0
                ORDER BY SP.TENSP, SP.MASP
            """)
            keys = ("masp", "tensp", "dvt", "price", "stock", "vat", "barcode", "isbn")
            return [dict(zip(keys, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def list_invoices(self, start_date, end_date, keyword=""):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            sql = """
                SELECT
                    HD.MAHD, HD.NGAYLAP, HD.MANV, NV.TENNV,
                    HD.MACA, C.SOCA, HD.TIENKHACHDUA,
                    COALESCE(SUM(CT.DONGIA * CT.SOLUONG), 0)
                        * (1 - COALESCE(KM.TYLEGIAM, 0) / 100.0) AS TOTAL_AMOUNT,
                    HD.TRANGTHAI
                FROM dbo.HOA_DON HD
                LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = HD.MANV
                LEFT JOIN dbo.CA_LAM_VIEC C ON C.MACA = HD.MACA
                LEFT JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.NGAYLAP >= ?
                  AND HD.NGAYLAP < DATEADD(DAY, 1, CAST(? AS date))
            """
            params = [start_date, end_date]
            keyword = str(keyword or "").strip()
            if keyword:
                like = f"%{keyword}%"
                sql += """
                    AND (
                        HD.MAHD LIKE ? OR HD.MANV LIKE ? OR NV.TENNV LIKE ?
                        OR CONVERT(NVARCHAR(20), HD.MACA) LIKE ?
                        OR CONVERT(NVARCHAR(20), C.SOCA) LIKE ?
                        OR KM.MAKM LIKE ? OR KM.TENKM LIKE ?
                        OR EXISTS (
                            SELECT 1
                            FROM dbo.CHI_TIET_HOA_DON CT_SEARCH
                            INNER JOIN dbo.SAN_PHAM SP_SEARCH
                                ON SP_SEARCH.MASP = CT_SEARCH.MASP
                            WHERE CT_SEARCH.MAHD = HD.MAHD
                              AND (CT_SEARCH.MASP LIKE ? OR SP_SEARCH.TENSP LIKE ?)
                        )
                    )
                """
                params.extend([like] * 9)
            sql += """
                GROUP BY HD.MAHD, HD.NGAYLAP, HD.MANV, NV.TENNV,
                         HD.MACA, C.SOCA, HD.TIENKHACHDUA, HD.TRANGTHAI,
                         KM.TYLEGIAM
                ORDER BY HD.NGAYLAP DESC, HD.MAHD DESC
            """
            cursor.execute(sql, *params)
            return [tuple(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_invoice_detail(self, invoice_code):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    HD.MAHD, HD.NGAYLAP, HD.TIENKHACHDUA,
                    HD.TRANGTHAI, HD.MANV, NV.TENNV, NV.VAITRO,
                    HD.MACA, C.SOCA, C.NGAYLAM, C.TGMO, C.TGDONG,
                    HD.MAKM, KM.TENKM, KM.TYLEGIAM
                FROM dbo.HOA_DON HD
                LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = HD.MANV
                LEFT JOIN dbo.CA_LAM_VIEC C ON C.MACA = HD.MACA
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.MAHD = ?
            """, invoice_code)
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Không tìm thấy hóa đơn.")
            header = dict(zip(
                ("mahd", "ngaylap", "cash", "status", "manv", "tennv", "vaitro",
                 "maca", "soca", "ngaylam", "tgmo", "tgdong", "makm", "tenkm",
                 "discount_rate"),
                row,
            ))
            cursor.execute("""
                SELECT CT.MASP, SP.TENSP, SP.DVT,
                       CT.DONGIA, CT.SOLUONG, CT.VAT
                FROM dbo.CHI_TIET_HOA_DON CT
                LEFT JOIN dbo.SAN_PHAM SP ON SP.MASP = CT.MASP
                WHERE CT.MAHD = ?
                ORDER BY CT.MASP
            """, invoice_code)
            items = []
            for item in cursor.fetchall():
                items.append({
                    "masp": item[0],
                    "tensp": item[1] or "(Sản phẩm đã ngừng lưu thông)",
                    "dvt": item[2],
                    "price": item[3],
                    "quantity": item[4],
                    "vat": item[5],
                })
            return {"header": header, "items": items}
        finally:
            cursor.close()

    @staticmethod
    def assert_cart_prices_unchanged(cursor, cart, promotion_code, expected_discount_rate):
        """Đối chiếu giá/VAT và chụp giá vốn bình quân trong lúc đang khóa sản phẩm."""
        cost_snapshots = {}
        for product_code, item in cart.items():
            cursor.execute("""
                SELECT GIABAN, VAT, GIANHAP
                FROM dbo.SAN_PHAM WITH (UPDLOCK, HOLDLOCK)
                WHERE MASP = ? AND ISNULL(IS_DELETED, 0) = 0
            """, product_code)
            current = cursor.fetchone()
            if current is None:
                raise RuntimeError(
                    f"Sản phẩm {product_code} đã bị xóa hoặc ngừng kinh doanh."
                )
            if (
                Decimal(str(current[0])) != Decimal(str(item["price"]))
                or Decimal(str(current[1])) != Decimal(str(item["vat"]))
            ):
                raise RuntimeError(
                    f"Giá bán hoặc VAT của sản phẩm {product_code} đã thay đổi trong lúc lập hóa đơn."
                )

            cost = Decimal(str(current[2] or 0))
            if not cost.is_finite() or cost < 0:
                raise RuntimeError(
                    f"Giá vốn bình quân của sản phẩm {product_code} không hợp lệ."
                )
            cost_snapshots[product_code] = cost

        if promotion_code:
            cursor.execute("""
                SELECT TYLEGIAM
                FROM dbo.CHUONG_TRINH_KM WITH (UPDLOCK, HOLDLOCK)
                WHERE MAKM = ?
                  AND NGAYBD <= SYSDATETIME()
                  AND NGAYKT >= SYSDATETIME()
                  AND ISNULL(IS_DELETED, 0) = 0
            """, promotion_code)
            promotion = cursor.fetchone()
            if (
                promotion is None
                or Decimal(str(promotion[0])) != Decimal(str(expected_discount_rate))
            ):
                raise RuntimeError(
                    "Chương trình khuyến mãi đã hết hạn hoặc thay đổi tỷ lệ giảm. Hãy tải lại biểu mẫu trước khi thanh toán."
                )
        return cost_snapshots

    @staticmethod
    def assert_active_shift(cursor, employee, shift):
        """Kiểm tra lại ca từ SQL Server bên trong transaction."""
        employee_code = (employee or {}).get("manv")
        shift_code = (shift or {}).get("maca")
        if not employee_code or shift_code is None:
            raise RuntimeError("Không xác định được nhân viên hoặc ca làm việc hiện tại.")
        cursor.execute("""
            SELECT TOP (1) C.MACA
            FROM dbo.NHAN_VIEN NV WITH (UPDLOCK, HOLDLOCK)
            INNER JOIN dbo.LAMCA L WITH (UPDLOCK, HOLDLOCK) ON L.MANV = NV.MANV
            INNER JOIN dbo.CA_LAM_VIEC C WITH (UPDLOCK, HOLDLOCK) ON C.MACA = L.MACA
            WHERE NV.MANV = ? AND C.MACA = ?
              AND CAST(C.NGAYLAM AS date) = CAST(SYSDATETIME() AS date)
              AND CAST(SYSDATETIME() AS time) >= C.TGMO
              AND CAST(SYSDATETIME() AS time) < C.TGDONG
              AND C.TMCUOICA IS NULL
        """, employee_code, shift_code)
        if cursor.fetchone() is None:
            raise RuntimeError(
                "Ca làm việc của bạn đã kết thúc, đã được chốt hoặc không còn đăng ký hiệu lực. Hóa đơn chưa được lưu."
            )

    @staticmethod
    def assert_no_return_vouchers(has_return_vouchers):
        if has_return_vouchers:
            raise RuntimeError(
                "Không thể hủy hóa đơn đã phát sinh phiếu đổi trả. Hãy xử lý chứng từ đổi trả trước."
            )

    @staticmethod
    def _next_invoice_code(cursor):
        cursor.execute("""
            SELECT COALESCE(
                MAX(TRY_CONVERT(BIGINT, SUBSTRING(MAHD, 3, 18))), 0
            )
            FROM dbo.HOA_DON WITH (TABLOCKX, HOLDLOCK)
            WHERE UPPER(LEFT(MAHD, 2)) = 'HD'
              AND TRY_CONVERT(BIGINT, SUBSTRING(MAHD, 3, 18)) IS NOT NULL
        """)
        code = f"HD{int(cursor.fetchone()[0] or 0) + 1:06d}"
        if len(code) > 20:
            raise ValueError("Đã vượt giới hạn độ dài mã hóa đơn.")
        return code

    def create_invoice(self, payload, is_admin=False):
        """Ghi hóa đơn/chi tiết và trừ tồn kho trong một transaction."""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            employee = payload["employee"]
            shift = payload.get("active_shift")
            if not is_admin:
                self.assert_active_shift(cursor, employee, shift)

            cost_snapshots = self.assert_cart_prices_unchanged(
                cursor,
                payload["cart"],
                payload.get("promotion_code"),
                payload["discount_rate"],
            )

            invoice_code = self._next_invoice_code(cursor)
            cursor.execute("""
                INSERT INTO dbo.HOA_DON
                    (MAHD, NGAYLAP, TIENKHACHDUA, TRANGTHAI, MANV, MAKM, MACA)
                VALUES (?, SYSDATETIME(), ?, 1, ?, ?, ?)
            """, invoice_code, payload["cash"], employee.get("manv"),
                 payload.get("promotion_code"),
                 shift["maca"] if shift else None)

            for product_code, item in payload["cart"].items():
                cursor.execute("""
                    UPDATE dbo.SAN_PHAM
                    SET SLTON = SLTON - ?
                    WHERE MASP = ?
                      AND ISNULL(IS_DELETED, 0) = 0
                      AND ISNULL(SLTON, 0) >= ?
                """, item["quantity"], product_code, item["quantity"])
                if cursor.rowcount != 1:
                    raise RuntimeError(
                        f"Sản phẩm {product_code} không còn đủ tồn kho. Hóa đơn chưa được lưu."
                    )
                cursor.execute("""
                    INSERT INTO dbo.CHI_TIET_HOA_DON
                        (MAHD, MASP, DONGIA, SOLUONG, VAT, GIAVON)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, invoice_code, product_code, item["price"],
                     item["quantity"], item["vat"], cost_snapshots[product_code])

            conn.commit()
            return invoice_code
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def cancel_invoice(self, invoice_code, username, role, is_admin=False):
        """Hủy hóa đơn, từ chối nếu đã đổi trả và hoàn kho nguyên tử."""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            # Không tin role/is_admin do UI truyền lên; xác thực principal SQL thực.
            cursor.execute("""
                SELECT CASE
                    WHEN USER_NAME() = N'admin' THEN 1
                    WHEN IS_ROLEMEMBER(N'rl_QuanLy') = 1
                     AND EXISTS (
                         SELECT 1 FROM dbo.NHAN_VIEN
                         WHERE MANV = USER_NAME()
                           AND MANV = ? AND VAITRO = N'Quản lý'
                     )
                    THEN 1 ELSE 0
                END
            """, str(username or "").strip())
            permission = cursor.fetchone()
            if permission is None or int(permission[0] or 0) != 1:
                raise PermissionError("Chỉ Quản lý/Admin được hủy hóa đơn.")

            cursor.execute("""
                SELECT TRANGTHAI
                FROM dbo.HOA_DON WITH (UPDLOCK, HOLDLOCK)
                WHERE MAHD = ?
            """, invoice_code)
            invoice = cursor.fetchone()
            if invoice is None:
                raise LookupError("Không tìm thấy hóa đơn cần hủy.")
            if invoice[0] is None or int(invoice[0]) != 1:
                raise ValueError("Hóa đơn đã bị hủy hoặc không còn ở trạng thái có hiệu lực.")

            cursor.execute("""
                SELECT TOP (1) MAHD
                FROM dbo.PHIEU_DOI_TRA WITH (UPDLOCK, HOLDLOCK)
                WHERE MAHD = ?
            """, invoice_code)
            self.assert_no_return_vouchers(cursor.fetchone() is not None)

            cursor.execute("""
                SELECT MASP, SUM(ISNULL(SOLUONG, 0))
                FROM dbo.CHI_TIET_HOA_DON WITH (UPDLOCK, HOLDLOCK)
                WHERE MAHD = ?
                GROUP BY MASP
            """, invoice_code)
            items = cursor.fetchall()
            if not items:
                raise ValueError("Hóa đơn không có chi tiết sản phẩm nên không thể hoàn kho.")

            for item in items:
                product_code = str(item[0])
                quantity = int(item[1] or 0)
                if quantity <= 0:
                    raise ValueError(f"Số lượng hoàn kho không hợp lệ cho sản phẩm {product_code}.")
                # Hủy hóa đơn có thể hoàn hàng về sản phẩm đã xóa mềm.
                # Khôi phục trạng thái hoạt động và cộng tồn trong cùng transaction.
                if not restore_and_activate_product(cursor, product_code, quantity):
                    raise LookupError(
                        f"Không tìm thấy sản phẩm {product_code}; thao tác hủy đã được hoàn tác."
                    )

            cursor.execute("""
                UPDATE dbo.HOA_DON SET TRANGTHAI = 0
                WHERE MAHD = ? AND TRANGTHAI = 1
            """, invoice_code)
            if cursor.rowcount != 1:
                raise RuntimeError("Không thể cập nhật trạng thái hóa đơn.")
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
