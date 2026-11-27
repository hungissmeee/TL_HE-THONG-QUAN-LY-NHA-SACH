"""Tiện ích cấu hình lịch popup dùng chung cho các ô ngày."""

from PySide6.QtWidgets import QDateEdit, QToolButton


MONTH_BUTTON_OBJECT_NAME = "qt_calendar_monthbutton"


def configure_date_edit_calendar(date_edit):
    """Dùng lịch Qt mặc định nhưng bỏ menu xổ tháng không cần thiết.

    Hai nút chuyển tháng và ô chọn năm vẫn giữ nguyên chức năng native.
    """
    if not isinstance(date_edit, QDateEdit):
        raise TypeError("date_edit phải là một QDateEdit.")

    date_edit.setCalendarPopup(True)
    calendar = date_edit.calendarWidget()
    month_button = calendar.findChild(
        QToolButton,
        MONTH_BUTTON_OBJECT_NAME,
    )
    if month_button is not None:
        # QToolButton không còn menu nên Qt không vẽ menu-indicator
        # nhỏ dưới tên tháng. Không ảnh hưởng hai nút tháng trước/sau.
        month_button.setMenu(None)

    return calendar
