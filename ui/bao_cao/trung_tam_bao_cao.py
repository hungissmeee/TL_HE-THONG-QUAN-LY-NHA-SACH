"""Trung tâm báo cáo POS theo dạng bảng chứng từ."""

from datetime import date, datetime
from decimal import Decimal

import xlsxwriter
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QDateEdit, QComboBox, QLineEdit, QSpinBox,
    QFrame, QFileDialog, QMessageBox,
)

from core.bao_cao.repository import BaoCaoRepository
from core.bao_cao.service import BaoCaoService
from ui.calendar_utils import configure_date_edit_calendar
from ui.formatters import (
    format_report_money as money_text,
    format_number as number_text,
    format_report_date as date_text,
)
from ui.table_sort import SORT_ROLE, SortableTableWidgetItem


REPORTS = {
    "daily_sales": {
        "title": "BÁO CÁO CUỐI NGÀY BÁN HÀNG",
        "description": "Chi tiết hóa đơn, số lượng bán, giảm giá, tiền hoàn và số tiền còn lại theo hóa đơn gốc.",
        "method": "daily_sales_report",
        "headers": [
            "Mã hóa đơn", "Khách hàng", "Nhân viên", "Ngày lập", "Ca",
            "Số dòng", "SL bán", "Tiền hàng", "Giảm giá", "Doanh số",
            "Số phiếu trả", "SL hoàn tiền", "SL đổi hàng", "Tiền hoàn",
            "Còn lại sau hoàn", "Khách đưa", "Tiền thừa", "Trạng thái",
        ],
        "money_cols": [7, 8, 9, 13, 14, 15, 16],
        "number_cols": [5, 6, 10, 11, 12],
        "date_cols": [3],
        "sum_cols": [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
        "search": True,
        "employee": True,
    },
    "sales_time": {
        "title": "BÁO CÁO BÁN HÀNG THEO THỜI GIAN",
        "description": "Doanh số được nhóm theo ngày lập hóa đơn; phiếu trả được nhóm theo ngày xử lý. Chênh lệch theo kỳ không phải doanh thu thuần theo hóa đơn gốc.",
        "method": "sales_by_period_report",
        "headers": [
            "Thời gian", "SL đơn bán", "SL bán", "Tổng tiền hàng",
            "Giảm giá HĐ", "Doanh số", "SL phiếu trả", "SL hàng trả",
            "Giá trị hoàn", "Doanh số sau hoàn theo kỳ",
        ],
        "money_cols": [3, 4, 5, 8, 9],
        "number_cols": [1, 2, 6, 7],
        "date_cols": [0],
        "sum_cols": [1, 2, 3, 4, 5, 6, 7, 8, 9],
        "period": True,
    },
    "sales_employee": {
        "title": "BÁO CÁO BÁN HÀNG THEO NHÂN VIÊN",
        "description": "Doanh số ghi theo nhân viên lập hóa đơn; số phiếu đổi trả và tiền hoàn ghi theo nhân viên trực tiếp xử lý phiếu.",
        "method": "sales_by_employee_report",
        "headers": [
            "Mã NV", "Tên nhân viên", "SL hóa đơn", "SL bán",
            "Tiền hàng", "Giảm giá", "Doanh số", "SL phiếu trả",
            "SL hoàn tiền", "SL đổi hàng", "Tiền đã hoàn",
        ],
        "money_cols": [4, 5, 6, 10],
        "number_cols": [2, 3, 7, 8, 9],
        "sum_cols": [2, 3, 4, 5, 6, 7, 8, 9, 10],
        "search": True,
    },
    "sales_product": {
        "title": "BÁO CÁO BÁN HÀNG THEO SẢN PHẨM",
        "description": "Tập trung vào số hóa đơn, số lượng bán, hoàn tiền, đổi hàng và tồn hiện tại; không phân bổ tiền hoàn xuống từng sản phẩm.",
        "method": "sales_by_product_report",
        "headers": [
            "Mã hàng", "Mã vạch", "ISBN", "Tên hàng", "Đơn vị",
            "SL hóa đơn", "SL bán", "SL hoàn tiền", "SL đổi hàng", "Tồn hiện tại",
        ],
        "number_cols": [5, 6, 7, 8, 9],
        "sum_cols": [5, 6, 7, 8],
        "search": True,
    },
    "promotion": {
        "title": "BÁO CÁO HIỆU QUẢ KHUYẾN MÃI",
        "description": "Tổng hợp theo hóa đơn gốc trong kỳ; tiền hoàn được cộng lũy kế theo hóa đơn thuộc chương trình.",
        "method": "promotion_report",
        "headers": [
            "Mã khuyến mãi", "Tên chương trình", "Tỷ lệ giảm",
            "SL hóa đơn", "Tiền hàng", "Tiền giảm", "Doanh số",
            "Số phiếu trả", "Tiền hoàn lũy kế", "Còn lại sau hoàn",
        ],
        "money_cols": [4, 5, 6, 8, 9],
        "number_cols": [3, 7],
        "percent_cols": [2],
        "sum_cols": [3, 4, 5, 6, 7, 8, 9],
        "search": True,
    },
    "import_detail": {
        "title": "BÁO CÁO CHI TIẾT NHẬP HÀNG",
        "description": "Chi tiết từng dòng hàng trên phiếu nhập còn hiệu lực trong kỳ đã chọn.",
        "method": "import_detail_report",
        "headers": [
            "Mã phiếu nhập", "Ngày nhập", "Loại phiếu", "Nhà cung cấp",
            "Số HĐ NCC", "Nhân viên lập", "Mã hàng", "Tên hàng",
            "Số lượng", "Đơn giá nhập", "Thành tiền",
        ],
        "money_cols": [9, 10],
        "number_cols": [8],
        "date_cols": [1],
        "sum_cols": [8, 10],
        "search": True,
    },
    "import_supplier": {
        "title": "BÁO CÁO NHẬP HÀNG THEO NHÀ CUNG CẤP",
        "description": "Tổng hợp số phiếu, số lượng và trị giá nhập theo nhà cung cấp.",
        "method": "import_supplier_report",
        "headers": [
            "Mã NCC", "Nhà cung cấp", "Số điện thoại",
            "Số phiếu nhập", "Số lượng nhập", "Tổng trị giá nhập",
        ],
        "money_cols": [5],
        "number_cols": [3, 4],
        "sum_cols": [3, 4, 5],
        "search": True,
    },
    "return_detail": {
        "title": "BÁO CÁO CHI TIẾT ĐỔI TRẢ",
        "description": "Tiền hoàn chỉ lấy ở cấp phiếu đổi trả; không có đơn giá hoàn từng dòng sản phẩm.",
        "method": "return_detail_report",
        "headers": [
            "Mã phiếu đổi trả", "Ngày xử lý", "Hóa đơn gốc", "Nhân viên xử lý",
            "Lý do", "Số dòng", "SL hoàn tiền", "SL đổi hàng",
            "SL hàng nguyên vẹn", "SL hàng hỏng", "Tổng tiền hoàn",
        ],
        "money_cols": [10],
        "number_cols": [5, 6, 7, 8, 9],
        "date_cols": [1],
        "sum_cols": [5, 6, 7, 8, 9, 10],
        "search": True,
    },
    "current_inventory": {
        "title": "BÁO CÁO TỒN KHO HIỆN TẠI",
        "description": "Ảnh chụp số lượng tồn hiện tại; giá trị tồn ước tính theo giá nhập đang lưu trên sản phẩm.",
        "method": "current_inventory_report",
        "headers": [
            "Mã hàng", "Mã vạch", "Tên hàng", "Đơn vị",
            "Số lượng tồn", "Giá nhập hiện tại", "Giá bán",
            "Giá trị tồn ước tính", "Tình trạng",
        ],
        "money_cols": [5, 6, 7],
        "number_cols": [4],
        "sum_cols": [4, 7],
        "search": True,
        "stock_filter": True,
        "no_date": True,
    },
    "stock_movement": {
        "title": "BÁO CÁO NHẬP – XUẤT – TỒN KHO",
        "description": "Tồn đầu/cuối được tái dựng từ số tồn hiện tại và chứng từ còn hiệu lực. Giá trị tồn, xuất bán, hàng trả và đổi hàng là ước tính theo giá nhập hiện tại; trị giá nhập NCC lấy giá trên phiếu nhập.",
        "method": "stock_movement_report",
        "headers": [
            "Mã hàng", "Tên hàng", "Đơn vị",
            "Tồn đầu - SL", "Tồn đầu - Thành tiền*",
            "Nhập NCC - SL", "Nhập NCC - Thành tiền",
            "Khách trả - SL", "Khách trả - Thành tiền*",
            "Xuất bán - SL", "Xuất bán - Thành tiền*",
            "Xuất đổi - SL", "Xuất đổi - Thành tiền*",
            "Tồn cuối - SL", "Tồn cuối - Thành tiền*",
        ],
        "number_cols": [3, 5, 7, 9, 11, 13],
        "money_cols": [4, 6, 8, 10, 12, 14],
        "sum_cols": list(range(3, 15)),
        "group_headers": [
            (0, 2, "Thông tin hàng hóa"),
            (3, 4, "Tồn đầu kỳ"),
            (5, 6, "Nhập trong kỳ"),
            (7, 8, "Khách trả nhập lại"),
            (9, 10, "Xuất bán"),
            (11, 12, "Xuất đổi hàng"),
            (13, 14, "Tồn cuối kỳ"),
        ],
        "search": True,
    },
    "stock_card": {
        "title": "BÁO CÁO XUẤT NHẬP TỒN CHI TIẾT (THẺ KHO)",
        "description": "Theo dõi tồn đầu kỳ, từng lần nhập/bán/khách trả/đổi hàng và tồn sau giao dịch. Trị giá nhập nhà cung cấp lấy theo chứng từ; khách trả và trị giá xuất được ước tính theo giá nhập hiện lưu.",
        "method": "stock_card_report",
        "headers": [
            "Ngày giao dịch", "Loại giao dịch", "Mã chứng từ",
            "Mã hàng", "Tên hàng", "Tồn đầu kỳ", "SL nhập",
            "Giá trị nhập†", "SL xuất", "Giá trị xuất*", "Tồn sau giao dịch",
        ],
        "number_cols": [5, 6, 8, 10],
        "money_cols": [7, 9],
        "date_cols": [0],
        "sum_cols": [6, 7, 8, 9],
        "search": True,
    },
    "shift": {
        "title": "BÁO CÁO CUỐI CA",
        "description": "Số hóa đơn và doanh số theo ca; tiền cuối ca là số kiểm kê được ghi nhận, không tự động đồng nhất với doanh số.",
        "method": "shift_report",
        "headers": [
            "Mã ca", "Ngày làm", "Ca", "Giờ mở", "Giờ đóng",
            "Lượt nhân viên", "SL hóa đơn", "SL bán", "Doanh số",
            "Số phiếu trả", "Tiền hoàn", "Tiền đầu ca",
            "Tiền cuối ca", "Trạng thái chốt",
        ],
        "money_cols": [8, 10, 11, 12],
        "number_cols": [5, 6, 7, 9],
        "date_cols": [1],
        "sum_cols": [5, 6, 7, 8, 9, 10, 11, 12],
    },
}


class ReportCenterPage(QWidget):
    """Trung tâm báo cáo POS với menu xổ xuống, bộ lọc và bảng chứng từ."""

    GROUPS = [
        ("BÁO CÁO BÁN HÀNG", [
            ("daily_sales", "Báo cáo cuối ngày"),
            ("sales_time", "Bán hàng theo thời gian"),
            ("sales_employee", "Bán hàng theo nhân viên"),
            ("sales_product", "Bán hàng theo sản phẩm"),
            ("promotion", "Hiệu quả khuyến mãi"),
        ]),
        ("BÁO CÁO HÀNG HÓA / KHO", [
            ("stock_movement", "Báo cáo nhập xuất tồn"),
            ("stock_card", "Xuất nhập tồn chi tiết"),
            ("current_inventory", "Tồn kho hiện tại"),
        ]),
        ("BÁO CÁO NHẬP HÀNG", [
            ("import_detail", "Chi tiết nhập hàng"),
            ("import_supplier", "Nhập hàng theo nhà cung cấp"),
        ]),
        ("BÁO CÁO ĐỔI TRẢ", [
            ("return_detail", "Chi tiết đổi trả"),
        ]),
        ("BÁO CÁO CA LÀM VIỆC", [
            ("shift", "Báo cáo cuối ca"),
        ]),
    ]

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.service = BaoCaoService(BaoCaoRepository(db))
        self.current_report = "daily_sales"
        self.rows = []
        self._build_ui()
        self._load_employees()
        self._configure_report()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.right_panel = QWidget()
        self.right_panel.setObjectName("reportPaper")
        self.right_panel.setStyleSheet("""
            QWidget#reportPaper { background: #171B24; }
            QLabel { color: #D6DEE9; background: transparent; }
            QLabel#reportTitle { color: #F3F4F6; font-size: 18px; font-weight: 800; }
            QLabel#reportDescription { color: #AAB7C8; font-size: 10px; }
            QLabel#reportPeriod { color: #D6DEE9; font-size: 11px; font-weight: 600; }
            QFrame#reportFilters {
                background: #202938; border: 1px solid #39465A; border-radius: 5px;
            }
            QComboBox#reportCategoryCombo,
            QComboBox#reportTypeCombo {
                background: #263448; color: #E5E7EB;
                border: 1px solid #46546A; border-radius: 5px;
                padding: 7px 9px; min-height: 22px;
            }
            QComboBox#reportCategoryCombo:hover,
            QComboBox#reportTypeCombo:hover {
                border-color: #71839B;
            }
            QTableWidget#reportTable {
                background: #202938; alternate-background-color: #263448;
                color: #E5E7EB; gridline-color: #344256;
                border: 1px solid #39465A; selection-background-color: #3B526E;
                selection-color: #FFFFFF; font-size: 10px;
            }
            QTableWidget#reportGroupHeader {
                background: #29374B; color: #E5E7EB;
                border: 1px solid #39465A; font-weight: 700;
            }
            QTableWidget#reportFooter {
                background: #29374B; color: #F3F4F6;
                border: 1px solid #536174; font-weight: 800;
            }
            QHeaderView { background: #202938; color: #E5E7EB; }
            QHeaderView::section {
                background: #29374B; color: #E5E7EB; font-weight: 700;
                border: 1px solid #39465A; padding: 7px 6px;
            }
            QComboBox, QDateEdit, QSpinBox, QLineEdit {
                background: #263448; color: #E5E7EB;
                border: 1px solid #46546A; border-radius: 4px;
                padding: 6px 7px; min-height: 20px;
            }
            QComboBox QAbstractItemView {
                background: #202938; color: #E5E7EB;
                selection-background-color: #3B526E;
            }
            QToolTip {
                color: #F3F4F6; background: #29374B;
                border: 1px solid #536174;
            }
        """)
        right = QVBoxLayout(self.right_panel)
        right.setContentsMargins(12, 10, 12, 8)
        right.setSpacing(8)

        # Chọn nhóm và loại báo cáo bằng QComboBox giống form hóa đơn.
        selection_frame = QFrame()
        selection_frame.setObjectName("reportSelection")
        selection_layout = QHBoxLayout(selection_frame)
        selection_layout.setContentsMargins(0, 0, 0, 0)
        selection_layout.setSpacing(8)

        self.report_category_combo = QComboBox()
        self.report_category_combo.setObjectName("reportCategoryCombo")
        self.report_category_combo.setMinimumWidth(175)
        self.report_category_combo.addItem("Bán hàng", "BÁO CÁO BÁN HÀNG")
        for group_name, _ in self.GROUPS[1:]:
            label = group_name.replace("BÁO CÁO ", "").title()
            self.report_category_combo.addItem(label, group_name)

        self.report_combo = QComboBox()
        self.report_combo.setObjectName("reportTypeCombo")
        self.report_combo.setMinimumWidth(230)
        for report_key, report_title in self.GROUPS[0][1]:
            self.report_combo.addItem(report_title, report_key)

        self.report_category_combo.currentIndexChanged.connect(
            self._on_report_category_changed
        )
        self.report_combo.currentIndexChanged.connect(
            self._on_report_combo_changed
        )

        selection_layout.addWidget(QLabel("Nhóm báo cáo:"))
        selection_layout.addWidget(self.report_category_combo)
        selection_layout.addWidget(QLabel("Loại báo cáo:"))
        selection_layout.addWidget(self.report_combo)
        selection_layout.addStretch(1)
        right.addWidget(selection_frame)

        self.title_label = QLabel("BÁO CÁO CUỐI NGÀY BÁN HÀNG")
        self.title_label.setObjectName("reportTitle")
        right.addWidget(self.title_label)

        self.description_label = QLabel("")
        self.description_label.setObjectName("reportDescription")
        self.description_label.setWordWrap(True)
        right.addWidget(self.description_label)

        self.period_label = QLabel("")
        self.period_label.setObjectName("reportPeriod")
        self.period_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        right.addWidget(self.period_label)

        filter_frame = QFrame()
        filter_frame.setObjectName("reportFilters")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(8, 7, 8, 7)
        filter_layout.setSpacing(6)

        self.preset_combo = QComboBox()
        self.preset_combo.addItem("Tháng này", "this_month")
        self.preset_combo.addItem("Hôm nay", "today")
        self.preset_combo.addItem("7 ngày qua", "last_7_days")
        self.preset_combo.addItem("Tháng trước", "last_month")
        self.preset_combo.addItem("Tùy chọn", "custom")
        self.preset_combo.currentIndexChanged.connect(self._apply_date_preset)
        filter_layout.addWidget(self.preset_combo)

        today = QDate.currentDate()
        self.date_from = QDateEdit()
        configure_date_edit_calendar(self.date_from)
        self.date_from.setDisplayFormat("dd/MM/yyyy")
        self.date_from.setDate(QDate(today.year(), today.month(), 1))
        self.date_from_label = QLabel("Từ")
        filter_layout.addWidget(self.date_from_label)
        filter_layout.addWidget(self.date_from)

        self.date_to = QDateEdit()
        configure_date_edit_calendar(self.date_to)
        self.date_to.setDisplayFormat("dd/MM/yyyy")
        self.date_to.setDate(today)
        self.date_to_label = QLabel("Đến")
        filter_layout.addWidget(self.date_to_label)
        filter_layout.addWidget(self.date_to)

        self.period_combo = QComboBox()
        self.period_combo.addItem("Theo ngày", "day")
        self.period_combo.addItem("Theo tháng", "month")
        self.period_combo.addItem("Theo năm", "year")
        filter_layout.addWidget(self.period_combo)

        self.employee_combo = QComboBox()
        self.employee_combo.setMinimumWidth(130)
        self.employee_combo.addItem("Tất cả nhân viên", "")
        filter_layout.addWidget(self.employee_combo)

        self.stock_status_combo = QComboBox()
        self.stock_status_combo.addItem("Tất cả hàng hóa", "all")
        self.stock_status_combo.addItem("Sắp hết hàng", "low")
        self.stock_status_combo.addItem("Hết hàng", "out")
        filter_layout.addWidget(self.stock_status_combo)

        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(1, 100000)
        self.threshold_spin.setValue(5)
        self.threshold_spin.setPrefix("Ngưỡng: ")
        self.threshold_spin.setMaximumWidth(120)
        filter_layout.addWidget(self.threshold_spin)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm mã / tên / chứng từ...")
        self.search_input.setMinimumWidth(160)
        filter_layout.addWidget(self.search_input, 1)

        self.view_button = QPushButton("Xem báo cáo")
        self.view_button.clicked.connect(self.refresh_data)
        filter_layout.addWidget(self.view_button)

        self.export_button = QPushButton("Xuất Excel")
        self.export_button.clicked.connect(self.export_xlsx)
        filter_layout.addWidget(self.export_button)

        right.addWidget(filter_frame)

        self.filter_note = QLabel("")
        self.filter_note.setWordWrap(True)
        self.filter_note.setStyleSheet("color: #AAB7C8; font-size: 9px;")
        right.addWidget(self.filter_note)

        # Một khung bảng duy nhất: tiêu đề nhóm cột, dữ liệu và hàng tổng cộng
        # nối liền nhau, không có khoảng cách như ba bảng độc lập.
        self.report_table_frame = QFrame()
        self.report_table_frame.setObjectName("reportTableFrame")
        self.report_table_frame.setStyleSheet(
            "QFrame#reportTableFrame { border: 1px solid #39465A; "
            "border-radius: 5px; background: #202938; }"
        )
        report_table_layout = QVBoxLayout(self.report_table_frame)
        report_table_layout.setContentsMargins(0, 0, 0, 0)
        report_table_layout.setSpacing(0)

        self.group_header = QTableWidget(1, 0)
        self.group_header.setObjectName("reportGroupHeader")
        self.group_header.setFixedHeight(30)
        self.group_header.verticalHeader().setVisible(False)
        self.group_header.horizontalHeader().setVisible(False)
        self.group_header.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.group_header.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.group_header.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.group_header.setStyleSheet(
            "QTableWidget { background: #29374B; color: #E5E7EB; "
            "border: none; border-bottom: 1px solid #39465A; font-weight: 700; }"
        )
        self.group_header.hide()
        report_table_layout.addWidget(self.group_header)

        self.table = QTableWidget(0, 0)
        self.table.setObjectName("reportTable")
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setMinimumSectionSize(78)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setFrameShape(QFrame.Shape.NoFrame)
        self.table.setSortingEnabled(True)
        report_table_layout.addWidget(self.table, 1)

        self.footer = QTableWidget(1, 0)
        self.footer.setObjectName("reportFooter")
        self.footer.setFixedHeight(32)
        self.footer.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.footer.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.footer.verticalHeader().setVisible(False)
        self.footer.horizontalHeader().setVisible(False)
        self.footer.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.footer.setStyleSheet("""
            QTableWidget {
                background: #29374B; color: #F3F4F6;
                border: none; border-top: 1px solid #536174;
                font-weight: 800;
            }
        """)
        report_table_layout.addWidget(self.footer)
        right.addWidget(self.report_table_frame, 1)
        self.table.horizontalHeader().sectionResized.connect(self._sync_footer_widths)
        self.table.horizontalScrollBar().valueChanged.connect(
            self._sync_horizontal_scroll
        )
        self.table.horizontalScrollBar().rangeChanged.connect(
            self._sync_horizontal_scroll_range
        )

        self.status_label = QLabel("Chọn nhóm báo cáo ở thanh phía trên.")
        self.status_label.setStyleSheet("color: #AAB7C8; font-size: 10px;")
        right.addWidget(self.status_label)
        root.addWidget(self.right_panel, 1)

    def _load_employees(self):
        try:
            for code, name in self.service.employees():
                self.employee_combo.addItem(f"{name} ({code})", str(code))
        except Exception:
            # Các báo cáo không cần lọc nhân viên vẫn có thể mở; lỗi sẽ hiện khi tải.
            pass

    def _apply_date_preset(self, *_):
        preset = self.preset_combo.currentData()
        today = QDate.currentDate()
        if preset == "today":
            start = end = today
        elif preset == "last_7_days":
            start, end = today.addDays(-6), today
        elif preset == "last_month":
            first_this_month = QDate(today.year(), today.month(), 1)
            end = first_this_month.addDays(-1)
            start = QDate(end.year(), end.month(), 1)
        elif preset == "this_month":
            start, end = QDate(today.year(), today.month(), 1), today
        else:
            return
        self.date_from.setDate(start)
        self.date_to.setDate(end)

    def _on_report_category_changed(self, *_):
        group_name = self.report_category_combo.currentData()
        group = next(
            (children for name, children in self.GROUPS if name == group_name),
            [],
        )
        self.report_combo.blockSignals(True)
        self.report_combo.clear()
        for report_key, report_title in group:
            self.report_combo.addItem(report_title, report_key)
        self.report_combo.blockSignals(False)
        if group:
            self._select_report(group[0][0])

    def _on_report_combo_changed(self, *_):
        report_key = self.report_combo.currentData()
        if report_key:
            self._select_report(report_key)

    def _select_report(self, key):
        if key not in REPORTS:
            return
        if key == self.current_report:
            return
        self.current_report = key
        self._configure_report()

    def _configure_report(self):
        definition = REPORTS[self.current_report]
        self.title_label.setText(definition["title"])
        self.description_label.setText(definition["description"])

        selected_group = next(
            (
                (group_name, children)
                for group_name, children in self.GROUPS
                if any(key == self.current_report for key, _ in children)
            ),
            self.GROUPS[0],
        )
        self.report_category_combo.blockSignals(True)
        category_index = self.report_category_combo.findData(selected_group[0])
        self.report_category_combo.setCurrentIndex(max(0, category_index))
        self.report_category_combo.blockSignals(False)

        self.report_combo.blockSignals(True)
        self.report_combo.clear()
        selected_index = 0
        for index, (report_key, report_title) in enumerate(selected_group[1]):
            self.report_combo.addItem(report_title, report_key)
            if report_key == self.current_report:
                selected_index = index
        self.report_combo.setCurrentIndex(selected_index)
        self.report_combo.blockSignals(False)

        is_no_date = definition.get("no_date", False)
        for widget in (
            self.preset_combo, self.date_from_label, self.date_from,
            self.date_to_label, self.date_to,
        ):
            widget.setVisible(not is_no_date)
        self.period_combo.setVisible(bool(definition.get("period")))
        self.employee_combo.setVisible(bool(definition.get("employee")))
        self.stock_status_combo.setVisible(bool(definition.get("stock_filter")))
        self.threshold_spin.setVisible(bool(definition.get("stock_filter")))
        self.search_input.setVisible(bool(definition.get("search")))
        self.search_input.clear()
        self._build_table_headers(definition)
        note_by_report = {
            "stock_movement": (
                "CSDL chưa có nhật ký điều chỉnh kho riêng; tồn đầu/tồn cuối được tái dựng từ SLTON và chứng từ. "
                "Thành tiền tồn, khách trả, xuất bán và xuất đổi là ước tính theo giá nhập hiện lưu; trị giá nhập NCC lấy theo phiếu nhập."
            ),
            "stock_card": (
                "Tồn đầu và tồn sau giao dịch được tái dựng từ SLTON cùng chứng từ đã lưu. "
                "Giá trị nhập NCC (†) lấy theo đơn giá phiếu nhập; khách trả nhập lại và giá trị xuất ( * ) ước tính theo giá nhập hiện lưu."
            ),
            "current_inventory": (
                "Đây là ảnh chụp số tồn hiện tại. Giá trị tồn được ước tính bằng số lượng tồn nhân giá nhập hiện lưu; "
                "không phải giá vốn lịch sử và không gồm điều chỉnh tồn thực hiện ngoài hệ thống."
            ),
        }
        self.filter_note.setText(note_by_report.get(self.current_report, ""))
        self.refresh_data()

    def _build_table_headers(self, definition):
        headers = definition["headers"]
        self.table.setSortingEnabled(False)
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.footer.setColumnCount(len(headers))
        self.footer.setRowCount(1)

        money_cols = set(definition.get("money_cols", []))
        number_cols = set(definition.get("number_cols", []))
        date_cols = set(definition.get("date_cols", []))
        for col, header in enumerate(headers):
            if col in money_cols:
                width = 132
            elif col in number_cols:
                width = 88
            elif col in date_cols:
                width = 132
            elif any(token in header.lower() for token in ("tên", "nhà cung cấp", "lý do")):
                width = 168
            elif "mã" in header.lower():
                width = 112
            else:
                width = 122
            self.table.setColumnWidth(col, width)

        groups = definition.get("group_headers", [])
        self.group_header.clear()
        self.group_header.clearSpans()
        self.group_header.setColumnCount(len(headers))
        self.group_header.setRowCount(1)
        self.group_header.setHorizontalHeaderLabels([""] * len(headers))
        if groups:
            self.group_header.show()
            for start_col, end_col, label in groups:
                if end_col > start_col:
                    self.group_header.setSpan(0, start_col, 1, end_col - start_col + 1)
                item = QTableWidgetItem(label)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.group_header.setItem(0, start_col, item)
        else:
            self.group_header.hide()

        self.table.setSortingEnabled(True)
        self._sync_footer_widths()

    def _date_values(self):
        start, end = self.date_from.date(), self.date_to.date()
        if start > end:
            raise ValueError("Ngày bắt đầu không được lớn hơn ngày kết thúc.")
        return start.toString("yyyy-MM-dd"), end.toString("yyyy-MM-dd")

    def _load_rows(self):
        definition = REPORTS[self.current_report]
        method = definition["method"]
        keyword = self.search_input.text().strip() if definition.get("search") else ""
        if definition.get("no_date"):
            return self.service.current_inventory_report(
                self.threshold_spin.value(),
                self.stock_status_combo.currentData(),
                keyword,
            )

        start, end = self._date_values()
        if self.current_report == "daily_sales":
            employee = self.employee_combo.currentData() or None
            return self.service.daily_sales_report(start, end, employee, keyword)
        if self.current_report == "sales_time":
            return self.service.sales_by_period_report(
                start, end, self.period_combo.currentData()
            )
        if method in {
            "sales_by_employee_report", "sales_by_product_report",
            "promotion_report", "return_detail_report",
            "import_detail_report", "import_supplier_report",
            "stock_movement_report", "stock_card_report",
        }:
            return getattr(self.service, method)(start, end, keyword)
        return getattr(self.service, method)(start, end)

    def refresh_data(self):
        try:
            self.view_button.setEnabled(False)
            self.status_label.setText("Đang tải dữ liệu báo cáo...")
            self.rows = list(self._load_rows() or [])
            self._fill_table()
            definition = REPORTS[self.current_report]
            self.period_label.setText(
                "TỒN KHO TẠI THỜI ĐIỂM HIỆN TẠI"
                if definition.get("no_date")
                else f"KỲ BÁO CÁO: {self.date_from.date().toString('dd/MM/yyyy')} "
                     f"– {self.date_to.date().toString('dd/MM/yyyy')}"
            )
            self.status_label.setText(f"Có {len(self.rows):,} dòng dữ liệu.")
        except Exception as exc:
            self.rows = []
            self._fill_table()
            self.status_label.setText("Không thể tải báo cáo.")
            QMessageBox.critical(self, "Lỗi báo cáo", str(exc))
        finally:
            self.view_button.setEnabled(True)

    def _format_value(self, value, column, definition):
        if value is None:
            return ""
        if column in definition.get("date_cols", []):
            return date_text(value)
        if column in definition.get("money_cols", []):
            return money_text(value)
        if column in definition.get("percent_cols", []):
            return f"{float(value):.2f}%"
        if column in definition.get("number_cols", []):
            return number_text(value)
        return str(value)

    def _fill_table(self):
        definition = REPORTS[self.current_report]
        headers = definition["headers"]
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for values in self.rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, value in enumerate(values):
                item = SortableTableWidgetItem(self._format_value(value, col, definition))
                item.setData(Qt.ItemDataRole.UserRole, value)
                item.setData(SORT_ROLE, value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col in definition.get("money_cols", []) or col in definition.get("number_cols", []):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, col, item)
        self.table.setSortingEnabled(True)
        self._fill_footer()
        self._sync_footer_widths()

    def _fill_footer(self):
        definition = REPORTS[self.current_report]
        cols = self.table.columnCount()
        self.footer.setColumnCount(cols)
        self.footer.setRowCount(1)
        totals = {}
        for col in definition.get("sum_cols", []):
            total = Decimal("0")
            for row in self.rows:
                try:
                    total += Decimal(str(row[col] or 0))
                except Exception:
                    continue
            totals[col] = total
        for col in range(cols):
            value = "TỔNG CỘNG" if col == 0 else ""
            if col in totals:
                value = self._format_value(totals[col], col, definition)
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if col in definition.get("money_cols", []) or col in definition.get("number_cols", []):
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.footer.setItem(0, col, item)
        self.footer.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def _sync_footer_widths(self, *_):
        self.footer.setColumnCount(self.table.columnCount())
        self.group_header.setColumnCount(self.table.columnCount())
        for col in range(self.table.columnCount()):
            width = self.table.columnWidth(col)
            self.footer.setColumnWidth(col, width)
            self.group_header.setColumnWidth(col, width)
        viewport_width = max(100, self.table.viewport().width())
        self.footer.setFixedWidth(viewport_width)
        self.group_header.setFixedWidth(viewport_width)
        self._sync_horizontal_scroll_range(
            0, self.table.horizontalScrollBar().maximum()
        )

    def _sync_horizontal_scroll_range(self, minimum, maximum):
        page_step = self.table.horizontalScrollBar().pageStep()
        value = self.table.horizontalScrollBar().value()
        for target in (self.footer, self.group_header):
            scrollbar = target.horizontalScrollBar()
            scrollbar.setRange(minimum, maximum)
            scrollbar.setPageStep(page_step)
            scrollbar.setValue(value)

    def _sync_horizontal_scroll(self, value):
        for target in (self.footer, self.group_header):
            target.horizontalScrollBar().setValue(value)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "table"):
            self._sync_footer_widths()

    def export_xlsx(self):
        if not self.rows:
            QMessageBox.information(self, "Xuất Excel", "Báo cáo hiện không có dữ liệu.")
            return
        definition = REPORTS[self.current_report]
        safe_name = self.current_report.replace("-", "_")
        default_name = f"{safe_name}_{date.today():%Y%m%d}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self, "Xuất báo cáo Excel", default_name, "Excel Workbook (*.xlsx)"
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        try:
            self._write_workbook(path, definition)
            QMessageBox.information(self, "Xuất Excel", f"Đã xuất báo cáo:\\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi xuất Excel", str(exc))

    def _write_workbook(self, path, definition):
        workbook = xlsxwriter.Workbook(path)
        worksheet = workbook.add_worksheet("Bao cao")
        worksheet.hide_gridlines(2)
        worksheet.set_landscape()
        worksheet.fit_to_pages(1, 0)
        worksheet.repeat_rows(0, 5)

        title_fmt = workbook.add_format({
            "bold": True, "font_size": 16, "align": "center",
            "valign": "vcenter", "font_color": "#17324D",
        })
        subtitle_fmt = workbook.add_format({
            "font_size": 10, "align": "center", "font_color": "#526477",
        })
        group_fmt = workbook.add_format({
            "bold": True, "align": "center", "valign": "vcenter",
            "bg_color": "#DCE7F0", "border": 1, "border_color": "#AEBCCB",
            "text_wrap": True,
        })
        header_fmt = workbook.add_format({
            "bold": True, "align": "center", "valign": "vcenter",
            "bg_color": "#EAF0F5", "border": 1, "border_color": "#BAC7D3",
            "text_wrap": True,
        })
        text_fmt = workbook.add_format({"border": 1, "border_color": "#E0E6EC"})
        number_fmt = workbook.add_format({
            "border": 1, "border_color": "#E0E6EC", "num_format": "#,##0",
        })
        money_fmt = workbook.add_format({
            "border": 1, "border_color": "#E0E6EC", "num_format": "#,##0.00",
        })
        date_fmt = workbook.add_format({
            "border": 1, "border_color": "#E0E6EC", "num_format": "dd/mm/yyyy hh:mm",
        })
        percent_fmt = workbook.add_format({
            "border": 1, "border_color": "#E0E6EC", "num_format": "0.00%",
        })
        total_text_fmt = workbook.add_format({
            "bold": True, "bg_color": "#E6EDF3", "top": 1, "bottom": 1,
        })
        total_number_fmt = workbook.add_format({
            "bold": True, "bg_color": "#E6EDF3", "top": 1, "bottom": 1,
            "num_format": "#,##0",
        })
        total_money_fmt = workbook.add_format({
            "bold": True, "bg_color": "#E6EDF3", "top": 1, "bottom": 1,
            "num_format": "#,##0.00",
        })

        headers = definition["headers"]
        last_col = len(headers) - 1
        worksheet.merge_range(0, 0, 0, last_col, definition["title"], title_fmt)
        worksheet.set_row(0, 28)
        worksheet.merge_range(1, 0, 1, last_col, "HỆ THỐNG QUẢN LÝ NHÀ SÁCH", subtitle_fmt)
        period_text = (
            "Tồn kho tại thời điểm xuất báo cáo"
            if definition.get("no_date")
            else f"Kỳ báo cáo: {self.date_from.date().toString('dd/MM/yyyy')} – "
                 f"{self.date_to.date().toString('dd/MM/yyyy')}"
        )
        worksheet.merge_range(2, 0, 2, last_col, period_text, subtitle_fmt)
        worksheet.merge_range(
            3, 0, 3, last_col,
            f"Ngày xuất: {datetime.now():%d/%m/%Y %H:%M:%S}",
            subtitle_fmt,
        )

        group_row, header_row, data_row = 4, 5, 6
        group_headers = definition.get("group_headers")
        if group_headers:
            for start_col, end_col, label in group_headers:
                if start_col == end_col:
                    worksheet.merge_range(group_row, start_col, header_row, end_col, label, group_fmt)
                else:
                    worksheet.merge_range(group_row, start_col, group_row, end_col, label, group_fmt)
            for col, header in enumerate(headers):
                if not any(a <= col <= b for a, b, _ in group_headers):
                    worksheet.merge_range(group_row, col, header_row, col, header, group_fmt)
                else:
                    worksheet.write(header_row, col, header, header_fmt)
        else:
            worksheet.merge_range(group_row, 0, group_row, last_col, "CHI TIẾT BÁO CÁO", group_fmt)
            for col, header in enumerate(headers):
                worksheet.write(header_row, col, header, header_fmt)

        for col, header in enumerate(headers):
            width = max(12, min(34, len(header) + 3))
            if col in definition.get("money_cols", []):
                width = max(width, 17)
            worksheet.set_column(col, col, width)

        for row_index, row in enumerate(self.rows, start=data_row):
            for col, value in enumerate(row):
                if value is None:
                    worksheet.write_blank(row_index, col, None, text_fmt)
                elif col in definition.get("date_cols", []) and isinstance(value, (datetime, date)):
                    if isinstance(value, date) and not isinstance(value, datetime):
                        value = datetime.combine(value, datetime.min.time())
                    worksheet.write_datetime(row_index, col, value, date_fmt)
                elif isinstance(value, (int, float, Decimal)):
                    number = float(value)
                    if col in definition.get("money_cols", []):
                        fmt = money_fmt
                    elif col in definition.get("number_cols", []):
                        fmt = number_fmt
                    elif col in definition.get("percent_cols", []):
                        fmt = percent_fmt
                        number = number / 100.0
                    else:
                        fmt = text_fmt
                    worksheet.write_number(row_index, col, number, fmt)
                else:
                    worksheet.write(row_index, col, str(value), text_fmt)

        total_row = data_row + len(self.rows)
        sum_cols = set(definition.get("sum_cols", []))
        worksheet.write(total_row, 0, "TỔNG CỘNG", total_text_fmt)
        for col in range(1, len(headers)):
            if col in sum_cols:
                col_letter = xlsxwriter.utility.xl_col_to_name(col)
                formula = f"=SUM({col_letter}{data_row + 1}:{col_letter}{total_row})"
                cached = sum(
                    (Decimal(str(row[col] or 0)) for row in self.rows),
                    Decimal("0"),
                )
                fmt = total_money_fmt if col in definition.get("money_cols", []) else total_number_fmt
                worksheet.write_formula(total_row, col, formula, fmt, float(cached))
            else:
                worksheet.write_blank(total_row, col, None, total_text_fmt)

        worksheet.autofilter(header_row, 0, max(header_row, total_row - 1), last_col)
        worksheet.freeze_panes(data_row, 1)
        worksheet.set_margins(0.25, 0.25, 0.5, 0.5)
        worksheet.fit_to_pages(1, 0)
        worksheet.set_footer("&LBookHub - Báo cáo nội bộ&CTrang &P / &N")
        workbook.close()
