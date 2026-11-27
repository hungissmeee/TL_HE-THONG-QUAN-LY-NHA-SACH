"""Xác thực nhân viên bằng chính SQL Server Login của Desktop."""

from dataclasses import dataclass

import pyodbc

from backend.config import Settings
from backend.database import AuthenticationRejectedError, create_employee_auth_connection

ROLE_CHECKS = (
    ("admin", "Quản trị hệ thống", "IS_MEMBER(N'db_owner')"),
    ("rl_QuanLy", "Quản lý", "IS_ROLEMEMBER(N'rl_QuanLy')"),
    ("rl_ThuNgan", "Thu ngân", "IS_ROLEMEMBER(N'rl_ThuNgan')"),
    ("rl_NhanVienKho", "Nhân viên kho", "IS_ROLEMEMBER(N'rl_NhanVienKho')"),
    ("rl_KeToan", "Kế toán", "IS_ROLEMEMBER(N'rl_KeToan')"),
)


@dataclass(frozen=True)
class AuthenticatedEmployee:
    employee_code: str
    full_name: str
    role: str
    role_code: str
    phone: str | None


def authenticate_employee(settings: Settings, username: str, password: str) -> AuthenticatedEmployee:
    """Mở kết nối SQL tạm bằng credentials nhân viên và đọc role SQL hiện tại."""
    connection = create_employee_auth_connection(settings, username, password)
    cursor = None
    try:
        cursor = connection.cursor()
        role_sql = ", ".join(
            f"{expression} AS role_{index}"
            for index, (_code, _label, expression) in enumerate(ROLE_CHECKS)
        )
        cursor.execute(
            f"""
            SELECT NV.MANV, NV.TENNV, NV.VAITRO, NV.SDT, {role_sql}
            FROM dbo.NHAN_VIEN AS NV
            WHERE LOWER(NV.MANV) = LOWER(?)
            """,
            username,
        )
        row = cursor.fetchone()
        if row is None:
            raise AuthenticationRejectedError("Không tìm thấy hồ sơ nhân viên.")

        role = None
        role_code = None
        for index, (code, label, _expression) in enumerate(ROLE_CHECKS, start=4):
            if row[index] == 1:
                role_code = code
                role = label
                break

        if not role or not role_code:
            raise AuthenticationRejectedError("Tài khoản chưa được cấp vai trò hợp lệ.")

        return AuthenticatedEmployee(
            employee_code=str(row[0]),
            full_name=str(row[1] or ""),
            role=role,
            role_code=role_code,
            phone=str(row[3]) if row[3] is not None else None,
        )
    except AuthenticationRejectedError:
        raise
    except pyodbc.Error as exc:
        # Lỗi truy vấn sau khi xác thực thành công không được xem là sai mật khẩu.
        raise RuntimeError("Không thể kiểm tra hồ sơ và vai trò nhân viên.") from exc
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        try:
            connection.rollback()
        except Exception:
            pass
        try:
            connection.close()
        except Exception:
            pass
