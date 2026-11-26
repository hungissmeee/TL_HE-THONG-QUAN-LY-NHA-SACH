"""Kiểm tra import các package giao diện với dependency thật.

Không tạo QApplication, không mở cửa sổ và không kết nối SQL Server.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from co_so_du_lieu.ket_noi import Database
from giao_dien.tai_khoan import EmployeePermissionDialog
from giao_dien.danh_muc import CatalogPage
from giao_dien.doi_mat_khau import ChangePasswordDialog
from giao_dien.nhan_vien import EmployeeWindow
from giao_dien.phieu_nhap import CreateImportDialog, CreateSupplierDialog, ImportDetailDialog, ImportWindow
from giao_dien.hoa_don import CreateInvoiceDialog, InvoiceDetailDialog, InvoiceWindow
from giao_dien.cua_so_chinh import MainWindow
from giao_dien.san_pham import (
    ProductDetailDialog,
    ProductFormDialog,
    ProductWindow,
    SearchableMultiSelect,
    SearchableSingleSelect,
)
from giao_dien.ca_lam_viec import ShiftCreateDialog, ShiftWindow
from giao_dien.nha_cung_cap import SupplierDetailDialog, SupplierFormDialog, SupplierWindow


def main():
    print("All current UI package imports passed.")


if __name__ == "__main__":
    main()

# Keep this smoke test independent of database connectivity.
