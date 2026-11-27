"""Phân hệ nhan vien: xử lý dữ liệu và truy vấn SQL."""
from .truy_van_sql import NhanVienRepository
from .xu_ly_du_lieu import NhanVienService

__all__ = ["NhanVienRepository", "NhanVienService"]
