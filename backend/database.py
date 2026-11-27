"""Tạo kết nối SQL Server riêng cho mỗi request Backend."""

import pyodbc

from backend.config import ConfigurationError, Settings


class DatabaseUnavailableError(RuntimeError):
    """Không thể tạo kết nối SQL Server bằng cấu hình Backend hiện tại."""


class AuthenticationRejectedError(RuntimeError):
    """SQL Server từ chối thông tin đăng nhập hoặc tài khoản không hợp lệ."""


def _odbc_value(value: str) -> str:
    """Bao giá trị ODBC và escape dấu ngoặc nhọn đóng."""
    return "{" + str(value).replace("}", "}}") + "}"


def _build_connection_string(settings: Settings, username: str, password: str) -> str:
    """Tạo chuỗi ODBC cho một principal SQL Server cụ thể."""
    if not settings.sql_server.strip() or not settings.sql_database.strip() or not settings.sql_driver.strip():
        raise ConfigurationError("Thiếu cấu hình máy chủ SQL Server dành cho Backend.")
    return (
        f"DRIVER={_odbc_value(settings.sql_driver)};"
        f"SERVER={_odbc_value(settings.sql_server)};"
        f"DATABASE={_odbc_value(settings.sql_database)};"
        f"UID={_odbc_value(username)};"
        f"PWD={_odbc_value(password)};"
        f"Encrypt={'yes' if settings.sql_encrypt else 'no'};"
        f"TrustServerCertificate={'yes' if settings.sql_trust_server_certificate else 'no'};"
        f"Connection Timeout={settings.sql_timeout_seconds};"
    )


def build_connection_string(settings: Settings) -> str:
    """Tạo chuỗi kết nối từ tài khoản dịch vụ, không dùng mật khẩu nhân viên."""
    if not settings.database_configured:
        raise ConfigurationError(
            "Thiếu cấu hình tài khoản SQL Server dành riêng cho Backend."
        )
    return _build_connection_string(
        settings, settings.sql_username, settings.sql_password
    )


def _is_sql_login_rejection(error: pyodbc.Error) -> bool:
    """Nhận diện lỗi thông tin đăng nhập bị SQL Server từ chối."""
    message = " ".join(str(part) for part in error.args).casefold()
    return any(code in message for code in ("28000", "18456", "18452", "18470"))


def create_employee_auth_connection(settings: Settings, username: str, password: str):
    """Mở kết nối tạm bằng SQL Login nhân viên để xác thực danh tính."""
    try:
        connection_string = _build_connection_string(settings, username, password)
        return pyodbc.connect(
            connection_string,
            timeout=settings.sql_timeout_seconds,
            autocommit=False,
        )
    except ConfigurationError:
        raise
    except pyodbc.Error as exc:
        if _is_sql_login_rejection(exc):
            raise AuthenticationRejectedError(
                "SQL Server rejected the employee credentials."
            ) from None
        raise DatabaseUnavailableError(
            "Không thể kết nối SQL Server trong bước xác thực."
        ) from exc

def create_connection(settings: Settings):
    """Mở kết nối SQL Server; lỗi chi tiết chỉ được ghi ở log phía máy chủ."""
    try:
        connection_string = build_connection_string(settings)
        return pyodbc.connect(
            connection_string,
            timeout=settings.sql_timeout_seconds,
            autocommit=False,
        )
    except ConfigurationError:
        raise
    except (pyodbc.Error, OSError) as exc:
        raise DatabaseUnavailableError(
            "Không thể kết nối SQL Server từ Backend."
        ) from exc
