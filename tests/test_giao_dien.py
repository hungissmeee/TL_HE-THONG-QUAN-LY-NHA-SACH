"""Kiểm tra import các package giao diện với dependency thật.

Không tạo QApplication, không mở cửa sổ và không kết nối SQL Server.
"""

from pathlib import Path
import sys
import unittest

from PySide6.QtGui import QImageReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database.connection import Database
from ui.tai_khoan import EmployeePermissionDialog
from ui.danh_muc import CatalogPage
from ui.doi_mat_khau import ChangePasswordDialog
from ui.nhan_vien import EmployeeWindow
from ui.phieu_nhap import CreateImportDialog, CreateSupplierDialog, ImportDetailDialog, ImportWindow
from ui.hoa_don import CreateInvoiceDialog, InvoiceDetailDialog, InvoiceWindow
from ui.main_windows import MainWindow
from ui.styles import MAIN_WINDOW_STYLESHEET, CALENDAR_STYLESHEET
from ui.san_pham import (
    ProductDetailDialog,
    ProductFormDialog,
    ProductWindow,
    SearchableMultiSelect,
    SearchableSingleSelect,
)
from ui.ca_lam_viec import ShiftCreateDialog, ShiftWindow
from ui.nha_cung_cap import SupplierDetailDialog, SupplierFormDialog, SupplierWindow



class ArrowAssetTests(unittest.TestCase):
    """Đảm bảo Qt đọc được SVG dùng cho mũi tên trên các điều khiển."""

    def test_arrow_svg_assets_exist_and_are_readable(self):
        icon_dir = ROOT / "ui" / "assets" / "icons"
        icon_names = (
            "arrow-down.svg",
            "arrow-up.svg",
            "arrow-down-disabled.svg",
            "arrow-up-disabled.svg",
        )

        for icon_name in icon_names:
            with self.subTest(icon=icon_name):
                icon_path = icon_dir / icon_name
                self.assertTrue(icon_path.is_file(), str(icon_path))
                reader = QImageReader(str(icon_path))
                self.assertTrue(reader.canRead(), reader.errorString())

    def test_stylesheets_use_absolute_svg_paths(self):
        for stylesheet in (MAIN_WINDOW_STYLESHEET, CALENDAR_STYLESHEET):
            with self.subTest(stylesheet=stylesheet[:40]):
                self.assertIn("file:///", stylesheet)
                for icon_name in (
                    "arrow-down.svg",
                    "arrow-up.svg",
                ):
                    self.assertIn(icon_name, stylesheet)


def main():
    print("All current UI package imports passed.")


if __name__ == "__main__":
    main()

# Keep this smoke test independent of database connectivity.
