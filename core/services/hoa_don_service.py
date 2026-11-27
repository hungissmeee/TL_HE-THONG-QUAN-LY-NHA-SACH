"""Service nghiệp vụ hóa đơn bán hàng dùng chung cho Desktop và Backend."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from core.repositories.hoa_don_repository import HoaDonRepository


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
        total = (subtotal - discount).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
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
