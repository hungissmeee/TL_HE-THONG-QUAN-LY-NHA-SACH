"""Service nghiệp vụ ca làm việc."""

from decimal import Decimal, InvalidOperation

from core.ca_lam_viec.truy_van_sql import CaLamViecRepository


class CaLamViecService:
    SHIFT_SCHEDULE = {
        1: ("07:00:00", "12:00:00"),
        2: ("12:00:00", "17:00:00"),
        3: ("17:00:00", "22:00:00"),
    }

    def __init__(self, repository):
        if not isinstance(repository, CaLamViecRepository):
            raise TypeError("repository phải là CaLamViecRepository.")
        self.repository = repository

    def get_employee_role(self, username):
        return self.repository.get_employee_role(username)

    def get_server_time(self):
        return self.repository.get_server_time()

    def list_employee_shifts(self, username, is_accountant=False):
        return self.repository.list_employee_shifts(username, is_accountant)

    def register_current_shift(self, shift_id, username):
        return self.repository.register_current_shift(
            self._validate_shift_id(shift_id), username
        )

    def record_closing_cash(self, shift_id, username, amount):
        shift_id = self._validate_shift_id(shift_id)
        value = self.parse_cash(amount, "tiền cuối ca")
        return self.repository.record_closing_cash(shift_id, username, value)

    def create_shift(self, data, is_manager=False):
        if not is_manager:
            raise PermissionError("Chỉ Quản lý/Admin mới được tạo ca làm việc.")
        data = dict(data or {})
        try:
            shift_number = int(data.get("soca"))
        except (TypeError, ValueError):
            raise ValueError("Số ca không hợp lệ.")
        if shift_number not in self.SHIFT_SCHEDULE:
            raise ValueError("Chỉ được tạo ca 1, ca 2 hoặc ca 3.")
        date_value = str(data.get("ngaylam") or "").strip()
        try:
            from datetime import date
            parsed_date = date.fromisoformat(date_value)
        except (TypeError, ValueError):
            raise ValueError("Ngày làm không hợp lệ.")
        start, end = self.SHIFT_SCHEDULE[shift_number]
        opening_cash = self.parse_cash(data.get("tmdauca"), "tiền đầu ca")
        return self.repository.create_shift({
            "soca": shift_number,
            "ngaylam": parsed_date.isoformat(),
            "tgmo": start,
            "tgdong": end,
            "tmdauca": opening_cash,
        })

    def get_manager_summary(self):
        return self.repository.get_manager_summary()

    def list_current_shifts(self):
        return self.repository.list_current_shifts()

    def list_shift_history(self, period="all"):
        if period not in {"all", "today", "7days", "30days"}:
            raise ValueError("khoảng thời gian lịch sử ca không hợp lệ.")
        return self.repository.list_shift_history(period)

    def get_shift_roster(self, shift_id):
        return self.repository.get_shift_roster(self._validate_shift_id(shift_id))

    def delete_shift(self, shift_id, is_manager=False):
        if not is_manager:
            raise PermissionError("Chỉ Quản lý/Admin mới được xóa ca làm việc.")
        return self.repository.delete_shift(self._validate_shift_id(shift_id))

    @staticmethod
    def _validate_shift_id(shift_id):
        try:
            value = int(shift_id)
        except (TypeError, ValueError):
            raise ValueError("Mã ca không hợp lệ.")
        if value <= 0:
            raise ValueError("Mã ca phải là số nguyên dương.")
        return value

    @staticmethod
    def parse_cash(value, field_name):
        if isinstance(value, Decimal):
            amount = value
        else:
            raw = str(value if value is not None else "").strip()
            raw = raw.replace(",", "").replace(" ", "")
            if not raw:
                raise ValueError(f"Vui lòng nhập {field_name}.")
            try:
                amount = Decimal(raw)
            except InvalidOperation:
                raise ValueError(f"{field_name} phải là số hợp lệ.")
        if not amount.is_finite() or amount < 0:
            raise ValueError(f"{field_name} phải là số không âm.")
        if amount > Decimal("9999999999999.99"):
            raise ValueError(f"{field_name} vượt quá giới hạn DECIMAL(15,2).")
        return amount.quantize(Decimal("0.01"))
