"""Service nghiệp vụ hồ sơ nhân viên và tài khoản."""

import re

from core.nhan_vien.truy_van_sql import NhanVienRepository, ROLE_MAP


class NhanVienService:
    def __init__(self, repository):
        if not isinstance(repository, NhanVienRepository):
            raise TypeError("repository phải là NhanVienRepository.")
        self.repository = repository

    def list_employees(self, keyword=""):
        return self.repository.list_employees(str(keyword or "").strip())

    def get_employee(self, employee_code):
        code = str(employee_code or "").strip()
        if not code:
            raise ValueError("Mã nhân viên không hợp lệ.")
        employee = self.repository.get_employee(code)
        if employee is None:
            raise LookupError("Không tìm thấy nhân viên.")
        return employee

    def get_employee_permissions(self, employee_code):
        code = str(employee_code or "").strip()
        if not code:
            raise ValueError("Mã nhân viên không hợp lệ.")
        return self.repository.get_employee_permissions(code)

    def preview_next_employee_code(self):
        return self.repository.preview_next_employee_code()

    def create_employee(self, data):
        data = dict(data or {})
        name = str(data.get("name") or "").strip()
        role = str(data.get("role") or "").strip()
        phone = str(data.get("phone") or "").strip() or None
        password = data.get("password")
        confirmation = data.get("confirm_password")

        if not name:
            raise ValueError("Vui lòng nhập họ tên nhân viên.")
        if len(name) > 100:
            raise ValueError("Họ tên không được vượt quá 100 ký tự.")
        if role not in ROLE_MAP:
            raise ValueError("Vui lòng chọn vai trò nhân viên hợp lệ.")
        if phone and (len(phone) > 15 or not re.fullmatch(r"[0-9+(). -]+", phone)):
            raise ValueError("Số điện thoại không hợp lệ.")
        if not isinstance(password, str) or not password:
            raise ValueError("Vui lòng nhập mật khẩu.")
        if password != confirmation:
            raise ValueError("Mật khẩu xác nhận không khớp.")
        if len(password) > 128:
            raise ValueError("Mật khẩu không được vượt quá 128 ký tự.")

        return self.repository.create_employee({
            "name": name,
            "role": role,
            "phone": phone,
            "password": password,
        })

    def create_account(self, employee_code, name, role, phone, password):
        # Compatibility entry point for legacy Desktop database adapter.
        return self.repository.create_account(
            employee_code, name, role, phone, password
        )

    def update_employee_role(self, employee_code, role):
        code = str(employee_code or "").strip()
        role = str(role or "").strip()
        if not code:
            raise ValueError("Mã nhân viên không hợp lệ.")
        if role not in ROLE_MAP:
            raise ValueError("Vai trò không hợp lệ.")
        return self.repository.update_employee_role(code, role)

    def set_account_enabled(self, employee_code, enabled):
        code = str(employee_code or "").strip()
        if not code:
            raise ValueError("Mã nhân viên không hợp lệ.")
        if not isinstance(enabled, bool):
            raise ValueError("Trạng thái tài khoản không hợp lệ.")
        return self.repository.set_account_enabled(code, enabled)

    def delete_account(self, employee_code):
        code = str(employee_code or "").strip()
        if not code:
            raise ValueError("Mã nhân viên không hợp lệ.")
        return self.repository.delete_account(code)
