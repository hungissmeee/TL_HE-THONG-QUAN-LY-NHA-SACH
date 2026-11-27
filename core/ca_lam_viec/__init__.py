"""Phân hệ ca lam viec: xử lý dữ liệu và truy vấn SQL."""
from .truy_van_sql import CaLamViecRepository
from .xu_ly_du_lieu import CaLamViecService

__all__ = ["CaLamViecRepository", "CaLamViecService"]
