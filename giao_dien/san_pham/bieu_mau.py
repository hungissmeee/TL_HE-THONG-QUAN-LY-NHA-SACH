"""ProductFormDialog: thành phần giao diện quản lý sản phẩm."""

from decimal import (
    Decimal,
    InvalidOperation,
)
from PySide6.QtCore import (
    Qt,
    QDate,
)
from PySide6.QtGui import (
    QDoubleValidator,
    QIntValidator,
)
from PySide6.QtWidgets import (
    QWidget,
    QDialog,
    QLabel,
    QPushButton,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QMessageBox,
    QComboBox,
    QStackedWidget,
    QDateEdit,
    QGroupBox,
)
from .bo_chon import SearchableSingleSelect, SearchableMultiSelect


class ProductFormDialog(QDialog):
    """Biểu mẫu thêm mới hoặc cập nhật thông tin sản phẩm."""
    """Form thêm mới hoặc chỉnh sửa sản phẩm."""

    def __init__(self, db, parent=None, product_code=None):
        super().__init__(parent)
        self.db = db
        self.product_code = product_code
        self.is_edit = product_code is not None
        self.existing = None

        self.setWindowTitle("Chỉnh sửa sản phẩm" if self.is_edit else "Thêm sản phẩm mới")
        self.setMinimumWidth(580)
        self.setMinimumHeight(880)

        if self.is_edit:
            self.load_existing_product()

        self.setup_ui()
        self.load_lookup_data()

        if self.is_edit:
            self.populate_form()
        else:
            self.refresh_product_code_preview()

    def _next_product_code(self, cursor, lock_table=False):
        """
        Tạo mã dạng SP001, SP002... dựa trên hậu tố số lớn nhất.
        Không lọc IS_DELETED nên mã của sản phẩm đã xóa vẫn được tính.
        Khi lưu thật, khóa bảng trong transaction để tránh hai người
        cùng nhận một mã nếu tạo sản phẩm đồng thời.
        """
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
        last_number = cursor.fetchone()[0] or 0
        next_number = int(last_number) + 1
        code = f"SP{next_number:03d}"
        if len(code) > 20:
            raise ValueError("Đã vượt giới hạn độ dài mã sản phẩm (20 ký tự).")
        return code

    def refresh_product_code_preview(self):
        """Hiển thị trước mã kế tiếp; mã sẽ được tính lại lúc lưu."""
        conn = self.db.get_connection()
        if conn is None:
            self.masp.setText("")
            return

        cursor = None
        try:
            cursor = conn.cursor()
            code = self._next_product_code(cursor, lock_table=False)
            self.masp.setText(code)
            # Kết thúc transaction đọc preview nếu driver đang dùng autocommit off.
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.masp.setText("Không tạo được mã")
            QMessageBox.warning(
                self,
                "Không thể tạo mã sản phẩm",
                f"Không lấy được mã sản phẩm tự động.\n{e}"
            )
        finally:
            if cursor is not None:
                cursor.close()

    def load_existing_product(self):
        cursor = None
        try:
            cursor = self.db.get_connection().cursor()
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
                    SPK.NGAYSX, SPK.MATH
                FROM dbo.SAN_PHAM SP
                LEFT JOIN dbo.SACH S ON S.MASP = SP.MASP
                LEFT JOIN dbo.SAN_PHAM_KHAC SPK ON SPK.MASP = SP.MASP
                WHERE SP.MASP = ?
                  AND ISNULL(SP.IS_DELETED, 0) = 0
            """, self.product_code)
            row = cursor.fetchone()
            if row is None:
                raise Exception("Không tìm thấy sản phẩm cần chỉnh sửa!")
            if row[7] == "Chưa phân loại":
                raise Exception("Sản phẩm chưa được phân loại thành sách hoặc sản phẩm khác, không thể chỉnh sửa bằng form này.")

            self.existing = {
                "masp": row[0], "tensp": row[1], "dvt": row[2],
                "gianhap": row[3], "giaban": row[4], "slton": row[5],
                "vat": row[6], "loai": row[7], "isbn": row[8],
                "namxb": row[9], "manxb": row[10],
                "ngaysx": row[11], "math": row[12]
            }

            cursor.execute(
                "SELECT MATG FROM dbo.THUOC_TG WHERE MASP = ?",
                self.product_code
            )
            self.selected_author_codes = {r[0] for r in cursor.fetchall()}

            cursor.execute(
                "SELECT MATL FROM dbo.THUOC_TL WHERE MASP = ?",
                self.product_code
            )
            self.selected_genre_codes = {r[0] for r in cursor.fetchall()}

        finally:
            if cursor is not None:
                cursor.close()

    def setup_ui(self):
        root = QVBoxLayout(self)

        title = QLabel("CHỈNH SỬA SẢN PHẨM" if self.is_edit else "THÊM SẢN PHẨM MỚI")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        root.addWidget(title)

        self.type_combo = QComboBox()
        self.type_combo.addItem("Sách", "book")
        self.type_combo.addItem("Sản phẩm khác", "other")
        root.addWidget(QLabel("Loại sản phẩm:"))
        root.addWidget(self.type_combo)

        common_group = QGroupBox("Thông tin chung")
        common_form = QFormLayout(common_group)

        self.masp = QLineEdit()
        self.masp.setMaxLength(20)
        self.masp.setReadOnly(True)
        self.masp.setPlaceholderText("Mã sản phẩm được tạo tự động")
        self.masp.setToolTip(
            "Mã sản phẩm được hệ thống tự tăng theo mã lớn nhất đã có, "
            "kể cả sản phẩm đã xóa mềm."
        )

        self.tensp = QLineEdit()
        self.tensp.setMaxLength(150)

        self.dvt = QLineEdit()
        self.dvt.setMaxLength(30)
        self.dvt.setPlaceholderText("Ví dụ: Quyển, Cái, Chiếc")

        self.gianhap = QLineEdit()
        self.gianhap.setPlaceholderText("0.00")
        self.gianhap.setValidator(QDoubleValidator(0, 9999999999999.99, 2, self))

        self.giaban = QLineEdit()
        self.giaban.setPlaceholderText("0.00")
        self.giaban.setValidator(QDoubleValidator(0, 9999999999999.99, 2, self))

        self.slton = QLineEdit("0")
        self.slton.setValidator(QIntValidator(0, 2147483647, self))

        self.vat = QLineEdit("0")
        self.vat.setValidator(QDoubleValidator(0, 999.99, 2, self))

        common_form.addRow("Mã sản phẩm:", self.masp)
        common_form.addRow("Tên sản phẩm:", self.tensp)
        common_form.addRow("Đơn vị tính:", self.dvt)
        common_form.addRow("Giá nhập:", self.gianhap)
        common_form.addRow("Giá bán:", self.giaban)
        common_form.addRow("Số lượng tồn:", self.slton)
        common_form.addRow("VAT (%):", self.vat)
        root.addWidget(common_group)

        self.type_stack = QStackedWidget()

        # Thông tin riêng của sách
        book_page = QWidget()
        book_form = QFormLayout(book_page)

        self.isbn = QLineEdit()
        self.isbn.setMaxLength(20)

        self.namxb = QLineEdit()
        self.namxb.setValidator(QIntValidator(0, 9999, self))

        # Chọn nhà xuất bản bằng tìm kiếm, không dùng combo box.
        self.publisher_combo = SearchableSingleSelect(
            "Tìm mã hoặc tên nhà xuất bản..."
        )

        # Tác giả và thể loại hỗ trợ tìm kiếm, chọn nhiều mục bằng cách nhấn kết quả.
        self.authors_list = SearchableMultiSelect(
            "Tìm mã hoặc tên tác giả..."
        )
        self.genres_list = SearchableMultiSelect(
            "Tìm mã hoặc tên thể loại..."
        )

        book_form.addRow("ISBN:", self.isbn)
        book_form.addRow("Năm xuất bản:", self.namxb)
        book_form.addRow("Nhà xuất bản:", self.publisher_combo)
        book_form.addRow("Tác giả (tìm và chọn nhiều):", self.authors_list)
        book_form.addRow("Thể loại (tìm và chọn nhiều):", self.genres_list)
        self.type_stack.addWidget(book_page)

        # Thông tin riêng của sản phẩm khác
        other_page = QWidget()
        other_form = QFormLayout(other_page)

        self.ngaysx = QDateEdit()
        self.ngaysx.setCalendarPopup(True)
        self.ngaysx.setDisplayFormat("dd/MM/yyyy")
        self.ngaysx.setDate(QDate.currentDate())

        self.brand_combo = SearchableSingleSelect(
            "Tìm mã hoặc tên thương hiệu..."
        )

        other_form.addRow("Ngày sản xuất:", self.ngaysx)
        other_form.addRow("Thương hiệu:", self.brand_combo)
        self.type_stack.addWidget(other_page)

        root.addWidget(self.type_stack)
        self.type_combo.currentIndexChanged.connect(self.type_stack.setCurrentIndex)

        buttons = QHBoxLayout()
        save_button = QPushButton("Lưu thay đổi" if self.is_edit else "Thêm sản phẩm")
        save_button.clicked.connect(self.save_product)
        cancel_button = QPushButton("Hủy")
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        root.addLayout(buttons)

        if self.is_edit:
            # Không cho đổi mã hoặc chuyển loại khi chỉnh sửa.
            self.masp.setReadOnly(True)
            self.masp.setToolTip("Mã sản phẩm không thể thay đổi.")
            self.type_combo.setEnabled(False)
            self.type_combo.setToolTip("Không thể đổi loại sản phẩm khi chỉnh sửa.")
        else:
            # Khi thêm mới, mã luôn do hệ thống sinh, không nhập tay.
            self.masp.setReadOnly(True)

    def _fill_combo(self, cursor, sql, combo, placeholder, selected_code=None):
        cursor.execute(sql, selected_code) if "?" in sql else cursor.execute(sql)
        combo.clear()
        combo.addItem(placeholder, None)
        for code, name, is_deleted in cursor.fetchall():
            suffix = " (đã xóa mềm)" if is_deleted else ""
            combo.addItem(f"{code} - {name}{suffix}", code)
        if selected_code is not None:
            index = combo.findData(selected_code)
            if index >= 0:
                combo.setCurrentIndex(index)

    def load_lookup_data(self):
        """Tải danh mục đang hoạt động; giữ mục đã xóa nếu đang gắn với sản phẩm cũ."""
        conn = self.db.get_connection()
        if conn is None:
            raise Exception("Chưa có kết nối database!")

        cursor = conn.cursor()
        try:
            selected_publisher = (
                self.existing.get("manxb")
                if self.is_edit and self.existing["loai"] == "Sách"
                else None
            )
            selected_brand = (
                self.existing.get("math")
                if self.is_edit and self.existing["loai"] == "Sản phẩm khác"
                else None
            )

            # Nhà xuất bản: chọn một bằng tìm kiếm.
            if selected_publisher is None:
                cursor.execute("""
                    SELECT MANXB, TENNXB, ISNULL(IS_DELETED, 0)
                    FROM dbo.NHA_XUAT_BAN
                    WHERE ISNULL(IS_DELETED, 0) = 0
                    ORDER BY TENNXB
                """)
            else:
                cursor.execute("""
                    SELECT MANXB, TENNXB, ISNULL(IS_DELETED, 0)
                    FROM dbo.NHA_XUAT_BAN
                    WHERE ISNULL(IS_DELETED, 0) = 0 OR MANXB = ?
                    ORDER BY TENNXB
                """, selected_publisher)
            self.publisher_combo.set_options(
                cursor.fetchall(), selected_publisher
            )

            # Tác giả: tìm kiếm và chọn nhiều.
            selected_authors = self.selected_author_codes if self.is_edit else set()
            if selected_authors:
                placeholders = ",".join("?" for _ in selected_authors)
                cursor.execute(f"""
                    SELECT MATG, TENTG, ISNULL(IS_DELETED, 0)
                    FROM dbo.TAC_GIA
                    WHERE ISNULL(IS_DELETED, 0) = 0
                       OR MATG IN ({placeholders})
                    ORDER BY TENTG
                """, tuple(selected_authors))
            else:
                cursor.execute("""
                    SELECT MATG, TENTG, ISNULL(IS_DELETED, 0)
                    FROM dbo.TAC_GIA
                    WHERE ISNULL(IS_DELETED, 0) = 0
                    ORDER BY TENTG
                """)
            self.authors_list.set_options(
                cursor.fetchall(), selected_authors
            )

            # Thể loại: tìm kiếm và chọn nhiều.
            selected_genres = self.selected_genre_codes if self.is_edit else set()
            if selected_genres:
                placeholders = ",".join("?" for _ in selected_genres)
                cursor.execute(f"""
                    SELECT MATL, TENTL, ISNULL(IS_DELETED, 0)
                    FROM dbo.THE_LOAI
                    WHERE ISNULL(IS_DELETED, 0) = 0
                       OR MATL IN ({placeholders})
                    ORDER BY TENTL
                """, tuple(selected_genres))
            else:
                cursor.execute("""
                    SELECT MATL, TENTL, ISNULL(IS_DELETED, 0)
                    FROM dbo.THE_LOAI
                    WHERE ISNULL(IS_DELETED, 0) = 0
                    ORDER BY TENTL
                """)
            self.genres_list.set_options(
                cursor.fetchall(), selected_genres
            )

            # Thương hiệu: chọn một bằng tìm kiếm.
            if selected_brand is None:
                cursor.execute("""
                    SELECT MATH, TENTH, ISNULL(IS_DELETED, 0)
                    FROM dbo.THUONG_HIEU
                    WHERE ISNULL(IS_DELETED, 0) = 0
                    ORDER BY TENTH
                """)
            else:
                cursor.execute("""
                    SELECT MATH, TENTH, ISNULL(IS_DELETED, 0)
                    FROM dbo.THUONG_HIEU
                    WHERE ISNULL(IS_DELETED, 0) = 0 OR MATH = ?
                    ORDER BY TENTH
                """, selected_brand)
            self.brand_combo.set_options(
                cursor.fetchall(), selected_brand
            )
        finally:
            cursor.close()

    def populate_form(self):
        p = self.existing
        self.masp.setText(str(p["masp"]))
        self.tensp.setText(p["tensp"] or "")
        self.dvt.setText(p["dvt"] or "")
        self.gianhap.setText(str(p["gianhap"] if p["gianhap"] is not None else 0))
        self.giaban.setText(str(p["giaban"] if p["giaban"] is not None else 0))
        self.slton.setText(str(p["slton"] if p["slton"] is not None else 0))
        self.vat.setText(str(p["vat"] if p["vat"] is not None else 0))

        type_data = "book" if p["loai"] == "Sách" else "other"
        type_index = self.type_combo.findData(type_data)
        self.type_combo.setCurrentIndex(type_index)
        self.type_stack.setCurrentIndex(type_index)

        if type_data == "book":
            self.isbn.setText(p["isbn"] or "")
            self.namxb.setText(str(p["namxb"]) if p["namxb"] is not None else "")
        else:
            date_value = p["ngaysx"]
            if date_value is not None:
                self.ngaysx.setDate(QDate(date_value.year, date_value.month, date_value.day))

    @staticmethod
    def parse_decimal(value, field_name):
        try:
            result = Decimal(value.strip().replace(",", "."))
        except (InvalidOperation, AttributeError):
            raise ValueError(f"{field_name} phải là số hợp lệ!")
        if result < 0:
            raise ValueError(f"{field_name} không được âm!")
        return result

    def save_product(self):
        masp = self.masp.text().strip()
        tensp = self.tensp.text().strip()
        dvt = self.dvt.text().strip()

        if (self.is_edit and not masp) or not tensp or not dvt:
            QMessageBox.warning(
                self, "Thiếu thông tin",
                "Vui lòng nhập tên sản phẩm và đơn vị tính."
            )
            return

        if not self.gianhap.text().strip() or not self.giaban.text().strip() or not self.slton.text().strip():
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập giá nhập, giá bán và số lượng tồn.")
            return

        try:
            gianhap = self.parse_decimal(self.gianhap.text(), "Giá nhập")
            giaban = self.parse_decimal(self.giaban.text(), "Giá bán")
            vat = self.parse_decimal(self.vat.text() or "0", "VAT")
            slton = int(self.slton.text())
            namxb_text = self.namxb.text().strip()
            namxb = int(namxb_text) if namxb_text else None
        except (ValueError, InvalidOperation) as e:
            QMessageBox.warning(self, "Dữ liệu không hợp lệ", str(e))
            return

        product_type = self.type_combo.currentData()
        if product_type == "book" and self.publisher_combo.currentData() is None:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn nhà xuất bản.")
            return
        if product_type == "other" and self.brand_combo.currentData() is None:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn thương hiệu.")
            return

        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối database!")
            return
        cursor = conn.cursor()

        try:
            if self.is_edit:
                # Khi chỉnh sửa, giữ nguyên mã sản phẩm hiện tại.
                masp = self.masp.text().strip()
            else:
                # Tính lại mã ngay lúc lưu và khóa bảng trong transaction.
                # Việc tính mã bao gồm cả các dòng IS_DELETED = 1.
                masp = self._next_product_code(cursor, lock_table=True)
                self.masp.setText(masp)

            if self.is_edit:
                # Cập nhật thông tin chung
                cursor.execute("""
                    UPDATE dbo.SAN_PHAM
                    SET TENSP = ?, DVT = ?, GIANHAP = ?,
                        GIABAN = ?, SLTON = ?, VAT = ?
                    OUTPUT inserted.MASP
                    WHERE MASP = ? AND ISNULL(IS_DELETED, 0) = 0
                """, tensp, dvt, gianhap, giaban, slton, vat, masp)
                if cursor.fetchone() is None:
                    raise Exception("Sản phẩm không tồn tại hoặc đã bị xóa mềm!")

                if product_type == "book":
                    cursor.execute("""
                        UPDATE dbo.SACH
                        SET ISBN = ?, NAMXB = ?, MANXB = ?
                        WHERE MASP = ?
                    """, self.isbn.text().strip() or None, namxb,
                         self.publisher_combo.currentData(), masp)
                    # Thay mới các liên kết tác giả và thể loại
                    cursor.execute("DELETE FROM dbo.THUOC_TG WHERE MASP = ?", masp)
                    for matg in self.authors_list.checked_codes():
                        cursor.execute("""
                            INSERT INTO dbo.THUOC_TG (MATG, MASP)
                            VALUES (?, ?)
                        """, matg, masp)

                    cursor.execute("DELETE FROM dbo.THUOC_TL WHERE MASP = ?", masp)
                    for matl in self.genres_list.checked_codes():
                        cursor.execute("""
                            INSERT INTO dbo.THUOC_TL (MATL, MASP)
                            VALUES (?, ?)
                        """, matl, masp)
                else:
                    cursor.execute("""
                        UPDATE dbo.SAN_PHAM_KHAC
                        SET NGAYSX = ?, MATH = ?
                        WHERE MASP = ?
                    """, self.ngaysx.date().toPython(),
                         self.brand_combo.currentData(), masp)
                success_message = "Đã cập nhật thông tin sản phẩm thành công!"
                success_title = "Cập nhật thành công"
            else:
                # Thêm thông tin chung
                cursor.execute("""
                    INSERT INTO dbo.SAN_PHAM
                        (MASP, TENSP, DVT, GIANHAP, GIABAN, SLTON, VAT, IS_DELETED)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """, masp, tensp, dvt, gianhap, giaban, slton, vat)

                if product_type == "book":
                    cursor.execute("""
                        INSERT INTO dbo.SACH (MASP, ISBN, NAMXB, MANXB)
                        VALUES (?, ?, ?, ?)
                    """, masp, self.isbn.text().strip() or None,
                         namxb, self.publisher_combo.currentData())

                    for matg in self.authors_list.checked_codes():
                        cursor.execute("""
                            INSERT INTO dbo.THUOC_TG (MATG, MASP)
                            VALUES (?, ?)
                        """, matg, masp)

                    for matl in self.genres_list.checked_codes():
                        cursor.execute("""
                            INSERT INTO dbo.THUOC_TL (MATL, MASP)
                            VALUES (?, ?)
                        """, matl, masp)
                else:
                    cursor.execute("""
                        INSERT INTO dbo.SAN_PHAM_KHAC (MASP, NGAYSX, MATH)
                        VALUES (?, ?, ?)
                    """, masp, self.ngaysx.date().toPython(), self.brand_combo.currentData())

                success_message = f"Đã thêm sản phẩm thành công!\nMã sản phẩm: {masp}"
                success_title = "Thành công"

            conn.commit()
            QMessageBox.information(self, success_title, success_message)
            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(
                self,
                "Lỗi cập nhật sản phẩm" if self.is_edit else "Lỗi thêm sản phẩm",
                str(e)
            )
        finally:
            cursor.close()



