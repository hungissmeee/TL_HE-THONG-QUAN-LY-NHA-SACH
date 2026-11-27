"""Kiểm thử các quy tắc đầu vào của service sản phẩm, không cần SQL Server."""

import unittest
from datetime import date
from decimal import Decimal

from core.repositories.san_pham_repository import SanPhamRepository
from core.services.san_pham_service import SanPhamService
from core.repositories.nha_cung_cap_repository import NhaCungCapRepository
from core.services.nha_cung_cap_service import NhaCungCapService
from core.repositories.phieu_nhap_repository import PhieuNhapRepository
from core.services.phieu_nhap_service import PhieuNhapService


class FakeProductRepository(SanPhamRepository):
    """Repository giả để kiểm tra service mà không mở kết nối database."""

    def __init__(self):
        self.saved = None

    def save_product(self, data, product_code=None):
        self.saved = (data, product_code)
        return product_code or "SP001"


class ProductServiceTests(unittest.TestCase):
    def setUp(self):
        self.repository = FakeProductRepository()
        self.service = SanPhamService(self.repository)

    def valid_book(self):
        return {
            "tensp": "Sách kiểm thử",
            "dvt": "Quyển",
            "giaban": "125000.50",
            "vat": "8",
            "barcode": "8930000000001",
            "product_type": "book",
            "isbn": "9786040000000",
            "namxb": "2025",
            "manxb": "NXB001",
            "authors": ["TG001", "TG001", "TG002"],
            "genres": ["TL001"],
        }

    def test_save_book_normalizes_values(self):
        code = self.service.save_product(self.valid_book())
        self.assertEqual(code, "SP001")
        payload, product_code = self.repository.saved
        self.assertIsNone(product_code)
        self.assertEqual(payload["giaban"], Decimal("125000.50"))
        self.assertEqual(payload["vat"], Decimal("8"))
        self.assertEqual(payload["authors"], ["TG001", "TG002"])
        self.assertEqual(payload["genres"], ["TL001"])

    def test_save_edit_passes_existing_product_code(self):
        code = self.service.save_product(self.valid_book(), product_code="SP023")
        self.assertEqual(code, "SP023")
        self.assertEqual(self.repository.saved[1], "SP023")

    def test_rejects_missing_name(self):
        data = self.valid_book()
        data["tensp"] = "  "
        with self.assertRaisesRegex(ValueError, "tên sản phẩm"):
            self.service.save_product(data)

    def test_rejects_negative_price(self):
        data = self.valid_book()
        data["giaban"] = "-1"
        with self.assertRaisesRegex(ValueError, "Giá bán"):
            self.service.save_product(data)

    def test_rejects_vat_above_100(self):
        data = self.valid_book()
        data["vat"] = "101"
        with self.assertRaisesRegex(ValueError, "VAT"):
            self.service.save_product(data)

    def test_rejects_missing_publisher_for_book(self):
        data = self.valid_book()
        data["manxb"] = None
        with self.assertRaisesRegex(ValueError, "nhà xuất bản"):
            self.service.save_product(data)

    def test_rejects_missing_brand_for_other_product(self):
        data = self.valid_book()
        data["product_type"] = "other"
        data["math"] = ""
        with self.assertRaisesRegex(ValueError, "thương hiệu"):
            self.service.save_product(data)

    def test_other_product_preserves_manufacturing_date(self):
        data = self.valid_book()
        data["product_type"] = "other"
        data["math"] = "TH001"
        data["ngaysx"] = date(2026, 1, 2)
        self.service.save_product(data)
        self.assertEqual(self.repository.saved[0]["ngaysx"], date(2026, 1, 2))


class FakeSupplierRepository(NhaCungCapRepository):
    def __init__(self):
        self.saved = None
        self.status = None

    def save_supplier(self, data, supplier_code=None):
        self.saved = (data, supplier_code)
        return supplier_code or "NCC001"

    def set_supplier_status(self, supplier_code, inactive):
        self.status = (supplier_code, inactive)
        return True


class SupplierServiceTests(unittest.TestCase):
    def setUp(self):
        self.repository = FakeSupplierRepository()
        self.service = NhaCungCapService(self.repository)

    def test_supplier_fields_are_trimmed_and_optional_values_become_none(self):
        code = self.service.save_supplier({
            "name": "  Nhà cung cấp A  ",
            "phone": "  ",
            "address": "  Huế  ",
            "tax": "",
        })
        self.assertEqual(code, "NCC001")
        self.assertEqual(self.repository.saved[0], {
            "name": "Nhà cung cấp A",
            "phone": None,
            "address": "Huế",
            "tax": None,
        })

    def test_supplier_update_preserves_code(self):
        self.service.save_supplier({"name": "A"}, supplier_code="NCC010")
        self.assertEqual(self.repository.saved[1], "NCC010")

    def test_supplier_name_is_required(self):
        with self.assertRaisesRegex(ValueError, "tên nhà cung cấp"):
            self.service.save_supplier({"name": " "})

    def test_supplier_fields_respect_database_lengths(self):
        with self.assertRaisesRegex(ValueError, "Số điện thoại"):
            self.service.save_supplier({"name": "A", "phone": "1" * 16})

    def test_supplier_status_delegates_normalized_code(self):
        self.assertTrue(self.service.set_supplier_status(" NCC001 ", True))
        self.assertEqual(self.repository.status, ("NCC001", True))


class FakeImportRepository(PhieuNhapRepository):
    def __init__(self):
        self.created = None
        self.cancelled = None

    def create_import(self, payload):
        self.created = payload
        return "PN000001"

    def cancel_import(self, import_code, username, role, is_admin=False):
        self.cancelled = (import_code, username, role, is_admin)
        return True


class ImportServiceTests(unittest.TestCase):
    def setUp(self):
        self.repository = FakeImportRepository()
        self.service = PhieuNhapService(self.repository)

    def valid_payload(self):
        return {
            "supplier_code": "NCC001",
            "supplier_invoice": "HD-01",
            "employee_code": "NV001",
            "import_type": "Nhập mua",
            "items": [
                {"product_code": "SP001", "quantity": 2, "price": "100.25", "vat": "8"},
                {"product_code": "SP002", "quantity": 1, "price": "50", "vat": "0"},
            ],
        }

    def test_import_total_is_recalculated_by_service(self):
        code = self.service.create_import(self.valid_payload())
        self.assertEqual(code, "PN000001")
        self.assertEqual(self.repository.created["total"], Decimal("250.50"))
        self.assertEqual(self.repository.created["items"][0]["price"], Decimal("100.25"))

    def test_import_rejects_missing_supplier(self):
        data = self.valid_payload()
        data["supplier_code"] = ""
        with self.assertRaisesRegex(ValueError, "nhà cung cấp"):
            self.service.create_import(data)

    def test_import_rejects_empty_items(self):
        data = self.valid_payload()
        data["items"] = []
        with self.assertRaisesRegex(ValueError, "chưa có sản phẩm"):
            self.service.create_import(data)

    def test_import_rejects_non_positive_quantity(self):
        data = self.valid_payload()
        data["items"][0]["quantity"] = 0
        with self.assertRaisesRegex(ValueError, "lớn hơn 0"):
            self.service.create_import(data)

    def test_import_rejects_zero_price(self):
        data = self.valid_payload()
        data["items"][0]["price"] = 0
        with self.assertRaisesRegex(ValueError, "đơn giá"):
            self.service.create_import(data)

    def test_import_rejects_invalid_vat(self):
        data = self.valid_payload()
        data["items"][0]["vat"] = 101
        with self.assertRaisesRegex(ValueError, "VAT"):
            self.service.create_import(data)

    def test_import_rejects_duplicate_product_lines(self):
        data = self.valid_payload()
        data["items"][1]["product_code"] = "SP001"
        with self.assertRaisesRegex(ValueError, "bị lặp"):
            self.service.create_import(data)

    def test_cancel_import_normalizes_code(self):
        self.assertTrue(self.service.cancel_import(" PN000001 ", "admin", "Quản lý", True))
        self.assertEqual(
            self.repository.cancelled,
            ("PN000001", "admin", "Quản lý", True),
        )


if __name__ == "__main__":
    unittest.main()
