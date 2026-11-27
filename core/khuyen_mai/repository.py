"""Repository SQL cho chương trình khuyến mãi."""

from datetime import datetime
from decimal import Decimal

from core.sql_support import resolve_connection


class KhuyenMaiRepository:
    """Đọc và ghi chương trình khuyến mãi."""

    def __init__(self, connection_source):
        self.connection_source = connection_source

    def _connection(self):
        return resolve_connection(self.connection_source)

    def get_employee_role(self, username):
        if str(username or "").strip().casefold() == "admin":
            return "Quản lý"
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT VAITRO FROM dbo.NHAN_VIEN WHERE MANV = ?",
                str(username or "").strip(),
            )
            row = cursor.fetchone()
            return str(row[0] or "").strip() if row else ""
        finally:
            cursor.close()

    @staticmethod
    def _require_manager(cursor):
        """Kiểm tra quyền ở database, không dựa vào trạng thái nút UI."""
        cursor.execute("""
            SELECT CASE
                WHEN USER_NAME() = N'admin'
                  OR IS_ROLEMEMBER(N'rl_QuanLy') = 1
                THEN 1 ELSE 0
            END
        """)
        row = cursor.fetchone()
        if row is None or int(row[0] or 0) != 1:
            raise PermissionError(
                "Chỉ tài khoản Admin/Quản lý được quản lý chương trình khuyến mãi."
            )

    def list_promotions(self, keyword="", show_deleted=False):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            sql = """
                SELECT
                    MAKM, TENKM, TYLEGIAM, NGAYBD, NGAYKT,
                    ISNULL(IS_DELETED, 0) AS IS_DELETED,
                    CASE
                        WHEN ISNULL(IS_DELETED, 0) = 1 THEN N'Đã xóa'
                        WHEN NGAYBD > SYSDATETIME() THEN N'Sắp diễn ra'
                        WHEN NGAYKT < SYSDATETIME() THEN N'Đã kết thúc'
                        ELSE N'Đang áp dụng'
                    END AS TRANGTHAI
                FROM dbo.CHUONG_TRINH_KM
                WHERE 1 = 1
            """
            params = []
            if not show_deleted:
                sql += " AND ISNULL(IS_DELETED, 0) = 0"
            keyword = str(keyword or "").strip()
            if keyword:
                like = f"%{keyword}%"
                sql += " AND (MAKM LIKE ? OR TENKM LIKE ?)"
                params.extend([like, like])
            sql += """
                ORDER BY
                    CASE WHEN ISNULL(IS_DELETED, 0) = 0 THEN 0 ELSE 1 END,
                    NGAYBD DESC, MAKM DESC
            """
            cursor.execute(sql, *params)
            return [tuple(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_promotion(self, promotion_code):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT MAKM, TENKM, TYLEGIAM, NGAYBD, NGAYKT,
                       ISNULL(IS_DELETED, 0),
                       CASE
                           WHEN ISNULL(IS_DELETED, 0) = 1 THEN N'Đã xóa'
                           WHEN NGAYBD > SYSDATETIME() THEN N'Sắp diễn ra'
                           WHEN NGAYKT < SYSDATETIME() THEN N'Đã kết thúc'
                           ELSE N'Đang áp dụng'
                       END
                FROM dbo.CHUONG_TRINH_KM
                WHERE MAKM = ?
            """, promotion_code)
            row = cursor.fetchone()
            return tuple(row) if row else None
        finally:
            cursor.close()

    @staticmethod
    def _next_code(cursor):
        cursor.execute("""
            SELECT COALESCE(
                MAX(TRY_CONVERT(BIGINT, SUBSTRING(MAKM, 3, 18))), 0
            )
            FROM dbo.CHUONG_TRINH_KM WITH (TABLOCKX, HOLDLOCK)
            WHERE UPPER(LEFT(MAKM, 2)) = 'KM'
              AND TRY_CONVERT(BIGINT, SUBSTRING(MAKM, 3, 18)) IS NOT NULL
        """)
        last_number = int(cursor.fetchone()[0] or 0)
        code = f"KM{last_number + 1:06d}"
        if len(code) > 20:
            raise ValueError("Mã khuyến mãi vượt quá 20 ký tự.")
        return code

    def preview_next_code(self):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            self._require_manager(cursor)
            code = self._next_code(cursor)
            conn.commit()
            return code
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def create_promotion(self, data):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            self._require_manager(cursor)
            code = self._next_code(cursor)
            cursor.execute("""
                INSERT INTO dbo.CHUONG_TRINH_KM
                    (MAKM, TENKM, TYLEGIAM, NGAYBD, NGAYKT, IS_DELETED)
                VALUES (?, ?, ?, ?, ?, 0)
            """, code, data["name"], data["discount_rate"],
                 data["start_at"], data["end_at"])
            conn.commit()
            return code
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def rename_promotion(self, promotion_code, name):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            self._require_manager(cursor)
            cursor.execute("""
                UPDATE dbo.CHUONG_TRINH_KM
                SET TENKM = ?
                OUTPUT inserted.MAKM
                WHERE MAKM = ? AND ISNULL(IS_DELETED, 0) = 0
            """, name, promotion_code)
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Khuyến mãi không tồn tại hoặc đã bị xóa.")
            conn.commit()
            return str(row[0])
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def soft_delete_promotion(self, promotion_code):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            self._require_manager(cursor)
            cursor.execute("""
                UPDATE dbo.CHUONG_TRINH_KM
                SET IS_DELETED = 1
                OUTPUT inserted.MAKM
                WHERE MAKM = ? AND ISNULL(IS_DELETED, 0) = 0
            """, promotion_code)
            row = cursor.fetchone()
            if row is None:
                raise LookupError(
                    "Khuyến mãi không tồn tại hoặc đã được ngừng áp dụng."
                )
            conn.commit()
            return str(row[0])
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
