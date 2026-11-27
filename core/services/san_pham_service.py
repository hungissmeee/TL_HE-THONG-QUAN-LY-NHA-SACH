"""Service nghiệp vụ sản phẩm dùng chung cho Desktop và Backend."""

from decimal import Decimal, InvalidOperation

from core.repositories.san_pham_repository import SanPhamRepository


class SanPhamService:
    """Kiểm tra dữ liệu đầu vào và điều phối thao tác sản phẩm."""

    def __init__(self, repository):
        if not isinstance(repository, SanPhamRepository):
            raise TypeError("repository phải là SanPhamRepository.")
        self.repository = repository

    def list_products(self, keyword=""):
        return self.repository.list_products(keyword)

    def get_product(self, product_code):
        return self.repository.get_product(product_code)

    def get_product_for_edit(self, product_code):
        return self.repository.get_product_for_edit(product_code)

    def get_product_detail(self, product_code):
        return self.repository.get_product_detail(product_code)

    def get_lookup_data(self, **selected):
        return self.repository.get_lookup_data(**selected)

    def get_permissions(self):
        return self.repository.get_permissions()

    def preview_next_product_code(self):
        return self.repository.preview_next_product_code()

    @staticmethod
    def _decimal(value, field_name):
        try:
            number = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError(f"{field_name} phải là số hợp lệ.")
        if not number.is_finite() or number < 0:
            raise ValueError(f"{field_name} phải là số không âm hợp lệ.")
        return number

    def save_product(self, data, product_code=None):
        """Chuẩn hóa và kiểm tra dữ liệu trước khi ghi sản phẩm."""
        payload = dict(data or {})
        name = str(payload.get("tensp") or "").strip()
        unit = str(payload.get("dvt") or "").strip()
        product_type = payload.get("product_type")

        if not name or not unit:
            raise ValueError("Vui lòng nhập tên sản phẩm và đơn vị tính.")
        if len(name) > 150 or len(unit) > 30:
            raise ValueError("Tên sản phẩm hoặc đơn vị tính vượt quá độ dài cho phép.")
        if product_type not in {"book", "other"}:
            raise ValueError("Loại sản phẩm không hợp lệ.")

        price = self._decimal(payload.get("giaban"), "Giá bán")
        vat = self._decimal(payload.get("vat", 0), "VAT")
        if vat > 100:
            raise ValueError("VAT phải nằm trong khoảng từ 0 đến 100.")

        barcode = str(payload.get("barcode") or "").strip() or None
        if barcode and len(barcode) > 50:
            raise ValueError("Mã vạch không được vượt quá 50 ký tự.")

        payload["tensp"] = name
        payload["dvt"] = unit
        payload["giaban"] = price
        payload["vat"] = vat
        payload["barcode"] = barcode

        if product_type == "book":
            publisher = str(payload.get("manxb") or "").strip()
            if not publisher:
                raise ValueError("Vui lòng chọn nhà xuất bản.")
            payload["manxb"] = publisher
            payload["isbn"] = str(payload.get("isbn") or "").strip() or None
            if payload["isbn"] and len(payload["isbn"]) > 20:
                raise ValueError("ISBN không được vượt quá 20 ký tự.")
            year = payload.get("namxb")
            if year in (None, ""):
                payload["namxb"] = None
            else:
                try:
                    payload["namxb"] = int(year)
                except (TypeError, ValueError):
                    raise ValueError("Năm xuất bản phải là số nguyên.")
                if not 0 <= payload["namxb"] <= 9999:
                    raise ValueError("Năm xuất bản phải nằm trong khoảng 0 đến 9999.")
            payload["authors"] = list(dict.fromkeys(payload.get("authors") or []))
            payload["genres"] = list(dict.fromkeys(payload.get("genres") or []))
        else:
            brand = str(payload.get("math") or "").strip()
            if not brand:
                raise ValueError("Vui lòng chọn thương hiệu.")
            payload["math"] = brand
            payload["ngaysx"] = payload.get("ngaysx")

        return self.repository.save_product(payload, product_code=product_code)

    def soft_delete_product(self, product_code):
        code = str(product_code or "").strip()
        if not code:
            raise ValueError("Mã sản phẩm không hợp lệ.")
        return self.repository.soft_delete_product(code)
