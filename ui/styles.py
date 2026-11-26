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
