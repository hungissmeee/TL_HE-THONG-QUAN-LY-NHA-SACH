"""Phân hệ khuyen mai: xử lý dữ liệu và truy vấn SQL."""
from .truy_van_sql import KhuyenMaiRepository
from .xu_ly_du_lieu import KhuyenMaiService

__all__ = ["KhuyenMaiRepository", "KhuyenMaiService"]
