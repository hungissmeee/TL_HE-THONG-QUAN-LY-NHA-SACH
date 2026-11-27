"""Tạo và xác minh JWT access token cho BookHub Web."""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from backend.config import ConfigurationError, load_settings

TOKEN_ISSUER = "bookhub-api"
TOKEN_AUDIENCE = "bookhub-web"
_bearer = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    employee_code: str
    full_name: str
    role: str
    role_code: str


def _get_token_secret() -> tuple[str, int]:
    settings = load_settings()
    if len(settings.jwt_secret) < 32:
        raise ConfigurationError(
            "BOOKHUB_WEB_JWT_SECRET chưa được cấu hình đủ mạnh (tối thiểu 32 ký tự)."
        )
    return settings.jwt_secret, settings.access_token_minutes


def create_access_token(user: CurrentUser) -> tuple[str, int]:
    """Phát hành JWT HS256 với thời hạn giới hạn."""
    secret, expires_minutes = _get_token_secret()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=expires_minutes)
    payload: dict[str, Any] = {
        "iss": TOKEN_ISSUER,
        "aud": TOKEN_AUDIENCE,
        "sub": user.employee_code,
        "manv": user.employee_code,
        "name": user.full_name,
        "role": user.role,
        "role_code": user.role_code,
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token, expires_minutes * 60


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    """Kiểm tra chữ ký, issuer, audience, hạn dùng và lấy danh tính từ token."""
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vui lòng đăng nhập để tiếp tục.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        secret, _expires_minutes = _get_token_secret()
    except ConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dịch vụ xác thực chưa được cấu hình.",
        ) from None

    try:
        payload = jwt.decode(
            credentials.credentials,
            secret,
            algorithms=["HS256"],
            issuer=TOKEN_ISSUER,
            audience=TOKEN_AUDIENCE,
            options={"require": ["exp", "iat", "sub", "manv", "role", "role_code"]},
        )
        return CurrentUser(
            employee_code=str(payload["manv"]),
            full_name=str(payload.get("name", "")),
            role=str(payload["role"]),
            role_code=str(payload["role_code"]),
        )
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

def require_roles(*allowed_role_codes: str):
    """Tạo dependency bảo vệ route theo role code; admin có toàn quyền."""
    allowed = frozenset(allowed_role_codes)
    if not allowed:
        raise ValueError("Phải chỉ định ít nhất một vai trò được phép.")

    def check_role(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role_code != "admin" and current_user.role_code not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thực hiện chức năng này.",
            )
        return current_user

    return check_role
