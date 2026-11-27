"""Service nghiệp vụ đổi trả dùng chung cho Desktop và Backend."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from core.doi_tra.repository import ReturnRepository


MONEY_QUANT = Decimal("0.01")


class ReturnService:
    def __init__(self, repository):
        if not isinstance(repository, ReturnRepository):
            raise TypeError("repository phải là ReturnRepository.")
        self.repository = repository

    def get_employee_role(self, username):
        return self.repository.get_employee_role(username)

    def list_eligible_invoices(self):
        return self.repository.list_eligible_invoices()

    def get_invoice_items(self, invoice_code):
        code = str(invoice_code or "").strip()
        if not code:
            raise ValueError("Mã hóa đơn không hợp lệ.")
        return self.repository.get_invoice_items(code)

    def list_returns(self, start_date, end_date, keyword=""):
        if str(start_date) > str(end_date):
            raise ValueError("Ngày bắt đầu không được lớn hơn ngày kết thúc.")
        return self.repository.list_returns(start_date, end_date, keyword)

    def get_return_detail(self, return_code):
        code = str(return_code or "").strip()
        if not code:
            raise ValueError("Mã phiếu đổi trả không hợp lệ.")
        return self.repository.get_return_detail(code)

    def get_deleted_products_to_restore(self, items):
        """Kiểm tra trước các sản phẩm xóa mềm sẽ được cộng tồn khi hoàn hàng."""
        return self.repository.get_deleted_products_to_restore(items)

    @staticmethod
    def _integer(value, field):
        try:
            number = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"{field} phải là số nguyên.")
        if number <= 0:
            raise ValueError(f"{field} phải lớn hơn 0.")
        return number

    def create_return(
        self, data, username, is_admin=False, confirmed_restore_codes=None
    ):
        data = dict(data or {})
        invoice_code = str(data.get("invoice_code") or "").strip()
        reason = str(data.get("reason") or "").strip()
        if not invoice_code:
            raise ValueError("Vui lòng chọn hóa đơn hợp lệ.")
        if not reason:
            raise ValueError("Vui lòng nhập lý do đổi trả.")
        if len(reason) > 255:
            raise ValueError("Lý do đổi trả không được vượt quá 255 ký tự.")

        source_items = data.get("items") or []
        if not source_items:
            raise ValueError("Vui lòng chọn ít nhất một sản phẩm cần xử lý.")

        items = []
        seen = set()
        for source in source_items:
            item = dict(source or {})
            code = str(item.get("product_code") or "").strip()
            if not code:
                raise ValueError("Có dòng sản phẩm không có mã hợp lệ.")
            if code in seen:
                raise ValueError(f"Sản phẩm {code} bị chọn nhiều lần.")
            seen.add(code)
            quantity = self._integer(item.get("quantity"), f"Số lượng {code}")
            condition = item.get("condition")
            action = item.get("action")
            if condition not in (0, 1) or action not in (0, 1):
                raise ValueError(f"Tình trạng hoặc hình thức xử lý của {code} không hợp lệ.")
            if action == 1 and condition != 0:
                raise ValueError(f"Sản phẩm {code}: chỉ được đổi hàng khi hàng trả đã hỏng.")
            items.append({
                "product_code": code,
                "quantity": quantity,
                "condition": condition,
                "action": action,
            })
        payload = {
            "invoice_code": invoice_code,
            "reason": reason,
            "items": items,
        }
        if confirmed_restore_codes is None:
            # Giữ tương thích với các adapter/mock Repository cũ khi không cần khôi phục.
            return self.repository.create_return(
                payload, username, is_admin=is_admin
            )
        return self.repository.create_return(
            payload,
            username,
            is_admin=is_admin,
            confirmed_restore_codes=confirmed_restore_codes,
        )

    def delete_return(self, return_code, username, is_admin=False):
        code = str(return_code or "").strip()
        if not code:
            raise ValueError("Mã phiếu đổi trả không hợp lệ.")
        return self.repository.delete_return(
            code, username, is_admin=is_admin
        )

    @staticmethod
    def calculate_refund(lines):
        """Hàm thuần hỗ trợ test và hiển thị số tiền hoàn dự kiến."""
        total = Decimal("0.00")
        for line in lines:
            try:
                price = Decimal(str(line["net_price"]))
                quantity = int(line["quantity"])
            except (KeyError, TypeError, ValueError, InvalidOperation):
                raise ValueError("Dữ liệu tính tiền hoàn không hợp lệ.")
            if not price.is_finite() or price < 0 or quantity < 0:
                raise ValueError("Đơn giá hoặc số lượng hoàn không hợp lệ.")
            if int(line.get("action", 0)) == 0:
                total += price * quantity
        return total.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
