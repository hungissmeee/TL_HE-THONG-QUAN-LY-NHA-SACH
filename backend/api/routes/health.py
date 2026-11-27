"""Endpoint kiểm tra trạng thái sống và khả năng truy cập SQL Server."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from backend.dependencies import get_db_connection

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health/live", summary="Kiểm tra tiến trình API")
def live_check():
    """Cho biết tiến trình FastAPI đang hoạt động; không truy cập database."""
    return {"status": "ok"}


@router.get("/health/ready", summary="Kiểm tra khả năng phục vụ")
def ready_check(connection=Depends(get_db_connection)):
    """Chỉ báo ready khi Backend thực sự truy vấn được SQL Server."""
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        row = cursor.fetchone()
        if row is None or int(row[0]) != 1:
            raise RuntimeError("SQL Server readiness query returned no result.")
        return {"status": "ready", "database": "ok"}
    except Exception:
        logger.exception("Backend readiness query failed.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dịch vụ cơ sở dữ liệu hiện không khả dụng.",
        ) from None
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                logger.warning("Could not close health-check cursor.")
