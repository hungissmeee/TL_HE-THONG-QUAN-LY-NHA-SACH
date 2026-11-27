"""Các thành phần kết nối và cấu hình cơ sở dữ liệu SQL Server."""

import os

import pyodbc


DB_NAME = "CSDLTEST"

class Database:

    """Quản lý kết nối và phiên đăng nhập SQL Server của ứng dụng Desktop."""
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

    def close(self):
        """Đóng kết nối SQL Server hiện tại và xóa trạng thái tài khoản khỏi đối tượng."""

        if self.conn is not None:
            self.conn.close()
            self.conn = None

        self.username = None