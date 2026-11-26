"""Các hàm định dạng dùng chung cho chức năng đổi trả."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

MONEY_QUANT = Decimal("0.01")


def as_decimal(value):
    """Chuyển dữ liệu SQL hoặc chuỗi thành Decimal an toàn."""
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")


def money(value):
    """Định dạng số tiền theo quy ước Việt Nam."""
    number = as_decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    return f"{number:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def date_text(value):
    """Định dạng ngày giờ lấy từ SQL Server."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return str(value)
