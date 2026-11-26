"""Các thành phần kết nối và cấu hình cơ sở dữ liệu SQL Server."""

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


class Database:

    """Quản lý kết nối SQL Server, tài khoản đăng nhập và phân quyền nhân viên."""
    def __init__(self):
        self.conn = None
        self.username = None

        self.server = r"localhost"
        self.database = "CSDLQLNHASACH"
        self.driver = "ODBC Driver 18 for SQL Server"

    def _connection_string(self, username, password):

        return (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"UID={{{username}}};"
            f"PWD={{{password}}};"
            "Encrypt=yes;"
            "TrustServerCertificate=yes;"
        )

    def connect(self, username, password):

        self.close()

        self.conn = pyodbc.connect(
            self._connection_string(username, password),
            timeout=5
        )

        self.username = username

        return self.conn

    def get_connection(self):
        return self.conn

    def change_password(self, old_password, new_password):

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

        if (self.username or "").lower() != "admin":
            raise PermissionError(
                "Chỉ tài khoản admin được thực hiện chức năng này!"
            )

        if self.conn is None:
            raise Exception("Chưa kết nối database!")

    def _quote_login(self, manv):

        return "[" + manv.replace("]", "]]") + "]"

    # =====================================
    # TẠO TÀI KHOẢN NHÂN VIÊN
    # =====================================

    def create_account(
            self, manv, tennv, vaitro, sdt, password
    ):

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
                DEFAULT_DATABASE = [CSDLQLNHASACH];
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

        self._check_admin()

        cursor = self.conn.cursor()

        try:
            # Lấy thông tin nhân viên và kiểm tra Database User
            cursor.execute("""
                           SELECT NV.MANV,
                                  NV.TENNV,
                                  NV.VAITRO,
                                  NV.SDT,

                                  CASE
                                      WHEN EXISTS (SELECT 1
                                                   FROM sys.database_principals DP
                                                   WHERE LOWER(DP.name) = LOWER(NV.MANV)
                                                     AND DP.type = 'S')
                                          THEN 1
                                      ELSE 0
                                      END AS ACCOUNT_EXISTS

                           FROM dbo.NHAN_VIEN NV
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
                "account_exists": bool(employee[4])
            }

        finally:
            cursor.close()

    # =====================================
    # CẬP NHẬT VAI TRÒ NHÂN VIÊN
    # =====================================

    def update_employee_permissions(self, manv, vaitro):

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

            # Các role cũ và role tùy chỉnh cần loại bỏ
            old_roles = list(self.ROLE_MAP.values()) + [
                "db_datareader",
                "db_datawriter",
                "db_owner",
                "db_ddladmin",
                "db_securityadmin",
                "db_accessadmin",
                "db_backupoperator",
                "db_denydatareader",
                "db_denydatawriter"
            ]

            for role in old_roles:

                cursor.execute("""
                               SELECT 1
                               FROM sys.database_role_members DRM
                                        JOIN sys.database_principals R
                                             ON R.principal_id = DRM.role_principal_id
                                        JOIN sys.database_principals U
                                             ON U.principal_id = DRM.member_principal_id
                               WHERE U.name = ?
                                 AND R.name = ?
                               """, manv, role)

                if cursor.fetchone():
                    cursor.execute(
                        f"ALTER ROLE [{role}] "
                        f"DROP MEMBER {member}"
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
    # XÓA TÀI KHOẢN NHÂN VIÊN
    # =====================================

    def delete_employee_account(self, manv):

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

        if self.conn is not None:
            self.conn.close()
            self.conn = None

        self.username = None