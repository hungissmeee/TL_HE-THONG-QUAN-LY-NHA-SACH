"""Báo cáo hoạt động và chốt tiền ca làm việc."""

from ui.bao_cao.bao_cao_co_so import (
    ReportBasePage, money_text, number_text, date_text,
)


class ShiftReportPage(ReportBasePage):
    """Theo dõi lịch ca, nhân sự đăng ký và tình trạng chốt tiền cuối ca."""

    def __init__(self, db, parent=None):
        super().__init__(
            db,
            "Báo cáo ca làm việc",
            "Theo dõi số ca, lượt nhân viên đăng ký, tình trạng kết thúc và chốt tiền cuối ca. Tiền cuối ca là số tiền kiểm kê tại quầy, không phải doanh thu.",
            True,
            parent,
        )

        self.add_stat_cards([
            ("total", "Tổng số ca", "0",
             "Số ca được tạo trong khoảng thời gian", "neutral"),
            ("employees", "Lượt nhân viên đăng ký", "0",
             "Tổng lượt đăng ký ca, không phải số nhân viên duy nhất", "neutral"),
            ("ended", "Ca đã kết thúc", "0",
             "Đã qua giờ đóng ca", "positive"),
            ("unclosed", "Ca kết thúc chưa chốt", "0",
             "Đã qua giờ đóng ca nhưng chưa ghi tiền cuối ca", "warning"),
            ("cash", "Tổng tiền cuối ca đã ghi nhận", "0 đ",
             "Tổng số tiền kiểm kê của các ca đã chốt", "primary"),
        ], primary_key="cash")

        self.table = self.make_table([
            "Mã ca", "Ngày làm", "Ca", "Giờ mở", "Giờ đóng",
            "Số nhân viên", "Tiền đầu ca", "Tiền cuối ca",
            "Trạng thái ca", "Trạng thái chốt",
        ])
        self.content_layout.addWidget(self.table)
        self.register_export_table("Bao cao ca lam viec", self.table)

    @staticmethod
    def _time_text(value):
        if value is None:
            return ""
        if hasattr(value, "strftime"):
            return value.strftime("%H:%M")
        return str(value)[:5]

    def load_report(self):
        start_date, end_date = self.date_parameters()
        rows = self.service.shift_report(start_date, end_date)

        total_shifts = len(rows)
        employee_registrations = sum(int(row[5] or 0) for row in rows)
        ended_shifts = sum(1 for row in rows if row[8] == "Đã kết thúc")
        unclosed_shifts = sum(
            1 for row in rows if row[8] == "Đã kết thúc" and row[7] is None
        )
        closing_cash_total = sum((row[7] or 0) for row in rows if row[7] is not None)

        self.set_stat("total", number_text(total_shifts))
        self.set_stat("employees", number_text(employee_registrations))
        self.set_stat("ended", number_text(ended_shifts))
        self.set_stat("unclosed", number_text(unclosed_shifts))
        self.set_stat("cash", money_text(closing_cash_total))

        self.fill_table(self.table, [
            (
                row[0],
                date_text(row[1], include_time=False),
                row[2],
                self._time_text(row[3]),
                self._time_text(row[4]),
                number_text(row[5]),
                money_text(row[6]) if row[6] is not None else "Chưa ghi",
                money_text(row[7]) if row[7] is not None else "Chưa chốt",
                row[8],
                "Đã chốt" if row[7] is not None else "Chưa chốt",
            )
            for row in rows
        ])
