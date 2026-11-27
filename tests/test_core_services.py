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
from core.repositories.hoa_don_repository import HoaDonRepository
from core.services.hoa_don_service import HoaDonService
from core.repositories.doi_tra_repository import ReturnRepository
from core.services.doi_tra_service import ReturnService
from core.repositories.nhan_vien_repository import NhanVienRepository
from core.services.nhan_vien_service import NhanVienService


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

    def test_admin_can_create_import_without_employee_profile(self):
        data = self.valid_payload()
        data["employee_code"] = None
        data["is_admin"] = True
        self.assertEqual(self.service.create_import(data), "PN000001")
        self.assertIsNone(self.repository.created["employee_code"])

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
        with self.assertRaisesRegex(ValueError, "Đơn giá"):
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


class FakeInvoiceRepository(HoaDonRepository):
    def __init__(self):
        self.created = None
        self.cancelled = None

    def create_invoice(self, payload, is_admin=False):
        self.created = (payload, is_admin)
        return "HD000001"

    def cancel_invoice(self, invoice_code, username, role, is_admin=False):
        self.cancelled = (invoice_code, username, role, is_admin)
        return True


class InvoiceServiceTests(unittest.TestCase):
    def setUp(self):
        self.repository = FakeInvoiceRepository()
        self.service = HoaDonService(self.repository)

    def valid_payload(self):
        return {
            "employee": {"manv": "NV001", "tennv": "Thu ngân A"},
            "active_shift": {"maca": 10},
            "cart": {
                "SP001": {"quantity": 2, "price": "100.25", "vat": "8", "stock": 5},
                "SP002": {"quantity": 1, "price": "50", "vat": "0", "stock": 3},
            },
            "promotion_code": "KM01",
            "discount_rate": "10",
            "cash": "300",
        }

    def test_invoice_total_discount_and_change_are_calculated(self):
        code = self.service.create_invoice(self.valid_payload())
        payload, is_admin = self.repository.created
        self.assertEqual(code, "HD000001")
        self.assertFalse(is_admin)
        self.assertEqual(payload["subtotal"], Decimal("250.50"))
        self.assertEqual(payload["discount"], Decimal("25.05"))
        self.assertEqual(payload["total"], Decimal("225.45"))
        self.assertEqual(payload["change"], Decimal("74.55"))
        self.assertEqual(payload["cart"]["SP001"]["price"], Decimal("100.25"))

    def test_admin_can_create_invoice_without_employee_or_shift(self):
        data = self.valid_payload()
        data["employee"] = {"manv": None, "tennv": "Admin"}
        data["active_shift"] = None
        code = self.service.create_invoice(data, is_admin=True)
        payload, is_admin = self.repository.created
        self.assertEqual(code, "HD000001")
        self.assertTrue(is_admin)
        self.assertIsNone(payload["employee"]["manv"])
        self.assertIsNone(payload["active_shift"])

    def test_non_admin_requires_active_shift(self):
        data = self.valid_payload()
        data["active_shift"] = None
        with self.assertRaisesRegex(PermissionError, "ca làm việc"):
            self.service.create_invoice(data)

    def test_invoice_rejects_empty_cart(self):
        data = self.valid_payload()
        data["cart"] = {}
        with self.assertRaisesRegex(ValueError, "chưa có sản phẩm"):
            self.service.create_invoice(data)

    def test_invoice_rejects_insufficient_stock(self):
        data = self.valid_payload()
        data["cart"]["SP001"]["stock"] = 1
        with self.assertRaisesRegex(ValueError, "không đủ tồn kho"):
            self.service.create_invoice(data)

    def test_invoice_rejects_insufficient_cash(self):
        data = self.valid_payload()
        data["cash"] = "100"
        with self.assertRaisesRegex(ValueError, "chưa đủ tiền"):
            self.service.create_invoice(data)

    def test_invoice_rejects_discount_without_promotion(self):
        data = self.valid_payload()
        data["promotion_code"] = None
        with self.assertRaisesRegex(ValueError, "chưa chọn khuyến mãi"):
            self.service.create_invoice(data)

    def test_invoice_rejects_discount_above_one_hundred_percent(self):
        data = self.valid_payload()
        data["discount_rate"] = "101"
        with self.assertRaisesRegex(ValueError, "không được vượt quá"):
            self.service.create_invoice(data)

    def test_invoice_rejects_non_positive_quantity(self):
        data = self.valid_payload()
        data["cart"]["SP001"]["quantity"] = 0
        with self.assertRaisesRegex(ValueError, "phải lớn hơn 0"):
            self.service.create_invoice(data)

    def test_invoice_rejects_invalid_price(self):
        data = self.valid_payload()
        data["cart"]["SP001"]["price"] = "-1"
        with self.assertRaisesRegex(ValueError, "Đơn giá"):
            self.service.create_invoice(data)

    def test_invoice_rejects_vat_above_one_hundred(self):
        data = self.valid_payload()
        data["cart"]["SP001"]["vat"] = "101"
        with self.assertRaisesRegex(ValueError, "không được vượt quá"):
            self.service.create_invoice(data)

    def test_cancel_invoice_normalizes_code(self):
        self.assertTrue(self.service.cancel_invoice(
            " HD000001 ", "NV001", "Thu ngân"
        ))
        self.assertEqual(
            self.repository.cancelled,
            ("HD000001", "NV001", "Thu ngân", False),
        )



class FakeReturnRepository(ReturnRepository):
    def __init__(self):
        self.created = None
        self.deleted = None

    def create_return(self, payload, username, is_admin=False):
        self.created = (payload, username, is_admin)
        return {
            "return_code": "PDT000001",
            "invoice_code": payload["invoice_code"],
            "total_refund": Decimal("180.00"),
        }

    def delete_return(self, return_code, username, is_admin=False):
        self.deleted = (return_code, username, is_admin)
        return True


class ReturnServiceTests(unittest.TestCase):
    def setUp(self):
        self.repository = FakeReturnRepository()
        self.service = ReturnService(self.repository)

    def valid_payload(self):
        return {
            "invoice_code": " HD000001 ",
            "reason": "Sản phẩm bị lỗi",
            "items": [
                {"product_code": "SP001", "quantity": 2, "condition": 1, "action": 0},
                {"product_code": "SP002", "quantity": 1, "condition": 0, "action": 1},
            ],
        }

    def test_return_payload_is_normalized_and_validated(self):
        result = self.service.create_return(self.valid_payload(), "NV001")
        payload, username, is_admin = self.repository.created
        self.assertEqual(result["return_code"], "PDT000001")
        self.assertEqual(payload["invoice_code"], "HD000001")
        self.assertEqual(username, "NV001")
        self.assertFalse(is_admin)
        self.assertEqual(len(payload["items"]), 2)

    def test_admin_can_create_return_without_employee_profile(self):
        self.service.create_return(self.valid_payload(), "admin", is_admin=True)
        self.assertTrue(self.repository.created[2])

    def test_return_rejects_missing_invoice_or_reason(self):
        for key, value in (("invoice_code", ""), ("reason", "  ")):
            data = self.valid_payload()
            data[key] = value
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    self.service.create_return(data, "NV001")

    def test_return_rejects_empty_items(self):
        data = self.valid_payload()
        data["items"] = []
        with self.assertRaisesRegex(ValueError, "ít nhất một"):
            self.service.create_return(data, "NV001")

    def test_return_rejects_non_positive_quantity(self):
        data = self.valid_payload()
        data["items"][0]["quantity"] = 0
        with self.assertRaisesRegex(ValueError, "lớn hơn 0"):
            self.service.create_return(data, "NV001")

    def test_return_rejects_exchange_of_intact_goods(self):
        data = self.valid_payload()
        data["items"][0]["action"] = 1
        with self.assertRaisesRegex(ValueError, "hàng trả đã hỏng"):
            self.service.create_return(data, "NV001")

    def test_return_rejects_duplicate_product_lines(self):
        data = self.valid_payload()
        data["items"].append(dict(data["items"][0]))
        with self.assertRaisesRegex(ValueError, "nhiều lần"):
            self.service.create_return(data, "NV001")

    def test_return_delete_normalizes_code(self):
        self.assertTrue(self.service.delete_return(" PDT000001 ", "NV001"))
        self.assertEqual(self.repository.deleted, ("PDT000001", "NV001", False))

    def test_refund_total_ignores_exchange_lines(self):
        total = self.service.calculate_refund([
            {"net_price": "90", "quantity": 2, "action": 0},
            {"net_price": "50", "quantity": 1, "action": 1},
        ])
        self.assertEqual(total, Decimal("180.00"))



class FakeEmployeeRepository(NhanVienRepository):
    def __init__(self):
        self.created = None
        self.updated_role = None
        self.account_status = None
        self.deleted = None

    def create_employee(self, data):
        self.created = data
        return "NV003"

    def update_employee_role(self, employee_code, role):
        self.updated_role = (employee_code, role)
        return True

    def set_account_enabled(self, employee_code, enabled):
        self.account_status = (employee_code, enabled)
        return True

    def delete_account(self, employee_code):
        self.deleted = employee_code
        return True


class EmployeeServiceTests(unittest.TestCase):
    def setUp(self):
        self.repository = FakeEmployeeRepository()
        self.service = NhanVienService(self.repository)

    def valid_data(self):
        return {
            "name": "Nguyễn Văn A",
            "role": "Thu ngân",
            "phone": "0901234567",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
        }

    def test_create_employee_normalizes_and_delegates_data(self):
        code = self.service.create_employee(self.valid_data())
        self.assertEqual(code, "NV003")
        self.assertEqual(self.repository.created["name"], "Nguyễn Văn A")
        self.assertEqual(self.repository.created["role"], "Thu ngân")
        self.assertEqual(self.repository.created["phone"], "0901234567")
        self.assertNotIn("confirm_password", self.repository.created)

    def test_create_employee_rejects_missing_name(self):
        data = self.valid_data()
        data["name"] = "  "
        with self.assertRaisesRegex(ValueError, "họ tên"):
            self.service.create_employee(data)

    def test_create_employee_rejects_invalid_role(self):
        data = self.valid_data()
        data["role"] = "Admin"
        with self.assertRaisesRegex(ValueError, "vai trò"):
            self.service.create_employee(data)

    def test_create_employee_rejects_password_mismatch(self):
        data = self.valid_data()
        data["confirm_password"] = "different"
        with self.assertRaisesRegex(ValueError, "không khớp"):
            self.service.create_employee(data)

    def test_create_employee_rejects_invalid_phone(self):
        data = self.valid_data()
        data["phone"] = "phone-number"
        with self.assertRaisesRegex(ValueError, "Số điện thoại"):
            self.service.create_employee(data)

    def test_update_role_normalizes_employee_code(self):
        self.service.update_employee_role(" NV003 ", "Kế toán")
        self.assertEqual(self.repository.updated_role, ("NV003", "Kế toán"))

    def test_account_status_requires_boolean(self):
        with self.assertRaisesRegex(ValueError, "Trạng thái"):
            self.service.set_account_enabled("NV003", 1)

    def test_account_status_delegates_valid_value(self):
        self.service.set_account_enabled(" NV003 ", False)
        self.assertEqual(self.repository.account_status, ("NV003", False))

    def test_delete_account_normalizes_code(self):
        self.service.delete_account(" NV003 ")
        self.assertEqual(self.repository.deleted, "NV003")



if __name__ == "__main__":
    unittest.main()
