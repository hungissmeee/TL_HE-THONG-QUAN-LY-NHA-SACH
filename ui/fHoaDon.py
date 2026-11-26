"""Tương thích ngược cho các import hóa đơn cũ.

Mã giao diện được chia thành các module nhỏ trong :mod:`ui.invoices`.
"""

from ui.invoices.common import (
    MONEY_QUANT,
    money,
    as_decimal,
    date_text,
    time_text,
)
from ui.invoices import (
    CreateInvoiceDialog,
    InvoiceDetailDialog,
    InvoiceWindow,
)

__all__ = [
    "MONEY_QUANT",
    "money",
    "as_decimal",
    "date_text",
    "time_text",
    "CreateInvoiceDialog",
    "InvoiceDetailDialog",
    "InvoiceWindow",
]
