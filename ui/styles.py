"""Bảng màu và tiện ích giao diện dùng chung cho BookHub."""

from pathlib import Path

from PySide6.QtCore import QPoint, QSize, Qt, QUrl
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QPolygon
from PySide6.QtWidgets import (
    QDateEdit,
    QDateTimeEdit,
    QToolButton,
)


_ICON_DIR = Path(__file__).resolve().parent / "assets" / "icons"


def _icon_url(filename):
    """Trả URL file tuyệt đối để QSS tải icon ổn định khi chạy từ thư mục bất kỳ."""
    return QUrl.fromLocalFile(str(_ICON_DIR / filename)).toString()


def _make_triangle_icon(direction, color="#E5E7EB"):
    """Tạo icon tam giác cho hai nút chuyển tháng của lịch."""
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.GlobalColor.transparent)

    center = 9
    half_width = 4
    half_height = 5
    if direction == "left":
        points = [
            QPoint(center + half_height, center - half_width),
            QPoint(center + half_height, center + half_width),
            QPoint(center - half_height, center),
        ]
    else:
        points = [
            QPoint(center - half_height, center - half_width),
            QPoint(center - half_height, center + half_width),
            QPoint(center + half_height, center),
        ]

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    painter.drawPolygon(QPolygon(points))
    painter.end()
    return QIcon(pixmap)


def build_calendar_stylesheet():
    """Tạo stylesheet lịch với icon file SVG cho nút tháng/năm."""
    return f"""
        QCalendarWidget {{
            background-color: #202938;
            color: #E5E7EB;
            border: 1px solid #46546A;
        }}

        QCalendarWidget QWidget#qt_calendar_navigationbar {{
            background-color: #29374B;
            color: #E5E7EB;
            min-height: 42px;
            padding: 4px 6px;
        }}

        QCalendarWidget QToolButton {{
            color: #E5E7EB;
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 4px;
            min-height: 30px;
            padding: 3px 6px;
            font-weight: 600;
            text-align: center;
        }}

        QCalendarWidget QToolButton:hover {{
            background-color: #3B526E;
            border-color: #60758F;
        }}

        QCalendarWidget QToolButton#qt_calendar_prevmonth,
        QCalendarWidget QToolButton#qt_calendar_nextmonth {{
            min-width: 32px;
            max-width: 32px;
            min-height: 30px;
            max-height: 30px;
            padding: 2px;
        }}

        QCalendarWidget QToolButton#qt_calendar_monthbutton {{
            min-width: 112px;
            max-width: 132px;
            padding-left: 8px;
            padding-right: 24px;
        }}

        QCalendarWidget QToolButton#qt_calendar_yearbutton {{
            min-width: 72px;
            max-width: 86px;
            padding-left: 6px;
            padding-right: 22px;
        }}

        QCalendarWidget QToolButton#qt_calendar_monthbutton::menu-indicator,
        QCalendarWidget QToolButton#qt_calendar_yearbutton::menu-indicator {{
            image: url("{_icon_url("arrow-down.svg")}");
            subcontrol-origin: padding;
            subcontrol-position: right center;
            width: 12px;
            height: 12px;
            right: 7px;
        }}

        QCalendarWidget QMenu {{
            background-color: #202938;
            color: #E5E7EB;
            border: 1px solid #46546A;
            padding: 4px;
        }}

        QCalendarWidget QMenu::item {{
            padding: 5px 18px;
            border-radius: 3px;
        }}

        QCalendarWidget QMenu::item:selected {{
            background-color: #3B526E;
            color: #FFFFFF;
        }}

        QCalendarWidget QSpinBox {{
            min-width: 84px;
            min-height: 30px;
            padding-right: 28px;
        }}

        QCalendarWidget QAbstractItemView {{
            background-color: #202938;
            color: #E5E7EB;
            selection-background-color: #2563EB;
            selection-color: #FFFFFF;
            outline: none;
        }}

        QCalendarWidget QAbstractItemView:disabled {{
            color: #64748B;
        }}
    """


CALENDAR_STYLESHEET = build_calendar_stylesheet()


def configure_date_edit(date_edit):
    """Căn chỉnh lịch popup của QDateEdit/QDateTimeEdit dùng trong toàn hệ thống."""
    # QDateEdit kế thừa QDateTimeEdit nên phải kiểm tra QDateEdit trước.
    if isinstance(date_edit, QDateEdit):
        date_edit.setMinimumWidth(148)
    elif isinstance(date_edit, QDateTimeEdit):
        date_edit.setMinimumWidth(180)

    date_edit.setCalendarPopup(True)
    calendar = date_edit.calendarWidget()
    if calendar is None:
        return

    calendar.setMinimumWidth(340)
    calendar.setStyleSheet(build_calendar_stylesheet())

    previous_button = calendar.findChild(
        QToolButton, "qt_calendar_prevmonth"
    )
    next_button = calendar.findChild(
        QToolButton, "qt_calendar_nextmonth"
    )
    if previous_button is not None:
        previous_button.setText("")
        previous_button.setIcon(_make_triangle_icon("left"))
        previous_button.setIconSize(QSize(14, 14))
        previous_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonIconOnly
        )
        previous_button.setAccessibleName("Tháng trước")

    if next_button is not None:
        next_button.setText("")
        next_button.setIcon(_make_triangle_icon("right"))
        next_button.setIconSize(QSize(14, 14))
        next_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonIconOnly
        )
        next_button.setAccessibleName("Tháng sau")

    month_button = calendar.findChild(
        QToolButton, "qt_calendar_monthbutton"
    )
    if month_button is not None:
        month_button.setMinimumWidth(112)
        month_button.setMinimumHeight(30)

    year_button = calendar.findChild(
        QToolButton, "qt_calendar_yearbutton"
    )
    if year_button is not None:
        year_button.setMinimumWidth(72)
        year_button.setMinimumHeight(30)


MAIN_WINDOW_STYLESHEET = """
            QMainWindow {
                background-color: #171B24;
            }

            QWidget {
                color: #E5E7EB;
            }

            QWidget#sidebar {
                background-color: #202B3B;
            }

            QLabel#logo {
                color: white;
                font-size: 25px;
                font-weight: bold;
            }

            QLabel#subtitle {
                color: #AAB7C8;
                font-size: 10px;
            }

            QScrollArea#sidebarScroll,
            QWidget#navContainer {
                background-color: transparent;
                border: none;
            }

            QToolButton#navGroupButton {
                color: #9FB0C5;
                background-color: transparent;
                border: none;
                border-radius: 5px;
                padding: 8px 6px;
                text-align: left;
                font-size: 11px;
                font-weight: bold;
            }

            QToolButton#navGroupButton:hover {
                color: white;
                background-color: #29374B;
            }

            QToolButton#navGroupButton:checked {
                color: #FFFFFF;
            }

            QPushButton#navButton {
                color: #D6DEE9;
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 9px 8px 9px 18px;
                text-align: left;
                font-size: 13px;
            }

            QPushButton#navButton:hover {
                background-color: #34445A;
                color: white;
            }

            QPushButton#navButton:checked {
                background-color: #3B526E;
                color: white;
                font-weight: bold;
            }

            QPushButton#passwordButton {
                color: white;
                background-color: #34445A;
                border: none;
                border-radius: 6px;
                padding: 11px;
                text-align: left;
                font-size: 13px;
            }

            QPushButton#passwordButton:hover {
                background-color: #465B75;
            }

            QWidget#content,
            QStackedWidget {
                background-color: #171B24;
            }

            QLabel#pageTitle {
                color: #F3F4F6;
                font-size: 21px;
                font-weight: bold;
            }

            /* Bảng dùng một nền liền mạch; từng ô không còn viền bo góc như ô nhập liệu. */
            QTableWidget {
                background-color: #202938;
                alternate-background-color: #263448;
                color: #E5E7EB;
                gridline-color: #344256;
                border: 1px solid #39465A;
                selection-background-color: #3B526E;
                selection-color: white;
                outline: none;
            }

            QTableWidget::item {
                border: none;
                padding: 6px 9px;
            }

            QTableWidget::item:selected {
                background-color: #3B526E;
                color: #FFFFFF;
                border: none;
            }

            QTableWidget::item:focus {
                border: none;
                outline: none;
            }

            /* Vùng thao tác luôn nằm ngay dưới bảng và có cùng phong cách với giao diện. */
            QFrame#tableActionPanel {
                background-color: #202938;
                border: 1px solid #39465A;
                border-radius: 8px;
            }

            QLabel#tableActionHint {
                color: #AAB7C8;
                font-size: 11px;
                background: transparent;
                border: none;
            }

            QHeaderView {
                background-color: #202938;
                color: #E5E7EB;
            }

            QHeaderView::section {
                background-color: #29374B;
                color: #E5E7EB;
                padding: 8px;
                border: none;
                border-right: 1px solid #39465A;
                border-bottom: 1px solid #39465A;
                font-weight: bold;
            }

            QTableCornerButton::section {
                background-color: #29374B;
                border: 1px solid #39465A;
            }

            /* Mac dinh: nut phu (secondary). Dung selector co ban de Qt nhan dien. */
            QPushButton {
                background-color: #34445A;
                color: #E5E7EB;
                border: 1px solid #46546A;
                border-radius: 5px;
                padding: 7px 12px;
                min-height: 18px;
            }

            QPushButton:hover {
                background-color: #465B75;
                border-color: #60758F;
            }

            /* Primary: thao tac chinh cua man hinh/dialog. */
            QPushButton#primaryButton {
                background-color: #2563EB;
                color: #FFFFFF;
                border: 1px solid #2563EB;
                border-radius: 5px;
                padding: 7px 14px;
                min-height: 18px;
                font-weight: 600;
            }

            QPushButton#primaryButton:hover {
                background-color: #1D4ED8;
                border-color: #60A5FA;
            }

            QPushButton#primaryButton:pressed {
                background-color: #1E40AF;
                border-color: #1E40AF;
            }

            /* Danger: xoa hoac huy mot chung tu/giao dich. */
            QPushButton#dangerButton {
                background-color: #A83232;
                color: #FFFFFF;
                border: 1px solid #A83232;
                border-radius: 5px;
                padding: 7px 12px;
                min-height: 18px;
                font-weight: 600;
            }

            QPushButton#dangerButton:hover {
                background-color: #C94444;
                border-color: #EF7777;
            }

            QPushButton#dangerButton:pressed {
                background-color: #842525;
                border-color: #842525;
            }

            QLineEdit {
                background-color: #263448;
                color: white;
                border: 1px solid #46546A;
                border-radius: 5px;
                padding: 8px;
            }

            QLineEdit:focus {
                border: 1px solid #60A5FA;
            }

            /* Bộ điều khiển nhập liệu dùng chung cho toàn bộ form nghiệp vụ. */
            QComboBox,
            QDateEdit,
            QDateTimeEdit,
            QTimeEdit,
            QSpinBox,
            QDoubleSpinBox {
                background-color: #263448;
                color: #E5E7EB;
                border: 1px solid #46546A;
                border-radius: 5px;
                padding: 6px 8px;
                min-height: 18px;
                selection-background-color: #3B526E;
                selection-color: white;
            }

            QComboBox:hover,
            QDateEdit:hover,
            QDateTimeEdit:hover,
            QTimeEdit:hover,
            QSpinBox:hover,
            QDoubleSpinBox:hover {
                border: 1px solid #71839B;
            }

            QComboBox:focus,
            QDateEdit:focus,
            QDateTimeEdit:focus,
            QTimeEdit:focus,
            QSpinBox:focus,
            QDoubleSpinBox:focus {
                border: 1px solid #60A5FA;
            }

            QComboBox:disabled,
            QDateEdit:disabled,
            QDateTimeEdit:disabled,
            QTimeEdit:disabled,
            QSpinBox:disabled,
            QDoubleSpinBox:disabled,
            QLineEdit:disabled {
                background-color: #202938;
                color: #8291A5;
                border-color: #344256;
            }

            /* Chỉ chừa đúng vùng nút xổ xuống; phần chữ không bị ép hẹp. */
            QComboBox {
                padding-right: 30px;
            }

            /* Mũi tên tam giác của ComboBox. */
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border: none;
                border-left: 1px solid #46546A;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
                background-color: #34445A;
            }

            QComboBox::drop-down:hover {
                background-color: #465B75;
            }

            QComboBox::down-arrow {
                image: url("BOOKHUB_ARROW_DOWN");
                width: 10px;
                height: 10px;
            }

            QComboBox::down-arrow:disabled {
                image: url("BOOKHUB_ARROW_DOWN_DISABLED");
            }

            QComboBox QAbstractItemView {
                background-color: #202938;
                color: #E5E7EB;
                border: 1px solid #46546A;
                selection-background-color: #3B526E;
                selection-color: white;
                outline: none;
                padding: 3px;
            }

            /* Ô ngày cần đủ rộng cho dd/MM/yyyy và vùng mở lịch. */
            QDateEdit,
            QDateTimeEdit {
                padding-left: 8px;
                padding-right: 34px;
                min-width: 176px;
            }

            /* Đủ chỗ hiển thị trọn dd/MM/yyyy và vùng nút lịch. */
            QDateEdit {
                min-width: 144px;
            }

            QDateEdit::drop-down,
            QDateTimeEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border: none;
                border-left: 1px solid #46546A;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
                background-color: #34445A;
            }

            QDateEdit::drop-down:hover,
            QDateTimeEdit::drop-down:hover {
                background-color: #465B75;
            }

            QDateEdit::down-arrow,
            QDateTimeEdit::down-arrow {
                image: url("BOOKHUB_ARROW_DOWN");
                width: 10px;
                height: 10px;
            }

            QDateEdit::down-arrow:disabled,
            QDateTimeEdit::down-arrow:disabled {
                image: url("BOOKHUB_ARROW_DOWN_DISABLED");
            }

            /* Chừa vùng nhập cho hai nút của SpinBox. */
            QSpinBox,
            QDoubleSpinBox {
                padding-right: 24px;
            }

            /* Nút tăng/giảm chỉ áp dụng cho SpinBox dạng số. */
            QSpinBox::up-button,
            QDoubleSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 22px;
                border: none;
                border-left: 1px solid #46546A;
                border-bottom: 1px solid #46546A;
                border-top-right-radius: 4px;
                background-color: #34445A;
            }

            QSpinBox::down-button,
            QDoubleSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 22px;
                border: none;
                border-left: 1px solid #46546A;
                border-top: 1px solid #46546A;
                border-bottom-right-radius: 4px;
                background-color: #34445A;
            }

            QSpinBox::up-button:hover,
            QSpinBox::down-button:hover,
            QDoubleSpinBox::up-button:hover,
            QDoubleSpinBox::down-button:hover {
                background-color: #465B75;
            }

            QSpinBox::up-arrow,
            QDoubleSpinBox::up-arrow {
                image: url("BOOKHUB_ARROW_UP");
                width: 9px;
                height: 9px;
            }

            QSpinBox::down-arrow,
            QDoubleSpinBox::down-arrow {
                image: url("BOOKHUB_ARROW_DOWN");
                width: 9px;
                height: 9px;
            }

            QSpinBox::up-arrow:disabled,
            QDoubleSpinBox::up-arrow:disabled,
            QSpinBox::up-arrow:off,
            QDoubleSpinBox::up-arrow:off {
                image: url("BOOKHUB_ARROW_UP_DISABLED");
            }

            QSpinBox::down-arrow:disabled,
            QDoubleSpinBox::down-arrow:disabled,
            QSpinBox::down-arrow:off,
            QDoubleSpinBox::down-arrow:off {
                image: url("BOOKHUB_ARROW_DOWN_DISABLED");
            }

            QCheckBox,
            QRadioButton {
                color: #D6DEE9;
                spacing: 7px;
            }

            QCheckBox:disabled,
            QRadioButton:disabled {
                color: #8291A5;
            }

            QCheckBox::indicator,
            QRadioButton::indicator {
                width: 15px;
                height: 15px;
            }

            QCheckBox::indicator {
                border: 1px solid #71839B;
                border-radius: 3px;
                background-color: #263448;
            }

            QCheckBox::indicator:hover,
            QRadioButton::indicator:hover {
                border-color: #60A5FA;
            }

            QCheckBox::indicator:checked {
                background-color: #2563EB;
                border: 1px solid #60A5FA;
            }

            QRadioButton::indicator {
                border: 1px solid #71839B;
                border-radius: 8px;
                background-color: #263448;
            }

            QRadioButton::indicator:checked {
                background-color: #60A5FA;
                border: 4px solid #263448;
            }

            QGroupBox {
                color: #D6DEE9;
                background-color: transparent;
                border: 1px solid #46546A;
                border-radius: 7px;
                margin-top: 10px;
                padding: 10px 8px 8px 8px;
                font-weight: 600;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 9px;
                padding: 0 5px;
                color: #C7D2E0;
                background-color: #171B24;
            }

            QTextEdit,
            QPlainTextEdit {
                background-color: #263448;
                color: #E5E7EB;
                border: 1px solid #46546A;
                border-radius: 5px;
                padding: 7px;
                selection-background-color: #3B526E;
                selection-color: white;
            }

            QTextEdit:focus,
            QPlainTextEdit:focus {
                border: 1px solid #60A5FA;
            }

            QTextEdit:disabled,
            QPlainTextEdit:disabled {
                background-color: #202938;
                color: #8291A5;
                border-color: #344256;
            }

            QCalendarWidget QWidget {
                background-color: #202938;
                color: #E5E7EB;
            }

            QCalendarWidget QToolButton {
                color: #E5E7EB;
                background-color: #34445A;
                border: none;
                border-radius: 4px;
                padding: 5px;
            }

            QCalendarWidget QToolButton:hover {
                background-color: #465B75;
            }

            QCalendarWidget QAbstractItemView {
                background-color: #202938;
                color: #E5E7EB;
                selection-background-color: #3B526E;
                selection-color: white;
                alternate-background-color: #263448;
            }

            QTabWidget::pane {
                border: 1px solid #39465A;
                border-radius: 5px;
                background-color: #202938;
                top: -1px;
            }

            QTabBar::tab {
                background-color: #202938;
                color: #AAB7C8;
                border: 1px solid #39465A;
                padding: 7px 12px;
                margin-right: 3px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }

            QTabBar::tab:selected {
                background-color: #34445A;
                color: white;
                border-bottom-color: #34445A;
            }

            QTabBar::tab:hover:!selected {
                background-color: #29374B;
                color: white;
            }

            QMenu {
                background-color: #202938;
                color: #E5E7EB;
                border: 1px solid #46546A;
                padding: 4px;
            }

            QMenu::item {
                padding: 6px 24px 6px 10px;
                border-radius: 3px;
            }

            QMenu::item:selected {
                background-color: #3B526E;
                color: white;
            }

            QToolTip {
                color: #F3F4F6;
                background-color: #29374B;
                border: 1px solid #536174;
                padding: 5px 7px;
            }

            /* Trạng thái disabled áp dụng chung, các nút đặc biệt có selector riêng bên dưới. */
            QPushButton:disabled {
                background-color: #293442;
                color: #8291A5;
                border: 1px solid #344256;
            }

            QPushButton#primaryButton:disabled,
            QPushButton#dangerButton:disabled {
                background-color: #293442;
                color: #8291A5;
                border: 1px solid #344256;
            }

            QPushButton#navButton:disabled,
            QPushButton#passwordButton:disabled {
                color: #8291A5;
                background-color: transparent;
            }

            QPushButton:focus {
                border: 1px solid #60A5FA;
            }

            QScrollBar:vertical {
                background-color: #202938;
                width: 10px;
            }

            QScrollBar::handle:vertical {
                background-color: #536174;
                border-radius: 5px;
            }

            QScrollBar:horizontal {
                background-color: #202938;
                height: 10px;
            }

            QScrollBar::handle:horizontal {
                background-color: #536174;
                border-radius: 5px;
            }

            QWidget#userProfile {
                background-color: #29374B;
                border-radius: 8px;
            }

            QLabel#accountName {
                color: white;
                font-size: 13px;
                font-weight: bold;
            }

            QLabel#accountInfo {
                color: #AAB7C8;
                font-size: 11px;
            }

            QPushButton#logoutButton {
                color: white;
                background-color: #A83232;
                border: none;
                border-radius: 6px;
                padding: 11px;
                text-align: left;
                font-size: 13px;
            }

            QPushButton#logoutButton:hover {
                background-color: #C94444;
            }
"""

MAIN_WINDOW_STYLESHEET = (
    MAIN_WINDOW_STYLESHEET
    .replace("BOOKHUB_ARROW_DOWN_DISABLED", _icon_url("arrow-down-disabled.svg"))
    .replace("BOOKHUB_ARROW_UP_DISABLED", _icon_url("arrow-up-disabled.svg"))
    .replace("BOOKHUB_ARROW_DOWN", _icon_url("arrow-down.svg"))
    .replace("BOOKHUB_ARROW_UP", _icon_url("arrow-up.svg"))
)

