"""Kiểm thử các truy vấn quyền tự hủy và xác thực nhân viên đổi trả."""

import unittest

from core.doi_tra.repository import ReturnRepository
from core.hoa_don.repository import HoaDonRepository
from core.phieu_nhap.repository import PhieuNhapRepository


class FakeCursor:
    def __init__(self, results):
        self.results = list(results)
        self.commands = []
        self.closed = False

    def execute(self, sql, *params):
        self.commands.append((sql, params))
        return self

    def fetchone(self):
        return self.results.pop(0) if self.results else None

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


class FakeConnectionSource:
    def __init__(self, results):
        self.cursor = FakeCursor(results)
        self.connection = FakeConnection(self.cursor)

    def get_connection(self):
        return self.connection


class ReturnAuthorizationRepositoryTests(unittest.TestCase):
    def test_manager_must_match_sql_login_and_database_role(self):
        source = FakeConnectionSource([("NV001",), (1,)])

        result = ReturnRepository(source).get_authorized_employee(" NV001 ")

        self.assertEqual(result, "NV001")
        self.assertEqual(len(source.cursor.commands), 2)
        self.assertIn("ORIGINAL_LOGIN()", source.cursor.commands[0][0])
        self.assertIn("IS_ROLEMEMBER(N'rl_QuanLy')", source.cursor.commands[1][0])
        self.assertTrue(source.cursor.closed)

    def test_admin_is_authorized_only_when_current_sql_login_is_admin(self):
        source = FakeConnectionSource([("admin",), ("admin",)])

        result = ReturnRepository(source).get_authorized_employee(
            "admin", is_admin=True
        )

        self.assertEqual(result, "admin")
        self.assertEqual(len(source.cursor.commands), 2)
        self.assertIn("ORIGINAL_LOGIN()", source.cursor.commands[0][0])
        self.assertIn("FROM dbo.NHAN_VIEN", source.cursor.commands[1][0])
        self.assertTrue(source.cursor.closed)

    def test_rejects_username_that_does_not_match_sql_login(self):
        source = FakeConnectionSource([("NV002",)])

        with self.assertRaisesRegex(PermissionError, "không khớp"):
            ReturnRepository(source).get_authorized_employee("NV001")

        self.assertEqual(len(source.cursor.commands), 1)
        self.assertTrue(source.cursor.closed)

    def test_rejects_non_manager_database_user(self):
        source = FakeConnectionSource([("NV001",), (0,)])

        with self.assertRaises(PermissionError):
            ReturnRepository(source).get_authorized_employee("NV001")

        self.assertTrue(source.cursor.closed)

    def test_non_admin_cannot_claim_admin_flag(self):
        source = FakeConnectionSource([("NV001",)])

        with self.assertRaisesRegex(PermissionError, "Chỉ tài khoản admin"):
            ReturnRepository(source).get_authorized_employee(
                "NV001", is_admin=True
            )

        self.assertTrue(source.cursor.closed)


class InvoiceCancellationEligibilityTests(unittest.TestCase):
    def test_cashier_can_cancel_only_own_recent_active_invoice_without_return(self):
        source = FakeConnectionSource([(1,)])

        result = HoaDonRepository(source).can_cancel_invoice(
            " HD000001 ", " NV001 "
        )

        self.assertTrue(result)
        sql, params = source.cursor.commands[0]
        self.assertIn("ORIGINAL_LOGIN()", sql)
        self.assertIn("IS_ROLEMEMBER(N'rl_ThuNgan')", sql)
        self.assertIn("N'Thu ngân'", sql)
        self.assertIn("NOT EXISTS", sql)
        self.assertIn("dbo.PHIEU_DOI_TRA", sql)
        self.assertEqual(params, ("NV001", "NV001", "NV001", "HD000001"))
        self.assertTrue(source.cursor.closed)

    def test_ineligible_invoice_returns_false(self):
        source = FakeConnectionSource([(0,)])

        self.assertFalse(
            HoaDonRepository(source).can_cancel_invoice("HD000001", "NV001")
        )
        self.assertTrue(source.cursor.closed)

    def test_empty_invoice_or_username_does_not_query_database(self):
        source = FakeConnectionSource([])

        repository = HoaDonRepository(source)
        self.assertFalse(repository.can_cancel_invoice("", "NV001"))
        self.assertFalse(repository.can_cancel_invoice("HD000001", " "))
        self.assertEqual(source.cursor.commands, [])


class ImportCancellationEligibilityTests(unittest.TestCase):
    def test_warehouse_can_cancel_only_own_recent_active_import(self):
        source = FakeConnectionSource([(1,)])

        result = PhieuNhapRepository(source).can_cancel_import(
            " PN000001 ", " NV002 "
        )

        self.assertTrue(result)
        sql, params = source.cursor.commands[0]
        self.assertIn("ORIGINAL_LOGIN()", sql)
        self.assertIn("IS_ROLEMEMBER(N'rl_NhanVienKho')", sql)
        self.assertIn("N'Nhân viên kho'", sql)
        self.assertEqual(params, ("NV002", "NV002", "NV002", "PN000001"))
        self.assertTrue(source.cursor.closed)

    def test_ineligible_import_returns_false(self):
        source = FakeConnectionSource([(0,)])

        self.assertFalse(
            PhieuNhapRepository(source).can_cancel_import("PN000001", "NV002")
        )
        self.assertTrue(source.cursor.closed)

    def test_empty_import_or_username_does_not_query_database(self):
        source = FakeConnectionSource([])

        repository = PhieuNhapRepository(source)
        self.assertFalse(repository.can_cancel_import("", "NV002"))
        self.assertFalse(repository.can_cancel_import("PN000001", " "))
        self.assertEqual(source.cursor.commands, [])


if __name__ == "__main__":
    unittest.main()
