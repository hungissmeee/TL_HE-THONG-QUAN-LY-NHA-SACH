"""Kiểm tra import các package giao diện với dependency thật.

Không tạo QApplication, không mở cửa sổ và không kết nối SQL Server.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database.ket_noi import Database
from ui.tai_khoan import EmployeePermissionDialog
from ui.danh_muc import CatalogPage
from ui.doi_mat_khau import ChangePasswordDialog
from ui.nhan_vien import EmployeeWindow
from ui.phieu_nhap import CreateImportDialog, CreateSupplierDialog, ImportDetailDialog, ImportWindow
from ui.hoa_don import CreateInvoiceDialog, InvoiceDetailDialog, InvoiceWindow
from ui.cua_so_chinh import MainWindow
from ui.san_pham import (
    ProductDetailDialog,
    ProductFormDialog,
    ProductWindow,
    SearchableMultiSelect,
    SearchableSingleSelect,
)
from ui.ca_lam_viec import ShiftCreateDialog, ShiftWindow
from ui.nha_cung_cap import SupplierDetailDialog, SupplierFormDialog, SupplierWindow


def main():
    print("All current UI package imports passed.")


if __name__ == "__main__":
    main()

# Keep this smoke test independent of database connectivity.
