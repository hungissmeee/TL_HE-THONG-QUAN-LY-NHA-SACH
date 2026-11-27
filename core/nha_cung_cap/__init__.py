"""Phân hệ nha cung cap: xử lý dữ liệu và truy vấn SQL."""
from .truy_van_sql import NhaCungCapRepository
from .xu_ly_du_lieu import NhaCungCapService

__all__ = ["NhaCungCapRepository", "NhaCungCapService"]
