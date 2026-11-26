"""Các thành phần kết nối và cấu hình cơ sở dữ liệu SQL Server."""

import os

import pyodbc


_ROLE_MAP = {
    "Quản lý": "rl_QuanLy",
    "Thu ngân": "rl_ThuNgan",
    "Nhân viên kho": "rl_NhanVienKho",
    "Kế toán": "rl_KeToan",
}
_ROLE_DISPLAY_MAP = {
    sql_role: display_role
    for display_role, sql_role in _ROLE_MAP.items()
}

DB_NAME = "CSDLTEST"

class Database:

    """Quản lý kết nối SQL Server và các thao tác tài khoản, vai trò nhân viên."""
    def __init__(self):
        """Khởi tạo trạng thái kết nối và cấu hình SQL Server của ứng dụng."""
        self.conn = None
        self.username = None

        # Cấu hình có thể thay đổi theo máy triển khai mà không sửa mã nguồn.
        self.server = os.getenv("BOOKHUB_SQL_SERVER", r"localhost\MSSQLSERVER01")
        self.database = os.getenv("BOOKHUB_SQL_DATABASE", DB_NAME)
        self.driver = os.getenv(
            "BOOKHUB_SQL_DRIVER", "ODBC Driver 18 for SQL Server"
        )
        self.encrypt = os.getenv("BOOKHUB_SQL_ENCRYPT", "yes")
        self.trust_server_certificate = os.getenv(
            "BOOKHUB_TRUST_SERVER_CERTIFICATE", "yes"
        )

    @staticmethod
    def _odbc_value(value):
        """Bao giá trị theo cú pháp ODBC, kể cả khi chứa dấu ngoặc nhọn đóng."""
        return "{" + str(value).replace("}", "}}") + "}"

    def _connection_string(self, username, password):
        """Tạo chuỗi kết nối SQL Server từ cấu hình môi trường và thông tin đăng nhập."""
        return (
            f"DRIVER={self._odbc_value(self.driver)};"
            f"SERVER={self._odbc_value(self.server)};"
            f"DATABASE={self._odbc_value(self.database)};"
            f"UID={self._odbc_value(username)};"
            f"PWD={self._odbc_value(password)};"
            f"Encrypt={self.encrypt};"
            f"TrustServerCertificate={self.trust_server_certificate};"
        )

    def connect(self, username, password):
        """Mở kết nối SQL Server bằng thông tin đăng nhập của nhân viên."""

        self.close()

        self.conn = pyodbc.connect(
            self._connection_string(username, password),
            timeout=5
        )

        self.username = username

        return self.conn

    def get_connection(self):
        """Trả về kết nối hiện tại để các màn hình thực hiện truy vấn."""
        return self.conn

    def change_password(self, old_password, new_password):
        """Xác thực mật khẩu cũ và yêu cầu SQL Server đổi sang mật khẩu mới."""

        if not self.username:
            raise Exception("Chưa xác định tài khoản đăng nhập!")

        temp_conn = None

        try:
            # Tạo kết nối tạm thời bằng mật khẩu hiện tại
            temp_conn = pyodbc.connect(
                self._connection_string(
                    self.username,
                    old_password
                ),
                timeout=5,
                autocommit=True
            )

            cursor = temp_conn.cursor()

            # Bảo vệ tên Login và các giá trị mật khẩu
            login = "[" + self.username.replace("]", "]]") + "]"
            old_pwd = "N'" + old_password.replace("'", "''") + "'"
            new_pwd = "N'" + new_password.replace("'", "''") + "'"

            # Đổi mật khẩu SQL Server
            sql = f"""
                ALTER LOGIN {login}
                WITH PASSWORD = {new_pwd}
                OLD_PASSWORD = {old_pwd};
            """

            cursor.execute(sql)
            cursor.close()

        finally:
            if temp_conn is not None:
                temp_conn.close()

    ROLE_MAP = _ROLE_MAP
    ROLE_DISPLAY_MAP = _ROLE_DISPLAY_MAP

    def _check_admin(self):
        """Đảm bảo thao tác quản trị tài khoản chỉ được thực hiện bởi admin đang kết nối."""

        if (self.username or "").lower() != "admin":
            raise PermissionError(
                "Chỉ tài khoản admin được thực hiện chức năng này!"
            )

        if self.conn is None:
            raise Exception("Chưa kết nối database!")

    def _quote_login(self, manv):
        """Thoát ký tự đặc biệt trong tên Login để tạo SQL identifier hợp lệ."""

        return "[" + manv.replace("]", "]]") + "]"

    # =====================================
    # TẠO TÀI KHOẢN NHÂN VIÊN
    # =====================================

    def create_account(
            self, manv, tennv, vaitro, sdt, password
    ):
        """Tạo SQL Login, Database User, gán role và thêm hoặc cập nhật hồ sơ nhân viên trong cùng giao dịch."""

        self._check_admin()

        if vaitro not in self.ROLE_MAP:
            raise ValueError("Vai trò không hợp lệ!")

        cursor = self.conn.cursor()

        login = self._quote_login(manv)
        safe_password = password.replace("'", "''")
        sql_role = self.ROLE_MAP[vaitro]

        try:

            # Kiểm tra Login đã tồn tại
            cursor.execute("""
                           SELECT 1
                           FROM sys.server_principals
                           WHERE name = ?
                           """, manv)

            if cursor.fetchone():
                raise Exception("Tài khoản SQL đã tồn tại!")

            # Kiểm tra User cũ
            cursor.execute("""
                           SELECT 1
                           FROM sys.database_principals
                           WHERE name = ?
                           """, manv)

            if cursor.fetchone():
                raise Exception(
                    "Database User đã tồn tại. "
                    "Cần kiểm tra tài khoản cũ!"
                )

            # Kiểm tra nhân viên có hồ sơ từ trước không
            cursor.execute("""
                           SELECT 1
                           FROM NHAN_VIEN
                           WHERE MANV = ?
                           """, manv)

            employee_exists = cursor.fetchone() is not None

            # Tạo SQL Login
            cursor.execute(f"""
                CREATE LOGIN {login}
                WITH PASSWORD = N'{safe_password}',
                CHECK_POLICY = ON,
                CHECK_EXPIRATION = OFF,
                DEFAULT_DATABASE = {DB_NAME};
            """)

            # Tạo Database User
            cursor.execute(f"""
                CREATE USER {login} FOR LOGIN {login};
            """)

            # Gán vai trò
            cursor.execute(f"""
                ALTER ROLE [{sql_role}]
                ADD MEMBER {login};
            """)

            # Thêm hoặc cập nhật thông tin nhân viên
            if employee_exists:

                cursor.execute("""
                               UPDATE NHAN_VIEN
                               SET TENNV  = ?,
                                   VAITRO = ?,
                                   SDT    = ?
                               WHERE MANV = ?
                               """, tennv, vaitro, sdt, manv)

            else:

                cursor.execute("""
                               INSERT INTO NHAN_VIEN
                                   (MANV, TENNV, VAITRO, SDT)
                               VALUES (?, ?, ?, ?)
                               """, manv, tennv, vaitro, sdt)

            self.conn.commit()

        except Exception:
            self.conn.rollback()
            raise

        finally:
            cursor.close()

    # =====================================
    # LẤY THÔNG TIN VÀ QUYỀN NHÂN VIÊN
    # =====================================

    def get_employee_permissions(self, manv):
        """Đọc hồ sơ nhân viên, kiểm tra tài khoản SQL và lấy role đang được gán."""

        self._check_admin()

        cursor = self.conn.cursor()

        try:
            # Đọc trạng thái SQL Login trực tiếp từ SQL Server.
            cursor.execute("""
                           SELECT NV.MANV,
                                  NV.TENNV,
                                  NV.VAITRO,
                                  NV.SDT,
                                  CASE
                                      WHEN SP.principal_id IS NOT NULL THEN 1
                                      ELSE 0
                                  END AS ACCOUNT_EXISTS,
                                  CASE
                                      WHEN SP.principal_id IS NOT NULL
                                           AND SP.is_disabled = 0 THEN 1
                                      ELSE 0
                                  END AS ACCOUNT_ENABLED
                           FROM dbo.NHAN_VIEN NV
                           LEFT JOIN sys.server_principals SP
                             ON LOWER(SP.name) = LOWER(NV.MANV)
                            AND SP.type = 'S'
                           WHERE NV.MANV = ?
                           """, manv)

            employee = cursor.fetchone()

            if employee is None:
                raise Exception("Không tìm thấy nhân viên!")

            # Lấy các quyền hiện tại
            cursor.execute("""
                           SELECT R.name
                           FROM sys.database_role_members DRM

                                    JOIN sys.database_principals R
                                         ON R.principal_id = DRM.role_principal_id

                                    JOIN sys.database_principals U
                                         ON U.principal_id = DRM.member_principal_id

                           WHERE LOWER(U.name) = LOWER(?)
                           """, manv)

            roles = {
                row[0]
                for row in cursor.fetchall()
            }

            # Xác định vai trò
            current_role = employee[2]

            for sql_role, display_role in self.ROLE_DISPLAY_MAP.items():
                if sql_role in roles:
                    current_role = display_role
                    break

            return {
                "manv": employee[0],
                "tennv": employee[1],
                "vaitro": current_role,
                "sdt": employee[3],
                "account_exists": bool(employee[4]),
                "account_enabled": bool(employee[5])
            }

        finally:
            cursor.close()

    # =====================================
    # CẬP NHẬT VAI TRÒ NHÂN VIÊN
    # =====================================

    def update_employee_permissions(self, manv, vaitro):
        """Gỡ các role cũ, gán role mới và cập nhật vai trò hiển thị trong hồ sơ nhân viên."""

        self._check_admin()

        if manv.lower() == "admin":
            raise PermissionError(
                "Không được thay đổi vai trò tài khoản admin!"
            )

        if vaitro not in self.ROLE_MAP:
            raise ValueError("Vai trò không hợp lệ!")

        cursor = self.conn.cursor()

        member = self._quote_login(manv)
        target_role = self.ROLE_MAP[vaitro]

        try:

            # Kiểm tra Database User
            cursor.execute("""
                           SELECT 1
                           FROM sys.database_principals
                           WHERE name = ?
                           """, manv)

            if not cursor.fetchone():
                raise Exception(
                    "Nhân viên chưa có tài khoản SQL Server!"
                )

            # Gỡ toàn bộ role hiện tại (kể cả role tùy chỉnh) để tránh
            # quyền cũ còn sót lại sau khi đổi chức vụ.
            cursor.execute("""
                SELECT R.name
                FROM sys.database_role_members DRM
                INNER JOIN sys.database_principals R
                    ON R.principal_id = DRM.role_principal_id
                INNER JOIN sys.database_principals U
                    ON U.principal_id = DRM.member_principal_id
                WHERE U.name = ?
                  AND R.name <> N'public'
            """, manv)
            old_roles = [row[0] for row in cursor.fetchall()]

            for role in old_roles:
                quoted_role = self._quote_login(role)
                cursor.execute(
                    f"ALTER ROLE {quoted_role} DROP MEMBER {member}"
                )

            # Gán role mới
            cursor.execute(f"""
                ALTER ROLE [{target_role}]
                ADD MEMBER {member};
            """)

            # Cập nhật chức vụ trong NHAN_VIEN
            cursor.execute("""
                           UPDATE NHAN_VIEN
                           SET VAITRO = ?
                           WHERE MANV = ?
                           """, vaitro, manv)

            self.conn.commit()

        except Exception:
            self.conn.rollback()
            raise

        finally:
            cursor.close()

    # =====================================
    # NGƯNG HOẠT ĐỘNG / KÍCH HOẠT TÀI KHOẢN
    # =====================================

    def set_employee_account_enabled(self, manv, enabled):
        """Bật hoặc vô hiệu hóa SQL Login của nhân viên, không xóa hồ sơ hay quyền."""

        self._check_admin()

        if not manv or manv.strip().lower() == "admin":
            raise PermissionError(
                "Không thể ngưng hoạt động hoặc thay đổi tài khoản admin!"
            )

        if not isinstance(enabled, bool):
            raise ValueError("Trạng thái tài khoản phải là True hoặc False!")

        cursor = self.conn.cursor()
        login = self._quote_login(manv)

        try:
            cursor.execute("""
                           SELECT is_disabled
                           FROM sys.server_principals
                           WHERE name = ?
                             AND type = 'S'
                           """, manv)

            account = cursor.fetchone()
            if account is None:
                raise Exception("Tài khoản SQL Server không tồn tại!")

            currently_enabled = not bool(account[0])
            if currently_enabled == enabled:
                return

            action = "ENABLE" if enabled else "DISABLE"
            cursor.execute(f"ALTER LOGIN {login} {action}")
            self.conn.commit()

        except Exception:
            self.conn.rollback()
            raise

        finally:
            cursor.close()

    # =====================================
    # XÓA TÀI KHOẢN NHÂN VIÊN
    # =====================================

    def delete_employee_account(self, manv):
        """Xóa Database User và SQL Login của nhân viên, không tự xóa hồ sơ nhân viên."""

        self._check_admin()

        if manv.lower() == "admin":
            raise PermissionError(
                "Không thể xóa tài khoản admin!"
            )

        cursor = self.conn.cursor()
        login = self._quote_login(manv)

        try:

            cursor.execute("""
                           SELECT 1
                           FROM sys.server_principals
                           WHERE name = ?
                             AND type = 'S'
                           """, manv)

            if not cursor.fetchone():
                raise Exception("Tài khoản SQL không tồn tại!")

            cursor.execute("""
                           SELECT 1
                           FROM sys.database_principals
                           WHERE name = ?
                           """, manv)

            if cursor.fetchone():
                cursor.execute(
                    f"DROP USER {login}"
                )

            # Xóa SQL Login
            cursor.execute(
                f"DROP LOGIN {login}"
            )

            self.conn.commit()

        except Exception:
            self.conn.rollback()
            raise

        finally:
            cursor.close()

    def close(self):
        """Đóng kết nối SQL Server hiện tại và xóa trạng thái tài khoản khỏi đối tượng."""

        if self.conn is not None:
            self.conn.close()
            self.conn = None

        self.username = None