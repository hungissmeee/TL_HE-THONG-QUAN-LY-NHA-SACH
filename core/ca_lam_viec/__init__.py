"""Phân hệ ca lam viec: xử lý dữ liệu và truy vấn SQL."""
from .repository import CaLamViecRepository
from .service import CaLamViecService

__all__ = ["CaLamViecRepository", "CaLamViecService"]
