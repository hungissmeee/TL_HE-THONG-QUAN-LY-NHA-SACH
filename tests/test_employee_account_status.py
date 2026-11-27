"""Kiểm thử thao tác ngưng hoạt động và kích hoạt lại tài khoản nhân viên."""

import unittest

from database.connection import Database
from core.nhan_vien.repository import NhanVienRepository


class FakeCursor:
    def __init__(self, disabled_state=None):
        self.disabled_state = disabled_state
        self.commands = []
        self.closed = False

    def execute(self, sql, *params):
        self.commands.append((sql, params))
        return self

    def fetchone(self):
        if self.disabled_state is None:
            return None
        return (self.disabled_state,)

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class EmployeeAccountStatusTests(unittest.TestCase):
    def make_database(self, disabled_state):
        cursor = FakeCursor(disabled_state)
        connection = FakeConnection(cursor)
        db = Database()
        db.username = "admin"
        db.conn = connection
        return db, cursor, connection

    def test_disable_account_uses_alter_login_disable(self):
        db, cursor, connection = self.make_database(0)

        NhanVienRepository(db).set_account_enabled("NV001", False)

        self.assertIn(
            ("ALTER LOGIN [NV001] DISABLE", ()),
            cursor.commands,
        )
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)
        self.assertTrue(cursor.closed)

    def test_enable_account_uses_alter_login_enable(self):
        db, cursor, connection = self.make_database(1)

        NhanVienRepository(db).set_account_enabled("NV001", True)

        self.assertIn(
            ("ALTER LOGIN [NV001] ENABLE", ()),
            cursor.commands,
        )
        self.assertEqual(connection.commits, 1)

    def test_admin_account_cannot_be_disabled(self):
        db, cursor, connection = self.make_database(0)

        with self.assertRaises(PermissionError):
            NhanVienRepository(db).set_account_enabled("admin", False)

        self.assertEqual(cursor.commands, [])
        self.assertEqual(connection.commits, 0)

    def test_missing_sql_login_is_rejected(self):
        db, cursor, connection = self.make_database(None)

        with self.assertRaisesRegex(Exception, "không tồn tại"):
            NhanVienRepository(db).set_account_enabled("NV999", False)

        self.assertEqual(connection.rollbacks, 1)
        self.assertTrue(cursor.closed)


if __name__ == "__main__":
    unittest.main()
