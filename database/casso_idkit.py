"""Tích hợp Casso IDKit để tra cứu thông tin nhà cung cấp theo mã số thuế."""

import json
import os
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


BASE_URL = "https://openapi.casso.vn"
DEFAULT_TIMEOUT = 15


class CassoIdKitError(RuntimeError):
    """Lỗi xác thực hoặc tra cứu dữ liệu từ Casso IDKit."""


class CassoIdKitClient:
    """Client OAuth2 client-credentials cho API tra cứu MST của Casso."""

    def __init__(self, app_id=None, app_secret=None, timeout=DEFAULT_TIMEOUT):
        self.app_id = app_id or os.getenv("CASSO_APP_ID", "").strip()
        self.app_secret = app_secret or os.getenv("CASSO_APP_SECRET", "").strip()
        self.timeout = timeout
        self._access_token = None
        self._token_expires_at = 0
        self._token_lock = threading.Lock()

    @staticmethod
    def validate_tax_code(tax_code):
        """Chấp nhận MST doanh nghiệp, chi nhánh hoặc hộ kinh doanh."""
        value = str(tax_code or "").strip()
        valid_business = len(value) == 10 and value.isdigit()
        valid_branch = (
            len(value) == 14 and value[:10].isdigit()
            and value[10] == "-" and len(value[11:]) == 3 and value[11:].isdigit()
        )
        valid_household = len(value) == 12 and value.isdigit()
        if not (valid_business or valid_branch or valid_household):
            raise ValueError("Mã số thuế phải gồm 10 số, 12 số hoặc dạng 10-3 số.")
        return value

    def _get_access_token(self):
        """Lấy JWT và cache đến trước thời điểm hết hạn 60 giây."""
        with self._token_lock:
            if self._access_token and time.time() < self._token_expires_at - 60:
                return self._access_token

            if not self.app_id or not self.app_secret:
                raise CassoIdKitError(
                    "Chưa cấu hình CASSO_APP_ID và CASSO_APP_SECRET. "
                    "Hãy khai báo hai biến môi trường trước khi tra cứu."
                )

            payload = json.dumps({
                "app_id": self.app_id,
                "app_secret": self.app_secret,
            }).encode("utf-8")
            request = Request(
                f"{BASE_URL}/oauth/token",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            data = self._request_json(request)
            token = data.get("access_token")
            if not token:
                raise CassoIdKitError("Casso không trả về access_token hợp lệ.")

            expires_in = int(data.get("expires_in", 900))
            self._access_token = token
            self._token_expires_at = time.time() + expires_in
            return token

    def _request_json(self, request):
        """Gửi HTTP request và chuẩn hóa lỗi API thành thông báo dễ hiểu."""
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            try:
                body = error.read().decode("utf-8")
                detail = json.loads(body)
                message = detail.get("message") or detail.get("error") or body
            except Exception:
                message = str(error)
            if error.code == 401:
                message = "Phiên xác thực Casso không hợp lệ hoặc đã hết hạn."
            elif error.code == 403:
                message = "Ứng dụng Casso chưa được cấp quyền tra cứu MST."
            elif error.code == 429:
                message = "Casso đang giới hạn lượt tra cứu hoặc đã hết hạn mức."
            elif error.code >= 500:
                message = "Dịch vụ tra cứu Casso hiện không khả dụng."
            raise CassoIdKitError(f"{message} (HTTP {error.code})") from error
        except (URLError, TimeoutError) as error:
            raise CassoIdKitError(
                "Không thể kết nối Casso. Hãy kiểm tra Internet và thử lại."
            ) from error
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise CassoIdKitError("Casso trả về dữ liệu không đúng định dạng JSON.") from error

    def lookup(self, tax_code):
        """Tra cứu doanh nghiệp hoặc hộ kinh doanh và chuẩn hóa dữ liệu trả về."""
        tax_code = self.validate_tax_code(tax_code)
        token = self._get_access_token()
        endpoint = "household" if len(tax_code) == 12 else "business"
        request = Request(
            f"{BASE_URL}/idkit/v1/{endpoint}/{quote(tax_code, safe='-')}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            method="GET",
        )
        response = self._request_json(request)
        record = response.get(endpoint) or response.get("data", {}).get(endpoint)
        if not isinstance(record, dict):
            raise CassoIdKitError(
                "Không tìm thấy thông tin MST hoặc cấu trúc dữ liệu Casso không hợp lệ."
            )

        return {
            "tax_code": str(record.get("taxCode") or tax_code),
            "name": str(record.get("name") or "").strip(),
            "address": str(record.get("address") or "").strip(),
            "tax_department": str(record.get("taxDepartment") or "").strip(),
            "status": str(record.get("status") or "").strip(),
            "source": str(record.get("source") or "").strip(),
        }
