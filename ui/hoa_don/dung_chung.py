"""Các hàm dùng chung bên trong nhóm màn hình hóa đơn."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

MONEY_QUANT = Decimal("0.01")

from ui.dinh_dang import (
    format_decimal_money as money,
    to_invoice_decimal as as_decimal,
    format_invoice_date as date_text,
    format_time as time_text,
)
