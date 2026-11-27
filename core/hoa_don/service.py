"""Service nghiệp vụ hóa đơn bán hàng dùng chung cho Desktop và Backend."""

from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_UP

from core.hoa_don.repository import HoaDonRepository


MONEY_QUANT = Decimal("0.01")


class HoaDonService:
    def __init__(self, repository):
        if not isinstance(repository, HoaDonRepository):
            raise TypeError("repository phải là HoaDonRepository.")
        self.repository = repository

    @staticmethod
    def _decimal(value, field, allow_zero=True):
        try:
            result = Decimal(str(value))
        except (TypeError, ValueError, InvalidOperation):
            raise ValueError(f"{field} phải là số hợp lệ.")
        if not result.is_finite() or result < 0 or (not allow_zero and result == 0):
            raise ValueError(f"{field} không hợp lệ.")
        return result

    def get_employee_and_active_shift(self, username, is_admin=False):
        return self.repository.get_employee_and_active_shift(username, is_admin)

    def get_employee_role(self, username):
        return self.repository.get_employee_role(username)

    def list_active_promotions(self):
        return self.repository.list_active_promotions()

    def list_available_products(self):
        return self.repository.list_available_products()

    def list_invoices(self, start_date, end_date, keyword=""):
        if str(start_date) > str(end_date):
            raise ValueError("Ngày bắt đầu không được lớn hơn ngày kết thúc.")
        return self.repository.list_invoices(start_date, end_date, keyword)

    def get_invoice_detail(self, invoice_code):
        code = str(invoice_code or "").strip()
        if not code:
            raise ValueError("Mã hóa đơn không hợp lệ.")
        return self.repository.get_invoice_detail(code)

    @staticmethod
    def allocate_invoice_discount(cart, discount):
        """Phân bổ tiền giảm cấp hóa đơn về từng dòng, bảo đảm tổng khớp tuyệt đối."""
        discount = Decimal(str(discount)).quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP
        )
        line_amounts = {
            code: (item["price"] * item["quantity"]).quantize(
                MONEY_QUANT, rounding=ROUND_HALF_UP
            )
            for code, item in cart.items()
        }
        subtotal = sum(line_amounts.values(), Decimal("0.00"))
        if not line_amounts or subtotal <= 0 or discount == 0:
            return {
                code: {
                    "line_total": amount,
                    "line_discount": Decimal("0.00"),
                    "line_total_after_discount": amount,
                }
                for code, amount in line_amounts.items()
            }

        raw_shares = {
            code: discount * amount / subtotal
            for code, amount in line_amounts.items()
        }
        allocated = {
            code: raw.quantize(MONEY_QUANT, rounding=ROUND_DOWN)
            for code, raw in raw_shares.items()
        }
        remaining_cents = int(
            (discount - sum(allocated.values(), Decimal("0.00"))) / MONEY_QUANT
        )
        ranked_codes = sorted(
            line_amounts,
            key=lambda code: (
                -(raw_shares[code] - allocated[code]),
                str(code).casefold(),
            ),
        )
        for code in ranked_codes[:remaining_cents]:
            allocated[code] += MONEY_QUANT

        return {
            code: {
                "line_total": line_amounts[code],
                "line_discount": allocated[code],
                "line_total_after_discount": (
                    line_amounts[code] - allocated[code]
                ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP),
            }
            for code in line_amounts
        }

    def create_invoice(self, data, is_admin=False):
        data = dict(data or {})
        employee = dict(data.get("employee") or {})
        shift = data.get("active_shift")
        if not employee.get("manv") and not is_admin:
            raise ValueError("Không xác định được nhân viên lập hóa đơn.")
        if not is_admin and not (shift and shift.get("maca") is not None):
            raise PermissionError("Nhân viên chưa có ca làm việc hợp lệ.")

        source_cart = data.get("cart") or {}
        if not source_cart:
            raise ValueError("Hóa đơn chưa có sản phẩm.")
        cart = {}
        subtotal = Decimal("0.00")
        for raw_code, source in source_cart.items():
            code = str(raw_code or "").strip()
            if not code:
                raise ValueError("Có sản phẩm không có mã hợp lệ.")
            item = dict(source or {})
            try:
                quantity = int(item.get("quantity"))
            except (TypeError, ValueError):
                raise ValueError(f"Số lượng của sản phẩm {code} không hợp lệ.")
            if quantity <= 0:
                raise ValueError(f"Số lượng của sản phẩm {code} phải lớn hơn 0.")
            price = self._decimal(item.get("price"), f"Đơn giá {code}", allow_zero=False)
            vat = self._decimal(item.get("vat"), f"VAT {code}")
            if vat > 100:
                raise ValueError(f"VAT của sản phẩm {code} không được vượt quá 100%.")
            stock = item.get("stock")
            if stock is not None and quantity > int(stock):
                raise ValueError(f"Sản phẩm {code} không đủ tồn kho.")
            price = price.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            vat = vat.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            subtotal += price * quantity
            cart[code] = {
                "quantity": quantity, "price": price, "vat": vat,
            }

        promotion_code = str(data.get("promotion_code") or "").strip() or None
        discount_rate = self._decimal(data.get("discount_rate", 0), "Tỷ lệ giảm")
        if discount_rate > 100:
            raise ValueError("Tỷ lệ giảm không được vượt quá 100%.")
        if not promotion_code and discount_rate != 0:
            raise ValueError("Không thể áp dụng giảm giá khi chưa chọn khuyến mãi.")
        discount_rate = discount_rate.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        subtotal = subtotal.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        discount = (subtotal * discount_rate / Decimal("100")).quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP
        )
        allocated = self.allocate_invoice_discount(cart, discount)
        for code, amounts in allocated.items():
            cart[code].update(amounts)
        total = sum(
            (item["line_total_after_discount"] for item in cart.values()),
            Decimal("0.00"),
        ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        if total != (subtotal - discount).quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP
        ):
            raise RuntimeError("Phân bổ khuyến mãi không khớp tổng tiền hóa đơn.")
        cash = self._decimal(data.get("cash"), "Tiền khách đưa").quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP
        )
        if cash < total:
            raise ValueError(
                f"Khách cần trả {total} nhưng mới đưa {cash}; chưa đủ tiền thanh toán."
            )
        payload = {
            "employee": employee,
            "active_shift": dict(shift) if shift else None,
            "cart": cart,
            "promotion_code": promotion_code,
            "discount_rate": discount_rate,
            "cash": cash,
            "subtotal": subtotal,
            "discount": discount,
            "total": total,
            "change": (cash - total).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP),
        }
        return self.repository.create_invoice(payload, is_admin=is_admin)

    def cancel_invoice(self, invoice_code, username, role, is_admin=False):
        code = str(invoice_code or "").strip()
        if not code:
            raise ValueError("Mã hóa đơn không hợp lệ.")
        return self.repository.cancel_invoice(code, username, role, is_admin)
