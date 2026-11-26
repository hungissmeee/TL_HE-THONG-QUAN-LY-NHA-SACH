"""Các hàm dùng chung bên trong nhóm màn hình phiếu nhập."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

MONEY_QUANT = Decimal("0.01")

from giao_dien.dinh_dang import (
    format_decimal_money as money,
    to_import_decimal as as_decimal,
    format_import_date as date_text,
)
