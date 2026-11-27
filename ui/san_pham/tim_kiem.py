"""Các hàm tìm kiếm sản phẩm dùng chung cho mã sản phẩm, mã vạch và ISBN."""


def find_matching_product_codes(products, keyword):
    """Trả về mã sản phẩm khớp chính xác trước, sau đó mới khớp một phần.

    products là dict có key là MASP; mỗi value có thể gồm tensp, barcode, isbn.
    """
    normalized = str(keyword or "").strip().casefold()
    if not normalized:
        return []

    searchable_fields = {}
    for code, product in products.items():
        searchable_fields[code] = (
            str(code or "").strip().casefold(),
            str(product.get("tensp") or "").strip().casefold(),
            str(product.get("barcode") or "").strip().casefold(),
            str(product.get("isbn") or "").strip().casefold(),
        )

    exact_matches = [
        code for code, fields in searchable_fields.items()
        if normalized in fields and fields[fields.index(normalized)]
    ]
    if exact_matches:
        return exact_matches

    return [
        code for code, fields in searchable_fields.items()
        if any(normalized in field for field in fields if field)
    ]
