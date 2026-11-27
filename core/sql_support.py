"""Tiện ích lấy kết nối SQL mà không phụ thuộc vào giao diện Desktop hay Web."""

def resolve_connection(connection_source):
    """Lấy connection từ Database Desktop, callable dependency hoặc connection trực tiếp.

    Backend nên truyền một callable trả về connection dành riêng cho request.
    Desktop có thể truyền đối tượng Database hiện tại.
    Repository không tự đóng connection vì quyền sở hữu vòng đời thuộc về nơi
    tạo connection (Desktop Database hoặc dependency của Backend).
    """
    if connection_source is None:
        raise RuntimeError("Chưa cấu hình nguồn kết nối SQL Server.")

    getter = getattr(connection_source, "get_connection", None)
    if callable(getter):
        connection = getter()
    elif callable(connection_source) and not callable(
        getattr(connection_source, "cursor", None)
    ):
        connection = connection_source()
    else:
        connection = connection_source

    if connection is None:
        raise RuntimeError("Chưa có kết nối SQL Server.")
    return connection


def restore_and_activate_product(cursor, product_code, quantity):
    """Kích hoạt lại sản phẩm và cộng tồn kho trong cùng transaction."""
    cursor.execute("""
        UPDATE dbo.SAN_PHAM
        SET IS_DELETED = 0,
            SLTON = ISNULL(SLTON, 0) + ?
        WHERE MASP = ?
    """, quantity, product_code)
    return cursor.rowcount == 1
