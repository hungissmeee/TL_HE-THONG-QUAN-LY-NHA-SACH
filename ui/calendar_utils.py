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
        # Chỉ ẩn hình tam giác menu; giữ nguyên QMenu và popupMode
        # để người dùng vẫn nhấn tên tháng và chọn tháng như trước.
        month_button.setStyleSheet(
            "QToolButton::menu-indicator { image: none; }"
        )

    return calendar
