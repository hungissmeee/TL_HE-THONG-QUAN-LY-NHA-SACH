"""Repository SQL cho nghiệp vụ phiếu nhập kho."""

from decimal import Decimal, ROUND_HALF_UP

from core.sql_support import resolve_connection


class PhieuNhapRepository:
    """Truy vấn và giao dịch phiếu nhập, không phụ thuộc PySide6."""

    def __init__(self, connection_source):
        self.connection_source = connection_source

    def _connection(self):
        return resolve_connection(self.connection_source)

    def get_employee(self, username, is_admin=False):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT MANV, TENNV, VAITRO
                FROM dbo.NHAN_VIEN WHERE MANV = ?
            """, username)
            row = cursor.fetchone()
            if row is None and not is_admin:
                raise LookupError(
                    "Tài khoản đăng nhập chưa có hồ sơ tương ứng trong NHAN_VIEN."
                )
            return {
                "manv": row[0] if row else None,
                "tennv": (row[1] or row[0]) if row else "Admin",
                "vaitro": (row[2] or "") if row else "Quản lý",
            }
        finally:
            cursor.close()

    def list_suppliers_for_import(self):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT MANCC, TENNCC FROM dbo.NHA_CUNG_CAP
                WHERE ISNULL(IS_DELETED, 0) = 0
                ORDER BY TENNCC, MANCC
            """)
            return [(str(r[0]), str(r[1] or "")) for r in cursor.fetchall()]
        finally:
            cursor.close()

    def list_products_for_import(self):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT SP.MASP, SP.TENSP, SP.DVT, SP.GIANHAP,
                       SP.SLTON, SP.VAT, SP.BARCODE, S.ISBN
                FROM dbo.SAN_PHAM SP
                LEFT JOIN dbo.SACH S ON S.MASP = SP.MASP
                WHERE ISNULL(SP.IS_DELETED, 0) = 0
                ORDER BY SP.TENSP, SP.MASP
            """)
            keys = ("masp", "tensp", "dvt", "price", "stock", "vat", "barcode", "isbn")
            return [dict(zip(keys, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def list_imports(self, start_date, end_date, keyword=""):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            sql = """
                SELECT PN.MAPN, PN.NGAYNHAP, PN.MANV, NV.TENNV,
                       PN.MANCC, NCC.TENNCC, PN.LOAIPHIEUNHAP,
                       PN.SHDNCC, PN.TONGTRIGIA, ISNULL(PN.TRANGTHAI, 1)
                FROM dbo.PHIEU_NHAP PN
                LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = PN.MANV
                LEFT JOIN dbo.NHA_CUNG_CAP NCC ON NCC.MANCC = PN.MANCC
                WHERE PN.NGAYNHAP >= ?
                  AND PN.NGAYNHAP < DATEADD(DAY, 1, CAST(? AS date))
            """
            params = [start_date, end_date]
            keyword = str(keyword or "").strip()
            if keyword:
                like = f"%{keyword}%"
                sql += """
                    AND (PN.MAPN LIKE ? OR PN.SHDNCC LIKE ? OR PN.MANV LIKE ?
                         OR NV.TENNV LIKE ? OR PN.MANCC LIKE ? OR NCC.TENNCC LIKE ?)
                """
                params.extend([like] * 6)
            sql += " ORDER BY PN.NGAYNHAP DESC, PN.MAPN DESC"
            cursor.execute(sql, *params)
            return [tuple(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_import_detail(self, import_code, include_return_history=True):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT PN.MAPN, PN.NGAYNHAP, PN.LOAIPHIEUNHAP, PN.SHDNCC,
                       PN.TONGTRIGIA, PN.MANV, NV.TENNV, PN.MANCC,
                       NCC.TENNCC, NCC.SDT, NCC.DIACHI, NCC.MST, PN.TRANGTHAI
                FROM dbo.PHIEU_NHAP PN
                LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = PN.MANV
                LEFT JOIN dbo.NHA_CUNG_CAP NCC ON NCC.MANCC = PN.MANCC
                WHERE PN.MAPN = ?
            """, import_code)
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Không tìm thấy phiếu nhập.")
            header = dict(zip(
                ("mapn", "ngaynhap", "loai", "shdncc", "total", "manv",
                 "tennv", "mancc", "tenncc", "sdt", "diachi", "mst", "status"),
                row
            ))
            cursor.execute("""
                SELECT CT.MASP, SP.TENSP, SP.DVT, CT.SOLUONG, CT.DONGIA, CT.VAT
                FROM dbo.CHI_TIET_PHIEU_NHAP CT
                LEFT JOIN dbo.SAN_PHAM SP ON SP.MASP = CT.MASP
                WHERE CT.MAPN = ?
                ORDER BY SP.TENSP, CT.MASP
            """, import_code)
            items = [
                dict(zip(("masp", "tensp", "dvt", "quantity", "price", "vat"), detail))
                for detail in cursor.fetchall()
            ]
            header["has_later_stock_movement"] = False
            if int(header.get("status") or 0) == 1:
                for item in items:
                    item["has_later_movement"] = self._has_later_stock_movement(
                        cursor, import_code, item["masp"], header["ngaynhap"],
                        include_return_history=include_return_history,
                    )
                    header["has_later_stock_movement"] = (
                        header["has_later_stock_movement"] or item["has_later_movement"]
                    )
                if not include_return_history:
                    # Không thể xác minh lịch sử đổi trả bằng quyền hiện tại:
                    # khóa an toàn chi tiết và hủy, nhưng vẫn cho sửa thông tin chung.
                    header["history_check_incomplete"] = True
                    header["has_later_stock_movement"] = True
            else:
                for item in items:
                    item["has_later_movement"] = False
            return {"header": header, "items": items}
        finally:
            cursor.close()

    @staticmethod
    def _has_later_stock_movement(
        cursor, import_code, product_code, import_date,
        include_return_history=True
    ):
        """Kiểm tra phát sinh kho sau phiếu theo từng sản phẩm."""
        if import_date is None:
            return False
        return_sql = ""
        params = [
            import_code, product_code, import_date,
            product_code, import_date,
        ]
        if include_return_history:
            return_sql = """
                UNION ALL
                SELECT PDT.NGAY_DOI_TRA AS NGAY_GIAO_DICH
                FROM dbo.PHIEU_DOI_TRA PDT
                INNER JOIN dbo.CHI_TIET_DOI_TRA CT ON CT.MAPDT = PDT.MAPDT
                WHERE CT.MASP = ?
                  AND PDT.NGAY_DOI_TRA > ?
                  AND (
                      ISNULL(CT.TINHTRANGHANG, 0) = 1
                      OR ISNULL(CT.HINH_THUC_XU_LY, 0) = 1
                  )
            """
            params.extend([product_code, import_date])
        cursor.execute(f"""
            SELECT TOP (1) 1
            FROM (
                SELECT PN.NGAYNHAP AS NGAY_GIAO_DICH
                FROM dbo.PHIEU_NHAP PN
                INNER JOIN dbo.CHI_TIET_PHIEU_NHAP CT ON CT.MAPN = PN.MAPN
                WHERE PN.MAPN <> ?
                  AND ISNULL(PN.TRANGTHAI, 1) = 1
                  AND CT.MASP = ?
                  AND PN.NGAYNHAP > ?

                UNION ALL
                SELECT HD.NGAYLAP AS NGAY_GIAO_DICH
                FROM dbo.HOA_DON HD
                INNER JOIN dbo.CHI_TIET_HOA_DON CT ON CT.MAHD = HD.MAHD
                WHERE ISNULL(HD.TRANGTHAI, 0) = 1
                  AND CT.MASP = ?
                  AND HD.NGAYLAP > ?
                {return_sql}
            ) AS GIAO_DICH
            WHERE NGAY_GIAO_DICH IS NOT NULL
        """, *params)
        return cursor.fetchone() is not None

    @staticmethod
    def _assert_header_edit_permission(status, username, role, is_admin=False):
        """Quản lý/nhân viên kho được sửa thông tin chung trên phiếu còn hiệu lực."""
        if int(status or 0) != 1:
            raise ValueError("Phiếu nhập đã bị hủy, không được chỉnh sửa nữa.")
        role = str(role or "").strip().casefold()
        username = str(username or "").strip()
        admin = bool(is_admin) or username.casefold() == "admin"
        if not (admin or role in {"quản lý", "nhân viên kho"}):
            raise PermissionError(
                "Chỉ Quản lý, Nhân viên kho hoặc Admin được sửa thông tin chung phiếu nhập."
            )

    @staticmethod
    def _assert_modify_permission(header, username, role, is_admin=False):
        """Sửa chi tiết theo quyền SQL hiện tại; thời hạn 5 phút chỉ áp dụng cho hủy phiếu."""
        status, _owner, _within_five_minutes = header
        if int(status or 0) != 1:
            raise ValueError("Phiếu nhập đã bị hủy, không được chỉnh sửa nữa.")
        role = str(role or "").strip().casefold()
        username = str(username or "").strip()
        admin = bool(is_admin) or username.casefold() == "admin"
        manager = role == "quản lý"
        warehouse = role == "nhân viên kho"
        if not (admin or manager or warehouse):
            raise PermissionError("Tài khoản không có quyền chỉnh sửa chi tiết phiếu nhập.")

    def update_import_header(
        self, import_code, supplier_code, supplier_invoice,
        username, role, is_admin=False
    ):
        """Chỉ sửa nhà cung cấp và số chứng từ NCC; giữ nguyên ngày, người lập và mã phiếu."""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT TRANGTHAI, MANV,
                       CASE WHEN NGAYNHAP >= DATEADD(MINUTE, -5, SYSDATETIME())
                                  AND NGAYNHAP <= SYSDATETIME()
                            THEN 1 ELSE 0 END
                FROM dbo.PHIEU_NHAP WITH (UPDLOCK, HOLDLOCK)
                WHERE MAPN = ?
            """, import_code)
            header = cursor.fetchone()
            if header is None:
                raise LookupError("Không tìm thấy phiếu nhập.")
            self._assert_header_edit_permission(
                header[0], username, role, is_admin
            )

            cursor.execute("""
                SELECT 1
                FROM dbo.NHA_CUNG_CAP WITH (UPDLOCK, HOLDLOCK)
                WHERE MANCC = ? AND ISNULL(IS_DELETED, 0) = 0
            """, supplier_code)
            if cursor.fetchone() is None:
                raise LookupError("Nhà cung cấp không tồn tại hoặc đã ngừng sử dụng.")

            if supplier_invoice:
                cursor.execute("""
                    SELECT TOP (1) 1
                    FROM dbo.PHIEU_NHAP WITH (UPDLOCK, HOLDLOCK)
                    WHERE MAPN <> ? AND MANCC = ? AND SHDNCC = ?
                      AND ISNULL(TRANGTHAI, 1) = 1
                """, import_code, supplier_code, supplier_invoice)
                if cursor.fetchone():
                    raise ValueError(
                        "Số hóa đơn nhà cung cấp này đã được ghi nhận cho nhà cung cấp đã chọn."
                    )

            cursor.execute("""
                UPDATE dbo.PHIEU_NHAP
                SET MANCC = ?, SHDNCC = ?
                WHERE MAPN = ? AND TRANGTHAI = 1
            """, supplier_code, supplier_invoice, import_code)
            if cursor.rowcount != 1:
                raise RuntimeError("Không thể cập nhật thông tin chung của phiếu nhập.")
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def update_import_details(
        self, import_code, items, total, username, role, is_admin=False
    ):
        """Sửa chi tiết khi chưa có phát sinh kho tiếp theo; cập nhật tồn và giá vốn bình quân."""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            # Không tin vai trò do UI truyền lên; kiểm tra principal SQL thực.
            cursor.execute("""
                SELECT CASE
                    WHEN USER_NAME() = N'admin' THEN 1
                    WHEN IS_ROLEMEMBER(N'rl_QuanLy') = 1
                     AND EXISTS (
                         SELECT 1 FROM dbo.NHAN_VIEN
                         WHERE MANV = USER_NAME()
                           AND MANV = ? AND VAITRO = N'Quản lý'
                     )
                    THEN 1
                    WHEN IS_ROLEMEMBER(N'rl_NhanVienKho') = 1
                     AND EXISTS (
                         SELECT 1 FROM dbo.NHAN_VIEN
                         WHERE MANV = USER_NAME()
                           AND MANV = ? AND VAITRO = N'Nhân viên kho'
                     )
                    THEN 1 ELSE 0
                END
            """, str(username or "").strip(), str(username or "").strip())
            permission = cursor.fetchone()
            if permission is None or int(permission[0] or 0) != 1:
                raise PermissionError(
                    "Chỉ Quản lý, Nhân viên kho hoặc Admin được chỉnh sửa chi tiết phiếu nhập."
                )

            cursor.execute("""
                SELECT
                    TRANGTHAI,
                    MANV,
                    CASE
                        WHEN NGAYNHAP >= DATEADD(MINUTE, -5, SYSDATETIME())
                         AND NGAYNHAP <= SYSDATETIME()
                        THEN 1 ELSE 0
                    END,
                    NGAYNHAP
                FROM dbo.PHIEU_NHAP WITH (UPDLOCK, HOLDLOCK)
                WHERE MAPN = ?
            """, import_code)
            header = cursor.fetchone()
            if header is None:
                raise LookupError("Không tìm thấy phiếu nhập.")
            self._assert_modify_permission(
                (header[0], header[1], header[2]), username, role, is_admin
            )
            if not items:
                raise ValueError("Phiếu nhập phải có ít nhất một sản phẩm.")

            cursor.execute("""
                SELECT MASP, SOLUONG, DONGIA
                FROM dbo.CHI_TIET_PHIEU_NHAP WITH (UPDLOCK, HOLDLOCK)
                WHERE MAPN = ?
            """, import_code)
            old_items = {}
            for row in cursor.fetchall():
                code = str(row[0] or "").strip()
                old_items[code] = {
                    "quantity": int(row[1] or 0),
                    "price": Decimal(str(row[2] or 0)),
                }

            new_items = {}
            for item in items:
                code = str(item["product_code"]).strip()
                if not code or code in new_items:
                    raise ValueError("Danh sách sản phẩm chỉnh sửa không hợp lệ hoặc bị trùng.")
                new_items[code] = item

            affected_codes = sorted(set(old_items) | set(new_items), key=str.casefold)
            product_snapshots = {}
            for code in affected_codes:
                # Khóa dòng sản phẩm để không có giao dịch kho chen vào giữa lúc kiểm tra và cập nhật.
                cursor.execute("""
                    SELECT ISNULL(SLTON, 0), ISNULL(GIANHAP, 0),
                           ISNULL(IS_DELETED, 0)
                    FROM dbo.SAN_PHAM WITH (UPDLOCK, HOLDLOCK)
                    WHERE MASP = ?
                """, code)
                product = cursor.fetchone()
                if product is None:
                    raise LookupError(f"Không tìm thấy sản phẩm {code}.")
                is_deleted = int(product[2] or 0) == 1
                if is_deleted and code not in old_items:
                    raise ValueError(f"Sản phẩm {code} đã ngừng sử dụng, không thể thêm vào phiếu.")
                if self._has_later_stock_movement(cursor, import_code, code, header[3]):
                    raise ValueError(
                        f"Không thể chỉnh sửa chi tiết phiếu nhập vì sản phẩm {code} "
                        "đã có giao dịch kho phát sinh sau phiếu này."
                    )
                product_snapshots[code] = {
                    "stock": int(product[0] or 0),
                    "average_cost": Decimal(str(product[1] or 0)),
                }

            # Điều chỉnh số tồn và đảo phần giá trị của dòng cũ trước khi tính lại giá bình quân.
            for code in affected_codes:
                snapshot = product_snapshots[code]
                current_stock = snapshot["stock"]
                current_average = snapshot["average_cost"]
                old_line = old_items.get(code, {"quantity": 0, "price": Decimal("0")})
                new_line = new_items.get(code, {"quantity": 0, "price": Decimal("0")})
                old_quantity = int(old_line["quantity"])
                new_quantity = int(new_line["quantity"])
                new_stock = current_stock - old_quantity + new_quantity
                if new_stock < 0:
                    raise ValueError(
                        f"Không thể cập nhật sản phẩm {code} vì tồn kho sau điều chỉnh sẽ âm."
                    )

                remaining_value = (
                    Decimal(current_stock) * current_average
                    - Decimal(old_quantity) * old_line["price"]
                )
                rounding_tolerance = (
                    Decimal(max(current_stock, 1)) * Decimal("0.005")
                    + Decimal("0.01")
                )
                if remaining_value < -rounding_tolerance:
                    raise ValueError(
                        f"Không thể xác định lại giá nhập bình quân của sản phẩm {code}; "
                        "dữ liệu giá vốn hiện tại không nhất quán."
                    )
                if remaining_value < 0:
                    remaining_value = Decimal("0")
                new_value = remaining_value + Decimal(new_quantity) * new_line["price"]
                new_average = (
                    (new_value / Decimal(new_stock)).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    if new_stock > 0 else Decimal("0.00")
                )
                cursor.execute("""
                    UPDATE dbo.SAN_PHAM
                    SET SLTON = ?, GIANHAP = ?
                    WHERE MASP = ?
                """, new_stock, new_average, code)
                if cursor.rowcount != 1:
                    raise RuntimeError(f"Không thể cập nhật tồn kho sản phẩm {code}.")

            role_name = str(role or "").strip().casefold()
            may_delete_lines = (
                bool(is_admin)
                or str(username or "").strip().casefold() == "admin"
                or role_name == "quản lý"
            )
            removed_codes = set(old_items) - set(new_items)
            if removed_codes and not may_delete_lines:
                raise PermissionError(
                    "Nhân viên kho không có quyền xóa mặt hàng đã lưu khỏi phiếu nhập."
                )
            if may_delete_lines:
                cursor.execute(
                    "DELETE FROM dbo.CHI_TIET_PHIEU_NHAP WHERE MAPN = ?",
                    import_code,
                )
                for code, item in new_items.items():
                    cursor.execute("""
                        INSERT INTO dbo.CHI_TIET_PHIEU_NHAP
                            (MAPN, MASP, DONGIA, SOLUONG, VAT)
                        VALUES (?, ?, ?, ?, ?)
                    """, import_code, code, item["price"], item["quantity"], item["vat"])
            else:
                # Vai trò Nhân viên kho không có quyền DELETE trên CHI_TIET_PHIEU_NHAP.
                for code, item in new_items.items():
                    if code in old_items:
                        cursor.execute("""
                            UPDATE dbo.CHI_TIET_PHIEU_NHAP
                            SET DONGIA = ?, SOLUONG = ?, VAT = ?
                            WHERE MAPN = ? AND MASP = ?
                        """, item["price"], item["quantity"], item["vat"], import_code, code)
                        if cursor.rowcount != 1:
                            raise RuntimeError(
                                f"Không thể cập nhật chi tiết sản phẩm {code}."
                            )
                    else:
                        cursor.execute("""
                            INSERT INTO dbo.CHI_TIET_PHIEU_NHAP
                                (MAPN, MASP, DONGIA, SOLUONG, VAT)
                            VALUES (?, ?, ?, ?, ?)
                        """, import_code, code, item["price"], item["quantity"], item["vat"])

            cursor.execute("""
                UPDATE dbo.PHIEU_NHAP
                SET TONGTRIGIA = ?
                WHERE MAPN = ? AND TRANGTHAI = 1
            """, total, import_code)
            if cursor.rowcount != 1:
                raise RuntimeError("Không thể cập nhật tổng giá trị phiếu nhập.")
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def _next_import_code(cursor):
        cursor.execute("""
            SELECT COALESCE(MAX(TRY_CONVERT(BIGINT, SUBSTRING(MAPN, 3, 18))), 0)
            FROM dbo.PHIEU_NHAP WITH (TABLOCKX, HOLDLOCK)
            WHERE UPPER(LEFT(MAPN, 2)) = 'PN'
              AND TRY_CONVERT(BIGINT, SUBSTRING(MAPN, 3, 18)) IS NOT NULL
        """)
        code = f"PN{int(cursor.fetchone()[0] or 0) + 1:06d}"
        if len(code) > 20:
            raise ValueError("Đã vượt giới hạn độ dài mã phiếu nhập.")
        return code

    def create_import(self, payload):
        """Tạo phiếu, chi tiết, cập nhật tồn và giá nhập bình quân trong một transaction."""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            supplier_code = payload["supplier_code"]
            supplier_invoice = payload.get("supplier_invoice")
            if supplier_invoice:
                cursor.execute("""
                    SELECT 1 FROM dbo.PHIEU_NHAP WITH (UPDLOCK, HOLDLOCK)
                    WHERE MANCC = ? AND SHDNCC = ? AND ISNULL(TRANGTHAI, 1) = 1
                """, supplier_code, supplier_invoice)
                if cursor.fetchone():
                    raise ValueError(
                        "Số hóa đơn nhà cung cấp này đã được ghi nhận cho nhà cung cấp đã chọn."
                    )
            import_code = self._next_import_code(cursor)

            # Khóa nhà cung cấp và xác minh trạng thái ngay trong transaction.
            # Nếu NCC bị ngừng sử dụng khi biểu mẫu còn mở, không được tạo phiếu.
            cursor.execute("""
                SELECT 1
                FROM dbo.NHA_CUNG_CAP WITH (UPDLOCK, HOLDLOCK)
                WHERE MANCC = ? AND ISNULL(IS_DELETED, 0) = 0
            """, supplier_code)
            if cursor.fetchone() is None:
                raise LookupError("Nhà cung cấp không tồn tại hoặc đã ngừng sử dụng.")

            cursor.execute("""
                INSERT INTO dbo.PHIEU_NHAP
                    (MAPN, NGAYNHAP, LOAIPHIEUNHAP, SHDNCC,
                     TONGTRIGIA, MANV, MANCC, TRANGTHAI)
                VALUES (?, SYSDATETIME(), ?, ?, ?, ?, ?, 1)
            """, import_code, payload["import_type"], supplier_invoice,
                 payload["total"], payload["employee_code"], supplier_code)

            for item in payload["items"]:
                code = item["product_code"]
                quantity = item["quantity"]
                price = item["price"]
                cursor.execute("""
                    UPDATE dbo.SAN_PHAM
                    SET GIANHAP = CAST((
                        CAST(ISNULL(SLTON, 0) AS DECIMAL(18, 2))
                        * CAST(ISNULL(GIANHAP, 0) AS DECIMAL(18, 2))
                        + CAST(? AS DECIMAL(18, 2)) * CAST(? AS DECIMAL(10, 0))
                    ) / NULLIF(
                        CAST(ISNULL(SLTON, 0) AS DECIMAL(18, 2))
                        + CAST(? AS DECIMAL(18, 2)), 0
                    ) AS DECIMAL(15, 2)),
                    SLTON = ISNULL(SLTON, 0) + ?
                    WHERE MASP = ? AND ISNULL(IS_DELETED, 0) = 0
                """, price, quantity, quantity, quantity, code)
                if cursor.rowcount != 1:
                    raise LookupError(
                        f"Không tìm thấy sản phẩm {code} hoặc sản phẩm đã ngừng sử dụng."
                    )
                cursor.execute("""
                    INSERT INTO dbo.CHI_TIET_PHIEU_NHAP
                        (MAPN, MASP, DONGIA, SOLUONG, VAT)
                    VALUES (?, ?, ?, ?, ?)
                """, import_code, code, price, quantity, item["vat"])
            conn.commit()
            return import_code
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def cancel_import(self, import_code, username, role, is_admin=False):
        """Hủy phiếu và hoàn tác tồn kho/giá nhập trong cùng transaction."""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            # Chỉ principal SQL Admin/Quản lý được hủy; bỏ qua role truyền từ UI.
            cursor.execute("""
                SELECT CASE
                    WHEN USER_NAME() = N'admin' THEN 1
                    WHEN IS_ROLEMEMBER(N'rl_QuanLy') = 1
                     AND EXISTS (
                         SELECT 1 FROM dbo.NHAN_VIEN
                         WHERE MANV = USER_NAME()
                           AND MANV = ? AND VAITRO = N'Quản lý'
                     )
                    THEN 1 ELSE 0
                END
            """, str(username or "").strip())
            permission = cursor.fetchone()
            if permission is None or int(permission[0] or 0) != 1:
                raise PermissionError("Chỉ Quản lý/Admin được hủy phiếu nhập.")

            cursor.execute("""
                SELECT TRANGTHAI, NGAYNHAP
                FROM dbo.PHIEU_NHAP WITH (UPDLOCK, HOLDLOCK)
                WHERE MAPN = ?
            """, import_code)
            header = cursor.fetchone()
            if header is None:
                raise LookupError("Không tìm thấy phiếu nhập.")
            if int(header[0] or 0) != 1:
                raise ValueError("Phiếu nhập đã bị hủy trước đó.")

            cursor.execute("""
                SELECT MASP, SUM(ISNULL(SOLUONG, 0)),
                       SUM(ISNULL(SOLUONG, 0) * ISNULL(DONGIA, 0))
                FROM dbo.CHI_TIET_PHIEU_NHAP WITH (UPDLOCK, HOLDLOCK)
                WHERE MAPN = ?
                GROUP BY MASP
                ORDER BY MASP
            """, import_code)
            details = cursor.fetchall()
            if not details:
                raise ValueError("Phiếu nhập không có chi tiết sản phẩm.")

            # Khóa tất cả sản phẩm theo thứ tự mã để tuần tự hóa với bán hàng/nhập hàng.
            # Giữ khóa đến commit: giao dịch kho khác không thể chen vào sau bước kiểm tra lịch sử.
            product_snapshots = {}
            for detail in details:
                product_code = str(detail[0])
                cursor.execute("""
                    SELECT ISNULL(SLTON, 0), ISNULL(GIANHAP, 0)
                    FROM dbo.SAN_PHAM WITH (UPDLOCK, HOLDLOCK)
                    WHERE MASP = ?
                """, product_code)
                product = cursor.fetchone()
                if product is None:
                    raise LookupError(f"Không tìm thấy sản phẩm {product_code}.")
                product_snapshots[product_code] = {
                    "stock": int(product[0] or 0),
                    "average_cost": Decimal(str(product[1] or 0)),
                }

            # Chỉ kiểm tra lịch sử sau khi đã giữ khóa sản phẩm.
            for detail in details:
                product_code = str(detail[0])
                if self._has_later_stock_movement(
                    cursor, import_code, product_code, header[1]
                ):
                    raise ValueError(
                        f"Không thể hủy phiếu nhập vì sản phẩm {product_code} "
                        "đã có giao dịch kho phát sinh sau phiếu này."
                    )

            new_balances = {}
            for detail in details:
                product_code = str(detail[0])
                quantity = int(detail[1] or 0)
                import_value = Decimal(str(detail[2] or 0))
                if quantity <= 0:
                    raise ValueError(f"Số lượng nhập của {product_code} không hợp lệ.")

                snapshot = product_snapshots[product_code]
                current_stock = snapshot["stock"]
                current_average = snapshot["average_cost"]
                new_stock = current_stock - quantity
                if new_stock < 0:
                    raise ValueError(
                        f"Không thể hủy phiếu vì tồn kho {product_code} không còn đủ "
                        f"{quantity} sản phẩm để hoàn tác."
                    )

                # Đảo giá trị của chính lần nhập này khỏi giá trị tồn hiện tại.
                # Không tính lại toàn bộ lịch sử vì tồn kho có thể từng về 0,
                # khiến giá bình quân của chu kỳ tồn trước không còn liên quan.
                remaining_value = (
                    Decimal(current_stock) * current_average - import_value
                )
                rounding_tolerance = (
                    Decimal(max(current_stock, 1)) * Decimal("0.005")
                    + Decimal("0.01")
                )
                if remaining_value < -rounding_tolerance:
                    raise ValueError(
                        f"Không thể xác định lại giá nhập bình quân của sản phẩm {product_code}; "
                        "dữ liệu giá vốn hiện tại không nhất quán."
                    )
                if remaining_value < 0:
                    remaining_value = Decimal("0")
                new_average = (
                    (remaining_value / Decimal(new_stock)).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    if new_stock > 0 else Decimal("0.00")
                )
                new_balances[product_code] = (new_stock, new_average)

            for product_code, (new_stock, new_average) in new_balances.items():
                cursor.execute("""
                    UPDATE dbo.SAN_PHAM
                    SET SLTON = ?, GIANHAP = ?
                    WHERE MASP = ?
                """, new_stock, new_average, product_code)
                if cursor.rowcount != 1:
                    raise RuntimeError(f"Không thể cập nhật tồn kho sản phẩm {product_code}.")

            cursor.execute("""
                UPDATE dbo.PHIEU_NHAP SET TRANGTHAI = 0
                WHERE MAPN = ? AND TRANGTHAI = 1
            """, import_code)
            if cursor.rowcount != 1:
                raise RuntimeError("Không thể cập nhật trạng thái phiếu nhập.")
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
