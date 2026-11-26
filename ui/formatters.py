"""Các hàm định dạng và chuyển đổi dữ liệu dùng chung trong Hệ thống quản lý nhà sách."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

MONEY_QUANT = Decimal("0.01")
ZERO_MONEY = Decimal("0.00")


def _quantize_money(value, default=None):
    """Chuyển giá trị thành Decimal hai chữ số; giữ nguyên lỗi nếu không có mặc định."""
    try:
        return Decimal(str(value or 0)).quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP
        )
    except (InvalidOperation, ValueError, TypeError):
        if default is None:
            raise
        return default


def format_decimal_money(value):
    """Định dạng số tiền với dấu phân cách kiểu Việt Nam, không kèm đơn vị."""
    amount = _quantize_money(value, default=ZERO_MONEY)
    return (
        f"{amount:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def to_invoice_decimal(value):
    """Chuyển đổi tiền của hóa đơn; giá trị không hợp lệ được báo lỗi như trước."""
    return _quantize_money(value)


def to_import_decimal(value):
    """Chuyển đổi tiền của phiếu nhập; giá trị không hợp lệ trở thành 0 như trước."""
    return _quantize_money(value, default=ZERO_MONEY)


def format_invoice_date(value):
    """Định dạng ngày/giờ trên hóa đơn theo quy tắc hiện tại."""
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        if hasattr(value, "hour"):
            return value.strftime("%d/%m/%Y %H:%M:%S")
        return value.strftime("%d/%m/%Y")
    return str(value)


def format_import_date(value):
    """Định dạng ngày trên phiếu nhập theo quy tắc hiện tại."""
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y %H:%M:%S")
    return str(value)


def format_time(value):
    if value is None:
        return ""
    return value.strftime("%H:%M") if hasattr(value, "strftime") else str(value)[:5]


def format_report_money(value, decimals=0):
    """Định dạng tiền dùng trong báo cáo, có hậu tố đồng."""
    amount = _quantize_money(value, default=ZERO_MONEY)
    if decimals <= 0:
        return f"{amount:,.0f} đ".replace(",", ".")
    return (
        f"{amount:,.{decimals}f} đ"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def format_number(value):
    try:
        return f"{int(value or 0):,}".replace(",", ".")
    except (ValueError, TypeError):
        return "0"


def format_report_date(value, include_time=True):
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        date_format = "%d/%m/%Y %H:%M" if include_time else "%d/%m/%Y"
        return value.strftime(date_format)
    return str(value)


def format_product_number(value):
    if value is None:
        return ""
    try:
        amount = Decimal(str(value))
        return (
            f"{amount:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
    except Exception:
        return str(value)
