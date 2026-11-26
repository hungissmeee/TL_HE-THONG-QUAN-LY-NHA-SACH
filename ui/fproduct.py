"""Tương thích ngược cho các import sản phẩm cũ.

Mã giao diện được chia thành các module nhỏ trong :mod:`ui.products`.
"""

from ui.products import (
    SearchableSingleSelect,
    SearchableMultiSelect,
    ProductDetailDialog,
    ProductFormDialog,
    ProductWindow,
)
from ui.formatters import format_product_number

__all__ = [
    "SearchableSingleSelect",
    "SearchableMultiSelect",
    "ProductDetailDialog",
    "ProductFormDialog",
    "ProductWindow",
    "format_product_number",
]
