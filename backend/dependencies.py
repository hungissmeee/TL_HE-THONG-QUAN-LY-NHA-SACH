"""Dependency quản lý vòng đời kết nối SQL Server cho từng request."""

import logging
from collections.abc import Generator

from fastapi import HTTPException, status

from backend.config import ConfigurationError, load_settings
from backend.database import DatabaseUnavailableError, create_connection

logger = logging.getLogger(__name__)


def get_db_connection() -> Generator:
    """Mở kết nối khi request cần DB và luôn rollback/đóng sau khi xử lý."""
    try:
        settings = load_settings()
        connection = create_connection(settings)
    except (ConfigurationError, DatabaseUnavailableError):
        logger.exception("Backend database connection is unavailable.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dịch vụ cơ sở dữ liệu hiện không khả dụng.",
        ) from None

    try:
        yield connection
    finally:
        try:
            connection.rollback()
        except Exception:
            logger.warning("Could not rollback request-scoped DB connection.")
        try:
            connection.close()
        except Exception:
            logger.warning("Could not close request-scoped DB connection.")
