"""Service xác thực tham số cho trung tâm báo cáo POS."""

from datetime import date

from core.bao_cao.repository import BaoCaoRepository


class BaoCaoService:
    """Facade chỉ cho phép gọi các báo cáo đã định nghĩa."""

    def __init__(self, repository):
        if not isinstance(repository, BaoCaoRepository):
            raise TypeError("repository phải là BaoCaoRepository.")
        self.repository = repository

    @staticmethod
    def validate_dates(start_date, end_date):
        try:
            start = date.fromisoformat(str(start_date))
            end = date.fromisoformat(str(end_date))
        except (TypeError, ValueError):
            raise ValueError("Khoảng ngày báo cáo không hợp lệ.")
        if start > end:
            raise ValueError("Ngày bắt đầu không được lớn hơn ngày kết thúc.")
        return start.isoformat(), end.isoformat()

    @staticmethod
    def _keyword(value):
        value = str(value or "").strip()
        if len(value) > 100:
            raise ValueError("Từ khóa tìm kiếm không được vượt quá 100 ký tự.")
        return value

    def employees(self):
        return self.repository.employees()

    def daily_sales_report(self, start_date, end_date, employee_code=None, keyword=""):
        start, end = self.validate_dates(start_date, end_date)
        return self.repository.daily_sales_report(
            start, end, str(employee_code or "").strip() or None,
            self._keyword(keyword),
        )

    def sales_by_period_report(self, start_date, end_date, period="day"):
        start, end = self.validate_dates(start_date, end_date)
        if period not in {"day", "month", "year"}:
            raise ValueError("Kiểu tổng hợp thời gian không hợp lệ.")
        return self.repository.sales_by_period_report(start, end, period)

    def cash_flow_report(self, start_date, end_date, period="day"):
        start, end = self.validate_dates(start_date, end_date)
        if period not in {"day", "month", "year"}:
            raise ValueError("Kiểu tổng hợp thời gian không hợp lệ.")
        return self.repository.cash_flow_report(start, end, period)

    def revenue_report(self, start_date, end_date, period="day"):
        start, end = self.validate_dates(start_date, end_date)
        if period not in {"day", "month", "year"}:
            raise ValueError("Kiểu tổng hợp thời gian không hợp lệ.")
        return self.repository.revenue_report(start, end, period)

    def revenue_by_shift_report(self, start_date, end_date):
        start, end = self.validate_dates(start_date, end_date)
        return self.repository.revenue_by_shift_report(start, end)

    def sales_by_employee_report(self, start_date, end_date, keyword=""):
        start, end = self.validate_dates(start_date, end_date)
        return self.repository.sales_by_employee_report(start, end, self._keyword(keyword))

    def sales_by_product_report(self, start_date, end_date, keyword=""):
        start, end = self.validate_dates(start_date, end_date)
        return self.repository.sales_by_product_report(start, end, self._keyword(keyword))

    def promotion_report(self, start_date, end_date, keyword=""):
        start, end = self.validate_dates(start_date, end_date)
        return self.repository.promotion_report(start, end, self._keyword(keyword))

    def return_detail_report(self, start_date, end_date, keyword=""):
        start, end = self.validate_dates(start_date, end_date)
        return self.repository.return_detail_report(start, end, self._keyword(keyword))

    def import_detail_report(self, start_date, end_date, keyword=""):
        start, end = self.validate_dates(start_date, end_date)
        return self.repository.import_detail_report(start, end, self._keyword(keyword))

    def import_product_report(self, start_date, end_date, keyword=""):
        start, end = self.validate_dates(start_date, end_date)
        return self.repository.import_product_report(
            start, end, self._keyword(keyword)
        )

    def import_supplier_report(self, start_date, end_date, keyword=""):
        start, end = self.validate_dates(start_date, end_date)
        return self.repository.import_supplier_report(start, end, self._keyword(keyword))

    def current_inventory_report(self, threshold=5, status="all", keyword=""):
        try:
            threshold = int(threshold)
        except (TypeError, ValueError):
            raise ValueError("Ngưỡng sắp hết hàng phải là số nguyên.")
        if threshold < 1 or threshold > 100000:
            raise ValueError("Ngưỡng sắp hết hàng phải từ 1 đến 100000.")
        if status not in {"all", "low", "out"}:
            raise ValueError("Tình trạng tồn kho không hợp lệ.")
        return self.repository.current_inventory_report(
            threshold, status, self._keyword(keyword)
        )

    def stock_movement_report(self, start_date, end_date, keyword=""):
        start, end = self.validate_dates(start_date, end_date)
        return self.repository.stock_movement_report(start, end, self._keyword(keyword))

    def stock_card_report(self, start_date, end_date, keyword=""):
        start, end = self.validate_dates(start_date, end_date)
        return self.repository.stock_card_report(start, end, self._keyword(keyword))

    def shift_report(self, start_date, end_date):
        start, end = self.validate_dates(start_date, end_date)
        return self.repository.shift_report(start, end)
