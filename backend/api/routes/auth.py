"""API đăng nhập và thông tin nhân viên đang đăng nhập."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.authentication import authenticate_employee
from backend.config import ConfigurationError, load_settings
from backend.database import AuthenticationRejectedError, DatabaseUnavailableError
from backend.security import CurrentUser, create_access_token, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=20)
    password: str = Field(min_length=1, max_length=256)


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


@router.get("/me", response_model=EmployeeSummary, summary="Thông tin phiên hiện tại")
def get_me(current_user: CurrentUser = Depends(get_current_user)):
    """Trả về danh tính đã được xác minh trong access token."""
    return EmployeeSummary(
        employee_code=current_user.employee_code,
        full_name=current_user.full_name,
        role=current_user.role,
        role_code=current_user.role_code,
    )
