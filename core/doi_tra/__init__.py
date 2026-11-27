"""Phân hệ doi tra: xử lý dữ liệu và truy vấn SQL."""
from .truy_van_sql import ReturnRepository
from .xu_ly_du_lieu import ReturnService

__all__ = ["ReturnRepository", "ReturnService"]
