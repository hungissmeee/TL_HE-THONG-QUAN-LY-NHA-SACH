"""Kiểm thử các quy tắc đầu vào của service sản phẩm, không cần SQL Server."""

import unittest
from datetime import date
from decimal import Decimal

from core.repositories.san_pham_repository import SanPhamRepository
from core.services.san_pham_service import SanPhamService


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


if __name__ == "__main__":
    unittest.main()
