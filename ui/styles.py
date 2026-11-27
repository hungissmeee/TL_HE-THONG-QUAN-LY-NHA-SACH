"""Bảng màu và stylesheet chung cho giao diện BookHub."""

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

            QPushButton:not(#navButton):not(#passwordButton):not(#logoutButton) {
                background-color: #34445A;
                color: white;
            }

            QPushButton:not(#navButton):not(#passwordButton):not(#logoutButton):hover {
                background-color: #465B75;
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

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border: none;
                border-left: 1px solid #39465A;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
                background-color: transparent;
            }

            QComboBox::down-arrow {
                width: 9px;
                height: 9px;
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

            QAbstractSpinBox::up-button,
            QAbstractSpinBox::down-button {
                width: 18px;
                background-color: #34445A;
                border: none;
            }

            QAbstractSpinBox::up-button:hover,
            QAbstractSpinBox::down-button:hover {
                background-color: #465B75;
            }

            QAbstractSpinBox::up-arrow,
            QAbstractSpinBox::down-arrow {
                width: 8px;
                height: 8px;
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

            /* Trạng thái nút được thống nhất; không làm mất màu riêng của nút nguy hiểm. */
            QPushButton:not(#navButton):not(#passwordButton):not(#logoutButton):hover {
                border: 1px solid #60758F;
            }

            QPushButton:disabled {
                background-color: #293442;
                color: #8291A5;
                border: 1px solid #344256;
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
