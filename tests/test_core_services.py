"""Kiểm thử các quy tắc đầu vào của service sản phẩm, không cần SQL Server."""

import unittest
from datetime import date, datetime
from decimal import Decimal

from core.san_pham.repository import SanPhamRepository
from core.san_pham.service import SanPhamService
from core.nha_cung_cap.repository import NhaCungCapRepository
from core.nha_cung_cap.service import NhaCungCapService
from core.phieu_nhap.repository import PhieuNhapRepository
from core.phieu_nhap.service import PhieuNhapService
from core.hoa_don.repository import HoaDonRepository
from core.hoa_don.service import HoaDonService
from core.doi_tra.repository import ReturnRepository
from core.doi_tra.service import ReturnService
from core.nhan_vien.repository import NhanVienRepository
from core.nhan_vien.service import NhanVienService
from core.ca_lam_viec.repository import CaLamViecRepository
from core.ca_lam_viec.service import CaLamViecService
from core.khuyen_mai.repository import KhuyenMaiRepository
from core.khuyen_mai.service import KhuyenMaiService
from core.bao_cao.repository import BaoCaoRepository
from core.bao_cao.service import BaoCaoService


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

    def test_refund_is_difference_between_original_and_hypothetical_invoice(self):
        items = [{
            "product_code": "SP001",
            "purchased": 3,
            "processed": 0,
            "refunded": 0,
            "original_price": Decimal("5555.00"),
        }]
        first = self.service.calculate_invoice_refund(
            items,
            [{"product_code": "SP001", "quantity": 1, "condition": 1, "action": 0}],
            Decimal("10.00"),
        )
        self.assertEqual(first["before_total"], Decimal("14998.50"))
        self.assertEqual(first["after_total"], Decimal("9999.00"))
        self.assertEqual(first["total_refund"], Decimal("4999.50"))

        # Lần trả sau phải lấy hóa đơn còn lại làm số dư trước khi trả.
        items[0]["processed"] = 1
        items[0]["refunded"] = 1
        second = self.service.calculate_invoice_refund(
            items,
            [{"product_code": "SP001", "quantity": 1, "condition": 1, "action": 0}],
            Decimal("10.00"),
        )
        self.assertEqual(second["before_total"], Decimal("9999.00"))
        self.assertEqual(second["after_total"], Decimal("4999.50"))
        self.assertEqual(second["total_refund"], Decimal("4999.50"))

        # Trả sản phẩm cuối cùng: hoàn đúng phần còn lại.
        items[0]["processed"] = 2
        items[0]["refunded"] = 2
        last = self.service.calculate_invoice_refund(
            items,
            [{"product_code": "SP001", "quantity": 1, "condition": 1, "action": 0}],
            Decimal("10.00"),
        )
        self.assertEqual(last["before_total"], Decimal("4999.50"))
        self.assertEqual(last["after_total"], Decimal("0.00"))
        self.assertEqual(last["total_refund"], Decimal("4999.50"))
        self.assertEqual(
            first["total_refund"] + second["total_refund"] + last["total_refund"],
            Decimal("14998.50"),
        )

    def test_full_return_refunds_exact_original_discounted_total(self):
        result = self.service.calculate_invoice_refund(
            [
                {
                    "product_code": "SP001",
                    "purchased": 2,
                    "processed": 0,
                    "refunded": 0,
                    "original_price": Decimal("0.05"),
                },
                {
                    "product_code": "SP002",
                    "purchased": 1,
                    "processed": 0,
                    "refunded": 0,
                    "original_price": Decimal("5.555"),
                },
            ],
            [
                {"product_code": "SP001", "quantity": 2, "condition": 1, "action": 0},
                {"product_code": "SP002", "quantity": 1, "condition": 1, "action": 0},
            ],
            Decimal("10.00"),
        )
        self.assertEqual(result["after_total"], Decimal("0.00"))
        self.assertEqual(result["total_refund"], result["before_total"])

    def test_exchange_does_not_reduce_hypothetical_invoice_total(self):
        result = self.service.calculate_invoice_refund(
            [{
                "product_code": "SP001",
                "purchased": 2,
                "processed": 0,
                "refunded": 0,
                "original_price": Decimal("100.00"),
            }],
            [{"product_code": "SP001", "quantity": 1, "condition": 0, "action": 1}],
            Decimal("10.00"),
        )
        self.assertEqual(result["before_total"], Decimal("180.00"))
        self.assertEqual(result["after_total"], Decimal("180.00"))
        self.assertEqual(result["total_refund"], Decimal("0.00"))



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



class FakeShiftRepository(CaLamViecRepository):
    def __init__(self):
        self.created = None
        self.registered = None
        self.closed = None
        self.deleted = None
        self.period = None

    def create_shift(self, values):
        self.created = values
        return 12

    def register_current_shift(self, shift_id, username):
        self.registered = (shift_id, username)
        return True

    def record_closing_cash(self, shift_id, username, amount):
        self.closed = (shift_id, username, amount)
        return True

    def list_shift_history(self, period="all"):
        self.period = period
        return []

    def delete_shift(self, shift_id):
        self.deleted = shift_id
        return True


class ShiftServiceTests(unittest.TestCase):
    def setUp(self):
        self.repository = FakeShiftRepository()
        self.service = CaLamViecService(self.repository)

    def test_create_shift_uses_fixed_schedule_and_decimal_cash(self):
        shift_id = self.service.create_shift({
            "soca": 2, "ngaylam": "2026-11-28", "tmdauca": "500000"
        }, is_manager=True)
        self.assertEqual(shift_id, 12)
        self.assertEqual(self.repository.created["tgmo"], "12:00:00")
        self.assertEqual(self.repository.created["tgdong"], "17:00:00")
        self.assertEqual(self.repository.created["tmdauca"], Decimal("500000.00"))


    def test_create_shift_requires_manager(self):
        with self.assertRaises(PermissionError):
            self.service.create_shift({
                "soca": 1, "ngaylam": "2026-11-28", "tmdauca": "0"
            })

    def test_create_shift_rejects_unknown_shift_number(self):
        with self.assertRaisesRegex(ValueError, "ca 1"):
            self.service.create_shift({
                "soca": 4, "ngaylam": "2026-11-28", "tmdauca": "0"
            }, is_manager=True)

    def test_create_shift_rejects_invalid_date(self):
        with self.assertRaisesRegex(ValueError, "Ngày làm"):
            self.service.create_shift({
                "soca": 1, "ngaylam": "not-a-date", "tmdauca": "0"
            }, is_manager=True)

    def test_cash_parser_accepts_zero_and_formats_decimal(self):
        self.assertEqual(
            self.service.parse_cash("0", "tiền đầu ca"), Decimal("0.00")
        )

    def test_cash_parser_rejects_negative_and_non_finite(self):
        for amount in ("-1", "NaN", "Infinity"):
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError):
                    self.service.parse_cash(amount, "tiền cuối ca")

    def test_cash_parser_rejects_value_above_sql_decimal(self):
        with self.assertRaisesRegex(ValueError, "giới hạn"):
            self.service.parse_cash("10000000000000", "tiền đầu ca")

    def test_register_shift_normalizes_identifier(self):
        self.service.register_current_shift(" 12 ", "NV001")
        self.assertEqual(self.repository.registered, (12, "NV001"))

    def test_record_closing_cash_uses_decimal(self):
        self.service.record_closing_cash(12, "NV002", "1234.5")
        self.assertEqual(
            self.repository.closed, (12, "NV002", Decimal("1234.50"))
        )

    def test_history_rejects_unknown_period(self):
        with self.assertRaisesRegex(ValueError, "khoảng thời gian"):
            self.service.list_shift_history("forever")

    def test_history_passes_supported_period(self):
        self.service.list_shift_history("7days")
        self.assertEqual(self.repository.period, "7days")

    def test_delete_shift_requires_manager(self):
        with self.assertRaises(PermissionError):
            self.service.delete_shift(12, is_manager=False)

    def test_delete_shift_delegates_for_manager(self):
        self.assertTrue(self.service.delete_shift("12", is_manager=True))
        self.assertEqual(self.repository.deleted, 12)

    def test_shift_id_must_be_positive_integer(self):
        for shift_id in (0, -1, "invalid"):
            with self.subTest(shift_id=shift_id):
                with self.assertRaises(ValueError):
                    self.service.register_current_shift(shift_id, "NV001")



class FakePromotionRepository(KhuyenMaiRepository):
    def __init__(self):
        self.created = None
        self.renamed = None
        self.deleted = None

    def create_promotion(self, data):
        self.created = data
        return "KM000123"

    def rename_promotion(self, promotion_code, name):
        self.renamed = (promotion_code, name)
        return promotion_code

    def soft_delete_promotion(self, promotion_code):
        self.deleted = promotion_code
        return promotion_code


class PromotionServiceTests(unittest.TestCase):
    def setUp(self):
        self.repository = FakePromotionRepository()
        self.service = KhuyenMaiService(self.repository)

    def valid_data(self):
        return {
            "name": "  Khuyến mãi cuối tuần  ",
            "discount_rate": "15.5",
            "start_at": datetime(2026, 11, 28, 7, 0),
            "end_at": datetime(2026, 12, 1, 22, 0),
        }

    def test_create_promotion_normalizes_fields(self):
        code = self.service.create_promotion(self.valid_data(), can_manage=True)
        self.assertEqual(code, "KM000123")
        self.assertEqual(self.repository.created["name"], "Khuyến mãi cuối tuần")
        self.assertEqual(self.repository.created["discount_rate"], Decimal("15.50"))
        self.assertEqual(self.repository.created["start_at"], datetime(2026, 11, 28, 7, 0))

    def test_create_promotion_requires_manager(self):
        with self.assertRaises(PermissionError):
            self.service.create_promotion(self.valid_data(), can_manage=False)

    def test_create_promotion_requires_name(self):
        data = self.valid_data()
        data["name"] = " "
        with self.assertRaisesRegex(ValueError, "không được để trống"):
            self.service.create_promotion(data, can_manage=True)

    def test_create_promotion_rejects_name_over_database_limit(self):
        data = self.valid_data()
        data["name"] = "x" * 101
        with self.assertRaisesRegex(ValueError, "100 ký tự"):
            self.service.create_promotion(data, can_manage=True)

    def test_create_promotion_rejects_invalid_discount(self):
        for rate in ("-0.01", "100.01", "NaN", "Infinity", "invalid"):
            data = self.valid_data()
            data["discount_rate"] = rate
            with self.subTest(rate=rate):
                with self.assertRaises(ValueError):
                    self.service.create_promotion(data, can_manage=True)

    def test_create_promotion_accepts_zero_and_one_hundred_percent(self):
        for rate in ("0", "100"):
            data = self.valid_data()
            data["discount_rate"] = rate
            self.service.create_promotion(data, can_manage=True)
            self.assertEqual(self.repository.created["discount_rate"], Decimal(rate).quantize(Decimal("0.01")))

    def test_create_promotion_rejects_end_before_start(self):
        data = self.valid_data()
        data["end_at"] = datetime(2026, 11, 28, 7, 0)
        with self.assertRaisesRegex(ValueError, "phải sau"):
            self.service.create_promotion(data, can_manage=True)

    def test_create_promotion_rejects_timezone_aware_datetime(self):
        data = self.valid_data()
        data["start_at"] = "2026-11-28T07:00:00+07:00"
        with self.assertRaisesRegex(ValueError, "không kèm timezone"):
            self.service.create_promotion(data, can_manage=True)

    def test_rename_promotion_only_delegates_name(self):
        self.assertEqual(
            self.service.rename_promotion(" KM000123 ", "  Đổi tên  ", can_manage=True),
            "KM000123",
        )
        self.assertEqual(self.repository.renamed, ("KM000123", "Đổi tên"))

    def test_rename_promotion_requires_manager(self):
        with self.assertRaises(PermissionError):
            self.service.rename_promotion("KM001", "New", can_manage=False)

    def test_soft_delete_promotion_requires_manager(self):
        with self.assertRaises(PermissionError):
            self.service.soft_delete_promotion("KM001", can_manage=False)

    def test_soft_delete_promotion_normalizes_code(self):
        self.assertEqual(
            self.service.soft_delete_promotion(" KM001 ", can_manage=True),
            "KM001",
        )
        self.assertEqual(self.repository.deleted, "KM001")


class FakeReportRepository(BaoCaoRepository):
    def __init__(self):
        self.calls = []

    def employees(self):
        self.calls.append(("employees",))
        return [("NV01", "Thu ngân 1")]

    def daily_sales_report(self, start, end, employee=None, keyword=""):
        self.calls.append(("daily_sales_report", start, end, employee, keyword))
        return []

    def sales_by_period_report(self, start, end, period="day"):
        self.calls.append(("sales_by_period_report", start, end, period))
        return []

    def sales_by_employee_report(self, start, end, keyword=""):
        self.calls.append(("sales_by_employee_report", start, end, keyword))
        return []

    def sales_by_product_report(self, start, end, keyword=""):
        self.calls.append(("sales_by_product_report", start, end, keyword))
        return []

    def promotion_report(self, start, end, keyword=""):
        self.calls.append(("promotion_report", start, end, keyword))
        return []

    def return_detail_report(self, start, end, keyword=""):
        self.calls.append(("return_detail_report", start, end, keyword))
        return []

    def import_detail_report(self, start, end, keyword=""):
        self.calls.append(("import_detail_report", start, end, keyword))
        return []

    def import_product_report(self, start, end, keyword=""):
        self.calls.append(("import_product_report", start, end, keyword))
        return []

    def import_supplier_report(self, start, end, keyword=""):
        self.calls.append(("import_supplier_report", start, end, keyword))
        return []

    def current_inventory_report(self, threshold, status="all", keyword=""):
        self.calls.append(("current_inventory_report", threshold, status, keyword))
        return []

    def stock_movement_report(self, start, end, keyword=""):
        self.calls.append(("stock_movement_report", start, end, keyword))
        return []

    def stock_card_report(self, start, end, keyword=""):
        self.calls.append(("stock_card_report", start, end, keyword))
        return []

    def cash_flow_report(self, start, end, period="day"):
        self.calls.append(("cash_flow_report", start, end, period))
        return []

    def shift_report(self, start, end):
        self.calls.append(("shift_report", start, end))
        return []


class ReportServiceTests(unittest.TestCase):
    def setUp(self):
        self.repository = FakeReportRepository()
        self.service = BaoCaoService(self.repository)

    def test_service_exposes_defined_report_methods(self):
        for method in (
            "daily_sales_report", "sales_by_period_report", "cash_flow_report",
            "sales_by_employee_report", "sales_by_product_report",
            "promotion_report", "return_detail_report",
            "import_detail_report", "import_product_report", "import_supplier_report",
            "current_inventory_report", "stock_movement_report",
            "stock_card_report", "shift_report",
        ):
            self.assertTrue(callable(getattr(self.service, method)))
        self.assertFalse(hasattr(self.service, "fetch_all"))
        self.assertFalse(hasattr(self.service, "fetch_one"))

    def test_report_service_validates_date_range(self):
        with self.assertRaisesRegex(ValueError, "không được lớn hơn"):
            self.service.daily_sales_report("2026-12-02", "2026-12-01")

    def test_report_service_rejects_invalid_date(self):
        with self.assertRaisesRegex(ValueError, "không hợp lệ"):
            self.service.shift_report("today", "2026-12-01")

    def test_daily_sales_passes_employee_and_keyword_filters(self):
        self.service.daily_sales_report(
            "2026-11-01", "2026-11-30", "NV01", "HD001"
        )
        self.assertEqual(
            self.repository.calls[-1],
            ("daily_sales_report", "2026-11-01", "2026-11-30", "NV01", "HD001"),
        )

    def test_period_report_accepts_only_supported_periods(self):
        for period in ("day", "month", "year"):
            self.service.sales_by_period_report("2026-01-01", "2026-01-31", period)
        self.assertEqual(
            self.repository.calls[-3:],
            [
                ("sales_by_period_report", "2026-01-01", "2026-01-31", "day"),
                ("sales_by_period_report", "2026-01-01", "2026-01-31", "month"),
                ("sales_by_period_report", "2026-01-01", "2026-01-31", "year"),
            ],
        )
        with self.assertRaisesRegex(ValueError, "thời gian"):
            self.service.sales_by_period_report(
                "2026-01-01", "2026-01-31", "day; DROP TABLE HOA_DON"
            )

    def test_cash_flow_report_delegates_and_validates_period(self):
        self.service.cash_flow_report("2026-01-01", "2026-01-31", "month")
        self.assertEqual(
            self.repository.calls[-1],
            ("cash_flow_report", "2026-01-01", "2026-01-31", "month"),
        )
        with self.assertRaisesRegex(ValueError, "thời gian"):
            self.service.cash_flow_report(
                "2026-01-01", "2026-01-31", "invalid"
            )

    def test_keyword_length_is_limited(self):
        with self.assertRaisesRegex(ValueError, "100 ký tự"):
            self.service.sales_by_product_report(
                "2026-01-01", "2026-01-31", "x" * 101
            )

    def test_import_product_report_delegates_with_validated_dates_and_keyword(self):
        self.service.import_product_report(
            "2026-11-01", "2026-11-30", "BARCODE01"
        )
        self.assertEqual(
            self.repository.calls[-1],
            ("import_product_report", "2026-11-01", "2026-11-30", "BARCODE01"),
        )
        with self.assertRaisesRegex(ValueError, "không được lớn hơn"):
            self.service.import_product_report("2026-11-30", "2026-11-01")

    def test_current_inventory_validates_threshold_and_status(self):
        self.service.current_inventory_report(10, "low", "book")
        self.assertEqual(
            self.repository.calls[-1],
            ("current_inventory_report", 10, "low", "book"),
        )
        with self.assertRaises(ValueError):
            self.service.current_inventory_report(0, "low")
        with self.assertRaises(ValueError):
            self.service.current_inventory_report(5, "unknown")

    def test_stock_and_shift_reports_delegate_with_validated_dates(self):
        self.service.stock_movement_report("2026-01-01", "2026-01-31", "SP")
        self.service.stock_card_report("2026-01-01", "2026-01-31", "SP")
        self.service.shift_report("2026-01-01", "2026-01-31")
        self.assertEqual(
            self.repository.calls[-3:],
            [
                ("stock_movement_report", "2026-01-01", "2026-01-31", "SP"),
                ("stock_card_report", "2026-01-01", "2026-01-31", "SP"),
                ("shift_report", "2026-01-01", "2026-01-31"),
            ],
        )

    def test_report_repository_exposes_only_private_fetch_helpers(self):
        import inspect
        source = inspect.getsource(BaoCaoRepository)
        self.assertIn("def _fetch_all(", source)
        self.assertIn("def _fetch_one(", source)
        self.assertNotIn("\n    def fetch_all(", source)
        self.assertNotIn("\n    def fetch_one(", source)

    def test_daily_sales_sql_uses_invoice_level_refund_total_and_outer_alias(self):
        class CaptureRepository(BaoCaoRepository):
            def __init__(self):
                self.sql = ""
                self.params = None

            def _fetch_all(self, sql, params=()):
                self.sql = sql
                self.params = params
                return []

        repository = CaptureRepository()
        repository.daily_sales_report(
            "2026-01-01", "2026-01-31", "NV01", "HD"
        )
        self.assertIn("ReturnHeaders AS", repository.sql)
        self.assertIn("I.TENNV LIKE ?", repository.sql)
        self.assertNotIn("NV.TENNV LIKE ?", repository.sql)
        self.assertIn("SUM(COALESCE(TONG_TIEN_HOAN, 0))", repository.sql)
        self.assertNotIn("ReturnLines AS", repository.sql)
        self.assertNotIn("SO_PHIEU_TRA", repository.sql)
        self.assertEqual(
            repository.params,
            ("2026-01-01", "2026-01-31", "NV01",
             "%HD%", "%HD%", "%HD%", "%HD%"),
        )

    def test_daily_sales_projection_matches_pos_report_column_order(self):
        class CaptureRepository(BaoCaoRepository):
            def __init__(self):
                self.sql = ""
                self.params = None

            def _fetch_all(self, sql, params=()):
                self.sql = sql
                self.params = params
                return []

        repository = CaptureRepository()
        repository.daily_sales_report("2026-01-01", "2026-01-31", None, "NV01")
        select = repository.sql.split("FROM InvoiceLines I", 1)[0]
        ordered_tokens = [
            "SELECT I.MAHD, I.NGAYLAP, I.SO_LUONG, I.TIEN_HANG,",
            "ROUND(I.TIEN_HANG * I.TYLEGIAM / 100.0, 2)",
            "AS THUC_THU",
            "COALESCE(RH.TIEN_HOAN, 0)",
            "AS DOANH_THU_SAU_HOAN",
            "AS TIEN_THUA",
            "I.TENNV,",
            "I.SO_DONG, N'Bán hàng'",
        ]
        positions = [select.index(token) for token in ordered_tokens]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("COALESCE(RH.SO_PHIEU_TRA, 0)", select)
        self.assertEqual(
            repository.params,
            ("2026-01-01", "2026-01-31",
             "%NV01%", "%NV01%", "%NV01%", "%NV01%"),
        )

    def test_import_detail_projection_puts_product_and_amount_before_extra_fields(self):
        class CaptureRepository(BaoCaoRepository):
            def __init__(self):
                self.sql = ""

            def _fetch_all(self, sql, params=()):
                self.sql = sql
                return []

        repository = CaptureRepository()
        repository.import_detail_report("2026-01-01", "2026-01-31")
        select = repository.sql.split("FROM dbo.PHIEU_NHAP PN", 1)[0]
        ordered_tokens = [
            "SELECT PN.MAPN, PN.NGAYNHAP",
            "COALESCE(NCC.TENNCC, PN.MANCC, N''), CT.MASP",
            "COALESCE(SP.TENSP, N''), COALESCE(SP.DVT, N''),",
            "COALESCE(CT.SOLUONG, 0), COALESCE(CT.DONGIA, 0)",
            "COALESCE(CT.SOLUONG, 0) * COALESCE(CT.DONGIA, 0)",
            "COALESCE(PN.SHDNCC, N''), COALESCE(NV.TENNV, PN.MANV, N'')",
        ]
        positions = [select.index(token) for token in ordered_tokens]
        self.assertEqual(positions, sorted(positions))

    def test_current_inventory_projection_starts_with_quantity_and_stock_value(self):
        class CaptureRepository(BaoCaoRepository):
            def __init__(self):
                self.sql = ""
                self.params = None

            def _fetch_all(self, sql, params=()):
                self.sql = sql
                self.params = params
                return []

        repository = CaptureRepository()
        repository.current_inventory_report(5, "all", "BOOK")
        self.assertIn("ROW_NUMBER() OVER", repository.sql)
        self.assertIn("AS STT", repository.sql)
        self.assertIn(
            "COALESCE(SP.SLTON, 0) * COALESCE(SP.GIANHAP, 0)",
            repository.sql,
        )
        self.assertEqual(
            repository.params,
            (5, "%BOOK%", "%BOOK%", "%BOOK%"),
        )

    def test_import_product_report_uses_only_persisted_purchase_values(self):
        class CaptureRepository(BaoCaoRepository):
            def __init__(self):
                self.sql = ""
                self.params = None

            def _fetch_all(self, sql, params=()):
                self.sql = sql
                self.params = params
                return []

        repository = CaptureRepository()
        repository.import_product_report(
            "2026-01-01", "2026-01-31", "BOOK"
        )
        self.assertIn("SUM(CT.SOLUONG)", repository.sql)
        self.assertIn("SUM(CT.SOLUONG * CT.DONGIA)", repository.sql)
        self.assertIn("COUNT(DISTINCT PN.MAPN)", repository.sql)
        self.assertIn("PN.TRANGTHAI", repository.sql)
        self.assertNotIn("CHIETKHAU", repository.sql.upper())
        self.assertNotIn("TRALAI", repository.sql.upper())
        self.assertEqual(
            repository.params,
            ("2026-01-01", "2026-01-31",
             "%BOOK%", "%BOOK%", "%BOOK%", "%BOOK%"),
        )

    def test_sales_product_projection_matches_product_report_column_order(self):
        class CaptureRepository(BaoCaoRepository):
            def __init__(self):
                self.sql = ""

            def _fetch_all(self, sql, params=()):
                self.sql = sql
                return []

        repository = CaptureRepository()
        repository.sales_by_product_report("2026-01-01", "2026-01-31")
        select = repository.sql.split("FROM dbo.SAN_PHAM SP", 1)[0]
        self.assertIn(
            "SELECT SP.MASP, COALESCE(SP.TENSP, N''), COALESCE(SP.DVT, N''),",
            select,
        )
        self.assertIn(
            "COALESCE(SP.BARCODE, N''), COALESCE(BK.ISBN, N'')",
            select,
        )

    def test_stock_movement_uses_historical_opening_and_return_date_adjustments(self):
        class CaptureRepository(BaoCaoRepository):
            def __init__(self):
                self.sql = ""
                self.params = None

            def _fetch_all(self, sql, params=()):
                self.sql = sql
                self.params = params
                return []

        repository = CaptureRepository()
        repository.stock_movement_report(
            "2026-11-01", "2026-11-28", "SP001"
        )
        self.assertIn("M.NGAY < B.START_DATE", repository.sql)
        self.assertIn("N'Phiếu đổi trả' AS LOAI_CHUNG_TU", repository.sql)
        self.assertIn("PDT.NGAY_DOI_TRA", repository.sql)
        self.assertIn("CTDT.HINH_THUC_XU_LY = 0", repository.sql)
        self.assertIn("CTDT.TINHTRANGHANG = 1", repository.sql)
        self.assertIn("CTDT.HINH_THUC_XU_LY = 1", repository.sql)
        self.assertIn("COALESCE(M.TON_DAU, 0)", repository.sql)
        self.assertIn("+ COALESCE(M.SL_NHAP, 0)", repository.sql)
        self.assertIn("- COALESCE(M.SL_XUAT, 0)", repository.sql)
        self.assertNotIn("SP.SLTON", repository.sql)
        self.assertNotIn("ReturnByInvoiceProduct", repository.sql)
        self.assertEqual(
            repository.params,
            ("2026-11-01", "2026-11-28", "%SP001%", "%SP001%", "%SP001%"),
        )



    def test_stock_card_uses_return_voucher_date_for_running_stock_balance(self):
        class CaptureRepository(BaoCaoRepository):
            def __init__(self):
                self.sql = ""
                self.params = None

            def _fetch_all(self, sql, params=()):
                self.sql = sql
                self.params = params
                return []

        repository = CaptureRepository()
        repository.stock_card_report(
            "2026-11-01", "2026-11-28", "SP001"
        )
        self.assertIn("N'Phiếu đổi trả' AS LOAI_CHUNG_TU", repository.sql)
        self.assertIn("PDT.NGAY_DOI_TRA", repository.sql)
        self.assertIn("O.TON_DAU + SUM(P.SL_NHAP - P.SL_XUAT)", repository.sql)
        self.assertNotIn("SP.SLTON", repository.sql)
        self.assertEqual(
            repository.params,
            ("2026-11-01", "2026-11-28", "%SP001%", "%SP001%", "%SP001%"),
        )



    def test_shift_report_binds_all_six_date_placeholders(self):
        class CaptureRepository(BaoCaoRepository):
            def __init__(self):
                self.sql = ""
                self.params = None

            def _fetch_all(self, sql, params=()):
                self.sql = sql
                self.params = params
                return []

        repository = CaptureRepository()
        repository.shift_report("2026-11-01", "2026-11-30")
        self.assertEqual(repository.sql.count("?"), 6)
        self.assertEqual(
            repository.params,
            (
                "2026-11-01", "2026-11-30",
                "2026-11-01", "2026-11-30",
                "2026-11-01", "2026-11-30",
            ),
        )
        self.assertIn("FROM dbo.CA_LAM_VIEC C", repository.sql)
        self.assertIn("LEFT JOIN Sales S ON S.MACA = C.MACA", repository.sql)
        self.assertIn("LEFT JOIN Returns R ON R.MACA = C.MACA", repository.sql)

    def test_cash_flow_report_aggregates_sales_imports_and_refunds(self):
        class CaptureRepository(BaoCaoRepository):
            def __init__(self):
                self.sql = ""
                self.params = None

            def _fetch_all(self, sql, params=()):
                self.sql = sql
                self.params = params
                return []

        repository = CaptureRepository()
        repository.cash_flow_report("2026-01-01", "2026-01-31", "month")
        self.assertIn("FROM dbo.HOA_DON HD", repository.sql)
        self.assertIn("PN.TONGTRIGIA", repository.sql)
        self.assertIn("FROM dbo.PHIEU_DOI_TRA PDT", repository.sql)
        self.assertIn("PDT.TONG_TIEN_HOAN", repository.sql)
        self.assertIn("ISNULL(PN.TRANGTHAI, 1) = 1", repository.sql)
        self.assertNotIn("TIENKHACHDUA", repository.sql)
        self.assertEqual(repository.sql.count("?"), 6)
        self.assertEqual(
            repository.params,
            (
                "2026-01-01", "2026-01-31",
                "2026-01-01", "2026-01-31",
                "2026-01-01", "2026-01-31",
            ),
        )

    def test_employee_report_does_not_multiply_return_header_amounts(self):
        class CaptureRepository(BaoCaoRepository):
            def __init__(self):
                self.sql = ""
                self.params = None

            def _fetch_all(self, sql, params=()):
                self.sql = sql
                self.params = params
                return []

        repository = CaptureRepository()
        repository.sales_by_employee_report("2026-01-01", "2026-01-31")
        self.assertIn("ReturnHeaders AS", repository.sql)
        self.assertNotIn("ReturnLines AS", repository.sql)
        self.assertIn("SUM(COALESCE(TONG_TIEN_HOAN, 0))", repository.sql)
        self.assertEqual(
            repository.params,
            ("2026-01-01", "2026-01-31",
             "2026-01-01", "2026-01-31"),
        )



if __name__ == "__main__":
    unittest.main()
