"""Kiểm thử client tích hợp Casso IDKit."""

import json
import unittest
from unittest.mock import patch

from database.casso_idkit import CassoIdKitClient, CassoIdKitError


class FakeResponse:
    """Response HTTP giả cho kiểm thử không cần Internet."""

    def __init__(self, data):
        self.data = json.dumps(data).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.data


class CassoIdKitTests(unittest.TestCase):
    """Kiểm thử định dạng MST, OAuth token và chuẩn hóa kết quả tra cứu."""

    def test_validate_tax_code_accepts_supported_formats(self):
        self.assertEqual(CassoIdKitClient.validate_tax_code("0316794479"), "0316794479")
        self.assertEqual(CassoIdKitClient.validate_tax_code("0316794479-001"), "0316794479-001")
        self.assertEqual(CassoIdKitClient.validate_tax_code("123456789012"), "123456789012")

    def test_validate_tax_code_rejects_invalid_values(self):
        for value in ("", "123", "1234567890-12", "abcdefghij"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    CassoIdKitClient.validate_tax_code(value)

    @patch("database.casso_idkit.urlopen")
    def test_lookup_business_fetches_token_and_business_data(self, mocked_urlopen):
        mocked_urlopen.side_effect = [
            FakeResponse({"access_token": "jwt-test", "expires_in": 900}),
            FakeResponse({
                "business": {
                    "taxCode": "0316794479",
                    "name": "CÔNG TY TNHH CASSO",
                    "address": "Thành phố Hồ Chí Minh",
                    "taxDepartment": "Cơ quan thuế",
                    "status": "Đang hoạt động",
                    "source": "Cổng thông tin thuế",
                }
            }),
        ]
        client = CassoIdKitClient("app-id", "app-secret")

        result = client.lookup("0316794479")

        self.assertEqual(result["tax_code"], "0316794479")
        self.assertEqual(result["name"], "CÔNG TY TNHH CASSO")
        self.assertEqual(result["address"], "Thành phố Hồ Chí Minh")
        self.assertEqual(mocked_urlopen.call_count, 2)
        self.assertIn("/idkit/v1/business/0316794479", mocked_urlopen.call_args[0][0].full_url)

    @patch("database.casso_idkit.urlopen")
    def test_lookup_caches_access_token(self, mocked_urlopen):
        mocked_urlopen.side_effect = [
            FakeResponse({"access_token": "jwt-test", "expires_in": 900}),
            FakeResponse({"business": {"taxCode": "0316794479", "name": "A"}}),
            FakeResponse({"business": {"taxCode": "0316794479", "name": "A"}}),
        ]
        client = CassoIdKitClient("app-id", "app-secret")

        client.lookup("0316794479")
        client.lookup("0316794479")

        self.assertEqual(mocked_urlopen.call_count, 3)

    def test_missing_credentials_returns_actionable_error(self):
        client = CassoIdKitClient("", "")

        with self.assertRaisesRegex(CassoIdKitError, "CASSO_APP_ID"):
            client.lookup("0316794479")


if __name__ == "__main__":
    unittest.main()
