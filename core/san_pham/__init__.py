"""Phân hệ san pham: xử lý dữ liệu và truy vấn SQL."""
from .truy_van_sql import SanPhamRepository
from .xu_ly_du_lieu import SanPhamService

__all__ = ["SanPhamRepository", "SanPhamService"]
