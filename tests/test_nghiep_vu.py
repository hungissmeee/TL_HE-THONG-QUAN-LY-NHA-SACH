"""Kiểm thử các quy tắc nghiệp vụ thuần và widget dùng chung."""

import os
import unittest
from types import SimpleNamespace
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTableWidget

from database.connection import Database
from ui.table_sort import (
    SORT_ROLE,
    SortableTableWidgetItem,
    prepare_sortable_table,
    pause_table_sorting,
    resume_table_sorting,
)
from ui.san_pham.bieu_mau import ProductFormDialog
from ui.san_pham.bo_chon import SearchableSingleSelect, SearchableMultiSelect
from ui.danh_muc import CatalogPage, CATALOGS
from ui.nha_cung_cap.bieu_mau import SupplierFormDialog
from ui.nhan_vien import EmployeeWindow
from ui.phieu_nhap.tao_bieu_mau import CreateImportDialog
from ui.hoa_don.tao_bieu_mau import CreateInvoiceDialog
from ui.ca_lam_viec.tao_bieu_mau import ShiftCreateDialog
from ui.main_windows import MainWindow
from ui.permissions import is_admin_account, allowed_pages_for_user
from ui.doi_tra.tao_bieu_mau import CreateReturnDialog


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


class DatabaseUtilityTests(unittest.TestCase):
    """Kiểm thử cấu hình kết nối, vai trò và kiểm tra quyền quản trị."""

    def test_connection_string_contains_configured_sql_server_values(self):
        db = Database()
        db.server = "localhost\\SQLEXPRESS"
        db.database = "CSDLQLNHASACH"
        db.driver = "ODBC Driver 18 for SQL Server"

        result = db._connection_string("NV01", "ExamplePass123!")

        self.assertIn("SERVER=localhost\\SQLEXPRESS;", result)
        self.assertIn("DATABASE=CSDLQLNHASACH;", result)
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
            "report_inventory", "report_product",
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


if __name__ == "__main__":
    unittest.main()
