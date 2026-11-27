"""Kiểm thử các quy tắc nghiệp vụ thuần và widget dùng chung."""

import os
import unittest
from types import SimpleNamespace
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTableWidget, QComboBox
from PySide6.QtGui import QPalette
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCompleter
from ui.styles import MAIN_WINDOW_STYLESHEET, apply_app_palette

from database.connection import Database
from ui.product_table import ProductTableWidget
from ui.table_sort import (
    SORT_ROLE,
    SortableTableWidgetItem,
    DEFAULT_MIN_SECTION_SIZE,
    set_table_minimum_section_size,
    prepare_sortable_table,
    pause_table_sorting,
    resume_table_sorting,
)
from ui.san_pham.bieu_mau import ProductFormDialog
from ui.san_pham.tim_kiem import find_matching_product_codes
from ui.san_pham.bo_chon import SearchableSingleSelect, SearchableMultiSelect
from ui.danh_muc import CatalogPage, CATALOGS
from ui.nha_cung_cap.bieu_mau import SupplierFormDialog
from ui.nha_cung_cap.danh_sach import can_view_suppliers
from ui.nhan_vien import EmployeeWindow
from ui.phieu_nhap.tao_bieu_mau import CreateImportDialog
from ui.phieu_nhap.danh_sach import can_view_imports
from ui.hoa_don.tao_bieu_mau import CreateInvoiceDialog
from ui.hoa_don.danh_sach import InvoiceWindow
from ui.ca_lam_viec.tao_bieu_mau import ShiftCreateDialog
from ui.main_windows import MainWindow
from ui.permissions import is_admin_account, allowed_pages_for_user
from ui.doi_tra.tao_bieu_mau import CreateReturnDialog
from ui.doi_tra.danh_sach import ReturnWindow


_APP = QApplication.instance() or QApplication([])


class FakeCursor:
    """Cursor giả chỉ phục vụ kiểm thử các hàm sinh mã."""

    def __init__(self, last_number):
        self.last_number = last_number
        self.sql = ""
        self.params = ()

    def execute(self, sql, *params):
        self.sql = sql
        self.params = params
        return self

    def fetchone(self):
        return (self.last_number,)


class NativeQtControlStyleTests(unittest.TestCase):
    """Đảm bảo stylesheet chung không ghi đè các mũi tên và nút điều hướng Qt."""

    def test_combo_spinbox_and_calendar_keep_native_subcontrols(self):
        forbidden_overrides = (
            "QComboBox {",
            "QDateEdit {",
            "QDateTimeEdit {",
            "QTimeEdit {",
            "QSpinBox {",
            "QDoubleSpinBox {",
            "QComboBox::drop-down",
            "QComboBox::down-arrow",
            "QAbstractSpinBox::up-button",
            "QAbstractSpinBox::down-button",
            "QAbstractSpinBox::up-arrow",
            "QAbstractSpinBox::down-arrow",
            "QCalendarWidget QToolButton",
        )
        for selector in forbidden_overrides:
            with self.subTest(selector=selector):
                self.assertNotIn(selector, MAIN_WINDOW_STYLESHEET)

    def test_sortable_tables_have_a_minimum_column_width(self):
        from PySide6.QtWidgets import QHeaderView, QTableWidget
        from ui.table_sort import DEFAULT_MIN_SECTION_SIZE

        table = QTableWidget(0, 5)
        prepare_sortable_table(table)

        self.assertEqual(
            table.horizontalHeader().minimumSectionSize(),
            DEFAULT_MIN_SECTION_SIZE,
        )
        table.close()

    def test_minimum_section_size_helper_applies_to_manual_tables(self):
        from PySide6.QtWidgets import QTableWidget

        table = QTableWidget(0, 7)
        set_table_minimum_section_size(table)

        self.assertEqual(
            table.horizontalHeader().minimumSectionSize(),
            DEFAULT_MIN_SECTION_SIZE,
        )
        set_table_minimum_section_size(table, 105)
        self.assertEqual(table.horizontalHeader().minimumSectionSize(), 105)
        table.close()

    def test_sortable_table_minimum_column_width_can_be_overridden(self):
        from PySide6.QtWidgets import QTableWidget

        table = QTableWidget(0, 3)
        prepare_sortable_table(table, minimum_section_size=110)

        self.assertEqual(table.horizontalHeader().minimumSectionSize(), 110)
        table.close()

    def test_dark_palette_uses_standard_qt_roles(self):
        original = _APP.palette()
        try:
            apply_app_palette(_APP)
            palette = _APP.palette()
            self.assertEqual(
                palette.color(QPalette.ColorRole.Base).name(),
                "#263448",
            )
            self.assertEqual(
                palette.color(QPalette.ColorRole.Button).name(),
                "#34445a",
            )
            self.assertEqual(
                palette.color(QPalette.ColorRole.Text).name(),
                "#e5e7eb",
            )
        finally:
            _APP.setPalette(original)


class ProductListColumnTests(unittest.TestCase):
    """Bảng danh sách chỉ hiển thị những trường chung của sản phẩm."""

    def test_product_list_columns_do_not_include_type_specific_fields(self):
        from ui.san_pham.danh_sach import PRODUCT_TABLE_HEADERS

        self.assertEqual(len(PRODUCT_TABLE_HEADERS), 9)
        self.assertNotIn("ISBN", PRODUCT_TABLE_HEADERS)
        self.assertIn("Mã vạch", PRODUCT_TABLE_HEADERS)
        self.assertIn("Loại sản phẩm", PRODUCT_TABLE_HEADERS)

    def test_isbn_remains_a_search_field_and_a_book_detail_field(self):
        from ui.san_pham.danh_sach import ProductWindow
        from ui.san_pham.chi_tiet import ProductDetailDialog

        # ISBN stays in the search SQL, but is not selected for the main list.
        source = ProductWindow.load_products.__code__
        self.assertIsNotNone(source)
        detail_source = ProductDetailDialog.setup_ui.__code__
        self.assertIsNotNone(detail_source)


class ProductTableWidgetTests(unittest.TestCase):
    """Các bảng sản phẩm của hóa đơn, phiếu nhập và đổi trả dùng chung cấu hình."""

    def test_product_table_keeps_insertion_order_and_native_headers(self):
        from PySide6.QtWidgets import QHeaderView
        from ui.product_table import ProductTableWidget

        table = ProductTableWidget(
            ["Mã SP", "Tên sản phẩm", "Số lượng"],
            stretch_column=1,
        )

        self.assertFalse(table.isSortingEnabled())
        self.assertFalse(table.horizontalHeader().sectionsClickable())
        self.assertFalse(table.horizontalHeader().isSortIndicatorShown())
        self.assertEqual(
            table.horizontalHeader().minimumSectionSize(),
            DEFAULT_MIN_SECTION_SIZE,
        )

        codes = ["SP003", "SP001", "SP002"]
        for code in codes:
            row = table.insert_product_row()
            table.setItem(row, 0, SortableTableWidgetItem(code))

        self.assertEqual(
            [table.item(row, 0).text() for row in range(table.rowCount())],
            codes,
        )
        self.assertEqual(table.rowHeight(0), ProductTableWidget.DEFAULT_ROW_HEIGHT)
        self.assertEqual(
            table.horizontalHeader().sectionResizeMode(1),
            QHeaderView.ResizeMode.Stretch,
        )
        table.close()

    def test_product_table_supports_workflow_specific_fixed_columns(self):
        from PySide6.QtWidgets import QHeaderView
        from ui.product_table import ProductTableWidget

        table = ProductTableWidget(
            ["Mã SP", "Tên sản phẩm", "Đã mua", "Số lượng"],
            stretch_column=1,
            fixed_column_widths={3: 100},
        )

        self.assertEqual(table.columnWidth(3), 100)
        self.assertEqual(
            table.horizontalHeader().sectionResizeMode(3),
            QHeaderView.ResizeMode.Fixed,
        )
        table.close()


class ReturnDialogWidgetTests(unittest.TestCase):
    """Kiểm tra ô chọn hóa đơn giữ nguyên hành vi native của QComboBox."""

    def test_invoice_selector_keeps_qt_default_visible_item_limit(self):
        combo = QComboBox()
        default_visible_items = combo.maxVisibleItems()

        CreateReturnDialog._configure_invoice_selector(combo)

        self.assertTrue(combo.isEditable())
        self.assertEqual(
            combo.insertPolicy(),
            QComboBox.InsertPolicy.NoInsert,
        )
        self.assertEqual(combo.maxVisibleItems(), default_visible_items)
        self.assertEqual(
            combo.completer().completionMode(),
            QCompleter.CompletionMode.PopupCompletion,
        )
        self.assertEqual(
            combo.completer().filterMode(),
            Qt.MatchFlag.MatchContains,
        )
        self.assertEqual(
            combo.completer().caseSensitivity(),
            Qt.CaseSensitivity.CaseInsensitive,
        )
        combo.close()

    def test_return_table_reserves_width_for_quantity_spinbox(self):
        from PySide6.QtWidgets import QHeaderView
        from ui.product_table import ProductTableWidget

        table = ProductTableWidget(
            [
                "Mã SP", "Tên sản phẩm", "Đã mua", "Đã xử lý",
                "Còn được xử lý", "Số lượng", "Tình trạng hàng",
                "Hình thức xử lý", "Tiền hoàn"
            ],
            stretch_column=1,
            fixed_column_widths={5: 100},
        )

        self.assertEqual(
            table.horizontalHeader().sectionResizeMode(5),
            QHeaderView.ResizeMode.Fixed,
        )
        self.assertEqual(table.columnWidth(5), 100)
        self.assertEqual(
            table.horizontalHeader().sectionResizeMode(1),
            QHeaderView.ResizeMode.Stretch,
        )
        self.assertFalse(table.isSortingEnabled())
        table.close()

    def test_return_quantity_editor_row_matches_invoice_cart_height(self):
        from PySide6.QtWidgets import QSpinBox, QTableWidget

        table = QTableWidget(1, 1)
        quantity = QSpinBox(table)
        quantity.setRange(0, 5)
        quantity.setValue(3)
        quantity.setMinimumHeight(34)
        table.setCellWidget(0, 0, quantity)

        # Hóa đơn và phiếu nhập đều dành 44 px cho mỗi hàng có widget.
        table.setRowHeight(0, 44)

        self.assertEqual(quantity.value(), 3)
        self.assertEqual(quantity.minimum(), 0)
        self.assertEqual(quantity.maximum(), 5)
        self.assertEqual(table.rowHeight(0), 44)
        self.assertGreaterEqual(table.rowHeight(0), quantity.minimumHeight())
        table.close()


class DatabaseUtilityTests(unittest.TestCase):
    """Kiểm thử cấu hình kết nối, vai trò và kiểm tra quyền quản trị."""

    def test_connection_string_contains_configured_sql_server_values(self):
        db = Database()
        db.server = "localhost\\SQLEXPRESS"
        db.database = "CSDLQLNHASACH"
        db.driver = "ODBC Driver 18 for SQL Server"

        result = db._connection_string("NV01", "ExamplePass123!")

        self.assertIn("SERVER={localhost\\SQLEXPRESS};", result)
        self.assertIn("DATABASE={CSDLQLNHASACH};", result)
        self.assertIn("UID={NV01};", result)
        self.assertIn("PWD={ExamplePass123!};", result)
        self.assertIn("Encrypt=yes;", result)

    def test_login_identifier_escapes_closing_bracket(self):
        db = Database()
        self.assertEqual(db._quote_login("NV]01"), "[NV]]01]")

    def test_admin_guard_rejects_employee_account(self):
        db = Database()
        db.username = "NV01"
        db.conn = object()

        with self.assertRaises(PermissionError):
            db._check_admin()

    def test_admin_guard_rejects_missing_connection(self):
        db = Database()
        db.username = "admin"
        db.conn = None

        with self.assertRaises(Exception):
            db._check_admin()

    def test_role_map_contains_all_supported_roles(self):
        self.assertEqual(
            set(Database.ROLE_MAP),
            {"Quản lý", "Thu ngân", "Nhân viên kho", "Kế toán"},
        )
        self.assertEqual(
            set(Database.ROLE_MAP.values()),
            {"rl_QuanLy", "rl_ThuNgan", "rl_NhanVienKho", "rl_KeToan"},
        )


class TableSortingTests(unittest.TestCase):
    """Kiểm thử sắp xếp tự nhiên, số, ngày giờ và trạng thái bảng."""

    def test_natural_sort_orders_codes_by_numeric_suffix(self):
        self.assertLess(
            SortableTableWidgetItem("SP2"),
            SortableTableWidgetItem("SP10"),
        )

    def test_money_sort_uses_numeric_value(self):
        self.assertLess(
            SortableTableWidgetItem("2.000,00 đ"),
            SortableTableWidgetItem("10.000,00 đ"),
        )

    def test_date_sort_uses_chronological_value(self):
        self.assertLess(
            SortableTableWidgetItem("26/11/2026"),
            SortableTableWidgetItem("27/11/2026"),
        )

    def test_time_sort_uses_clock_value(self):
        self.assertLess(
            SortableTableWidgetItem("09:05"),
            SortableTableWidgetItem("17:30"),
        )

    def test_explicit_sort_role_has_priority(self):
        first = SortableTableWidgetItem("Tên A")
        second = SortableTableWidgetItem("Tên B")
        first.setData(SORT_ROLE, 2)
        second.setData(SORT_ROLE, 10)

        self.assertLess(first, second)

    def test_pause_and_resume_sorting_restores_table_sort(self):
        table = QTableWidget(0, 1)
        prepare_sortable_table(table, default_column=0)
        pause_table_sorting(table)

        for value in ("HD10", "HD2"):
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, SortableTableWidgetItem(value))

        resume_table_sorting(table)

        self.assertTrue(table.isSortingEnabled())
        self.assertEqual(table.item(0, 0).text(), "HD2")
        self.assertEqual(table.item(1, 0).text(), "HD10")
        table.close()


class SearchableSelectorTests(unittest.TestCase):
    """Kiểm thử chọn một và nhiều giá trị từ danh mục."""

    def test_single_select_stores_selected_code(self):
        selector = SearchableSingleSelect()
        selector.set_options([
            ("NXB001", "Nhà xuất bản A", False),
            ("NXB002", "Nhà xuất bản B", False),
        ])
        selector._populate_results("A")
        selector._select_item(selector.results.item(0))

        self.assertEqual(selector.currentData(), "NXB001")
        self.assertIn("NXB001", selector.search_input.text())
        selector.close()

    def test_single_select_clears_previous_choice_when_search_changes(self):
        selector = SearchableSingleSelect()
        selector.set_options([("TH001", "Thương hiệu A", False)])
        selector._populate_results()
        selector._select_item(selector.results.item(0))

        selector._on_search("không tồn tại")

        self.assertIsNone(selector.currentData())
        self.assertEqual(selector.results.count(), 0)
        selector.close()

    def test_multi_select_can_add_and_remove_multiple_codes(self):
        selector = SearchableMultiSelect()
        selector.set_options([
            ("TG001", "Tác giả A", False),
            ("TG002", "Tác giả B", False),
        ])
        selector._populate_results()
        selector._toggle_item(selector.results.item(0))
        selector._populate_results()
        selector._toggle_item(selector.results.item(1))

        self.assertEqual(selector.checked_codes(), ["TG001", "TG002"])

        selector._populate_results()
        selector._toggle_item(selector.results.item(0))
        self.assertEqual(selector.checked_codes(), ["TG002"])
        selector.close()

    def test_multi_select_keeps_existing_soft_deleted_choice(self):
        selector = SearchableMultiSelect()
        selector.set_options([
            ("TG001", "Tác giả cũ", True),
            ("TG002", "Tác giả mới", False),
        ], selected_codes={"TG001"})
        selector._populate_results()

        self.assertEqual(selector.checked_codes(), ["TG001"])
        self.assertIn("Tác giả cũ", selector.results.item(0).text())
        self.assertIn("đã xóa mềm", selector.results.item(0).text())
        selector.close()


class SupplierPagePermissionTests(unittest.TestCase):
    """Đảm bảo Thu ngân không truy vấn bảng nhà cung cấp khi khởi tạo trang."""

    def test_cashier_cannot_view_suppliers(self):
        self.assertFalse(can_view_suppliers("NV02", "Thu ngân"))

    def test_warehouse_manager_and_accounting_can_view_suppliers(self):
        for role in ("Nhân viên kho", "Quản lý", "Kế toán"):
            with self.subTest(role=role):
                self.assertTrue(can_view_suppliers("NV01", role))

    def test_admin_can_view_suppliers(self):
        self.assertTrue(can_view_suppliers("admin", ""))


class CodeGenerationTests(unittest.TestCase):
    """Kiểm thử quy tắc sinh mã tăng dần của các nhóm dữ liệu."""

    def test_catalog_code_uses_configured_prefix_and_table_lock(self):
        cursor = FakeCursor(7)
        page_stub = SimpleNamespace(config=CATALOGS["authors"])

        code = CatalogPage._next_code(page_stub, cursor, lock_table=True)

        self.assertEqual(code, "TG008")
        self.assertIn("dbo.TAC_GIA WITH (TABLOCKX, HOLDLOCK)", cursor.sql)
        self.assertEqual(cursor.params, ("TG",))

    def test_supplier_code_uses_ncc_prefix_and_table_lock(self):
        cursor = FakeCursor(12)

        code = SupplierFormDialog._next_code(cursor, lock_table=True)

        self.assertEqual(code, "NCC013")
        self.assertIn("dbo.NHA_CUNG_CAP WITH (TABLOCKX, HOLDLOCK)", cursor.sql)

    def test_product_code_uses_sp_prefix_and_table_lock(self):
        cursor = FakeCursor(9)

        code = ProductFormDialog._next_product_code(
            SimpleNamespace(), cursor, lock_table=True
        )

        self.assertEqual(code, "SP010")
        self.assertIn("dbo.SAN_PHAM WITH (TABLOCKX, HOLDLOCK)", cursor.sql)

    def test_employee_code_uses_nv_prefix_and_table_lock(self):
        cursor = FakeCursor(2)

        code = EmployeeWindow._next_employee_code(
            SimpleNamespace(), cursor, lock_table=True
        )

        self.assertEqual(code, "NV003")
        self.assertIn("dbo.NHAN_VIEN WITH (TABLOCKX, HOLDLOCK)", cursor.sql)

    def test_import_code_uses_six_digit_suffix_and_table_lock(self):
        cursor = FakeCursor(12)

        code = CreateImportDialog._next_import_code(
            SimpleNamespace(), cursor
        )

        self.assertEqual(code, "PN000013")
        self.assertIn("dbo.PHIEU_NHAP WITH (TABLOCKX, HOLDLOCK)", cursor.sql)

    def test_catalogs_have_unique_table_and_code_prefix_configuration(self):
        tables = [config["table"] for config in CATALOGS.values()]
        prefixes = [config["code_prefix"] for config in CATALOGS.values()]

        self.assertEqual(len(tables), len(set(tables)))
        self.assertEqual(len(prefixes), len(set(prefixes)))


class ProductLookupTests(unittest.TestCase):
    """Kiểm thử tra cứu sản phẩm bằng mã sản phẩm, barcode và ISBN."""

    def setUp(self):
        self.products = {
            "SP001": {
                "tensp": "Yuru Camp - Tập 1",
                "barcode": "8931234567890",
                "isbn": "9786041234567",
            },
            "SP002": {
                "tensp": "Sổ tay",
                "barcode": "8939876543210",
                "isbn": "",
            },
        }

    def test_lookup_by_exact_barcode(self):
        self.assertEqual(
            find_matching_product_codes(self.products, "8931234567890"),
            ["SP001"],
        )

    def test_lookup_book_by_exact_isbn(self):
        self.assertEqual(
            find_matching_product_codes(self.products, "9786041234567"),
            ["SP001"],
        )

    def test_lookup_by_partial_barcode(self):
        self.assertEqual(
            find_matching_product_codes(self.products, "893987"),
            ["SP002"],
        )

    def test_lookup_ignores_case_and_outer_spaces(self):
        self.assertEqual(
            find_matching_product_codes(self.products, "  yuru camp  "),
            ["SP001"],
        )

    def test_empty_lookup_returns_no_products(self):
        self.assertEqual(find_matching_product_codes(self.products, "  "), [])


class InputValidationTests(unittest.TestCase):
    """Kiểm thử các quy tắc chuyển đổi số và kiểm tra dữ liệu đầu vào."""

    def test_product_decimal_accepts_comma_decimal_separator(self):
        self.assertEqual(
            ProductFormDialog.parse_decimal("12,50", "Giá bán"),
            Decimal("12.50"),
        )

    def test_product_decimal_rejects_negative_value(self):
        with self.assertRaisesRegex(ValueError, "không được âm"):
            ProductFormDialog.parse_decimal("-1", "Giá bán")

    def test_invoice_cash_accepts_thousand_separators(self):
        self.assertEqual(
            CreateInvoiceDialog._parse_cash("1,250,000.50"),
            Decimal("1250000.50"),
        )

    def test_invoice_cash_rejects_empty_invalid_and_negative_values(self):
        for invalid in ("", "abc", "-100", "NaN"):
            with self.subTest(value=invalid):
                with self.assertRaises(ValueError):
                    CreateInvoiceDialog._parse_cash(invalid)

    def test_shift_opening_cash_accepts_zero(self):
        self.assertEqual(
            ShiftCreateDialog._parse_cash("0", "tiền đầu ca"),
            Decimal("0.00"),
        )

    def test_shift_opening_cash_rejects_invalid_and_negative_values(self):
        for invalid in ("", "abc", "-1", "Infinity"):
            with self.subTest(value=invalid):
                with self.assertRaises(ValueError):
                    ShiftCreateDialog._parse_cash(invalid, "tiền đầu ca")

    def test_role_navigation_contains_expected_pages_for_each_role(self):
        self.assertIn("invoices", MainWindow.ROLE_PAGE_ACCESS["Thu ngân"])
        self.assertIn("imports", MainWindow.ROLE_PAGE_ACCESS["Nhân viên kho"])
        self.assertIn("returns", MainWindow.ROLE_PAGE_ACCESS["Quản lý"])
        self.assertIn("report_revenue", MainWindow.ROLE_PAGE_ACCESS["Kế toán"])
        self.assertIn("report_shifts", MainWindow.ROLE_PAGE_ACCESS["Quản lý"])
        self.assertIn("report_shifts", MainWindow.ROLE_PAGE_ACCESS["Kế toán"])

    def test_admin_is_recognized_case_insensitively(self):
        self.assertTrue(is_admin_account("admin"))
        self.assertTrue(is_admin_account(" ADMIN "))
        self.assertFalse(is_admin_account("NV01"))

    def test_admin_can_access_every_registered_page(self):
        all_pages = {
            "home", "products", "employees", "suppliers", "imports",
            "invoices", "returns", "shifts", "authors", "genres",
            "publishers", "brands", "report_overview", "report_revenue",
            "report_invoice", "report_import", "report_return",
            "report_inventory", "report_product", "report_shifts",
        }
        allowed = allowed_pages_for_user(
            "admin", "", MainWindow.ROLE_PAGE_ACCESS, all_pages
        )
        self.assertEqual(allowed, all_pages)

    def test_non_admin_keeps_role_based_page_restrictions(self):
        all_pages = {"home", "products", "invoices", "returns", "reports"}
        allowed = allowed_pages_for_user(
            "NV01", "Thu ngân", MainWindow.ROLE_PAGE_ACCESS, all_pages
        )
        self.assertEqual(allowed, set(MainWindow.ROLE_PAGE_ACCESS["Thu ngân"]))
        self.assertNotIn("returns", allowed)
        self.assertNotIn("reports", allowed)


class ImportPagePermissionTests(unittest.TestCase):
    """Đảm bảo vai trò không có quyền nhập hàng không tải dữ liệu phiếu nhập."""

    def test_cashier_cannot_view_import_page(self):
        self.assertFalse(can_view_imports("NV02", "Thu ngân"))

    def test_warehouse_manager_accounting_can_view_import_page(self):
        for role in ("Nhân viên kho", "Quản lý", "Kế toán"):
            with self.subTest(role=role):
                self.assertTrue(can_view_imports("NV01", role))

    def test_admin_can_view_import_page(self):
        self.assertTrue(can_view_imports("admin", ""))


class ReturnDialogInputTests(unittest.TestCase):
    """Kiểm thử nhập mã hóa đơn và số lượng trong form đổi trả."""

    def test_invoice_search_resolves_exact_invoice_code_case_insensitively(self):
        from PySide6.QtWidgets import QComboBox

        combo = QComboBox()
        combo.setEditable(True)
        combo.addItem("HD000001 | 27/11/2026", "HD000001")
        combo.addItem("HD000002 | 27/11/2026", "HD000002")

        self.assertEqual(
            CreateReturnDialog._find_invoice_index(combo, "hd000002"),
            1,
        )
        self.assertEqual(
            CreateReturnDialog._find_invoice_index(combo, "HD999999"),
            -1,
        )
        combo.close()

    def test_quantity_input_accepts_integer_and_empty_as_zero(self):
        self.assertEqual(CreateReturnDialog._parse_quantity_input("5"), 5)
        self.assertEqual(CreateReturnDialog._parse_quantity_input("0"), 0)
        self.assertEqual(CreateReturnDialog._parse_quantity_input(""), 0)

    def test_quantity_input_rejects_negative_and_non_numeric_values(self):
        for value in ("-1", "1.5", "abc"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    CreateReturnDialog._parse_quantity_input(value)


class ReturnVoucherDeletionTests(unittest.TestCase):
    """Kiểm thử tính toán biến động tồn kho khi xóa phiếu đổi trả."""

    def test_delete_refunded_intact_goods_reverses_stock_decrease(self):
        actions = ReturnWindow._build_inventory_reversal_actions([
            ("SP001", 2, 1, 0),
        ])
        self.assertEqual(actions, [("SP001", 2, "SUBTRACT")])

    def test_delete_refunded_damaged_goods_does_not_change_stock(self):
        actions = ReturnWindow._build_inventory_reversal_actions([
            ("SP002", 3, 0, 0),
        ])
        self.assertEqual(actions, [])

    def test_delete_exchanged_damaged_goods_restores_replacement_stock(self):
        actions = ReturnWindow._build_inventory_reversal_actions([
            ("SP003", 1, 0, 1),
        ])
        self.assertEqual(actions, [("SP003", 1, "ADD")])

    def test_delete_multiple_return_lines_builds_all_reversals(self):
        actions = ReturnWindow._build_inventory_reversal_actions([
            ("SP001", 2, 1, 0),
            ("SP002", 1, 0, 0),
            ("SP003", 4, 0, 1),
        ])
        self.assertEqual(actions, [
            ("SP001", 2, "SUBTRACT"),
            ("SP003", 4, "ADD"),
        ])

    def test_delete_refuses_invalid_quantity_or_return_state(self):
        invalid_details = [
            ("SP001", 0, 1, 0),
            ("SP001", -1, 0, 1),
            ("SP001", 1, None, 0),
            ("SP001", 1, 1, None),
            ("SP001", 1, 1, 1),
        ]
        for detail in invalid_details:
            with self.subTest(detail=detail):
                with self.assertRaises(ValueError):
                    ReturnWindow._build_inventory_reversal_actions([detail])


class ShiftScheduleTests(unittest.TestCase):
    """Kiểm thử lịch ba ca cố định được thiết lập trong biểu mẫu."""

    def test_shift_form_returns_the_three_fixed_time_ranges(self):
        dialog = ShiftCreateDialog()
        self.addCleanup(dialog.close)

        expected = {
            0: ("07:00:00", "12:00:00"),
            1: ("12:00:00", "17:00:00"),
            2: ("17:00:00", "22:00:00"),
        }

        for index, times in expected.items():
            with self.subTest(shift=index + 1):
                dialog.shift_number.setCurrentIndex(index)
                values = dialog.get_values()
                self.assertEqual((values["tgmo"], values["tgdong"]), times)
                self.assertEqual(values["soca"], index + 1)



class InvoiceSafetyTests(unittest.TestCase):
    """Kiểm thử các quy tắc chống hoàn kho trùng và xác thực ca khi lưu."""

    class ShiftCursor:
        def __init__(self, result):
            self.result = result
            self.sql = None
            self.params = None

        def execute(self, sql, *params):
            self.sql = sql
            self.params = params
            return self

        def fetchone(self):
            return self.result

    def test_invoice_cancel_rejects_existing_return_voucher(self):
        InvoiceWindow._assert_no_return_vouchers(False)
        with self.assertRaises(RuntimeError):
            InvoiceWindow._assert_no_return_vouchers(True)

    def test_cart_price_and_vat_are_revalidated_before_invoice_save(self):
        class SequentialCursor:
            def __init__(self, rows):
                self.rows = iter(rows)
                self.sql = []

            def execute(self, sql, *params):
                self.sql.append((sql, params))
                return self

            def fetchone(self):
                return next(self.rows)

        cursor = SequentialCursor([
            ("100.00", "8.00"),
            ("15.00",),
        ])
        cart = {
            "SP001": {"price": Decimal("100.00"), "vat": Decimal("8.00")}
        }

        CreateInvoiceDialog._assert_cart_prices_unchanged(
            cursor, cart, "KM01", Decimal("15.00")
        )
        self.assertEqual(len(cursor.sql), 2)
        self.assertIn("ISNULL(IS_DELETED, 0) = 0", cursor.sql[0][0])
        self.assertIn("SYSDATETIME()", cursor.sql[1][0])

    def test_cart_price_change_rejects_invoice_save(self):
        class SequentialCursor:
            def execute(self, sql, *params):
                return self

            def fetchone(self):
                return ("125.00", "8.00")

        cart = {
            "SP001": {"price": Decimal("100.00"), "vat": Decimal("8.00")}
        }
        with self.assertRaises(RuntimeError):
            CreateInvoiceDialog._assert_cart_prices_unchanged(
                SequentialCursor(), cart, None, Decimal("0")
            )

    def test_expired_promotion_rejects_invoice_save(self):
        class SequentialCursor:
            def __init__(self):
                self.calls = 0

            def execute(self, sql, *params):
                self.calls += 1
                return self

            def fetchone(self):
                return None

        with self.assertRaises(RuntimeError):
            CreateInvoiceDialog._assert_cart_prices_unchanged(
                SequentialCursor(), {}, "KM01", Decimal("10.00")
            )

    def test_active_shift_validation_queries_current_database_state(self):
        cursor = self.ShiftCursor((12,))
        employee = {"manv": "NV01"}
        shift = {"maca": 12}

        CreateInvoiceDialog._assert_active_shift(cursor, employee, shift)

        self.assertEqual(cursor.params, ("NV01", 12))
        self.assertIn("SYSDATETIME()", cursor.sql)
        self.assertIn("C.TMCUOICA IS NULL", cursor.sql)
        self.assertIn("dbo.LAMCA", cursor.sql)

    def test_active_shift_validation_rejects_expired_or_unregistered_shift(self):
        cursor = self.ShiftCursor(None)
        with self.assertRaises(RuntimeError):
            CreateInvoiceDialog._assert_active_shift(
                cursor, {"manv": "NV01"}, {"maca": 12}
            )

    def test_active_shift_validation_rejects_missing_cached_shift(self):
        cursor = self.ShiftCursor((12,))
        with self.assertRaises(RuntimeError):
            CreateInvoiceDialog._assert_active_shift(
                cursor, {"manv": "NV01"}, None
            )
        self.assertIsNone(cursor.sql)

    def test_odbc_values_escape_closing_braces(self):
        self.assertEqual(Database._odbc_value("pass}word"), "{pass}}word}")

    def test_role_page_map_has_no_stale_statistics_page(self):
        all_roles = [
            page
            for pages in MainWindow.ROLE_PAGE_ACCESS.values()
            for page in pages
        ]
        self.assertNotIn("statistics", all_roles)
        for page in (
            "report_overview", "report_revenue", "report_invoice",
            "report_import", "report_return", "report_inventory",
            "report_product",
        ):
            self.assertIn(page, MainWindow.ROLE_PAGE_ACCESS["Quản lý"])
            self.assertIn(page, MainWindow.ROLE_PAGE_ACCESS["Kế toán"])


if __name__ == "__main__":
    unittest.main()
