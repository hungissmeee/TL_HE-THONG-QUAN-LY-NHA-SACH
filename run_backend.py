"""Launcher khởi động Backend Web bằng cấu hình trong file .env.

Chạy từ thư mục gốc dự án:
    python run_backend.py

Các tuỳ chọn host, port và reload được đọc từ BOOKHUB_WEB_* trong .env.
"""

import os
from dataclasses import dataclass

from backend.config import ConfigurationError, load_settings


@dataclass(frozen=True)
class ServerOptions:
    host: str
    port: int
    reload: bool
    log_level: str


def _read_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().casefold()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} phải là true hoặc false.")


def load_server_options() -> ServerOptions:
    """Đọc cấu hình .env và kiểm tra host/port/reload trước khi chạy."""
    app_settings = load_settings()

    host = os.getenv("BOOKHUB_WEB_HOST", "127.0.0.1").strip()
    if not host:
        raise ConfigurationError("BOOKHUB_WEB_HOST không được để trống.")

    raw_port = os.getenv("BOOKHUB_WEB_PORT", "8000").strip()
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ConfigurationError("BOOKHUB_WEB_PORT phải là số nguyên.") from exc
    if not 1 <= port <= 65535:
        raise ConfigurationError("BOOKHUB_WEB_PORT phải nằm trong khoảng 1–65535.")

    default_reload = app_settings.environment == "development"
    reload_enabled = _read_bool("BOOKHUB_WEB_RELOAD", default_reload)
    if app_settings.environment == "production" and reload_enabled:
        raise ConfigurationError(
            "Không bật BOOKHUB_WEB_RELOAD trong môi trường production."
        )

    log_level = os.getenv("BOOKHUB_WEB_LOG_LEVEL", "info").strip().lower()
    if log_level not in {"critical", "error", "warning", "info", "debug", "trace"}:
        raise ConfigurationError(
            "BOOKHUB_WEB_LOG_LEVEL phải là critical/error/warning/info/debug/trace."
        )

    return ServerOptions(
        host=host,
        port=port,
        reload=reload_enabled,
        log_level=log_level,
    )


def main() -> None:
    try:
        options = load_server_options()
    except (ConfigurationError, ValueError) as exc:
        raise SystemExit(f"[BookHub] Cấu hình Backend không hợp lệ: {exc}") from exc

    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "[BookHub] Chưa cài dependencies. Hãy chạy: pip install -r requirements.txt"
        ) from exc

    print("[BookHub] Đang khởi động Backend Web...")
    print(f"[BookHub] Host: {options.host}")
    print(f"[BookHub] Port: {options.port}")
    print(f"[BookHub] Reload: {'bật' if options.reload else 'tắt'}")
    print(f"[BookHub] API: http://127.0.0.1:{options.port}")
    if options.host == "0.0.0.0":
        print("[BookHub] Đang lắng nghe trên mọi giao diện mạng (LAN).")
    if options.reload:
        print("[BookHub] Chế độ phát triển: tự khởi động lại khi code thay đổi.")

    uvicorn.run(
        "backend.main:app",
        host=options.host,
        port=options.port,
        reload=options.reload,
        log_level=options.log_level,
    )


if __name__ == "__main__":
    main()
