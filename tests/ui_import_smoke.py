"""Kiểm tra import các package giao diện với dependency thật.

Không tạo QApplication, không mở cửa sổ và không kết nối SQL Server.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database.connection import Database
from ui.account import EmployeePermissionDialog
from ui.catalog import CatalogPage
from ui.change_password import ChangePasswordDialog
from ui.employee import EmployeeWindow
from ui.imports import CreateImportDialog, CreateSupplierDialog, ImportDetailDialog, ImportWindow
from ui.invoices import CreateInvoiceDialog, InvoiceDetailDialog, InvoiceWindow
from ui.main_window import MainWindow
from ui.products import (
    ProductDetailDialog,
    ProductFormDialog,
    ProductWindow,
    SearchableMultiSelect,
    SearchableSingleSelect,
)
from ui.shifts import ShiftCreateDialog, ShiftWindow
from ui.suppliers import SupplierDetailDialog, SupplierFormDialog, SupplierWindow


def main():
    print("UI package imports passed.")


if __name__ == "__main__":
    main()
