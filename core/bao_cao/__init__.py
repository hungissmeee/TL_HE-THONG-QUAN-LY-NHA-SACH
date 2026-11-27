"""Phân hệ bao cao: xử lý dữ liệu và truy vấn SQL."""
from .truy_van_sql import BaoCaoRepository
from .xu_ly_du_lieu import BaoCaoService

__all__ = ["BaoCaoRepository", "BaoCaoService"]
