"""Service nghiệp vụ phiếu nhập kho dùng chung cho Desktop và Backend."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from core.phieu_nhap.repository import PhieuNhapRepository


class PhieuNhapService:
    def __init__(self, repository):
        if not isinstance(repository, PhieuNhapRepository):
            raise TypeError("repository phải là PhieuNhapRepository.")
        self.repository = repository

    def get_employee(self, username, is_admin=False):
        return self.repository.get_employee(username, is_admin)

    def list_suppliers_for_import(self):
        return self.repository.list_suppliers_for_import()

    def list_products_for_import(self):
        return self.repository.list_products_for_import()

    def list_imports(self, start_date, end_date, keyword=""):
        if start_date > end_date:
            raise ValueError("Ngày bắt đầu không được lớn hơn ngày kết thúc.")
        return self.repository.list_imports(start_date, end_date, keyword)

    def get_import_detail(self, import_code, username=None, is_admin=False):
        code = str(import_code or "").strip()
        if not code:
            raise ValueError("Mã phiếu nhập không hợp lệ.")
        include_return_history = True
        if username is not None:
            employee = self.get_employee(username, is_admin)
            role = str(employee.get("vaitro") or "").strip().casefold()
            include_return_history = (
                bool(is_admin)
                or str(username or "").strip().casefold() == "admin"
                or role in {"quản lý", "nhân viên kho", "kế toán"}
            )
        return self.repository.get_import_detail(
            code, include_return_history=include_return_history
        )

    def create_import(self, data):
        payload = dict(data or {})
        supplier = str(payload.get("supplier_code") or "").strip()
        employee = str(payload.get("employee_code") or "").strip()
        is_admin = bool(payload.get("is_admin"))
        import_type = str(payload.get("import_type") or "").strip()
        if not supplier:
            raise ValueError("Vui lòng chọn nhà cung cấp đang hoạt động.")
        if not employee and not is_admin:
            raise ValueError("Không xác định được nhân viên lập phiếu.")
        if not import_type:
            raise ValueError("Vui lòng chọn loại phiếu nhập.")
        invoice = str(payload.get("supplier_invoice") or "").strip() or None

        source_items = payload.get("items") or []
        if not source_items:
            raise ValueError("Phiếu nhập chưa có sản phẩm nào.")
        items = []
        seen = set()
        total = Decimal("0.00")
        for source in source_items:
            item = dict(source)
            code = str(item.get("product_code") or "").strip()
            if not code:
                raise ValueError("Có sản phẩm không có mã hợp lệ.")
            if code in seen:
                raise ValueError(f"Sản phẩm {code} bị lặp trong phiếu nhập.")
            seen.add(code)
            try:
                quantity = int(item.get("quantity"))
                price = Decimal(str(item.get("price")))
                vat = Decimal(str(item.get("vat", 0)))
            except (TypeError, ValueError, InvalidOperation):
                raise ValueError(f"Số lượng, đơn giá hoặc VAT của {code} không hợp lệ.")
            if quantity <= 0:
                raise ValueError(f"Số lượng nhập của {code} phải lớn hơn 0.")
            if not price.is_finite() or price <= 0:
                raise ValueError(f"Đơn giá nhập của {code} phải lớn hơn 0.")
            if not vat.is_finite() or vat < 0 or vat > 100:
                raise ValueError(f"VAT của {code} phải nằm trong khoảng 0 đến 100.")
            price = price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            vat = vat.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total += price * quantity
            items.append({
                "product_code": code,
                "quantity": quantity,
                "price": price,
                "vat": vat,
            })
        payload = {
            "supplier_code": supplier,
            "supplier_invoice": invoice,
            "employee_code": employee or None,
            "import_type": import_type,
            "items": items,
            "total": total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        }
        return self.repository.create_import(payload)

    def update_import_header(
        self, import_code, supplier_code, supplier_invoice,
        username, role, is_admin=False
    ):
        code = str(import_code or "").strip()
        supplier = str(supplier_code or "").strip()
        invoice = str(supplier_invoice or "").strip() or None
        if not code:
            raise ValueError("Mã phiếu nhập không hợp lệ.")
        if not supplier:
            raise ValueError("Vui lòng chọn nhà cung cấp đang hoạt động.")
        if invoice is not None and len(invoice) > 50:
            raise ValueError("Số hóa đơn nhà cung cấp không được vượt quá 50 ký tự.")
        return self.repository.update_import_header(
            code, supplier, invoice, username, role, is_admin
        )

    def update_import_details(
        self, import_code, source_items, username, role, is_admin=False
    ):
        code = str(import_code or "").strip()
        if not code:
            raise ValueError("Mã phiếu nhập không hợp lệ.")
        if not source_items:
            raise ValueError("Phiếu nhập phải có ít nhất một sản phẩm.")

        items = []
        seen = set()
        total = Decimal("0.00")
        for source in source_items:
            item = dict(source)
            product_code = str(item.get("product_code") or "").strip()
            if not product_code:
                raise ValueError("Có sản phẩm không có mã hợp lệ.")
            if product_code in seen:
                raise ValueError(f"Sản phẩm {product_code} bị lặp trong phiếu nhập.")
            seen.add(product_code)
            try:
                quantity = int(item.get("quantity"))
                price = Decimal(str(item.get("price")))
                vat = Decimal(str(item.get("vat", 0)))
            except (TypeError, ValueError, InvalidOperation):
                raise ValueError(
                    f"Số lượng, đơn giá hoặc VAT của {product_code} không hợp lệ."
                )
            if quantity <= 0:
                raise ValueError(f"Số lượng nhập của {product_code} phải lớn hơn 0.")
            if not price.is_finite() or price <= 0:
                raise ValueError(f"Đơn giá nhập của {product_code} phải lớn hơn 0.")
            if not vat.is_finite() or vat < 0 or vat > 100:
                raise ValueError(f"VAT của {product_code} phải nằm trong khoảng 0 đến 100.")
            price = price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            vat = vat.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total += price * quantity
            items.append({
                "product_code": product_code,
                "quantity": quantity,
                "price": price,
                "vat": vat,
            })
        total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return self.repository.update_import_details(
            code, items, total, username, role, is_admin
        )

    def cancel_import(self, import_code, username, role, is_admin=False):
        code = str(import_code or "").strip()
        if not code:
            raise ValueError("Mã phiếu nhập không hợp lệ.")
        return self.repository.cancel_import(code, username, role, is_admin)
