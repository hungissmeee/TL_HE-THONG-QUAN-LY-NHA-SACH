"""Service nghiệp vụ chương trình khuyến mãi."""

from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from core.khuyen_mai.truy_van_sql import KhuyenMaiRepository


class KhuyenMaiService:
    def __init__(self, repository):
        if not isinstance(repository, KhuyenMaiRepository):
            raise TypeError("repository phải là KhuyenMaiRepository.")
        self.repository = repository

    def get_employee_role(self, username):
        return self.repository.get_employee_role(username)

    def list_promotions(self, keyword="", show_deleted=False):
        return self.repository.list_promotions(keyword, bool(show_deleted))

    def get_promotion(self, promotion_code):
        code = str(promotion_code or "").strip()
        if not code:
            raise ValueError("Mã khuyến mãi không hợp lệ.")
        promotion = self.repository.get_promotion(code)
        if promotion is None:
            raise LookupError("Không tìm thấy chương trình khuyến mãi.")
        return promotion

    def preview_next_code(self):
        return self.repository.preview_next_code()

    @staticmethod
    def _parse_datetime(value, field_name):
        if isinstance(value, datetime):
            result = value
        else:
            try:
                result = datetime.fromisoformat(str(value).strip())
            except (TypeError, ValueError):
                raise ValueError(f"{field_name} không hợp lệ.")
        if result.tzinfo is not None:
            raise ValueError(
                f"{field_name} phải dùng giờ địa phương của SQL Server, không kèm timezone."
            )
        return result.replace(microsecond=0)

    def create_promotion(self, data, can_manage=False):
        if not can_manage:
            raise PermissionError("Chỉ Admin/Quản lý được thêm khuyến mãi.")
        data = dict(data or {})
        name = str(data.get("name") or "").strip()
        if not name:
            raise ValueError("Tên chương trình không được để trống.")
        if len(name) > 100:
            raise ValueError("Tên chương trình không được vượt quá 100 ký tự.")
        try:
            rate = Decimal(str(data.get("discount_rate")))
        except (TypeError, ValueError, InvalidOperation):
            raise ValueError("Tỷ lệ giảm phải là số hợp lệ.")
        if not rate.is_finite() or rate < 0 or rate > 100:
            raise ValueError("Tỷ lệ giảm phải nằm trong khoảng 0 đến 100%.")
        rate = rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        start_at = self._parse_datetime(data.get("start_at"), "Thời gian bắt đầu")
        end_at = self._parse_datetime(data.get("end_at"), "Thời gian kết thúc")
        if end_at <= start_at:
            raise ValueError("Thời gian kết thúc phải sau thời gian bắt đầu.")
        return self.repository.create_promotion({
            "name": name,
            "discount_rate": rate,
            "start_at": start_at,
            "end_at": end_at,
        })

    def rename_promotion(self, promotion_code, name, can_manage=False):
        if not can_manage:
            raise PermissionError("Chỉ Admin/Quản lý được đổi tên khuyến mãi.")
        code = str(promotion_code or "").strip()
        name = str(name or "").strip()
        if not code:
            raise ValueError("Mã khuyến mãi không hợp lệ.")
        if not name:
            raise ValueError("Tên chương trình không được để trống.")
        if len(name) > 100:
            raise ValueError("Tên chương trình không được vượt quá 100 ký tự.")
        return self.repository.rename_promotion(code, name)

    def soft_delete_promotion(self, promotion_code, can_manage=False):
        if not can_manage:
            raise PermissionError("Chỉ Admin/Quản lý được xóa khuyến mãi.")
        code = str(promotion_code or "").strip()
        if not code:
            raise ValueError("Mã khuyến mãi không hợp lệ.")
        return self.repository.soft_delete_promotion(code)
