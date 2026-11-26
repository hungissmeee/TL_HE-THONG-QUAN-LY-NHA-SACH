"""Các tiện ích phân quyền dùng chung cho giao diện nhà sách."""


def is_admin_account(username):
    """Nhận diện tài khoản quản trị hệ thống, không phân biệt hoa thường."""
    return str(username or "").strip().casefold() == "admin"


def allowed_pages_for_user(username, employee_role, role_page_access, all_page_keys):
    """Trả về các trang được phép mở; admin được truy cập toàn bộ trang."""
    if is_admin_account(username):
        return set(all_page_keys)
    return set(role_page_access.get(employee_role, ("home",)))
