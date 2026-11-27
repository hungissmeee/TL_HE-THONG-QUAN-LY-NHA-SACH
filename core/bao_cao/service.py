"""Service truy vấn và xác thực bộ lọc báo cáo."""

from datetime import date

from core.bao_cao.repository import BaoCaoRepository


class BaoCaoService:
    """Facade báo cáo dùng chung cho Desktop và Backend."""

    def __init__(self, repository):
        if not isinstance(repository, BaoCaoRepository):
            raise TypeError("repository phải là BaoCaoRepository.")
        self.repository = repository

    @staticmethod
    def _validate_dates(start_date, end_date):
        try:
            start = date.fromisoformat(str(start_date))
            end = date.fromisoformat(str(end_date))
        except (TypeError, ValueError):
            raise ValueError("Khoảng ngày báo cáo không hợp lệ.")
        if start > end:
            raise ValueError("Ngày bắt đầu không được lớn hơn ngày kết thúc.")
        return start.isoformat(), end.isoformat()

    def overview_summary(self, start_date, end_date):
        return self.repository.overview_summary(*self._validate_dates(start_date, end_date))

    def overview_refunds(self, start_date, end_date):
        return self.repository.overview_refunds(*self._validate_dates(start_date, end_date))

    def overview_imports(self, start_date, end_date):
        return self.repository.overview_imports(*self._validate_dates(start_date, end_date))

    def overview_trend(self, start_date, end_date):
        return self.repository.overview_trend(*self._validate_dates(start_date, end_date))

    def overview_top_products(self, start_date, end_date):
        return self.repository.overview_top_products(*self._validate_dates(start_date, end_date))

    def revenue_by_period(self, start_date, end_date, period):
        start, end = self._validate_dates(start_date, end_date)
        if period not in {"day", "month", "year"}:
            raise ValueError("Kiểu tổng hợp doanh thu không hợp lệ.")
        return self.repository.revenue_by_period(start, end, period)

    def promotion_effectiveness(self, start_date, end_date):
        return self.repository.promotion_effectiveness(*self._validate_dates(start_date, end_date))

    def invoice_report(self, start_date, end_date):
        return self.repository.invoice_report(*self._validate_dates(start_date, end_date))

    def employee_sales_report(self, start_date, end_date):
        return self.repository.employee_sales_report(
            *self._validate_dates(start_date, end_date)
        )

    def import_report(self, start_date, end_date):
        return self.repository.import_report(*self._validate_dates(start_date, end_date))

    def return_report(self, start_date, end_date):
        return self.repository.return_report(*self._validate_dates(start_date, end_date))

    def inventory_report(self, threshold, status, keyword=""):
        try:
            threshold = int(threshold)
        except (TypeError, ValueError):
            raise ValueError("Ngưỡng sắp hết hàng phải là số nguyên.")
        if threshold < 1 or threshold > 100000:
            raise ValueError("Ngưỡng sắp hết hàng phải từ 1 đến 100000.")
        if status not in {"all", "low", "out"}:
            raise ValueError("Bộ lọc tình trạng tồn kho không hợp lệ.")
        keyword = str(keyword or "").strip()
        if len(keyword) > 100:
            raise ValueError("Từ khóa tìm kiếm không được vượt quá 100 ký tự.")
        return self.repository.inventory_report(threshold, status, keyword)

    def product_report(self, start_date, end_date, sort, keyword=""):
        start, end = self._validate_dates(start_date, end_date)
        if sort not in {"quantity_desc", "quantity_asc", "refund_desc"}:
            raise ValueError("Kiểu sắp xếp báo cáo sản phẩm không hợp lệ.")
        keyword = str(keyword or "").strip()
        if len(keyword) > 100:
            raise ValueError("Từ khóa tìm kiếm không được vượt quá 100 ký tự.")
        return self.repository.product_report(start, end, sort, keyword)

    def product_report_summary(self, start_date, end_date):
        start, end = self._validate_dates(start_date, end_date)
        return self.repository.product_report_summary(start, end)

    def shift_report(self, start_date, end_date):
        return self.repository.shift_report(*self._validate_dates(start_date, end_date))
