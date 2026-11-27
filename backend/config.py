"""Cấu hình Backend lấy từ biến môi trường, không chứa bí mật trong mã nguồn."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"


class ConfigurationError(ValueError):
    """Cấu hình môi trường thiếu hoặc không hợp lệ."""


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().casefold()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"Biến môi trường {name} phải là true/false.")


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"Biến môi trường {name} phải là số nguyên.") from exc
    if not minimum <= value <= maximum:
        raise ConfigurationError(
            f"Biến môi trường {name} phải nằm trong khoảng {minimum}–{maximum}."
        )
    return value


@dataclass(frozen=True)
class Settings:
    app_name: str
    environment: str
    api_prefix: str
    allowed_origins: tuple[str, ...]
    docs_enabled: bool
    sql_server: str
    sql_database: str
    sql_driver: str
    sql_username: str = ""
    sql_password: str = field(default="", repr=False)
    sql_encrypt: bool = True
    sql_trust_server_certificate: bool = False
    sql_timeout_seconds: int = 5
    jwt_secret: str = field(default="", repr=False)
    access_token_minutes: int = 30

    @property
    def database_configured(self) -> bool:
        return bool(
            self.sql_server.strip()
            and self.sql_database.strip()
            and self.sql_driver.strip()
            and self.sql_username.strip()
            and self.sql_password
        )


def load_settings() -> Settings:
    """Tự nạp .env tại thư mục gốc rồi kiểm tra cấu hình Backend."""
    # Biến môi trường đã có từ hệ điều hành/CI được ưu tiên hơn nội dung .env.
    load_dotenv(dotenv_path=ENV_FILE, override=False)

    environment = os.getenv("BOOKHUB_WEB_ENV", "development").strip().casefold()
    if environment not in {"development", "test", "production"}:
        raise ConfigurationError(
            "BOOKHUB_WEB_ENV chỉ nhận development, test hoặc production."
        )

    prefix = os.getenv("BOOKHUB_WEB_API_PREFIX", "/api/v1").strip()
    if not prefix.startswith("/") or prefix == "/" or prefix.endswith("/"):
        raise ConfigurationError(
            "BOOKHUB_WEB_API_PREFIX phải có dạng /api/v1 và không có dấu / cuối."
        )

    origin_raw = os.getenv(
        "BOOKHUB_WEB_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    origins = tuple(
        origin.strip().rstrip("/")
        for origin in origin_raw.split(",")
        if origin.strip()
    )
    if not origins:
        raise ConfigurationError("Phải cấu hình ít nhất một Web origin được phép.")
    if "*" in origins and environment == "production":
        raise ConfigurationError("Không được dùng CORS wildcard trong production.")

    encrypt_raw = os.getenv("BOOKHUB_WEB_SQL_ENCRYPT", "yes").strip().casefold()
    if encrypt_raw not in {"yes", "no", "true", "false", "1", "0"}:
        raise ConfigurationError("BOOKHUB_WEB_SQL_ENCRYPT phải là yes hoặc no.")

    return Settings(
        app_name=os.getenv("BOOKHUB_WEB_APP_NAME", "BookHub API").strip(),
        environment=environment,
        api_prefix=prefix,
        allowed_origins=origins,
        docs_enabled=_env_bool("BOOKHUB_WEB_DOCS_ENABLED", environment != "production"),
        sql_server=os.getenv("BOOKHUB_WEB_SQL_SERVER", "").strip(),
        sql_database=os.getenv("BOOKHUB_WEB_SQL_DATABASE", "").strip(),
        sql_driver=os.getenv("BOOKHUB_WEB_SQL_DRIVER", "ODBC Driver 18 for SQL Server").strip(),
        sql_username=os.getenv("BOOKHUB_WEB_SQL_USERNAME", "").strip(),
        sql_password=os.getenv("BOOKHUB_WEB_SQL_PASSWORD", ""),
        sql_encrypt=encrypt_raw in {"yes", "true", "1"},
        sql_trust_server_certificate=_env_bool(
            "BOOKHUB_WEB_SQL_TRUST_SERVER_CERTIFICATE", False
        ),
        sql_timeout_seconds=_env_int(
            "BOOKHUB_WEB_SQL_TIMEOUT_SECONDS", 5, 1, 30
        ),
        jwt_secret=os.getenv("BOOKHUB_WEB_JWT_SECRET", ""),
        access_token_minutes=_env_int(
            "BOOKHUB_WEB_ACCESS_TOKEN_MINUTES", 30, 5, 1440
        ),
    )
