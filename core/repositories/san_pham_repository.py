"""Repository truy cập dữ liệu sản phẩm và các liên kết sách/sản phẩm khác."""

from core.sql_support import resolve_connection


class DuplicateProductBarcodeError(ValueError):
    """Mã vạch đã được sử dụng bởi một sản phẩm khác."""


class ProductHasStockError(RuntimeError):
    """Sản phẩm không thể xóa mềm vì vẫn còn số lượng tồn."""

    def __init__(self, product_code, stock_quantity):
        self.product_code = product_code
        self.stock_quantity = int(stock_quantity)
        super().__init__(
            f"Sản phẩm {product_code} vẫn còn {self.stock_quantity} sản phẩm trong kho. "
            "Vui lòng xử lý hết tồn kho trước khi xóa."
        )


class SanPhamRepository:
    """Chứa SQL và transaction cho phân hệ sản phẩm; không phụ thuộc PySide6."""

    def __init__(self, connection_source):
        self.connection_source = connection_source

    def _connection(self):
        return resolve_connection(self.connection_source)

    @staticmethod
    def _product_dict(row):
        keys = (
            "masp", "tensp", "loai", "dvt", "gianhap",
            "giaban", "slton", "vat", "barcode",
        )
        return dict(zip(keys, row))

    def list_products(self, keyword=""):
        """Tìm sản phẩm theo mã, tên, barcode, ISBN và thông tin liên quan."""
        conn = self._connection()
        cursor = conn.cursor()
        query = """
            SELECT
                SP.MASP, SP.TENSP,
                CASE
                    WHEN S.MASP IS NOT NULL THEN N'Sách'
                    WHEN SPK.MASP IS NOT NULL THEN N'Sản phẩm khác'
                    ELSE N'Chưa phân loại'
                END AS LOAI,
                SP.DVT, SP.GIANHAP, SP.GIABAN, SP.SLTON, SP.VAT, SP.BARCODE
            FROM dbo.SAN_PHAM SP
            LEFT JOIN dbo.SACH S ON S.MASP = SP.MASP
            LEFT JOIN dbo.SAN_PHAM_KHAC SPK ON SPK.MASP = SP.MASP
            WHERE ISNULL(SP.IS_DELETED, 0) = 0
        """
        try:
            keyword = str(keyword or "").strip()
            if keyword:
                pattern = f"%{keyword}%"
                query += """
                    AND (
                        SP.MASP LIKE ? OR SP.TENSP LIKE ?
                        OR SP.BARCODE LIKE ? OR SP.DVT LIKE ?
                        OR (
                            CASE
                                WHEN S.MASP IS NOT NULL THEN N'Sách'
                                WHEN SPK.MASP IS NOT NULL THEN N'Sản phẩm khác'
                                ELSE N'Chưa phân loại'
                            END
                        ) LIKE ?
                        OR EXISTS (
                            SELECT 1
                            FROM dbo.SACH S2
                            LEFT JOIN dbo.NHA_XUAT_BAN NXB ON NXB.MANXB = S2.MANXB
                            WHERE S2.MASP = SP.MASP
                              AND (S2.ISBN LIKE ? OR NXB.MANXB LIKE ? OR NXB.TENNXB LIKE ?)
                        )
                        OR EXISTS (
                            SELECT 1
                            FROM dbo.THUOC_TG TTG
                            JOIN dbo.TAC_GIA TG ON TG.MATG = TTG.MATG
                            WHERE TTG.MASP = SP.MASP
                              AND (TG.MATG LIKE ? OR TG.TENTG LIKE ?)
                        )
                        OR EXISTS (
                            SELECT 1
                            FROM dbo.THUOC_TL TTL
                            JOIN dbo.THE_LOAI TL ON TL.MATL = TTL.MATL
                            WHERE TTL.MASP = SP.MASP
                              AND (TL.MATL LIKE ? OR TL.TENTL LIKE ?)
                        )
                        OR EXISTS (
                            SELECT 1
                            FROM dbo.SAN_PHAM_KHAC SPK2
                            LEFT JOIN dbo.THUONG_HIEU TH ON TH.MATH = SPK2.MATH
                            WHERE SPK2.MASP = SP.MASP
                              AND (TH.MATH LIKE ? OR TH.TENTH LIKE ? OR TH.XUATXU LIKE ?)
                        )
                    )
                """
                cursor.execute(query + " ORDER BY SP.MASP", *([pattern] * 15))
            else:
                cursor.execute(query + " ORDER BY SP.MASP")
            return [self._product_dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def list_products_page(
        self, keyword="", product_type="all", page=1, page_size=20,
        sort_by="masp", sort_order="asc",
    ):
        """Tìm kiếm, lọc và phân trang sản phẩm ngay tại SQL Server."""
        sort_columns = {
            "masp": "SP.MASP",
            "tensp": "SP.TENSP",
            "loai": "LOAI",
            "dvt": "SP.DVT",
            "gianhap": "SP.GIANHAP",
            "giaban": "SP.GIABAN",
            "slton": "SP.SLTON",
            "vat": "SP.VAT",
            "barcode": "SP.BARCODE",
        }
        sort_column = sort_columns.get(str(sort_by or "").casefold(), "SP.MASP")
        sort_direction = "DESC" if str(sort_order or "").casefold() == "desc" else "ASC"

        filters = ["ISNULL(SP.IS_DELETED, 0) = 0"]
        params = []
        if product_type == "book":
            filters.append("S.MASP IS NOT NULL")
        elif product_type == "other":
            filters.append("SPK.MASP IS NOT NULL")
        elif product_type == "unclassified":
            filters.append("S.MASP IS NULL AND SPK.MASP IS NULL")

        keyword = str(keyword or "").strip()
        if keyword:
            filters.append("""
                (
                    SP.MASP LIKE ? OR SP.TENSP LIKE ?
                    OR SP.BARCODE LIKE ? OR SP.DVT LIKE ?
                    OR (
                        CASE
                            WHEN S.MASP IS NOT NULL THEN N'Sách'
                            WHEN SPK.MASP IS NOT NULL THEN N'Sản phẩm khác'
                            ELSE N'Chưa phân loại'
                        END
                    ) LIKE ?
                    OR EXISTS (
                        SELECT 1
                        FROM dbo.SACH S2
                        LEFT JOIN dbo.NHA_XUAT_BAN NXB ON NXB.MANXB = S2.MANXB
                        WHERE S2.MASP = SP.MASP
                          AND (S2.ISBN LIKE ? OR NXB.MANXB LIKE ? OR NXB.TENNXB LIKE ?)
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM dbo.THUOC_TG TTG
                        JOIN dbo.TAC_GIA TG ON TG.MATG = TTG.MATG
                        WHERE TTG.MASP = SP.MASP
                          AND (TG.MATG LIKE ? OR TG.TENTG LIKE ?)
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM dbo.THUOC_TL TTL
                        JOIN dbo.THE_LOAI TL ON TL.MATL = TTL.MATL
                        WHERE TTL.MASP = SP.MASP
                          AND (TL.MATL LIKE ? OR TL.TENTL LIKE ?)
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM dbo.SAN_PHAM_KHAC SPK2
                        LEFT JOIN dbo.THUONG_HIEU TH ON TH.MATH = SPK2.MATH
                        WHERE SPK2.MASP = SP.MASP
                          AND (TH.MATH LIKE ? OR TH.TENTH LIKE ? OR TH.XUATXU LIKE ?)
                    )
                )
            """)
            params.extend([f"%{keyword}%"] * 15)

        from_sql = """
            FROM dbo.SAN_PHAM SP
            LEFT JOIN dbo.SACH S ON S.MASP = SP.MASP
            LEFT JOIN dbo.SAN_PHAM_KHAC SPK ON SPK.MASP = SP.MASP
        """
        where_sql = " WHERE " + " AND ".join(filters)
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT COUNT_BIG(1) " + from_sql + where_sql,
                *params,
            )
            total = int(cursor.fetchone()[0] or 0)

            offset = (int(page) - 1) * int(page_size)
            cursor.execute(
                """
                SELECT
                    SP.MASP, SP.TENSP,
                    CASE
                        WHEN S.MASP IS NOT NULL THEN N'Sách'
                        WHEN SPK.MASP IS NOT NULL THEN N'Sản phẩm khác'
                        ELSE N'Chưa phân loại'
                    END AS LOAI,
                    SP.DVT, SP.GIANHAP, SP.GIABAN, SP.SLTON, SP.VAT,
                    SP.BARCODE, S.ISBN
                """
                + from_sql
                + where_sql
                + f" ORDER BY {sort_column} {sort_direction}"
                + (", SP.MASP ASC" if sort_column != "SP.MASP" else "")
                + " OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
                *params,
                offset,
                int(page_size),
            )
            items = []
            for row in cursor.fetchall():
                product = self._product_dict(row[:9])
                product["isbn"] = row[9]
                items.append(product)
            return {"items": items, "total": total}
        finally:
            cursor.close()

    def get_product(self, product_code):
        """Lấy thông tin chung sản phẩm đang hoạt động theo mã."""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    SP.MASP, SP.TENSP,
                    CASE
                        WHEN S.MASP IS NOT NULL THEN N'Sách'
                        WHEN SPK.MASP IS NOT NULL THEN N'Sản phẩm khác'
                        ELSE N'Chưa phân loại'
                    END AS LOAI,
                    SP.DVT, SP.GIANHAP, SP.GIABAN, SP.SLTON, SP.VAT, SP.BARCODE
                FROM dbo.SAN_PHAM SP
                LEFT JOIN dbo.SACH S ON S.MASP = SP.MASP
                LEFT JOIN dbo.SAN_PHAM_KHAC SPK ON SPK.MASP = SP.MASP
                WHERE SP.MASP = ?
                  AND ISNULL(SP.IS_DELETED, 0) = 0
            """, product_code)
            row = cursor.fetchone()
            return self._product_dict(row) if row else None
        finally:
            cursor.close()

    def get_product_for_edit(self, product_code):
        """Lấy dữ liệu form cùng các mã tác giả/thể loại đã liên kết."""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    SP.MASP, SP.TENSP, SP.DVT, SP.GIANHAP,
                    SP.GIABAN, SP.SLTON, SP.VAT,
                    CASE
                        WHEN S.MASP IS NOT NULL THEN N'Sách'
                        WHEN SPK.MASP IS NOT NULL THEN N'Sản phẩm khác'
                        ELSE N'Chưa phân loại'
                    END AS LOAI,
                    S.ISBN, S.NAMXB, S.MANXB,
                    SPK.NGAYSX, SPK.MATH, SP.BARCODE
                FROM dbo.SAN_PHAM SP
                LEFT JOIN dbo.SACH S ON S.MASP = SP.MASP
                LEFT JOIN dbo.SAN_PHAM_KHAC SPK ON SPK.MASP = SP.MASP
                WHERE SP.MASP = ?
                  AND ISNULL(SP.IS_DELETED, 0) = 0
            """, product_code)
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Không tìm thấy sản phẩm cần chỉnh sửa!")
            if row[7] == "Chưa phân loại":
                raise ValueError(
                    "Sản phẩm chưa được phân loại thành sách hoặc sản phẩm khác, "
                    "không thể chỉnh sửa bằng form này."
                )
            product = {
                "masp": row[0], "tensp": row[1], "dvt": row[2],
                "gianhap": row[3], "giaban": row[4], "slton": row[5],
                "vat": row[6], "loai": row[7], "isbn": row[8],
                "namxb": row[9], "manxb": row[10], "ngaysx": row[11],
                "math": row[12], "barcode": row[13],
            }
            cursor.execute("SELECT MATG FROM dbo.THUOC_TG WHERE MASP = ?", product_code)
            product["selected_author_codes"] = {item[0] for item in cursor.fetchall()}
            cursor.execute("SELECT MATL FROM dbo.THUOC_TL WHERE MASP = ?", product_code)
            product["selected_genre_codes"] = {item[0] for item in cursor.fetchall()}
            return product
        finally:
            cursor.close()

    def get_lookup_data(self, selected_publisher=None, selected_brand=None,
                        selected_authors=None, selected_genres=None):
        """Lấy danh mục hoạt động và giữ các liên kết đã xóa mềm của sản phẩm cũ."""
        conn = self._connection()
        cursor = conn.cursor()
        selected_authors = set(selected_authors or ())
        selected_genres = set(selected_genres or ())
        try:
            if selected_publisher is None:
                cursor.execute("""
                    SELECT MANXB, TENNXB, ISNULL(IS_DELETED, 0)
                    FROM dbo.NHA_XUAT_BAN
                    WHERE ISNULL(IS_DELETED, 0) = 0 ORDER BY TENNXB
                """)
            else:
                cursor.execute("""
                    SELECT MANXB, TENNXB, ISNULL(IS_DELETED, 0)
                    FROM dbo.NHA_XUAT_BAN
                    WHERE ISNULL(IS_DELETED, 0) = 0 OR MANXB = ?
                    ORDER BY TENNXB
                """, selected_publisher)
            publishers = cursor.fetchall()

            if selected_authors:
                marks = ",".join("?" for _ in selected_authors)
                cursor.execute(f"""
                    SELECT MATG, TENTG, ISNULL(IS_DELETED, 0)
                    FROM dbo.TAC_GIA
                    WHERE ISNULL(IS_DELETED, 0) = 0 OR MATG IN ({marks})
                    ORDER BY TENTG
                """, tuple(selected_authors))
            else:
                cursor.execute("""
                    SELECT MATG, TENTG, ISNULL(IS_DELETED, 0)
                    FROM dbo.TAC_GIA
                    WHERE ISNULL(IS_DELETED, 0) = 0 ORDER BY TENTG
                """)
            authors = cursor.fetchall()

            if selected_genres:
                marks = ",".join("?" for _ in selected_genres)
                cursor.execute(f"""
                    SELECT MATL, TENTL, ISNULL(IS_DELETED, 0)
                    FROM dbo.THE_LOAI
                    WHERE ISNULL(IS_DELETED, 0) = 0 OR MATL IN ({marks})
                    ORDER BY TENTL
                """, tuple(selected_genres))
            else:
                cursor.execute("""
                    SELECT MATL, TENTL, ISNULL(IS_DELETED, 0)
                    FROM dbo.THE_LOAI
                    WHERE ISNULL(IS_DELETED, 0) = 0 ORDER BY TENTL
                """)
            genres = cursor.fetchall()

            if selected_brand is None:
                cursor.execute("""
                    SELECT MATH, TENTH, ISNULL(IS_DELETED, 0)
                    FROM dbo.THUONG_HIEU
                    WHERE ISNULL(IS_DELETED, 0) = 0 ORDER BY TENTH
                """)
            else:
                cursor.execute("""
                    SELECT MATH, TENTH, ISNULL(IS_DELETED, 0)
                    FROM dbo.THUONG_HIEU
                    WHERE ISNULL(IS_DELETED, 0) = 0 OR MATH = ?
                    ORDER BY TENTH
                """, selected_brand)
            brands = cursor.fetchall()

            return {
                "publishers": publishers, "authors": authors,
                "genres": genres, "brands": brands,
            }
        finally:
            cursor.close()

    def get_product_detail(self, product_code):
        """Lấy thông tin chung và phần chi tiết sách hoặc sản phẩm khác."""
        product = self.get_product(product_code)
        if product is None:
            return None
        conn = self._connection()
        cursor = conn.cursor()
        try:
            if product["loai"] == "Sách":
                cursor.execute("""
                    SELECT S.ISBN, S.NAMXB, NXB.TENNXB
                    FROM dbo.SACH S
                    LEFT JOIN dbo.NHA_XUAT_BAN NXB ON NXB.MANXB = S.MANXB
                    WHERE S.MASP = ?
                """, product_code)
                book = cursor.fetchone()
                product["isbn"] = book[0] if book else None
                product["namxb"] = book[1] if book else None
                product["ten_nxb"] = book[2] if book else None
                cursor.execute("""
                    SELECT TG.TENTG
                    FROM dbo.THUOC_TG TTG
                    JOIN dbo.TAC_GIA TG ON TG.MATG = TTG.MATG
                    WHERE TTG.MASP = ? ORDER BY TG.TENTG
                """, product_code)
                product["authors"] = [row[0] for row in cursor.fetchall()]
                cursor.execute("""
                    SELECT TL.TENTL
                    FROM dbo.THUOC_TL TTL
                    JOIN dbo.THE_LOAI TL ON TL.MATL = TTL.MATL
                    WHERE TTL.MASP = ? ORDER BY TL.TENTL
                """, product_code)
                product["genres"] = [row[0] for row in cursor.fetchall()]
            else:
                cursor.execute("""
                    SELECT SPK.NGAYSX, TH.TENTH, TH.XUATXU
                    FROM dbo.SAN_PHAM_KHAC SPK
                    LEFT JOIN dbo.THUONG_HIEU TH ON TH.MATH = SPK.MATH
                    WHERE SPK.MASP = ?
                """, product_code)
                other = cursor.fetchone()
                product["ngaysx"] = other[0] if other else None
                product["brand_name"] = other[1] if other else None
                product["brand_origin"] = other[2] if other else None
            return product
        finally:
            cursor.close()

    def get_permissions(self):
        """Đọc quyền SQL của phiên Desktop cho các thao tác sản phẩm."""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    CASE WHEN
                        HAS_PERMS_BY_NAME('dbo.SAN_PHAM', 'OBJECT', 'INSERT') = 1
                        AND HAS_PERMS_BY_NAME('dbo.SACH', 'OBJECT', 'INSERT') = 1
                        AND HAS_PERMS_BY_NAME('dbo.SAN_PHAM_KHAC', 'OBJECT', 'INSERT') = 1
                        AND HAS_PERMS_BY_NAME('dbo.THUOC_TG', 'OBJECT', 'INSERT') = 1
                        AND HAS_PERMS_BY_NAME('dbo.THUOC_TL', 'OBJECT', 'INSERT') = 1
                    THEN 1 ELSE 0 END,
                    CASE WHEN
                        HAS_PERMS_BY_NAME('dbo.SAN_PHAM', 'OBJECT', 'UPDATE', 'TENSP', 'COLUMN') = 1
                        AND HAS_PERMS_BY_NAME('dbo.SAN_PHAM', 'OBJECT', 'UPDATE', 'DVT', 'COLUMN') = 1
                        AND HAS_PERMS_BY_NAME('dbo.SAN_PHAM', 'OBJECT', 'UPDATE', 'GIABAN', 'COLUMN') = 1
                        AND HAS_PERMS_BY_NAME('dbo.SAN_PHAM', 'OBJECT', 'UPDATE', 'VAT', 'COLUMN') = 1
                        AND HAS_PERMS_BY_NAME('dbo.SAN_PHAM', 'OBJECT', 'UPDATE', 'BARCODE', 'COLUMN') = 1
                        AND HAS_PERMS_BY_NAME('dbo.SACH', 'OBJECT', 'UPDATE', 'ISBN', 'COLUMN') = 1
                        AND HAS_PERMS_BY_NAME('dbo.SACH', 'OBJECT', 'UPDATE', 'NAMXB', 'COLUMN') = 1
                        AND HAS_PERMS_BY_NAME('dbo.SACH', 'OBJECT', 'UPDATE', 'MANXB', 'COLUMN') = 1
                        AND HAS_PERMS_BY_NAME('dbo.SAN_PHAM_KHAC', 'OBJECT', 'UPDATE', 'NGAYSX', 'COLUMN') = 1
                        AND HAS_PERMS_BY_NAME('dbo.SAN_PHAM_KHAC', 'OBJECT', 'UPDATE', 'MATH', 'COLUMN') = 1
                        AND HAS_PERMS_BY_NAME('dbo.THUOC_TG', 'OBJECT', 'DELETE') = 1
                        AND HAS_PERMS_BY_NAME('dbo.THUOC_TG', 'OBJECT', 'INSERT') = 1
                        AND HAS_PERMS_BY_NAME('dbo.THUOC_TL', 'OBJECT', 'DELETE') = 1
                        AND HAS_PERMS_BY_NAME('dbo.THUOC_TL', 'OBJECT', 'INSERT') = 1
                    THEN 1 ELSE 0 END,
                    CASE WHEN
                        HAS_PERMS_BY_NAME('dbo.SAN_PHAM', 'OBJECT', 'UPDATE', 'IS_DELETED', 'COLUMN') = 1
                    THEN 1 ELSE 0 END
            """)
            row = cursor.fetchone()
            return {
                "can_add": bool(row[0]),
                "can_edit": bool(row[1]),
                "can_delete": bool(row[2]),
            }
        finally:
            cursor.close()

    @staticmethod
    def _next_product_code(cursor, lock_table=False):
        """Sinh mã SP theo hậu tố lớn nhất, tính cả sản phẩm đã xóa mềm."""
        table_hint = " WITH (TABLOCKX, HOLDLOCK)" if lock_table else ""
        cursor.execute(f"""
            SELECT COALESCE(
                MAX(TRY_CONVERT(BIGINT, SUBSTRING(MASP, 3, 18))),
                0
            )
            FROM dbo.SAN_PHAM{table_hint}
            WHERE UPPER(LEFT(MASP, 2)) = 'SP'
              AND TRY_CONVERT(BIGINT, SUBSTRING(MASP, 3, 18)) IS NOT NULL
        """)
        code = f"SP{int(cursor.fetchone()[0] or 0) + 1:03d}"
        if len(code) > 20:
            raise ValueError("Đã vượt giới hạn độ dài mã sản phẩm (20 ký tự).")
        return code

    def preview_next_product_code(self):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            code = self._next_product_code(cursor)
            conn.commit()
            return code
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def save_product(self, data, product_code=None):
        """Thêm hoặc cập nhật sản phẩm cùng subtype và liên kết trong một transaction."""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            code = str(product_code or "").strip()
            if not code:
                code = self._next_product_code(cursor, lock_table=True)

            barcode = data.get("barcode") or None
            if barcode:
                cursor.execute("""
                    SELECT TOP (1) MASP
                    FROM dbo.SAN_PHAM
                    WHERE BARCODE = ? AND MASP <> ?
                """, barcode, code)
                duplicate = cursor.fetchone()
                if duplicate is not None:
                    raise DuplicateProductBarcodeError(
                        f"Mã vạch {barcode} đã được gán cho sản phẩm {duplicate[0]}."
                    )

            if product_code:
                cursor.execute("""
                    SELECT
                        CASE
                            WHEN EXISTS (SELECT 1 FROM dbo.SACH WHERE MASP = ?) THEN 'book'
                            WHEN EXISTS (SELECT 1 FROM dbo.SAN_PHAM_KHAC WHERE MASP = ?) THEN 'other'
                            ELSE 'unclassified'
                        END
                    FROM dbo.SAN_PHAM
                    WHERE MASP = ? AND ISNULL(IS_DELETED, 0) = 0
                """, code, code, code)
                existing_type = cursor.fetchone()
                if existing_type is None:
                    raise LookupError("Sản phẩm không tồn tại hoặc đã bị xóa mềm!")
                if existing_type[0] != data["product_type"]:
                    raise ValueError("Không thể thay đổi loại sản phẩm khi chỉnh sửa.")

                cursor.execute("""
                    UPDATE dbo.SAN_PHAM
                    SET TENSP = ?, BARCODE = ?, DVT = ?, GIABAN = ?, VAT = ?
                    OUTPUT inserted.MASP
                    WHERE MASP = ? AND ISNULL(IS_DELETED, 0) = 0
                """, data["tensp"], barcode, data["dvt"], data["giaban"],
                     data["vat"], code)
                if cursor.fetchone() is None:
                    raise LookupError("Sản phẩm không tồn tại hoặc đã bị xóa mềm!")

                if data["product_type"] == "book":
                    cursor.execute("""
                        UPDATE dbo.SACH
                        SET ISBN = ?, NAMXB = ?, MANXB = ?
                        WHERE MASP = ?
                    """, data.get("isbn"), data.get("namxb"), data.get("manxb"), code)
                    cursor.execute("DELETE FROM dbo.THUOC_TG WHERE MASP = ?", code)
                    for author_code in data.get("authors", []):
                        cursor.execute(
                            "INSERT INTO dbo.THUOC_TG (MATG, MASP) VALUES (?, ?)",
                            author_code, code
                        )
                    cursor.execute("DELETE FROM dbo.THUOC_TL WHERE MASP = ?", code)
                    for genre_code in data.get("genres", []):
                        cursor.execute(
                            "INSERT INTO dbo.THUOC_TL (MATL, MASP) VALUES (?, ?)",
                            genre_code, code
                        )
                else:
                    cursor.execute("""
                        UPDATE dbo.SAN_PHAM_KHAC
                        SET NGAYSX = ?, MATH = ?
                        WHERE MASP = ?
                    """, data.get("ngaysx"), data.get("math"), code)
            else:
                cursor.execute("""
                    INSERT INTO dbo.SAN_PHAM
                        (MASP, TENSP, BARCODE, DVT, GIANHAP, GIABAN, SLTON, VAT, IS_DELETED)
                    VALUES (?, ?, ?, ?, 0, ?, 0, ?, 0)
                """, code, data["tensp"], barcode, data["dvt"], data["giaban"], data["vat"])

                if data["product_type"] == "book":
                    cursor.execute("""
                        INSERT INTO dbo.SACH (MASP, ISBN, NAMXB, MANXB)
                        VALUES (?, ?, ?, ?)
                    """, code, data.get("isbn"), data.get("namxb"), data.get("manxb"))
                    for author_code in data.get("authors", []):
                        cursor.execute(
                            "INSERT INTO dbo.THUOC_TG (MATG, MASP) VALUES (?, ?)",
                            author_code, code
                        )
                    for genre_code in data.get("genres", []):
                        cursor.execute(
                            "INSERT INTO dbo.THUOC_TL (MATL, MASP) VALUES (?, ?)",
                            genre_code, code
                        )
                else:
                    cursor.execute("""
                        INSERT INTO dbo.SAN_PHAM_KHAC (MASP, NGAYSX, MATH)
                        VALUES (?, ?, ?)
                    """, code, data.get("ngaysx"), data.get("math"))

            conn.commit()
            return code
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def soft_delete_product(self, product_code):
        """Xóa mềm sản phẩm nếu tồn kho bằng 0, khóa dòng trong lúc kiểm tra/cập nhật."""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT TENSP, ISNULL(SLTON, 0)
                FROM dbo.SAN_PHAM WITH (UPDLOCK, HOLDLOCK)
                WHERE MASP = ? AND ISNULL(IS_DELETED, 0) = 0
            """, product_code)
            product = cursor.fetchone()
            if product is None:
                raise LookupError(
                    "Sản phẩm không tồn tại hoặc đã được xóa trước đó!"
                )
            stock = int(product[1] or 0)
            if stock > 0:
                raise ProductHasStockError(product_code, stock)

            cursor.execute("""
                UPDATE dbo.SAN_PHAM
                SET IS_DELETED = 1
                OUTPUT inserted.MASP
                WHERE MASP = ?
                  AND ISNULL(IS_DELETED, 0) = 0
                  AND ISNULL(SLTON, 0) = 0
            """, product_code)
            if cursor.fetchone() is None:
                raise RuntimeError(
                    "Không thể xóa sản phẩm. Vui lòng tải lại dữ liệu và thử lại."
                )
            conn.commit()
            return product[0]
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
