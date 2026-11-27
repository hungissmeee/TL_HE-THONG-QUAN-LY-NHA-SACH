"""Repository SQL cho phân hệ nhà cung cấp."""

from core.sql_support import resolve_connection


class NhaCungCapRepository:
    """Truy cập dữ liệu nhà cung cấp; không phụ thuộc giao diện Desktop."""

    def __init__(self, connection_source):
        self.connection_source = connection_source

    def get_employee_role(self, username):
        if (username or "").strip().casefold() == "admin":
            return "Quản lý"
        if not (username or "").strip():
            return ""
        conn = resolve_connection(self.connection_source)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT VAITRO FROM dbo.NHAN_VIEN WHERE MANV = ?",
                username.strip()
            )
            row = cursor.fetchone()
            return str(row[0] or "") if row else ""
        finally:
            cursor.close()

    def list_suppliers(self, keyword="", show_inactive=False):
        """Lấy danh sách theo từ khóa và tùy chọn hiển thị nhà cung cấp ngừng hoạt động."""
        conn = resolve_connection(self.connection_source)
        cursor = conn.cursor()
        try:
            sql = """
                SELECT MANCC, TENNCC, SDT, DIACHI, MST, ISNULL(IS_DELETED, 0)
                FROM dbo.NHA_CUNG_CAP
                WHERE 1 = 1
            """
            params = []
            if not show_inactive:
                sql += " AND ISNULL(IS_DELETED, 0) = 0"
            keyword = str(keyword or "").strip()
            if keyword:
                like = f"%{keyword}%"
                sql += """
                    AND (
                        MANCC LIKE ? OR TENNCC LIKE ? OR SDT LIKE ?
                        OR DIACHI LIKE ? OR MST LIKE ?
                    )
                """
                params.extend([like] * 5)
            sql += """
                ORDER BY
                    CASE WHEN ISNULL(IS_DELETED, 0) = 0 THEN 0 ELSE 1 END,
                    TENNCC, MANCC
            """
            cursor.execute(sql, *params)
            return [tuple(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_supplier(self, supplier_code):
        conn = resolve_connection(self.connection_source)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT MANCC, TENNCC, SDT, DIACHI, MST, ISNULL(IS_DELETED, 0)
                FROM dbo.NHA_CUNG_CAP
                WHERE MANCC = ?
            """, supplier_code)
            row = cursor.fetchone()
            return tuple(row) if row else None
        finally:
            cursor.close()

    @staticmethod
    def _next_code(cursor, lock_table=False):
        """Sinh mã NCC tăng dần, kể cả bản ghi đã ngừng hoạt động."""
        hint = " WITH (TABLOCKX, HOLDLOCK)" if lock_table else ""
        cursor.execute(f"""
            SELECT COALESCE(
                MAX(TRY_CONVERT(BIGINT, SUBSTRING(MANCC, 4, 17))), 0
            )
            FROM dbo.NHA_CUNG_CAP{hint}
            WHERE UPPER(LEFT(MANCC, 3)) = 'NCC'
              AND TRY_CONVERT(BIGINT, SUBSTRING(MANCC, 4, 17)) IS NOT NULL
        """)
        code = f"NCC{int(cursor.fetchone()[0] or 0) + 1:03d}"
        if len(code) > 20:
            raise ValueError("Mã nhà cung cấp đã vượt quá 20 ký tự.")
        return code

    def preview_next_code(self):
        conn = resolve_connection(self.connection_source)
        cursor = conn.cursor()
        try:
            code = self._next_code(cursor)
            conn.commit()
            return code
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def save_supplier(self, data, supplier_code=None):
        """Thêm/cập nhật nhà cung cấp trong transaction."""
        conn = resolve_connection(self.connection_source)
        cursor = conn.cursor()
        try:
            if supplier_code:
                code = str(supplier_code).strip()
                cursor.execute("""
                    UPDATE dbo.NHA_CUNG_CAP
                    SET TENNCC = ?, SDT = ?, DIACHI = ?, MST = ?
                    WHERE MANCC = ? AND ISNULL(IS_DELETED, 0) = 0
                """, data["name"], data["phone"], data["address"], data["tax"], code)
                if cursor.rowcount != 1:
                    raise LookupError(
                        "Nhà cung cấp không tồn tại hoặc đã ngừng hoạt động."
                    )
            else:
                code = self._next_code(cursor, lock_table=True)
                cursor.execute("""
                    INSERT INTO dbo.NHA_CUNG_CAP
                        (MANCC, TENNCC, SDT, DIACHI, MST, IS_DELETED)
                    VALUES (?, ?, ?, ?, ?, 0)
                """, code, data["name"], data["phone"], data["address"], data["tax"])
            conn.commit()
            return code
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def set_supplier_status(self, supplier_code, inactive):
        """Bật/tắt trạng thái bằng cập nhật có điều kiện để tránh ghi đè trạng thái mới."""
        conn = resolve_connection(self.connection_source)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE dbo.NHA_CUNG_CAP
                SET IS_DELETED = ?
                WHERE MANCC = ? AND ISNULL(IS_DELETED, 0) = ?
            """, 1 if inactive else 0, supplier_code, 0 if inactive else 1)
            changed = cursor.rowcount == 1
            if not changed:
                conn.rollback()
                return False
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
