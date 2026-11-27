"""Repository hồ sơ nhân viên và tài khoản SQL Server.

Các thao tác quản trị Login/User chỉ dành cho phiên Desktop đăng nhập bằng
tài khoản admin. Không expose trực tiếp các thao tác này thành API Web.
"""

from core.sql_support import resolve_connection


ROLE_MAP = {
    "Quản lý": "rl_QuanLy",
    "Thu ngân": "rl_ThuNgan",
    "Nhân viên kho": "rl_NhanVienKho",
    "Kế toán": "rl_KeToan",
}
ROLE_DISPLAY_MAP = {sql_role: display for display, sql_role in ROLE_MAP.items()}


class NhanVienRepository:
    """SQL access cho NHAN_VIEN và SQL Server Login/Database User."""

    def __init__(self, connection_source):
        self.connection_source = connection_source

    def _connection(self):
        return resolve_connection(self.connection_source)

    def _require_admin(self):
        username = str(getattr(self.connection_source, "username", "") or "")
        if username.strip().casefold() != "admin":
            raise PermissionError("Chỉ tài khoản admin được thực hiện chức năng này!")
        return self._connection()

    @staticmethod
    def quote_identifier(value):
        """Escape SQL Server identifier trước khi đưa vào DDL động."""
        return "[" + str(value).replace("]", "]]") + "]"

    @staticmethod
    def quote_literal(value):
        """Escape chuỗi literal T-SQL, dùng cho mật khẩu CREATE LOGIN."""
        return "N'" + str(value).replace("'", "''") + "'"

    @staticmethod
    def _next_employee_code(cursor, lock_table=False):
        """Sinh mã NV tăng dần từ mọi hồ sơ, kể cả hồ sơ không còn Login."""
        hint = " WITH (TABLOCKX, HOLDLOCK)" if lock_table else ""
        cursor.execute(f"""
            SELECT COALESCE(
                MAX(TRY_CONVERT(BIGINT, SUBSTRING(MANV, 3, 18))), 0
            )
            FROM dbo.NHAN_VIEN{hint}
            WHERE UPPER(LEFT(MANV, 2)) = 'NV'
              AND TRY_CONVERT(BIGINT, SUBSTRING(MANV, 3, 18)) IS NOT NULL
        """)
        last_number = int(cursor.fetchone()[0] or 0)
        code = f"NV{last_number + 1:03d}"
        if len(code) > 20:
            raise ValueError("Mã nhân viên vượt quá 20 ký tự.")
        return code

    def preview_next_employee_code(self):
        conn = self._require_admin()
        cursor = conn.cursor()
        try:
            code = self._next_employee_code(cursor)
            conn.commit()
            return code
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def list_employees(self, keyword=""):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            keyword = str(keyword or "").strip()
            pattern = f"%{keyword}%"
            cursor.execute("""
                SELECT MANV, TENNV, VAITRO, SDT
                FROM dbo.NHAN_VIEN
                WHERE MANV LIKE ? OR TENNV LIKE ?
                ORDER BY MANV
            """, pattern, pattern)
            return [tuple(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_employee(self, employee_code):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT MANV, TENNV, VAITRO, SDT
                FROM dbo.NHAN_VIEN
                WHERE MANV = ?
            """, employee_code)
            row = cursor.fetchone()
            return tuple(row) if row else None
        finally:
            cursor.close()

    def get_employee_permissions(self, employee_code):
        conn = self._require_admin()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT NV.MANV, NV.TENNV, NV.VAITRO, NV.SDT,
                       CASE WHEN SP.principal_id IS NOT NULL THEN 1 ELSE 0 END,
                       CASE WHEN SP.principal_id IS NOT NULL
                                  AND SP.is_disabled = 0 THEN 1 ELSE 0 END
                FROM dbo.NHAN_VIEN NV
                LEFT JOIN sys.server_principals SP
                  ON LOWER(SP.name) = LOWER(NV.MANV)
                 AND SP.type = 'S'
                WHERE NV.MANV = ?
            """, employee_code)
            employee = cursor.fetchone()
            if employee is None:
                raise LookupError("Không tìm thấy nhân viên.")

            cursor.execute("""
                SELECT R.name
                FROM sys.database_role_members DRM
                INNER JOIN sys.database_principals R
                    ON R.principal_id = DRM.role_principal_id
                INNER JOIN sys.database_principals U
                    ON U.principal_id = DRM.member_principal_id
                WHERE LOWER(U.name) = LOWER(?)
            """, employee_code)
            roles = {row[0] for row in cursor.fetchall()}

            current_role = employee[2]
            for sql_role, display_role in ROLE_DISPLAY_MAP.items():
                if sql_role in roles:
                    current_role = display_role
                    break

            return {
                "manv": employee[0],
                "tennv": employee[1],
                "vaitro": current_role,
                "sdt": employee[3],
                "account_exists": bool(employee[4]),
                "account_enabled": bool(employee[5]),
            }
        finally:
            cursor.close()

    def create_employee(self, data):
        """Sinh mã, tạo Login/User/role và lưu hồ sơ trong một transaction."""
        conn = self._require_admin()
        cursor = conn.cursor()
        try:
            employee_code = self._next_employee_code(cursor, lock_table=True)
            self._create_account_with_cursor(
                cursor,
                employee_code,
                data["name"],
                data["role"],
                data.get("phone"),
                data["password"],
            )
            conn.commit()
            return employee_code
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def create_account(self, employee_code, name, role, phone, password):
        """API tương thích với Database.create_account cũ."""
        conn = self._require_admin()
        cursor = conn.cursor()
        try:
            self._create_account_with_cursor(
                cursor, employee_code, name, role, phone, password
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def _create_account_with_cursor(self, cursor, employee_code, name, role, phone, password):
        if role not in ROLE_MAP:
            raise ValueError("Vai trò không hợp lệ!")
        code = str(employee_code or "").strip()
        if not code:
            raise ValueError("Mã nhân viên không hợp lệ.")
        if code.casefold() == "admin":
            raise PermissionError("Không thể tạo hoặc thay đổi hồ sơ tài khoản admin.")

        cursor.execute(
            "SELECT 1 FROM sys.server_principals WHERE name = ?",
            code,
        )
        if cursor.fetchone():
            raise ValueError("Tài khoản SQL đã tồn tại!")

        cursor.execute(
            "SELECT 1 FROM sys.database_principals WHERE name = ?",
            code,
        )
        if cursor.fetchone():
            raise ValueError("Database User đã tồn tại. Cần kiểm tra tài khoản cũ!")

        login = self.quote_identifier(code)
        password_literal = self.quote_literal(password)
        role_identifier = self.quote_identifier(ROLE_MAP[role])
        database_name = self.quote_identifier(
            getattr(self.connection_source, "database", "CSDLTEST")
        )

        cursor.execute(f"""
            CREATE LOGIN {login}
            WITH PASSWORD = {password_literal},
                 CHECK_POLICY = ON,
                 CHECK_EXPIRATION = OFF,
                 DEFAULT_DATABASE = {database_name};
        """)
        cursor.execute(f"CREATE USER {login} FOR LOGIN {login};")
        cursor.execute(f"ALTER ROLE {role_identifier} ADD MEMBER {login};")

        cursor.execute("""
            SELECT 1 FROM dbo.NHAN_VIEN WHERE MANV = ?
        """, code)
        if cursor.fetchone():
            cursor.execute("""
                UPDATE dbo.NHAN_VIEN
                SET TENNV = ?, VAITRO = ?, SDT = ?
                WHERE MANV = ?
            """, name, role, phone, code)
        else:
            cursor.execute("""
                INSERT INTO dbo.NHAN_VIEN (MANV, TENNV, VAITRO, SDT)
                VALUES (?, ?, ?, ?)
            """, code, name, role, phone)

    def update_employee_role(self, employee_code, role):
        conn = self._require_admin()
        code = str(employee_code or "").strip()
        if not code or code.casefold() == "admin":
            raise PermissionError("Không được thay đổi vai trò tài khoản admin!")
        if role not in ROLE_MAP:
            raise ValueError("Vai trò không hợp lệ!")

        cursor = conn.cursor()
        member = self.quote_identifier(code)
        target_role = self.quote_identifier(ROLE_MAP[role])
        try:
            cursor.execute("""
                SELECT 1 FROM sys.database_principals WHERE name = ?
            """, code)
            if not cursor.fetchone():
                raise LookupError("Nhân viên chưa có tài khoản SQL Server!")

            cursor.execute("""
                SELECT R.name
                FROM sys.database_role_members DRM
                INNER JOIN sys.database_principals R
                    ON R.principal_id = DRM.role_principal_id
                INNER JOIN sys.database_principals U
                    ON U.principal_id = DRM.member_principal_id
                WHERE U.name = ? AND R.name <> N'public'
            """, code)
            for row in cursor.fetchall():
                old_role = self.quote_identifier(row[0])
                cursor.execute(
                    f"ALTER ROLE {old_role} DROP MEMBER {member}"
                )

            cursor.execute(
                f"ALTER ROLE {target_role} ADD MEMBER {member}"
            )
            cursor.execute("""
                UPDATE dbo.NHAN_VIEN SET VAITRO = ? WHERE MANV = ?
            """, role, code)
            if cursor.rowcount != 1:
                raise LookupError("Không tìm thấy hồ sơ nhân viên để cập nhật vai trò.")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def set_account_enabled(self, employee_code, enabled):
        conn = self._require_admin()
        code = str(employee_code or "").strip()
        if not code or code.casefold() == "admin":
            raise PermissionError(
                "Không thể ngưng hoạt động hoặc thay đổi tài khoản admin!"
            )
        if not isinstance(enabled, bool):
            raise ValueError("Trạng thái tài khoản phải là True hoặc False!")

        cursor = conn.cursor()
        login = self.quote_identifier(code)
        try:
            cursor.execute("""
                SELECT is_disabled
                FROM sys.server_principals
                WHERE name = ? AND type = 'S'
            """, code)
            account = cursor.fetchone()
            if account is None:
                raise LookupError("Tài khoản SQL Server không tồn tại!")

            currently_enabled = not bool(account[0])
            if currently_enabled == enabled:
                return False

            action = "ENABLE" if enabled else "DISABLE"
            cursor.execute(f"ALTER LOGIN {login} {action}")
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def delete_account(self, employee_code):
        """Xóa SQL User/Login nhưng giữ lại hồ sơ và lịch sử nhân viên."""
        conn = self._require_admin()
        code = str(employee_code or "").strip()
        if not code or code.casefold() == "admin":
            raise PermissionError("Không thể xóa tài khoản admin!")

        cursor = conn.cursor()
        login = self.quote_identifier(code)
        try:
            cursor.execute("""
                SELECT 1 FROM sys.server_principals
                WHERE name = ? AND type = 'S'
            """, code)
            if not cursor.fetchone():
                raise LookupError("Tài khoản SQL không tồn tại!")

            cursor.execute("""
                SELECT 1 FROM sys.database_principals WHERE name = ?
            """, code)
            if cursor.fetchone():
                cursor.execute(f"DROP USER {login}")

            cursor.execute(f"DROP LOGIN {login}")
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
