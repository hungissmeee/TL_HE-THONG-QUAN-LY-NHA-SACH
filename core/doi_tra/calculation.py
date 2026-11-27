"""Tính tiền hoàn bằng chênh lệch tổng hóa đơn sau giảm giá."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


MONEY_QUANT = Decimal("0.01")
ONE_HUNDRED = Decimal("100")


def _decimal(value, field):
    try:
        result = Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation):
        raise ValueError(f"{field} không hợp lệ.")
    if not result.is_finite():
        raise ValueError(f"{field} không hợp lệ.")
    return result


def discounted_invoice_total(subtotal, discount_rate):
    """Áp dụng cùng quy tắc làm hóa đơn: làm tròn tiền giảm đến 2 số lẻ."""
    subtotal = _decimal(subtotal, "Tổng tiền hàng")
    discount_rate = _decimal(discount_rate, "Tỷ lệ giảm")

    if subtotal < 0:
        raise ValueError("Tổng tiền hàng không được âm.")
    if not Decimal("0") <= discount_rate <= ONE_HUNDRED:
        raise ValueError("Tỷ lệ giảm phải nằm trong khoảng 0 đến 100.")

    subtotal = subtotal.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    discount = (subtotal * discount_rate / ONE_HUNDRED).quantize(
        MONEY_QUANT, rounding=ROUND_HALF_UP
    )
    return (subtotal - discount).quantize(
        MONEY_QUANT, rounding=ROUND_HALF_UP
    )


def calculate_invoice_refund(invoice_items, selected_items, discount_rate):
    """Tính tiền hoàn bằng tổng hóa đơn trước trả trừ hóa đơn giả sau trả.

    'processed' bao gồm cả hàng đã hoàn tiền và hàng đã đổi. 'refunded' chỉ
    đếm các lượng đã hoàn tiền. Hàng đã đổi vẫn được tính trong hóa đơn giả
    vì khách đã nhận sản phẩm thay thế cùng mã.
    """
    invoice_by_code = {}
    subtotal_before = Decimal("0.00")

    for source in invoice_items or []:
        item = dict(source or {})
        code = str(item.get("product_code") or "").strip()
        if not code or code in invoice_by_code:
            raise ValueError("Danh sách sản phẩm hóa đơn không hợp lệ.")

        try:
            purchased = int(item.get("purchased"))
            processed = int(item.get("processed", 0) or 0)
            refunded = int(item.get("refunded", 0) or 0)
        except (TypeError, ValueError):
            raise ValueError(f"Số lượng của sản phẩm {code} không hợp lệ.")

        price = _decimal(
            item.get("original_price", item.get("price")),
            f"Đơn giá {code}",
        )
        if purchased <= 0 or processed < 0 or refunded < 0:
            raise ValueError(f"Số lượng của sản phẩm {code} không hợp lệ.")
        if processed > purchased or refunded > processed:
            raise ValueError(f"Lịch sử đổi trả của sản phẩm {code} không hợp lệ.")
        if price < 0:
            raise ValueError(f"Đơn giá của sản phẩm {code} không được âm.")

        price = price.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        invoice_by_code[code] = {
            "purchased": purchased,
            "processed": processed,
            "refunded": refunded,
            "available": purchased - processed,
            "price": price,
        }
        # Hàng đã đổi không bị trừ ở đây; chỉ hàng đã hoàn tiền bị loại.
        subtotal_before += price * (purchased - refunded)

    if not invoice_by_code:
        raise ValueError("Hóa đơn không có sản phẩm để tính tiền hoàn.")

    selected_codes = set()
    subtotal_removed = Decimal("0.00")

    for source in selected_items or []:
        item = dict(source or {})
        code = str(item.get("product_code") or "").strip()
        if not code or code not in invoice_by_code:
            raise ValueError(
                f"Sản phẩm {code or '(không rõ mã)'} không thuộc hóa đơn gốc."
            )
        if code in selected_codes:
            raise ValueError(f"Sản phẩm {code} bị chọn nhiều lần.")
        selected_codes.add(code)

        try:
            quantity = int(item.get("quantity"))
            action = int(item.get("action", 0))
        except (TypeError, ValueError):
            raise ValueError(
                f"Số lượng hoặc hình thức xử lý của {code} không hợp lệ."
            )
        if quantity <= 0:
            raise ValueError(f"Số lượng trả của sản phẩm {code} phải lớn hơn 0.")
        if action not in (0, 1):
            raise ValueError(f"Hình thức xử lý của sản phẩm {code} không hợp lệ.")

        invoice_line = invoice_by_code[code]
        if quantity > invoice_line["available"]:
            raise ValueError(
                f"Sản phẩm {code} chỉ còn {invoice_line['available']} sản phẩm có thể xử lý."
            )

        # action=0: hoàn tiền, loại khỏi hóa đơn giả.
        # action=1: đổi hàng cùng mã, khách vẫn giữ một sản phẩm nên không trừ.
        if action == 0:
            subtotal_removed += invoice_line["price"] * quantity

    subtotal_after = subtotal_before - subtotal_removed
    if subtotal_after < 0:
        raise ValueError("Giá trị hóa đơn sau khi trả hàng không hợp lệ.")

    before_total = discounted_invoice_total(subtotal_before, discount_rate)
    after_total = discounted_invoice_total(subtotal_after, discount_rate)
    total_refund = (before_total - after_total).quantize(
        MONEY_QUANT, rounding=ROUND_HALF_UP
    )
    if total_refund < 0:
        raise ValueError("Tiền hoàn tính được không hợp lệ.")

    return {
        "before_total": before_total,
        "after_total": after_total,
        "total_refund": total_refund,
    }
