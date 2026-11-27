"""Kiểm thử API sản phẩm và quyền truy cập, không cần SQL Server."""

import unittest

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.security import CurrentUser, get_current_user
from backend.api.routes.products import get_product_service
from core.repositories.san_pham_repository import SanPhamRepository


class FakeProductService:
    def __init__(self):
        self.saved = None
        self.deleted = None

    def list_products_page(self, **kwargs):
        return {
            "items": [{
                "masp": "SP001", "tensp": "Sách kiểm thử",
                "loai": "Sách", "dvt": "Quyển", "gianhap": 50000,
                "giaban": 75000, "slton": 3, "vat": 8,
                "barcode": "8930000000001", "isbn": "9786040000000",
            }],
            "total": 1,
        }

    def get_product_detail(self, code):
        if code != "SP001":
            return None
        return {"masp": code, "tensp": "Sách kiểm thử", "loai": "Sách"}

    def get_product_for_edit(self, code):
        return {
            "masp": code,
            "selected_author_codes": {"TG002", "TG001"},
            "selected_genre_codes": {"TL001"},
        }

    def get_lookup_data(self, **kwargs):
        return {
            "publishers": [("NXB001", "Nhà xuất bản", 0)],
            "authors": [("TG001", "Tác giả", 0)],
            "genres": [("TL001", "Thể loại", 0)],
            "brands": [("TH001", "Thương hiệu", 0)],
        }

    def preview_next_product_code(self):
        return "SP002"

    def save_product(self, data, product_code=None):
        self.saved = (data, product_code)
        return product_code or "SP002"

    def soft_delete_product(self, code):
        self.deleted = code
        return "Sách kiểm thử"


class ProductApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.service = FakeProductService()
        self.app.dependency_overrides[get_product_service] = lambda: self.service
        self.user = CurrentUser(
            employee_code="NV001",
            full_name="Nhân viên kiểm thử",
            role="Nhân viên kho",
            role_code="rl_NhanVienKho",
        )
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()

    def test_list_products_returns_pagination_and_barcode_isbn(self):
        response = self.client.get("/api/v1/products?keyword=893000&page=1&page_size=20")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["barcode"], "8930000000001")
        self.assertEqual(payload["items"][0]["isbn"], "9786040000000")
        self.assertEqual(payload["total_pages"], 1)

    def test_detail_returns_404_for_missing_product(self):
        response = self.client.get("/api/v1/products/UNKNOWN")
        self.assertEqual(response.status_code, 404)

    def test_lookups_return_named_options(self):
        response = self.client.get("/api/v1/products/lookups")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["publishers"][0]["code"], "NXB001")

    def test_create_product_passes_validated_data_to_service(self):
        response = self.client.post("/api/v1/products", json={
            "tensp": "Sách mới", "dvt": "Quyển", "giaban": "120000.00",
            "vat": "8", "barcode": "8930000000100", "product_type": "book",
            "isbn": "9786040000001", "namxb": 2025, "manxb": "NXB001",
            "authors": ["TG001"], "genres": ["TL001"],
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["masp"], "SP002")
        self.assertEqual(self.service.saved[1], None)
        self.assertEqual(self.service.saved[0]["manxb"], "NXB001")

    def test_invalid_vat_is_rejected_by_api(self):
        response = self.client.post("/api/v1/products", json={
            "tensp": "Sách mới", "dvt": "Quyển", "giaban": "120000",
            "vat": "120", "product_type": "book", "manxb": "NXB001",
        })
        self.assertEqual(response.status_code, 422)

    def test_update_converts_selected_code_sets_to_lists(self):
        response = self.client.get("/api/v1/products/SP001/edit")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["selected_author_codes"], ["TG001", "TG002"])

    def test_delete_product_returns_name(self):
        response = self.client.delete("/api/v1/products/SP001")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.deleted, "SP001")


class ProductApiAuthorizationTests(unittest.TestCase):
    def test_cashier_cannot_add_product(self):
        app = create_app()
        service = FakeProductService()
        user = CurrentUser(
            employee_code="NV002", full_name="Thu ngân",
            role="Thu ngân", role_code="rl_ThuNgan",
        )
        app.dependency_overrides[get_product_service] = lambda: service
        app.dependency_overrides[get_current_user] = lambda: user
        client = TestClient(app)
        try:
            response = client.post("/api/v1/products", json={
                "tensp": "Sản phẩm", "dvt": "Cái", "giaban": "10000",
                "product_type": "other", "math": "TH001",
            })
        finally:
            app.dependency_overrides.clear()
        self.assertEqual(response.status_code, 403)
        self.assertIsNone(service.saved)


class ProductRepositoryPaginationTests(unittest.TestCase):
    """Kiểm tra SQL phân trang không lặp cột trong ORDER BY."""

    class FakeCursor:
        def __init__(self):
            self.statements = []
            self.closed = False

        def execute(self, sql, *params):
            self.statements.append(sql)
            return self

        def fetchone(self):
            return (0,)

        def fetchall(self):
            return []

        def close(self):
            self.closed = True

    class FakeConnection:
        def __init__(self):
            self.fake_cursor = ProductRepositoryPaginationTests.FakeCursor()

        def cursor(self):
            return self.fake_cursor

    def _run_query(self, sort_by):
        connection = self.FakeConnection()
        result = SanPhamRepository(connection).list_products_page(sort_by=sort_by)
        self.assertEqual(result, {"items": [], "total": 0})
        self.assertTrue(connection.fake_cursor.closed)
        return connection.fake_cursor.statements[-1]

    def test_default_masp_sort_does_not_repeat_column(self):
        sql = self._run_query("masp")
        self.assertIn("ORDER BY SP.MASP ASC OFFSET", sql)
        self.assertNotIn("SP.MASP ASC, SP.MASP ASC", sql)

    def test_other_sort_columns_keep_masp_as_tiebreaker(self):
        sql = self._run_query("tensp")
        self.assertIn("ORDER BY SP.TENSP ASC, SP.MASP ASC OFFSET", sql)

    def test_descending_sort_keeps_masp_tiebreaker(self):
        sql = self._run_query("giaban")
        self.assertIn("ORDER BY SP.GIABAN DESC, SP.MASP ASC OFFSET", sql)


if __name__ == "__main__":
    unittest.main()
