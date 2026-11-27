"""Service kiểm tra dữ liệu và điều phối nghiệp vụ nhà cung cấp."""

from core.repositories.nha_cung_cap_repository import NhaCungCapRepository


class NhaCungCapService:
    """Nghiệp vụ nhà cung cấp dùng chung cho Desktop và Backend."""

    def __init__(self, repository):
        if not isinstance(repository, NhaCungCapRepository):
            raise TypeError("repository phải là NhaCungCapRepository.")
        self.repository = repository

    def get_employee_role(self, username):
        return self.repository.get_employee_role(username)

    def list_suppliers(self, keyword="", show_inactive=False):
        return self.repository.list_suppliers(keyword, show_inactive)

    def get_supplier(self, supplier_code):
        code = str(supplier_code or "").strip()
        if not code:
            raise ValueError("Mã nhà cung cấp không hợp lệ.")
        return self.repository.get_supplier(code)

    def preview_next_code(self):
        return self.repository.preview_next_code()

    def save_supplier(self, data, supplier_code=None):
        payload = dict(data or {})
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("Vui lòng nhập tên nhà cung cấp.")
        if len(name) > 100:
            raise ValueError("Tên nhà cung cấp không được vượt quá 100 ký tự.")

        fields = {
            "phone": ("Số điện thoại", 15),
            "address": ("Địa chỉ", 255),
            "tax": ("Mã số thuế", 20),
        }
        normalized = {"name": name}
        for key, (label, max_length) in fields.items():
            value = str(payload.get(key) or "").strip() or None
            if value and len(value) > max_length:
                raise ValueError(f"{label} không được vượt quá {max_length} ký tự.")
            normalized[key] = value

        code = str(supplier_code or "").strip() or None
        return self.repository.save_supplier(normalized, supplier_code=code)

    def set_supplier_status(self, supplier_code, inactive):
        code = str(supplier_code or "").strip()
        if not code:
            raise ValueError("Mã nhà cung cấp không hợp lệ.")
        return self.repository.set_supplier_status(code, bool(inactive))
