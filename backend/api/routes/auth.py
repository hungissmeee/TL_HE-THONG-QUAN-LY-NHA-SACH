"""API đăng nhập và thông tin nhân viên đang đăng nhập."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.authentication import (
    PasswordPolicyError,
    authenticate_employee,
    change_employee_password,
)
from backend.config import ConfigurationError, load_settings
from backend.database import AuthenticationRejectedError, DatabaseUnavailableError
from backend.security import CurrentUser, create_access_token, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=20)
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class EmployeeSummary(BaseModel):
    employee_code: str
    full_name: str
    role: str
    role_code: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: EmployeeSummary


@router.post("/login", response_model=LoginResponse, summary="Đăng nhập nhân viên")
def login(data: LoginRequest):
    """Xác thực SQL Server Login của nhân viên và trả JWT access token."""
    username = data.username.strip()
    if not username or not data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không đúng.",
        )

    try:
        settings = load_settings()
        employee = authenticate_employee(settings, username, data.password)
        current_user = CurrentUser(
            employee_code=employee.employee_code,
            full_name=employee.full_name,
            role=employee.role,
            role_code=employee.role_code,
        )
        token, expires_in = create_access_token(current_user)
    except AuthenticationRejectedError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không đúng, hoặc tài khoản chưa được phân quyền.",
        ) from None
    except ConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dịch vụ xác thực chưa được cấu hình.",
        ) from None
    except DatabaseUnavailableError:
        logger.exception("SQL Server is unavailable during employee sign-in.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể kết nối dịch vụ cơ sở dữ liệu.",
        ) from None
    except RuntimeError:
        logger.exception("Employee authentication query failed.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể xác minh tài khoản vào lúc này.",
        ) from None

    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=EmployeeSummary(
            employee_code=current_user.employee_code,
            full_name=current_user.full_name,
            role=current_user.role,
            role_code=current_user.role_code,
        ),
    )


@router.post("/change-password", summary="Đổi mật khẩu SQL Server")
def change_password(
    data: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Cho nhân viên tự đổi mật khẩu SQL Login bằng mật khẩu hiện tại."""
    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu mới phải khác mật khẩu hiện tại.",
        )

    try:
        settings = load_settings()
        change_employee_password(
            settings,
            current_user.employee_code,
            data.current_password,
            data.new_password,
        )
    except AuthenticationRejectedError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu hiện tại không đúng.",
        ) from None
    except PasswordPolicyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from None
    except ConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dịch vụ đổi mật khẩu chưa được cấu hình.",
        ) from None
    except DatabaseUnavailableError:
        logger.error("SQL Server is unavailable during employee password change.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể kết nối dịch vụ cơ sở dữ liệu.",
        ) from None
    except RuntimeError:
        # Không ghi câu lệnh SQL hoặc thông tin xác thực vào log.
        logger.error(
            "Employee SQL Server password change failed for %s.",
            current_user.employee_code,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể đổi mật khẩu lúc này. Vui lòng liên hệ quản trị viên.",
        ) from None

    return {"message": "Đổi mật khẩu thành công."}


@router.get("/me", response_model=EmployeeSummary, summary="Thông tin phiên hiện tại")
def get_me(current_user: CurrentUser = Depends(get_current_user)):
    """Trả về danh tính đã được xác minh trong access token."""
    return EmployeeSummary(
        employee_code=current_user.employee_code,
        full_name=current_user.full_name,
        role=current_user.role,
        role_code=current_user.role_code,
    )
