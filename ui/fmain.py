from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QStackedWidget,
    QMessageBox, QScrollArea, QToolButton, QFrame
)
from PySide6.QtCore import Qt

from ui.fproduct import ProductWindow
from ui.fChangePassword import ChangePasswordDialog
from ui.fEmployee import EmployeeWindow
from ui.fCatalog import CatalogPage
from ui.fCaLamViec import ShiftWindow
from ui.fHoaDon import InvoiceWindow
from ui.reports import (
    OverviewReportPage,
    RevenueReportPage,
    InvoiceReportPage,
    ImportReportPage,
    ReturnReportPage,
    InventoryReportPage,
    ProductReportPage, report_invoice,
)
from ui.reports.report_base import ReportBasePage
from ui.fPhieuNhap import ImportWindow
from ui.fNhaCungCap import SupplierWindow

class MainWindow(QMainWindow):

    def __init__(self, db, login_window=None):
        super().__init__()

        self.employee_role = ""
        self.db = db
        self.login_window = login_window

        self.setWindowTitle("BookHub - Quản lý nhà sách")
        self.resize(1200, 750)

        self.pages = {}
        self.nav_buttons = {}
        self.page_titles = {}

        # ==================================================
        # CẤU HÌNH NHÓM MENU TẠI ĐÂY
        # Chỉ cần sửa title hoặc danh sách pages để đổi nhóm.
        # Không có màn hình quản lý nhóm riêng.
        # ==================================================
        self.sidebar_group_config = [
            {
                "key": "overview",
                "title": "TỔNG QUAN",
                "pages": ["home"],
                "expanded": True,
            },
            {
                "key": "sales",
                "title": "BÁN HÀNG",
                "pages": ["invoices", "returns"],
                "expanded": True,
            },
            {
                "key": "inventory",
                "title": "QUẢN LÝ KHO",
                "pages": ["products", "suppliers", "imports"],
                "expanded": True,
            },
            {
                "key": "catalogs",
                "title": "QUẢN LÝ DANH MỤC",
                "pages": ["authors", "genres", "publishers", "brands"],
                "expanded": False,
            },
            {
                "key": "people",
                "title": "QUẢN LÝ NHÂN SỰ",
                "pages": ["employees", "shifts"],
                "expanded": True,
            },
            {
                "key": "reports",
                "title": "BÁO CÁO",
                "pages": [
                    "report_overview",
                    "report_revenue",
                    "report_invoice",
                    "report_import",
                    "report_return",
                    "report_inventory",
                    "report_product",
                ],
                "expanded": False,
            },
        ]

        self.nav_group_widgets = {}
        self.page_to_group = {}
        self.nav_group_state = {}

        # Widget chính
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ==================================================
        # SIDEBAR BÊN TRÁI
        # ==================================================
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(235)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 15)
        sidebar_layout.setSpacing(8)

        logo = QLabel("BOOKHUB")
        logo.setObjectName("logo")

        subtitle = QLabel("QUẢN LÝ NHÀ SÁCH")
        subtitle.setObjectName("subtitle")

        sidebar_layout.addWidget(logo)
        sidebar_layout.addWidget(subtitle)
        sidebar_layout.addSpacing(12)

        # Khu vực menu có thể cuộn khi có nhiều nhóm/mục
        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setObjectName("sidebarScroll")
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.sidebar_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.sidebar_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.nav_container = QWidget()
        self.nav_container.setObjectName("navContainer")
        self.nav_groups_layout = QVBoxLayout(self.nav_container)
        self.nav_groups_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_groups_layout.setSpacing(7)

        self._create_sidebar_groups()

        self.nav_groups_layout.addStretch()
        self.sidebar_scroll.setWidget(self.nav_container)
        sidebar_layout.addWidget(self.sidebar_scroll, 1)

        # Nút đổi mật khẩu
        self.password_button = QPushButton("Đổi mật khẩu")
        self.password_button.setObjectName("passwordButton")
        self.password_button.clicked.connect(self.open_change_password)
        sidebar_layout.addWidget(self.password_button)

        # Thông tin tài khoản
        self.user_profile = QWidget()
        self.user_profile.setObjectName("userProfile")

        profile_layout = QVBoxLayout(self.user_profile)
        profile_layout.setContentsMargins(10, 10, 10, 10)
        profile_layout.setSpacing(5)

        self.account_name = QLabel("Đang tải...")
        self.account_name.setObjectName("accountName")

        self.account_id = QLabel()
        self.account_id.setObjectName("accountInfo")

        self.account_role = QLabel()
        self.account_role.setObjectName("accountInfo")

        self.account_phone = QLabel()
        self.account_phone.setObjectName("accountInfo")

        profile_layout.addWidget(self.account_name)
        profile_layout.addWidget(self.account_id)
        profile_layout.addWidget(self.account_role)
        profile_layout.addWidget(self.account_phone)
        sidebar_layout.addWidget(self.user_profile)

        # Nút đăng xuất
        self.logout_button = QPushButton("Đăng xuất")
        self.logout_button.setObjectName("logoutButton")
        self.logout_button.clicked.connect(self.logout)
        sidebar_layout.addWidget(self.logout_button)

        # ==================================================
        # KHU VỰC HIỂN THỊ BÊN PHẢI
        # ==================================================
        content = QWidget()
        content.setObjectName("content")

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 15, 20, 20)
        content_layout.setSpacing(15)

        topbar = QHBoxLayout()
        self.page_title = QLabel("Tổng quan")
        self.page_title.setObjectName("pageTitle")
        topbar.addWidget(self.page_title)
        topbar.addStretch()
        content_layout.addLayout(topbar)

        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)

        # ==================================================
        # ĐĂNG KÝ CÁC TRANG
        # ==================================================
        self.add_page(
            "home", "Tổng quan", self.create_home_page()
        )

        self.add_page(
            "products", "Sản phẩm", ProductWindow(self.db)
        )

        # Nhân viên chỉ được đăng ký trang này theo điều kiện hiện tại
        if str(self.db.username or "").lower() == "admin":
            self.add_page(
                "employees", "Nhân viên", EmployeeWindow(self.db)
            )

        self.add_page(
            "authors", "Tác giả", CatalogPage(self.db, "authors")
        )
        self.add_page(
            "genres", "Thể loại", CatalogPage(self.db, "genres")
        )
        self.add_page(
            "publishers", "Nhà xuất bản", CatalogPage(self.db, "publishers")
        )
        self.add_page(
            "brands", "Thương hiệu", CatalogPage(self.db, "brands")
        )
        self.add_page(
            "shifts", "Ca làm việc", ShiftWindow(self.db)
        )
        self.add_page(
            "invoices", "Hóa đơn", InvoiceWindow(self.db)
        )
        self.add_page("report_overview", "Tổng quan", OverviewReportPage(self.db))
        self.add_page("report_revenue", "Doanh thu", RevenueReportPage(self.db))
        self.add_page("report_invoice", "Báo cáo hóa đơn", InvoiceReportPage(self.db))
        self.add_page("report_import", "Báo cáo nhập hàng", ImportReportPage(self.db))
        self.add_page("report_return", "Báo cáo đổi trả", ReturnReportPage(self.db))
        self.add_page("report_inventory", "Báo cáo tồn kho", InventoryReportPage(self.db))
        self.add_page("report_product", "Báo cáo sản phẩm", ProductReportPage(self.db))
        self.add_page(
            "imports", "Phiếu nhập", ImportWindow(self.db)
        )
        self.add_page(
            "suppliers", "Nhà cung cấp", SupplierWindow(self.db)
        )

        # Các trang đang phát triển sau
        future_pages = [
            ("returns", "Đổi trả")
        ]

        for key, title in future_pages:
            self.add_page(
                key, title, self.create_placeholder_page(title)
            )

        # Ghép giao diện
        main_layout.addWidget(sidebar)
        main_layout.addWidget(content)

        # Giao diện mặc định và phân quyền
        self.load_employee_info()
        self.apply_role_navigation()
        self.show_page("home")

        # ==================================================
        # DARK THEME
        # ==================================================
        self.setStyleSheet("""
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

            QTableWidget {
                background-color: #202938;
                alternate-background-color: #263448;
                color: #E5E7EB;
                gridline-color: #39465A;
                border: 1px solid #39465A;
                selection-background-color: #3B526E;
                selection-color: white;
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
        """)

    # ==================================================
    # TẠO CÁC NHÓM SIDEBAR (NHÓM ĐƯỢC KHAI BÁO TRONG CODE)
    # ==================================================
    def _create_sidebar_groups(self):
        for group in self.sidebar_group_config:
            group_key = group["key"]
            expanded = bool(group.get("expanded", False))

            header = QToolButton()
            header.setObjectName("navGroupButton")
            header.setText(group["title"])
            header.setCheckable(True)
            header.setChecked(expanded)
            header.setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon
            )
            header.setArrowType(
                Qt.ArrowType.DownArrow if expanded
                else Qt.ArrowType.RightArrow
            )

            content = QWidget()
            content.setObjectName(f"navGroupContent_{group_key}")
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(3)
            content.setVisible(expanded)

            self.nav_groups_layout.addWidget(header)
            self.nav_groups_layout.addWidget(content)

            self.nav_group_widgets[group_key] = {
                "header": header,
                "content": content,
                "layout": content_layout,
                "pages": list(group["pages"]),
            }
            self.nav_group_state[group_key] = expanded

            for page_key in group["pages"]:
                self.page_to_group[page_key] = group_key

            header.toggled.connect(
                lambda checked, key=group_key:
                self.toggle_nav_group(key, checked)
            )

    def toggle_nav_group(self, group_key, expanded):
        group = self.nav_group_widgets.get(group_key)
        if group is None:
            return

        self.nav_group_state[group_key] = bool(expanded)
        group["header"].setArrowType(
            Qt.ArrowType.DownArrow if expanded
            else Qt.ArrowType.RightArrow
        )
        group["content"].setVisible(
            bool(expanded) and group["header"].isVisible()
        )

    def _refresh_sidebar_groups(self):
        for group_key, group in self.nav_group_widgets.items():
            # isHidden() kiểm tra trạng thái ẩn trực tiếp của từng nút,
            # không bị ảnh hưởng bởi việc nhóm cha đang thu gọn.
            has_visible_page = any(
                key in self.nav_buttons
                and not self.nav_buttons[key].isHidden()
                for key in group["pages"]
            )

            group["header"].setVisible(has_visible_page)
            group["content"].setVisible(
                has_visible_page and self.nav_group_state[group_key]
            )

    # ==================================================
    # THÊM TRANG VÀO HỆ THỐNG
    # ==================================================
    def add_page(self, key, title, page):
        self.pages[key] = page
        self.page_titles[key] = title
        self.stack.addWidget(page)

        button = QPushButton(title)
        button.setObjectName("navButton")
        button.setCheckable(True)
        button.clicked.connect(
            lambda checked=False, k=key: self.show_page(k)
        )

        group_key = self.page_to_group.get(key)
        if group_key not in self.nav_group_widgets:
            # Trang chưa được khai báo nhóm sẽ tự đưa vào nhóm Khác.
            group_key = self._ensure_other_group()
            self.page_to_group[key] = group_key

        self.nav_group_widgets[group_key]["layout"].addWidget(button)
        self.nav_buttons[key] = button

    def _ensure_other_group(self):
        group_key = "other"
        if group_key not in self.nav_group_widgets:
            group = {
                "key": group_key,
                "title": "KHÁC",
                "pages": [],
                "expanded": True,
            }
            self.sidebar_group_config.append(group)

            header = QToolButton()
            header.setObjectName("navGroupButton")
            header.setText(group["title"])
            header.setCheckable(True)
            header.setChecked(True)
            header.setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon
            )
            header.setArrowType(Qt.ArrowType.DownArrow)

            content = QWidget()
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(3)

            self.nav_groups_layout.insertWidget(
                self.nav_groups_layout.count() - 1, header
            )
            self.nav_groups_layout.insertWidget(
                self.nav_groups_layout.count() - 1, content
            )

            self.nav_group_widgets[group_key] = {
                "header": header,
                "content": content,
                "layout": content_layout,
                "pages": group["pages"],
            }
            self.nav_group_state[group_key] = True
            header.toggled.connect(
                lambda checked, key=group_key:
                self.toggle_nav_group(key, checked)
            )

        return group_key

    # ==================================================
    # CHUYỂN TRANG
    # ==================================================
    def show_page(self, key):
        if key not in self.pages:
            return

        self.stack.setCurrentWidget(self.pages[key])
        self.page_title.setText(self.page_titles[key])

        # Tự mở nhóm chứa trang hiện tại nếu nhóm đang thu gọn.
        group_key = self.page_to_group.get(key)
        if group_key in self.nav_group_widgets:
            if not self.nav_group_state.get(group_key, False):
                self.nav_group_widgets[group_key]["header"].setChecked(True)
                self.toggle_nav_group(group_key, True)

        # Tải lại dữ liệu danh mục khi mở trang.
        page = self.pages[key]
        if isinstance(page, CatalogPage):
            page.load_data()

        if isinstance(page, ReportBasePage):
            page.refresh_data()

        if isinstance(page, (CatalogPage, SupplierWindow)):
            page.load_data()

        for page_key, button in self.nav_buttons.items():
            button.setChecked(page_key == key)

    # ==================================================
    # TRANG TỔNG QUAN
    # ==================================================
    def create_home_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        welcome = QLabel(
            "Chào mừng đến với hệ thống quản lý nhà sách BookHub!"
        )
        welcome.setStyleSheet("font-size: 18px; font-weight: bold;")

        description = QLabel(
            "Chọn chức năng ở thanh bên trái để bắt đầu sử dụng."
        )

        layout.addWidget(welcome)
        layout.addWidget(description)
        layout.addStretch()
        return page

    # ==================================================
    # TRANG CHƯA PHÁT TRIỂN
    # ==================================================
    def create_placeholder_page(self, title):
        page = QWidget()
        layout = QVBoxLayout(page)

        label = QLabel(
            f"Giao diện {title} sẽ được phát triển sau."
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(label)
        return page

    # ==================================================
    # ĐỔI MẬT KHẨU
    # ==================================================
    def open_change_password(self):
        dialog = ChangePasswordDialog(self.db, self)
        dialog.exec()

    # ==================================================
    # THÔNG TIN NHÂN VIÊN
    # ==================================================
    def load_employee_info(self):
        conn = self.db.get_connection()
        username = self.db.username

        if conn is None:
            self.account_name.setText(username or "Không xác định")
            self.account_id.setText("Không có kết nối database")
            return

        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MANV, TENNV, VAITRO, SDT
                FROM NHAN_VIEN
                WHERE MANV = ?
            """, username)

            employee = cursor.fetchone()

            if employee:
                manv = employee[0] or ""
                tennv = employee[1] or username
                vaitro = employee[2] or "Chưa cập nhật"
                sdt = employee[3] or "Chưa cập nhật"

                self.employee_role = employee[2] or ""
                self.account_name.setText(str(tennv))
                self.account_id.setText(f"Mã NV: {manv}")
                self.account_role.setText(f"Vai trò: {vaitro}")
                self.account_phone.setText(f"SĐT: {sdt}")
            else:
                self.account_name.setText(username or "Tài khoản")
                self.account_id.setText("Chưa có hồ sơ nhân viên")
                self.account_role.setText("MANV chưa khớp tài khoản")
                self.account_phone.setText("")

        except Exception as e:
            self.account_name.setText(username or "Tài khoản")
            self.account_id.setText("Không tải được thông tin")
            self.account_role.setText(str(e))

        finally:
            if cursor is not None:
                cursor.close()

    # ==================================================
    # ĐĂNG XUẤT
    # ==================================================
    def logout(self):
        confirm = QMessageBox.question(
            self,
            "Xác nhận đăng xuất",
            "Bạn có chắc chắn muốn đăng xuất?",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.db.close()

        if self.login_window:
            self.login_window.password.clear()
            self.login_window.show()
            self.login_window.raise_()
            self.login_window.activateWindow()

        self.close()

    # ==================================================
    # PHÂN QUYỀN SIDEBAR THEO VAI TRÒ
    # ==================================================
    def apply_role_navigation(self):
        username = str(self.db.username or "").lower()

        if username == "admin":
            allowed = set(self.nav_buttons.keys())
        else:
            role_pages = {
                "Quản lý": [
                    "home", "products", "suppliers",
                    "employees", "imports", "invoices",
                    "returns", "statistics", "authors",
                    "genres", "publishers", "brands", "shifts",
                ],
                "Thu ngân": [
                    "home", "products", "invoices", "shifts",
                ],
                "Nhân viên kho": [
                    "home", "products", "suppliers", "imports",
                    "authors", "genres", "publishers", "brands",
                    "shifts",
                ],
                "Kế toán": [
                    "home", "products", "suppliers", "imports",
                    "invoices", "returns", "statistics", "shifts", "report_product", "report_inventory", "report_return", "report_import", "report_invoice", "report_revenue", "report_overview"
                ],
            }
            allowed = set(role_pages.get(self.employee_role, ["home"]))

        for key, button in self.nav_buttons.items():
            button.setVisible(key in allowed)

        self._refresh_sidebar_groups()

        current_key = next(
            (
                key for key, page in self.pages.items()
                if page is self.stack.currentWidget()
            ),
            None,
        )

        if current_key not in allowed:
            self.show_page("home")
