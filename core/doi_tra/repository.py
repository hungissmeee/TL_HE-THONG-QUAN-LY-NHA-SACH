"""Repository SQL/transaction cho nghiệp vụ đổi trả."""

from decimal import Decimal, ROUND_HALF_UP

from core.sql_support import resolve_connection, restore_and_activate_product


MONEY_QUANT = Decimal("0.01")


class ReturnRepository:
    """Đọc/ghi phiếu đổi trả và đảo kho trong transaction."""

    def __init__(self, connection_source):
        self.connection_source = connection_source

    def _connection(self):
        return resolve_connection(self.connection_source)

    @staticmethod
    def ensure_manager(cursor, username, is_admin=False):
        """Xác nhận quyền từ SQL role và hồ sơ nhân viên; Admin được miễn hồ sơ."""
        if is_admin or str(username or "").strip().casefold() == "admin":
            cursor.execute(
                "SELECT MANV FROM dbo.NHAN_VIEN WHERE MANV = ?",
                username,
            )
            row = cursor.fetchone()
            return row[0] if row else None

        cursor.execute("""
            SELECT CASE
                WHEN IS_ROLEMEMBER(N'rl_QuanLy') = 1
                 AND EXISTS (
                     SELECT 1 FROM dbo.NHAN_VIEN
                     WHERE MANV = ? AND VAITRO = N'Quản lý'
                 )
                THEN 1 ELSE 0
            END
        """, username)
        row = cursor.fetchone()
        if row is None or int(row[0] or 0) != 1:
            raise PermissionError(
                "Chỉ tài khoản thuộc vai trò Quản lý được xử lý đổi trả."
            )
        return str(username or "").strip()

    def get_employee_role(self, username):
        if str(username or "").strip().casefold() == "admin":
            return ""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT VAITRO FROM dbo.NHAN_VIEN WHERE MANV = ?",
                username,
            )
            row = cursor.fetchone()
            return str(row[0] or "").strip() if row else ""
        finally:
            cursor.close()

    def list_eligible_invoices(self):
        """Chỉ hóa đơn có hiệu lực phát sinh trong ngày hiện tại."""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT MAHD, NGAYLAP
                FROM dbo.HOA_DON
                WHERE ISNULL(TRANGTHAI, 0) = 1
                  AND NGAYLAP >= CONVERT(date, SYSDATETIME())
                  AND NGAYLAP < DATEADD(day, 1, CONVERT(date, SYSDATETIME()))
                ORDER BY NGAYLAP DESC, MAHD DESC
            """)
            return [(str(row[0]), row[1]) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_invoice_items(self, invoice_code):
        """Lấy các dòng hàng gốc và số lượng đã được xử lý qua phiếu đổi trả."""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT HD.NGAYLAP, ISNULL(KM.TYLEGIAM, 0)
                FROM dbo.HOA_DON HD
                LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
                WHERE HD.MAHD = ?
                  AND ISNULL(HD.TRANGTHAI, 0) = 1
                  AND CAST(HD.NGAYLAP AS date) = CAST(SYSDATETIME() AS date)
            """, invoice_code)
            header = cursor.fetchone()
            if header is None:
                raise ValueError("Hóa đơn không còn đủ điều kiện đổi trả.")

            discount_rate = Decimal(str(header[1] or 0))
            cursor.execute("""
                SELECT
                    CT.MASP,
                    COALESCE(SP.TENSP, N'(Sản phẩm không còn trong danh mục)'),
                    COALESCE(SP.DVT, N''),
                    COALESCE(CT.SOLUONG, 0),
                    COALESCE(R.DA_XU_LY, 0),
                    COALESCE(R.DA_HOAN_TIEN, 0),
                    COALESCE(R.TIEN_DA_HOAN, 0),
                    COALESCE(CT.THANHTIENSAUGIAM, 0),
                    COALESCE(CT.VAT, 0)
                FROM dbo.CHI_TIET_HOA_DON CT
                LEFT JOIN dbo.SAN_PHAM SP ON SP.MASP = CT.MASP
                OUTER APPLY (
                    SELECT
                        SUM(COALESCE(CTDT.SOLUONG, 0)) AS DA_XU_LY,
                        SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0
                            THEN COALESCE(CTDT.SOLUONG, 0) ELSE 0 END) AS DA_HOAN_TIEN,
                        SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0
                            THEN COALESCE(CTDT.TONGTIENHOAN, 0) ELSE 0 END) AS TIEN_DA_HOAN
                    FROM dbo.PHIEU_DOI_TRA PDT
                    INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                    WHERE PDT.MAHD = CT.MAHD AND CTDT.MASP = CT.MASP
                ) R
                WHERE CT.MAHD = ?
                ORDER BY CT.MASP
            """, invoice_code)
            items = []
            for row in cursor.fetchall():
                purchased = int(row[3] or 0)
                processed = int(row[4] or 0)
                refunded_quantity = int(row[5] or 0)
                refunded_amount = Decimal(str(row[6] or 0))
                items.append({
                    "product_code": str(row[0]),
                    "product_name": str(row[1] or ""),
                    "unit": str(row[2] or ""),
                    "purchased": purchased,
                    "processed": processed,
                    "remaining": max(purchased - processed, 0),
                    "refunded_quantity": refunded_quantity,
                    "refunded_amount": refunded_amount,
                    "line_total_after_discount": Decimal(str(row[7] or 0)),
                    "vat": Decimal(str(row[8] or 0)),
                })
            return {
                "invoice_code": invoice_code,
                "invoice_date": header[0],
                "discount_rate": discount_rate,
                "items": items,
            }
        finally:
            cursor.close()

    def list_returns(self, start_date, end_date, keyword=""):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            sql = """
                SELECT
                    PDT.MAPDT, PDT.NGAY_DOI_TRA, COALESCE(PDT.MAHD, ''),
                    COALESCE(NV.TENNV, PDT.MANV, ''), COALESCE(PDT.LY_DO, ''),
                    COALESCE(CT.TONG_SOLUONG, 0), COALESCE(PDT.TONG_TIEN_HOAN, 0)
                FROM dbo.PHIEU_DOI_TRA PDT
                LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = PDT.MANV
                OUTER APPLY (
                    SELECT SUM(COALESCE(CTDT.SOLUONG, 0)) AS TONG_SOLUONG
                    FROM dbo.CHI_TIET_DOI_TRA CTDT
                    WHERE CTDT.MAPDT = PDT.MAPDT
                ) CT
                WHERE PDT.NGAY_DOI_TRA >= CONVERT(date, ?)
                  AND PDT.NGAY_DOI_TRA < DATEADD(day, 1, CONVERT(date, ?))
            """
            params = [start_date, end_date]
            keyword = str(keyword or "").strip()
            if keyword:
                like = f"%{keyword}%"
                sql += """
                    AND (
                        PDT.MAPDT LIKE ? OR PDT.MAHD LIKE ?
                        OR PDT.MANV LIKE ? OR NV.TENNV LIKE ?
                        OR PDT.LY_DO LIKE ?
                    )
                """
                params.extend([like] * 5)
            sql += " ORDER BY PDT.NGAY_DOI_TRA DESC, PDT.MAPDT DESC"
            cursor.execute(sql, *params)
            return [tuple(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_return_detail(self, return_code):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT PDT.MAPDT, PDT.NGAY_DOI_TRA, PDT.LY_DO,
                       PDT.TONG_TIEN_HOAN, PDT.MAHD, PDT.MANV,
                       COALESCE(NV.TENNV, N''), HD.NGAYLAP
                FROM dbo.PHIEU_DOI_TRA PDT
                LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = PDT.MANV
                LEFT JOIN dbo.HOA_DON HD ON HD.MAHD = PDT.MAHD
                WHERE PDT.MAPDT = ?
            """, return_code)
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Không tìm thấy phiếu đổi trả.")
            header = {
                "mapdt": row[0], "ngay": row[1], "reason": row[2] or "",
                "refund": row[3] or 0, "mahd": row[4] or "",
                "manv": row[5] or "", "tennv": row[6] or "",
                "ngay_hd": row[7],
            }
            cursor.execute("""
                SELECT CT.MASP,
                       COALESCE(SP.TENSP, N'(Sản phẩm không còn trong danh mục)'),
                       CT.SOLUONG, CT.DONGIAHOAN, CT.VAT,
                       CT.TINHTRANGHANG, CT.HINH_THUC_XU_LY
                FROM dbo.CHI_TIET_DOI_TRA CT
                LEFT JOIN dbo.SAN_PHAM SP ON SP.MASP = CT.MASP
                WHERE CT.MAPDT = ?
                ORDER BY CT.MASP
            """, return_code)
            items = []
            for item in cursor.fetchall():
                condition, action = item[5], item[6]
                items.append({
                    "masp": item[0],
                    "tensp": item[1] or "",
                    "quantity": int(item[2] or 0),
                    "line_refund_total": item[3] or 0,
                    "vat": item[4] or 0,
                    "condition": (
                        "Còn nguyên vẹn" if condition is not None and int(condition) == 1
                        else "Đã hỏng" if condition is not None else "Chưa ghi nhận"
                    ),
                    "action": (
                        "Đổi sản phẩm cùng mã" if action is not None and int(action) == 1
                        else "Hoàn tiền" if action is not None else "Chưa ghi nhận"
                    ),
                })
            return {"header": header, "items": items}
        finally:
            cursor.close()

    @staticmethod
    def build_inventory_reversal_actions(details):
        """Lập các biến động kho cần đảo khi xóa phiếu đổi trả."""
        actions = []
        for detail in details:
            product_code = str(detail[0] or "").strip()
            quantity = int(detail[1] or 0)
            condition = detail[2]
            action = detail[3]
            if not product_code or quantity <= 0:
                raise ValueError(
                    "Chi tiết đổi trả có mã sản phẩm hoặc số lượng không hợp lệ."
                )
            if condition not in (0, 1) or action not in (0, 1):
                raise ValueError(
                    f"Chi tiết sản phẩm {product_code} thiếu tình trạng hàng hoặc hình thức xử lý hợp lệ."
                )
            if action == 1:
                if condition != 0:
                    raise ValueError(
                        f"Sản phẩm {product_code}: dữ liệu đổi hàng không hợp lệ vì hàng trả không bị hỏng."
                    )
                actions.append((product_code, quantity, "ADD"))
            elif condition == 1:
                actions.append((product_code, quantity, "SUBTRACT"))
        return actions

    @staticmethod
    def get_stock_in_product_codes(items):
        """Lấy mã sản phẩm sẽ được cộng tồn khi lập phiếu đổi trả."""
        codes = {
            str(item.get("product_code") or "").strip()
            for item in (items or [])
            if isinstance(item, dict)
            and item.get("condition") == 1
            and item.get("action") == 0
            and str(item.get("product_code") or "").strip()
        }
        return sorted(codes, key=str.casefold)

    def get_deleted_products_to_restore(self, items):
        """Liệt kê sản phẩm xóa mềm sẽ được nhập lại kho khi hoàn hàng nguyên vẹn."""
        product_codes = self.get_stock_in_product_codes(items)
        if not product_codes:
            return []

        conn = self._connection()
        cursor = conn.cursor()
        try:
            placeholders = ", ".join("?" for _ in product_codes)
            cursor.execute(f"""
                SELECT MASP, TENSP
                FROM dbo.SAN_PHAM
                WHERE MASP IN ({placeholders})
                  AND ISNULL(IS_DELETED, 0) = 1
                ORDER BY TENSP, MASP
            """, *product_codes)
            return [
                {
                    "product_code": str(row[0]),
                    "product_name": str(row[1] or ""),
                }
                for row in cursor.fetchall()
            ]
        finally:
            cursor.close()

    @staticmethod
    def calculate_refund_delta(
        line_total, sold_quantity, refunded_quantity,
        already_refunded_amount, current_quantity,
    ):
        """Tính tiền hoàn mới, bảo đảm tổng hoàn lũy kế không vượt giá trị dòng."""
        total = Decimal(str(line_total or 0)).quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP
        )
        sold = int(sold_quantity or 0)
        refunded = int(refunded_quantity or 0)
        current = int(current_quantity or 0)
        already_paid = Decimal(str(already_refunded_amount or 0)).quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP
        )
        if sold <= 0 or refunded < 0 or current < 0 or refunded + current > sold:
            raise ValueError("Số lượng hoàn trả không hợp lệ.")

        def cumulative_amount(quantity):
            if quantity <= 0:
                return Decimal("0.00")
            if quantity >= sold:
                return total
            return (total * quantity / sold).quantize(
                MONEY_QUANT, rounding=ROUND_HALF_UP
            )

        target = cumulative_amount(refunded + current)
        remaining_value = max(total - already_paid, Decimal("0.00"))
        return min(
            max(target - already_paid, Decimal("0.00")),
            remaining_value,
        ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    @staticmethod
    def _next_return_code(cursor):
        cursor.execute("""
            SELECT COALESCE(
                MAX(TRY_CONVERT(BIGINT, SUBSTRING(MAPDT, 4, 18))), 0
            )
            FROM dbo.PHIEU_DOI_TRA WITH (TABLOCKX, HOLDLOCK)
            WHERE UPPER(LEFT(MAPDT, 3)) = 'PDT'
              AND TRY_CONVERT(BIGINT, SUBSTRING(MAPDT, 4, 18)) IS NOT NULL
        """)
        code = f"PDT{int(cursor.fetchone()[0] or 0) + 1:06d}"
        if len(code) > 20:
            raise ValueError("Đã vượt giới hạn độ dài mã phiếu đổi trả.")
        return code

    def create_return(
        self, payload, username, is_admin=False, confirmed_restore_codes=None
    ):
        """Tạo phiếu, khôi phục sản phẩm được xác nhận và cập nhật tồn kho nguyên tử."""
        confirmed_restore_codes = {
            str(code or "").strip().casefold()
            for code in (confirmed_restore_codes or [])
            if str(code or "").strip()
        }
        restored_products = []
        conn = self._connection()
        cursor = conn.cursor()
        try:
            employee_code = self.ensure_manager(cursor, username, is_admin)
            invoice_code = payload["invoice_code"]
            reason = payload["reason"]
            cursor.execute("""
                SELECT HD.NGAYLAP, HD.TRANGTHAI
                FROM dbo.HOA_DON HD WITH (UPDLOCK, HOLDLOCK)
                WHERE HD.MAHD = ?
            """, invoice_code)
            invoice = cursor.fetchone()
            if invoice is None or int(invoice[1] or 0) != 1:
                raise ValueError("Hóa đơn không tồn tại hoặc đã bị hủy.")

            cursor.execute("""
                SELECT CASE WHEN CAST(? AS date) = CAST(SYSDATETIME() AS date)
                            THEN 1 ELSE 0 END
            """, invoice[0])
            if int(cursor.fetchone()[0] or 0) != 1:
                raise ValueError("Chỉ được đổi trả trong cùng ngày lập hóa đơn.")

            verified_lines = []
            total_refund = Decimal("0.00")
            for line in payload["items"]:
                product_code = line["product_code"]
                quantity = line["quantity"]
                condition = line["condition"]
                action = line["action"]

                cursor.execute("""
                    SELECT COALESCE(SOLUONG, 0), COALESCE(VAT, 0),
                           COALESCE(THANHTIENSAUGIAM, 0)
                    FROM dbo.CHI_TIET_HOA_DON WITH (UPDLOCK, HOLDLOCK)
                    WHERE MAHD = ? AND MASP = ?
                """, invoice_code, product_code)
                sold_line = cursor.fetchone()
                if sold_line is None:
                    raise ValueError(f"Sản phẩm {product_code} không thuộc hóa đơn gốc.")

                purchased = int(sold_line[0] or 0)
                vat = Decimal(str(sold_line[1] or 0))
                line_total_after_discount = Decimal(str(sold_line[2] or 0))
                cursor.execute("""
                    SELECT
                        COALESCE(SUM(CTDT.SOLUONG), 0),
                        COALESCE(SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0
                            THEN CTDT.SOLUONG ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN CTDT.HINH_THUC_XU_LY = 0
                            THEN CTDT.TONGTIENHOAN ELSE 0 END), 0)
                    FROM dbo.PHIEU_DOI_TRA PDT WITH (UPDLOCK, HOLDLOCK)
                    INNER JOIN dbo.CHI_TIET_DOI_TRA CTDT ON CTDT.MAPDT = PDT.MAPDT
                    WHERE PDT.MAHD = ? AND CTDT.MASP = ?
                """, invoice_code, product_code)
                processed_row = cursor.fetchone()
                processed = int(processed_row[0] or 0)
                refunded_quantity = int(processed_row[1] or 0)
                already_refunded_amount = Decimal(str(processed_row[2] or 0))
                remaining = purchased - processed
                if remaining < 0 or quantity > remaining:
                    raise ValueError(
                        f"Sản phẩm {product_code} chỉ còn {max(remaining, 0)} sản phẩm có thể xử lý."
                    )
                if action == 1 and condition != 0:
                    raise ValueError(
                        f"Sản phẩm {product_code}: chỉ được đổi sản phẩm khi hàng trả đã hỏng."
                    )

                if action == 1:
                    cursor.execute("""
                        UPDATE dbo.SAN_PHAM
                        SET SLTON = SLTON - ?
                        WHERE MASP = ?
                          AND ISNULL(IS_DELETED, 0) = 0
                          AND ISNULL(SLTON, 0) >= ?
                    """, quantity, product_code, quantity)
                    if cursor.rowcount != 1:
                        raise ValueError(f"Sản phẩm {product_code} không đủ tồn kho để đổi.")
                    line_refund_total = Decimal("0.00")
                else:
                    if condition == 1:
                        cursor.execute("""
                            SELECT ISNULL(IS_DELETED, 0)
                            FROM dbo.SAN_PHAM WITH (UPDLOCK, HOLDLOCK)
                            WHERE MASP = ?
                        """, product_code)
                        product_state = cursor.fetchone()
                        if product_state is None:
                            raise LookupError(f"Không tìm thấy sản phẩm {product_code}.")

                        is_deleted = int(product_state[0] or 0) == 1
                        if is_deleted:
                            if product_code.casefold() not in confirmed_restore_codes:
                                raise ValueError(
                                    f"Sản phẩm {product_code} đã bị xóa mềm. "
                                    "Cần xác nhận khôi phục trước khi hoàn hàng."
                                )
                            cursor.execute("""
                                UPDATE dbo.SAN_PHAM
                                SET IS_DELETED = 0,
                                    SLTON = ISNULL(SLTON, 0) + ?
                                WHERE MASP = ? AND ISNULL(IS_DELETED, 0) = 1
                            """, quantity, product_code)
                            if cursor.rowcount != 1:
                                raise RuntimeError(
                                    f"Không thể khôi phục sản phẩm {product_code} và cập nhật tồn kho."
                                )
                            restored_products.append(product_code)
                        else:
                            cursor.execute("""
                                UPDATE dbo.SAN_PHAM
                                SET SLTON = ISNULL(SLTON, 0) + ?
                                WHERE MASP = ? AND ISNULL(IS_DELETED, 0) = 0
                            """, quantity, product_code)
                            if cursor.rowcount != 1:
                                raise LookupError(f"Không tìm thấy sản phẩm {product_code}.")
                    line_refund_total = self.calculate_refund_delta(
                        line_total_after_discount,
                        purchased,
                        refunded_quantity,
                        already_refunded_amount,
                        quantity,
                    )
                    total_refund += line_refund_total

                verified_lines.append((
                    product_code, quantity, line_refund_total,
                    vat, condition, action,
                ))

            total_refund = total_refund.quantize(
                MONEY_QUANT, rounding=ROUND_HALF_UP
            )
            return_code = self._next_return_code(cursor)
            cursor.execute("""
                INSERT INTO dbo.PHIEU_DOI_TRA
                    (MAPDT, NGAY_DOI_TRA, LY_DO, TONG_TIEN_HOAN, MAHD, MANV)
                VALUES (?, SYSDATETIME(), ?, ?, ?, ?)
            """, return_code, reason, total_refund, invoice_code, employee_code)

            for line in verified_lines:
                cursor.execute("""
                    INSERT INTO dbo.CHI_TIET_DOI_TRA
                        (MASP, MAPDT, SOLUONG, TONGTIENHOAN, VAT,
                         TINHTRANGHANG, HINH_THUC_XU_LY)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, line[0], return_code, line[1], line[2], line[3], line[4], line[5])

            conn.commit()
            return {
                "return_code": return_code,
                "invoice_code": invoice_code,
                "total_refund": total_refund,
                "restored_products": restored_products,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def delete_return(self, return_code, username, is_admin=False):
        """Xóa phiếu và đảo đúng biến động kho trong cùng transaction."""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            self.ensure_manager(cursor, username, is_admin)
            cursor.execute("""
                SELECT MAPDT
                FROM dbo.PHIEU_DOI_TRA WITH (UPDLOCK, HOLDLOCK)
                WHERE MAPDT = ?
            """, return_code)
            if cursor.fetchone() is None:
                raise LookupError("Phiếu đổi trả không còn tồn tại.")
            cursor.execute("""
                SELECT MASP, SOLUONG, TINHTRANGHANG, HINH_THUC_XU_LY
                FROM dbo.CHI_TIET_DOI_TRA WITH (UPDLOCK, HOLDLOCK)
                WHERE MAPDT = ?
                ORDER BY MASP
            """, return_code)
            details = cursor.fetchall()
            if not details:
                raise ValueError(
                    "Phiếu đổi trả không có chi tiết; không thể xác định biến động kho để đảo."
                )

            actions = self.build_inventory_reversal_actions(details)
            for product_code, quantity, direction in actions:
                if direction == "ADD":
                    # Đảo phiếu đổi hàng có thể hoàn sản phẩm đã bị xóa mềm.
                    if not restore_and_activate_product(cursor, product_code, quantity):
                        raise LookupError(
                            f"Không tìm thấy sản phẩm {product_code}; không thể đảo tồn kho."
                        )
                else:
                    cursor.execute("""
                        UPDATE dbo.SAN_PHAM
                        SET SLTON = SLTON - ?
                        WHERE MASP = ?
                          AND ISNULL(SLTON, 0) >= ?
                    """, quantity, product_code, quantity)
                if cursor.rowcount != 1:
                    if direction == "SUBTRACT":
                        raise ValueError(
                            f"Không thể xóa phiếu vì tồn kho {product_code} hiện không đủ "
                            f"{quantity} sản phẩm để đảo lần nhập lại. Hãy kiểm tra các giao dịch bán hàng liên quan."
                        )
                    raise LookupError(
                        f"Không tìm thấy sản phẩm {product_code}; không thể đảo tồn kho."
                    )

            cursor.execute(
                "DELETE FROM dbo.CHI_TIET_DOI_TRA WHERE MAPDT = ?",
                return_code,
            )
            cursor.execute(
                "DELETE FROM dbo.PHIEU_DOI_TRA WHERE MAPDT = ?",
                return_code,
            )
            if cursor.rowcount != 1:
                raise RuntimeError("Không thể xóa đầu phiếu đổi trả.")
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
