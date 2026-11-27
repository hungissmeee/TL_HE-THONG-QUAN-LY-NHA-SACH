"""Smoke tests cho API các phân hệ nghiệp vụ Web, không cần SQL Server."""

import unittest

from fastapi.testclient import TestClient

from backend.dependencies import get_db_connection
from backend.main import create_app
from backend.security import CurrentUser, get_current_user


class OperationsAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.dependency_overrides[get_db_connection] = lambda: object()
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()

    def _as_user(self, role_code, role):
        user = CurrentUser(
            employee_code="NVTEST",
            full_name="Nhân viên kiểm thử",
            role=role,
            role_code=role_code,
        )
        self.app.dependency_overrides[get_current_user] = lambda: user

    def test_operations_api_requires_login(self):
        response = self.client.get("/api/v1/suppliers")
        self.assertEqual(response.status_code, 401)

    def test_cashier_cannot_manage_promotions(self):
        self._as_user("rl_ThuNgan", "Thu ngân")
        response = self.client.post("/api/v1/promotions", json={
            "name": "Khuyến mãi thử",
            "discount_rate": "10",
            "start_at": "2026-11-27T08:00:00",
            "end_at": "2026-11-28T08:00:00",
        })
        self.assertEqual(response.status_code, 403)

    def test_accountant_cannot_create_invoice(self):
        self._as_user("rl_KeToan", "Kế toán")
        response = self.client.post("/api/v1/invoices", json={
            "cash": "100000",
            "items": [{"product_code": "SP001", "quantity": 1}],
        })
        self.assertEqual(response.status_code, 403)

    def test_cashier_cannot_read_management_reports(self):
        self._as_user("rl_ThuNgan", "Thu ngân")
        response = self.client.get("/api/v1/reports/report_overview")
        self.assertEqual(response.status_code, 403)

    def test_manager_cannot_manage_employee_sql_accounts(self):
        self._as_user("rl_QuanLy", "Quản lý")
        response = self.client.get("/api/v1/employees")
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
