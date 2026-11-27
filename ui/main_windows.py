"""Cửa sổ chính, điều hướng giữa các chức năng và áp dụng quyền của nhân viên."""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QStackedWidget,
    QMessageBox, QScrollArea, QToolButton, QFrame
)
from PySide6.QtCore import Qt
from ui.sidebar_navigation import SidebarNavigationMixin
from core.nhan_vien.repository import NhanVienRepository
from core.nhan_vien.service import NhanVienService

from ui.san_pham import ProductWindow
from ui.doi_mat_khau import ChangePasswordDialog
from ui.nhan_vien import EmployeeWindow
from ui.danh_muc import CatalogPage
from ui.ca_lam_viec import ShiftWindow
from ui.hoa_don import InvoiceWindow
from ui.bao_cao import ReportCenterPage
from ui.permissions import allowed_pages_for_user
from ui.phieu_nhap import ImportWindow
from ui.nha_cung_cap import SupplierWindow
from ui.doi_tra import ReturnWindow
from ui.khuyen_mai import PromotionWindow

class MainWindow(SidebarNavigationMixin, QMainWindow):
    """Cửa sổ chính quản lý điều hướng, nhóm menu và quyền hiển thị chức năng."""

    ROLE_PAGE_ACCESS = {
        # Quản lý giám sát nghiệp vụ và xem đầy đủ báo cáo.
        # Quản lý tài khoản nhân viên vẫn dành riêng cho Admin.
        "Quản lý": (
            "home", "products", "suppliers", "imports", "invoices",
            "returns", "promotions", "authors", "genres", "publishers", "brands",
            "shifts", "report_center",
        ),
        "Thu ngân": (
            "home", "products", "invoices", "shifts",
        ),
        "Nhân viên kho": (
            "home", "products", "suppliers", "imports", "authors",
            "genres", "publishers", "brands", "shifts",
        ),
        "Kế toán": (
            "home", "products", "suppliers", "imports", "invoices",
            "shifts", "report_center",
        ),
    }

    def __init__(self, db, login_window=None):
        """Khởi tạo sidebar, các trang chức năng, thông tin nhân viên và cấu hình phân quyền."""
        super().__init__()

        self.employee_role = ""
        self.db = db
        self.login_window = login_window
        self.employee_service = NhanVienService(NhanVienRepository(db))

        self.setWindowTitle("Hệ thống quản lý nhà sách")
        self.resize(1600, 750)

        self.danh_sachs = {}
        self.nav_buttons = {}
        self.danh_sach_titles = {}

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
                "pages": ["invoices", "returns", "promotions"],
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
                "key": "reports",
                "title": "BÁO CÁO",
                "pages": ["report_center"],
                "expanded": False,
            },
            {
                "key": "people",
                "title": "QUẢN LÝ NHÂN SỰ",
                "pages": ["employees", "shifts"],
                "expanded": True,
            },
        ]

        self.nav_group_widgets = {}
        self.danh_sach_to_group = {}
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

        logo = QLabel("HỆ THỐNG")
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
        self.danh_sach_title = QLabel("Tổng quan")
        self.danh_sach_title.setObjectName("pageTitle")
        topbar.addWidget(self.danh_sach_title)
        topbar.addStretch()
        content_layout.addLayout(topbar)

        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)

        # ==================================================
        # XÁC ĐỊNH QUYỀN TRƯỚC KHI KHỞI TẠO TRANG
        # ==================================================
        # Lấy vai trò trước để các trang không được phép không chạy truy vấn
        # dữ liệu trong constructor.
        self.load_employee_info()
        all_page_keys = [
            key
            for group in self.sidebar_group_config
            for key in group.get("pages", [])
        ] + [
            group["standalone_page"]
            for group in self.sidebar_group_config
            if group.get("standalone_page")
        ]
        self.allowed_pages = allowed_pages_for_user(
            self.db.username,
            self.employee_role,
            self.ROLE_PAGE_ACCESS,
            all_page_keys,
        )

        def add_allowed_page(key, title, factory):
            if key in self.allowed_pages:
                self.add_page(key, title, factory())

        add_allowed_page("home", "Tổng quan", self.create_home_page)
        add_allowed_page("products", "Sản phẩm", lambda: ProductWindow(self.db))
        # Trang nhân viên và quản lý tài khoản chỉ dành cho Admin.
        if str(self.db.username or "").strip().casefold() == "admin":
            add_allowed_page(
                "employees", "Nhân viên", lambda: EmployeeWindow(self.db)
            )

        add_allowed_page(
            "authors", "Tác giả", lambda: CatalogPage(self.db, "authors")
        )
        add_allowed_page(
            "genres", "Thể loại", lambda: CatalogPage(self.db, "genres")
        )
        add_allowed_page(
            "publishers", "Nhà xuất bản",
            lambda: CatalogPage(self.db, "publishers")
        )
        add_allowed_page(
            "brands", "Thương hiệu", lambda: CatalogPage(self.db, "brands")
        )
        add_allowed_page(
            "shifts", "Ca làm việc", lambda: ShiftWindow(self.db)
        )
        add_allowed_page(
            "invoices", "Hóa đơn", lambda: InvoiceWindow(self.db)
        )
        add_allowed_page(
            "report_center", "Trung tâm báo cáo",
            lambda: ReportCenterPage(self.db)
        )
        add_allowed_page(
            "imports", "Phiếu nhập", lambda: ImportWindow(self.db)
        )
        add_allowed_page(
            "suppliers", "Nhà cung cấp", lambda: SupplierWindow(self.db)
        )
        add_allowed_page(
            "returns", "Đổi trả", lambda: ReturnWindow(self.db)
        )
        add_allowed_page(
            "promotions", "Khuyến mãi", lambda: PromotionWindow(self.db)
        )

        # Ghép giao diện
        main_layout.addWidget(sidebar)
        main_layout.addWidget(content)

        # Giao diện mặc định và phân quyền
        self.apply_role_navigation()
        self.show_page("home")


    # ==================================================
    # TẠO CÁC NHÓM SIDEBAR (NHÓM ĐƯỢC KHAI BÁO TRONG CODE)
    # ==================================================






    @staticmethod
    def _refresh_page_data(page):
        """Tải lại dữ liệu khi người dùng quay lại trang chức năng."""
        if isinstance(page, (CatalogPage, SupplierWindow)):
            page.load_data()
        elif isinstance(page, ProductWindow):
            page.load_products()
        elif isinstance(page, InvoiceWindow):
            page.load_invoices()
        elif isinstance(page, ImportWindow):
            page.load_imports()
        elif isinstance(page, ReturnWindow):
            page.load_returns()
        elif isinstance(page, ShiftWindow):
            if page.is_manager:
                page.refresh_manager_view()
            else:
                page.refresh_employee_view()
        elif isinstance(page, ReportCenterPage):
            page.refresh_data()

    # ==================================================
    # TRANG TỔNG QUAN
    # ==================================================
    def create_home_page(self):
        """Tạo giao diện trang tổng quan mặc định."""
        page = QWidget()
        layout = QVBoxLayout(page)

        welcome = QLabel(
            "Chào mừng đến với Hệ thống quản lý nhà sách!"
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
        """Tạo trang thông báo tạm cho chức năng chưa được triển khai."""
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
        """Mở hộp thoại đổi mật khẩu cho tài khoản hiện tại."""
        dialog = ChangePasswordDialog(self.db, self)
        dialog.exec()

    # ==================================================
    # THÔNG TIN NHÂN VIÊN
    # ==================================================
    def load_employee_info(self):
        """Tải thông tin tài khoản qua Service, không truy vấn SQL tại UI."""
        username = str(self.db.username or "").strip()
        try:
            employee = self.employee_service.get_employee(username)
            if employee:
                manv, tennv, vaitro, sdt = employee
                self.employee_role = vaitro or ""
                self.account_name.setText(str(tennv or username))
                self.account_id.setText(f"Mã NV: {manv or username}")
                self.account_role.setText(f"Vai trò: {vaitro or 'Chưa cập nhật'}")
                self.account_phone.setText(f"SĐT: {sdt or 'Chưa cập nhật'}")
            else:
                self.account_name.setText(username or "Tài khoản")
                self.account_id.setText("Chưa có hồ sơ nhân viên")
                self.account_role.setText("MANV chưa khớp tài khoản")
                self.account_phone.setText("")
        except Exception as error:
            self.account_name.setText(username or "Tài khoản")
            self.account_id.setText("Không tải được thông tin")
            self.account_role.setText(str(error))
            self.account_phone.setText("")

    def logout(self):
        """Đăng xuất, đóng phiên kết nối và trả người dùng về cửa sổ đăng nhập."""
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
