"""Tạo kết nối SQL Server riêng cho mỗi request Backend."""

import pyodbc

from backend.config import ConfigurationError, Settings


class DatabaseUnavailableError(RuntimeError):
    """Không thể tạo kết nối SQL Server bằng cấu hình Backend hiện tại."""


def _odbc_value(value: str) -> str:
    """Bao giá trị ODBC và escape dấu ngoặc nhọn đóng."""
    return "{" + str(value).replace("}", "}}") + "}"


def build_connection_string(settings: Settings) -> str:
    """Tạo chuỗi kết nối từ tài khoản dịch vụ, không dùng mật khẩu nhân viên."""
    if not settings.database_configured:
        raise ConfigurationError(
            "Thiếu cấu hình tài khoản SQL Server dành riêng cho Backend."
        )
    return (
        f"DRIVER={_odbc_value(settings.sql_driver)};"
        f"SERVER={_odbc_value(settings.sql_server)};"
        f"DATABASE={_odbc_value(settings.sql_database)};"
        f"UID={_odbc_value(settings.sql_username)};"
        f"PWD={_odbc_value(settings.sql_password)};"
        f"Encrypt={'yes' if settings.sql_encrypt else 'no'};"
        f"TrustServerCertificate={'yes' if settings.sql_trust_server_certificate else 'no'};"
        f"Connection Timeout={settings.sql_timeout_seconds};"
    )


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
