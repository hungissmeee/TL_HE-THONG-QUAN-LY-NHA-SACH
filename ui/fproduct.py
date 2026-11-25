from decimal import Decimal, InvalidOperation

from ui.window_helpers import show_minimizable_dialog

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import (
    QWidget, QDialog, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QFormLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox,
    QAbstractItemView, QComboBox, QStackedWidget,
    QListWidget, QListWidgetItem, QDateEdit, QGroupBox
)


class SearchableSingleSelect(QWidget):
    """Ô tìm kiếm để chọn một mục từ danh mục SQL Server."""

    def __init__(self, placeholder="Tìm để chọn...", parent=None):
        super().__init__(parent)
        self.options = []
        self._selected_code = None
        self._selected_label = ""
        self._syncing_text = False

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(placeholder)
        self.search_input.textEdited.connect(self._on_search)

        self.results = QListWidget()
        self.results.setMaximumHeight(115)
        self.results.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.results.itemClicked.connect(self._select_item)
        self.results.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.search_input)
        layout.addWidget(self.results)

    def set_options(self, options, selected_code=None):
        """options: iterable (code, name, is_deleted)."""
        self.options = [
            (str(code), str(name or ""), bool(is_deleted))
            for code, name, is_deleted in options
        ]
        self._selected_code = None
        self._selected_label = ""

        for code, name, is_deleted in self.options:
            if selected_code is not None and str(selected_code) == code:
                suffix = " (đã xóa mềm)" if is_deleted else ""
                self._selected_code = code
                self._selected_label = f"{code} - {name}{suffix}"
                break

        self._syncing_text = True
        self.search_input.setText(self._selected_label)
        self._syncing_text = False
        self.results.clear()
        self.results.hide()

    def _on_search(self, text):
        if self._syncing_text:
            return
        # Khi người dùng thay nội dung ô tìm kiếm, lựa chọn trước đó bị bỏ.
        self._selected_code = None
        self._selected_label = ""
        self._populate_results(text)
        self.results.setVisible(self.results.count() > 0)

    def _populate_results(self, keyword=""):
        self.results.clear()
        keyword = (keyword or "").strip().casefold()
        for code, name, is_deleted in self.options:
            if keyword and keyword not in code.casefold() and keyword not in name.casefold():
                continue
            suffix = " (đã xóa mềm)" if is_deleted else ""
            item = QListWidgetItem(f"{code} - {name}{suffix}")
            item.setData(Qt.ItemDataRole.UserRole, code)
            self.results.addItem(item)

    def _select_item(self, item):
        code = item.data(Qt.ItemDataRole.UserRole)
        for option_code, name, is_deleted in self.options:
            if option_code == code:
                suffix = " (đã xóa mềm)" if is_deleted else ""
                self._selected_code = option_code
                self._selected_label = f"{option_code} - {name}{suffix}"
                break

        self._syncing_text = True
        self.search_input.setText(self._selected_label)
        self._syncing_text = False
        self.results.hide()

    def currentData(self):
        return self._selected_code


class SearchableMultiSelect(QWidget):
    """Ô tìm kiếm để chọn nhiều mục; nhấn kết quả để thêm/bỏ chọn."""

    def __init__(self, placeholder="Tìm để chọn...", parent=None):
        super().__init__(parent)
        self.options = []
        self.selected_codes = set()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(placeholder)
        self.search_input.textEdited.connect(self._on_search)

        self.results = QListWidget()
        self.results.setMaximumHeight(115)
        self.results.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.results.itemClicked.connect(self._toggle_item)
        self.results.hide()

        self.selected_label = QLabel("Chưa chọn mục nào")
        self.selected_label.setWordWrap(True)
        self.selected_label.setStyleSheet("color: #AAB7C8; font-size: 11px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.search_input)
        layout.addWidget(self.results)
        layout.addWidget(self.selected_label)

    def set_options(self, options, selected_codes=None):
        """options: iterable (code, name, is_deleted)."""
        self.options = [
            (str(code), str(name or ""), bool(is_deleted))
            for code, name, is_deleted in options
        ]
        valid_codes = {code for code, _, _ in self.options}
        self.selected_codes = {
            str(code) for code in (selected_codes or set())
            if str(code) in valid_codes
        }
        self.search_input.clear()
        self.results.clear()
        self.results.hide()
        self._update_selected_label()

    def _on_search(self, text):
        self._populate_results(text)
        self.results.setVisible(self.results.count() > 0)

    def _populate_results(self, keyword=""):
        self.results.clear()
        keyword = (keyword or "").strip().casefold()
        for code, name, is_deleted in self.options:
            if keyword and keyword not in code.casefold() and keyword not in name.casefold():
                continue
            marker = "✓ " if code in self.selected_codes else ""
            suffix = " (đã xóa mềm)" if is_deleted else ""
            item = QListWidgetItem(f"{marker}{code} - {name}{suffix}")
            item.setData(Qt.ItemDataRole.UserRole, code)
            self.results.addItem(item)

    def _toggle_item(self, item):
        code = str(item.data(Qt.ItemDataRole.UserRole))
        if code in self.selected_codes:
            self.selected_codes.remove(code)
        else:
            self.selected_codes.add(code)
        self._update_selected_label()
        # Giữ kết quả đang tìm để người dùng có thể chọn nhiều mục cùng từ khóa.
        self._populate_results(self.search_input.text())

    def _update_selected_label(self):
        selected_names = [
            f"{code} - {name}"
            for code, name, _ in self.options
            if code in self.selected_codes
        ]
        if selected_names:
            text = f"Đã chọn {len(selected_names)}: " + ", ".join(selected_names)
        else:
            text = "Chưa chọn mục nào"
        self.selected_label.setText(text)
        self.selected_label.setToolTip(text)

    def checked_codes(self):
        # Giữ tên phương thức cũ để không phải sửa phần lưu dữ liệu.
        return [
            code for code, _, _ in self.options
            if code in self.selected_codes
        ]


class ProductDetailDialog(QDialog):
    """Hiển thị chi tiết sản phẩm theo loại sách hoặc sản phẩm khác."""

    def __init__(self, db, product, parent=None, can_edit=False, can_delete=False):
        super().__init__(parent)
        # Hiển thị nút thu nhỏ trên thanh tiêu đề cửa sổ.
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, True)
        self.db = db
        self.product = product
        self.can_edit = can_edit
        self.can_delete = can_delete
        self.setWindowTitle("Chi tiết sản phẩm")
        self.setMinimumWidth(540)
        self.setup_ui()

    def add_info(self, form, label, value):
        value_label = QLabel("" if value is None else str(value))
        value_label.setWordWrap(True)
        form.addRow(label, value_label)

    @staticmethod
    def format_money(value):
        if value is None:
            return ""
        return f"{Decimal(str(value)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def setup_ui(self):
        p = self.product
        layout = QVBoxLayout(self)

        title = QLabel("CHI TIẾT SẢN PHẨM")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        common_group = QGroupBox("Thông tin chung")
        common_form = QFormLayout(common_group)
        self.add_info(common_form, "Mã sản phẩm:", p.get("masp"))
        self.add_info(common_form, "Tên sản phẩm:", p.get("tensp"))
        self.add_info(common_form, "Loại sản phẩm:", p.get("loai"))
        self.add_info(common_form, "Đơn vị tính:", p.get("dvt"))
        self.add_info(common_form, "Giá nhập:", self.format_money(p.get("gianhap")))
        self.add_info(common_form, "Giá bán:", self.format_money(p.get("giaban")))
        self.add_info(common_form, "Số lượng tồn:", p.get("slton"))
        self.add_info(common_form, "VAT (%):", p.get("vat"))
        layout.addWidget(common_group)

        detail_group = QGroupBox(
            "Thông tin sách" if p.get("loai") == "Sách" else "Thông tin sản phẩm khác"
        )
        detail_form = QFormLayout(detail_group)

        cursor = None
        try:
            cursor = self.db.get_connection().cursor()
            if p.get("loai") == "Sách":
                cursor.execute("""
                    SELECT S.ISBN, S.NAMXB, NXB.TENNXB
                    FROM dbo.SACH S
                    LEFT JOIN dbo.NHA_XUAT_BAN NXB ON NXB.MANXB = S.MANXB
                    WHERE S.MASP = ?
                """, p["masp"])
                book = cursor.fetchone()
                if book:
                    self.add_info(detail_form, "ISBN:", book[0])
                    self.add_info(detail_form, "Năm xuất bản:", book[1])
                    self.add_info(detail_form, "Nhà xuất bản:", book[2])

                cursor.execute("""
                    SELECT TG.TENTG
                    FROM dbo.THUOC_TG TTG
                    JOIN dbo.TAC_GIA TG ON TG.MATG = TTG.MATG
                    WHERE TTG.MASP = ?
                    ORDER BY TG.TENTG
                """, p["masp"])
                authors = [row[0] for row in cursor.fetchall()]
                self.add_info(
                    detail_form, "Tác giả:",
                    ", ".join(authors) if authors else "Chưa có thông tin"
                )

                cursor.execute("""
                    SELECT TL.TENTL
                    FROM dbo.THUOC_TL TTL
                    JOIN dbo.THE_LOAI TL ON TL.MATL = TTL.MATL
                    WHERE TTL.MASP = ?
                    ORDER BY TL.TENTL
                """, p["masp"])
                genres = [row[0] for row in cursor.fetchall()]
                self.add_info(
                    detail_form, "Thể loại:",
                    ", ".join(genres) if genres else "Chưa có thông tin"
                )
            else:
                cursor.execute("""
                    SELECT SPK.NGAYSX, TH.TENTH, TH.XUATXU
                    FROM dbo.SAN_PHAM_KHAC SPK
                    LEFT JOIN dbo.THUONG_HIEU TH ON TH.MATH = SPK.MATH
                    WHERE SPK.MASP = ?
                """, p["masp"])
                other = cursor.fetchone()
                if other:
                    self.add_info(detail_form, "Ngày sản xuất:", other[0])
                    self.add_info(detail_form, "Thương hiệu:", other[1])
                    self.add_info(detail_form, "Xuất xứ:", other[2])
        except Exception as e:
            QMessageBox.warning(self, "Không thể tải chi tiết", str(e))
        finally:
            if cursor is not None:
                cursor.close()

        layout.addWidget(detail_group)

        buttons = QHBoxLayout()
        if self.can_edit:
            edit_button = QPushButton("Chỉnh sửa")
            edit_button.clicked.connect(self.open_edit_dialog)
            buttons.addWidget(edit_button)

        if self.can_delete:
            delete_button = QPushButton("Xóa sản phẩm")
            delete_button.setStyleSheet("""
                QPushButton {
                    background-color: #A83232;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 14px;
                }
                QPushButton:hover {
                    background-color: #C94444;
                }
            """)
            delete_button.clicked.connect(self.delete_product)
            buttons.addWidget(delete_button)

        close_button = QPushButton("Đóng")
        close_button.clicked.connect(self.reject)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    def delete_product(self):
        """Ủy quyền cửa sổ danh sách thực hiện xóa mềm sản phẩm này."""
        if not self.can_delete:
            QMessageBox.warning(
                self, "Không có quyền",
                "Tài khoản của bạn không có quyền xóa sản phẩm."
            )
            return

        parent = self.parent()
        if parent is None or not hasattr(parent, "delete_product_by_code"):
            QMessageBox.critical(
                self, "Lỗi",
                "Không thể thực hiện xóa sản phẩm từ cửa sổ hiện tại."
            )
            return

        deleted = parent.delete_product_by_code(
            self.product["masp"],
            self.product.get("tensp")
        )
        if deleted:
            self.accept()

    def open_edit_dialog(self):
        try:
            dialog = ProductFormDialog(
                self.db, self, product_code=self.product["masp"]
            )
            def handle_finished(result):
                # Báo cho cửa sổ danh sách biết dữ liệu đã được cập nhật.
                if result == QDialog.DialogCode.Accepted:
                    self.accept()

            show_minimizable_dialog(self, dialog, handle_finished)
        except Exception as e:
            QMessageBox.critical(
                self, "Lỗi mở chỉnh sửa sản phẩm", str(e)
            )


class ProductFormDialog(QDialog):
    """Form thêm mới hoặc chỉnh sửa sản phẩm."""

    def __init__(self, db, parent=None, product_code=None):
        super().__init__(parent)
        # Hiển thị nút thu nhỏ trên thanh tiêu đề cửa sổ.
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, True)
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


class ProductWindow(QWidget):
    """Trang danh sách sản phẩm, xem chi tiết, thêm và chỉnh sửa sản phẩm."""

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.can_edit_products = False
        self.can_delete_products = False
        self.setObjectName("productPage")
        self.setup_ui()
        self.load_products()
        self.update_permissions()

    @staticmethod
    def format_number(value):
        if value is None:
            return ""
        try:
            return f"{Decimal(str(value)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return str(value)

    def setup_ui(self):
        root = QVBoxLayout(self)

        top = QHBoxLayout()
        title = QLabel("DANH SÁCH SẢN PHẨM")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        top.addWidget(title)
        top.addStretch()

        self.add_button = QPushButton("+ Thêm sản phẩm")
        self.add_button.clicked.connect(self.open_add_dialog)
        top.addWidget(self.add_button)

        refresh_button = QPushButton("Làm mới")
        refresh_button.clicked.connect(self.load_products)
        top.addWidget(refresh_button)
        root.addLayout(top)

        # Thanh tìm kiếm sản phẩm
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Tìm theo mã, tên, ISBN, tác giả, thể loại, NXB hoặc thương hiệu..."
        )
        self.search_input.returnPressed.connect(self.load_products)

        search_button = QPushButton("Tìm kiếm")
        search_button.clicked.connect(self.load_products)

        clear_search_button = QPushButton("Xóa tìm kiếm")
        clear_search_button.clicked.connect(self.clear_search)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_button)
        search_layout.addWidget(clear_search_button)
        root.addLayout(search_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Mã sản phẩm", "Tên sản phẩm", "Loại sản phẩm", "Đơn vị tính",
            "Giá nhập", "Giá bán", "Số lượng tồn", "VAT (%)"
        ])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.cellClicked.connect(self.open_product_detail)
        root.addWidget(self.table)

        bottom = QHBoxLayout()
        self.total_label = QLabel("Tổng số sản phẩm: 0")
        hint = QLabel("Nhấn vào sản phẩm để xem chi tiết và chỉnh sửa.")
        hint.setStyleSheet("color: #AAB7C8; font-size: 11px;")

        self.edit_button = QPushButton("Chỉnh sửa")
        self.edit_button.clicked.connect(self.open_edit_selected_product)

        self.detail_button = QPushButton("Xem chi tiết")
        self.detail_button.clicked.connect(self.open_selected_product_detail)

        bottom.addWidget(self.total_label)
        bottom.addStretch()
        bottom.addWidget(hint)
        bottom.addWidget(self.detail_button)
        bottom.addWidget(self.edit_button)
        root.addLayout(bottom)

    def update_permissions(self):
        """Kiểm tra quyền thực tế cho các bảng liên quan."""
        conn = self.db.get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
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
                        HAS_PERMS_BY_NAME('dbo.SAN_PHAM', 'OBJECT', 'UPDATE') = 1
                        AND HAS_PERMS_BY_NAME('dbo.SACH', 'OBJECT', 'UPDATE') = 1
                        AND HAS_PERMS_BY_NAME('dbo.SAN_PHAM_KHAC', 'OBJECT', 'UPDATE') = 1
                        AND HAS_PERMS_BY_NAME('dbo.THUOC_TG', 'OBJECT', 'DELETE') = 1
                        AND HAS_PERMS_BY_NAME('dbo.THUOC_TG', 'OBJECT', 'INSERT') = 1
                        AND HAS_PERMS_BY_NAME('dbo.THUOC_TL', 'OBJECT', 'DELETE') = 1
                        AND HAS_PERMS_BY_NAME('dbo.THUOC_TL', 'OBJECT', 'INSERT') = 1
                    THEN 1 ELSE 0 END,
                    CASE WHEN
                        HAS_PERMS_BY_NAME('dbo.SAN_PHAM', 'OBJECT', 'UPDATE') = 1
                    THEN 1 ELSE 0 END
            """)
            row = cursor.fetchone()
            self.add_button.setVisible(bool(row[0]))
            self.can_edit_products = bool(row[1])
            self.can_delete_products = bool(row[2])
            self.edit_button.setVisible(self.can_edit_products)
        except Exception:
            is_admin = (self.db.username or "").lower() == "admin"
            self.add_button.setVisible(is_admin)
            self.can_edit_products = is_admin
            self.can_delete_products = is_admin
            self.edit_button.setVisible(self.can_edit_products)
        finally:
            if cursor is not None:
                cursor.close()

    def load_products(self):
        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối database!")
            return

        keyword = self.search_input.text().strip()
        cursor = None
        try:
            cursor = conn.cursor()
            query = """
                SELECT
                    SP.MASP,
                    SP.TENSP,
                    CASE
                        WHEN S.MASP IS NOT NULL THEN N'Sách'
                        WHEN SPK.MASP IS NOT NULL THEN N'Sản phẩm khác'
                        ELSE N'Chưa phân loại'
                    END AS LOAI,
                    SP.DVT,
                    SP.GIANHAP,
                    SP.GIABAN,
                    SP.SLTON,
                    SP.VAT
                FROM dbo.SAN_PHAM SP
                LEFT JOIN dbo.SACH S ON S.MASP = SP.MASP
                LEFT JOIN dbo.SAN_PHAM_KHAC SPK ON SPK.MASP = SP.MASP
                WHERE ISNULL(SP.IS_DELETED, 0) = 0
            """

            if keyword:
                pattern = f"%{keyword}%"
                query += """
                    AND (
                        SP.MASP LIKE ?
                        OR SP.TENSP LIKE ?
                        OR SP.DVT LIKE ?
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
                            LEFT JOIN dbo.NHA_XUAT_BAN NXB
                                ON NXB.MANXB = S2.MANXB
                            WHERE S2.MASP = SP.MASP
                              AND (
                                  S2.ISBN LIKE ?
                                  OR NXB.MANXB LIKE ?
                                  OR NXB.TENNXB LIKE ?
                              )
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
                            LEFT JOIN dbo.THUONG_HIEU TH
                                ON TH.MATH = SPK2.MATH
                            WHERE SPK2.MASP = SP.MASP
                              AND (
                                  TH.MATH LIKE ?
                                  OR TH.TENTH LIKE ?
                                  OR TH.XUATXU LIKE ?
                              )
                        )
                    )
                """
                query += " ORDER BY SP.MASP"
                cursor.execute(
                    query,
                    pattern, pattern, pattern, pattern,
                    pattern, pattern, pattern,
                    pattern, pattern,
                    pattern, pattern,
                    pattern, pattern, pattern
                )
            else:
                query += " ORDER BY SP.MASP"
                cursor.execute(query)

            products = cursor.fetchall()
            self.table.setRowCount(0)

            for row_index, product in enumerate(products):
                self.table.insertRow(row_index)
                values = [
                    product[0], product[1], product[2], product[3],
                    self.format_number(product[4]),
                    self.format_number(product[5]),
                    product[6], self.format_number(product[7])
                ]
                for col_index, value in enumerate(values):
                    item = QTableWidgetItem("" if value is None else str(value))
                    if col_index in (4, 5, 6, 7):
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.table.setItem(row_index, col_index, item)

            self.total_label.setText(f"Tổng số sản phẩm: {len(products)}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tải danh sách sản phẩm!\n{e}")
        finally:
            if cursor is not None:
                cursor.close()

    def clear_search(self):
        self.search_input.clear()
        self.load_products()

    def get_selected_product(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Thông báo", "Vui lòng chọn một sản phẩm!")
            return None
        item = self.table.item(row, 0)
        return item.text() if item else None

    def open_selected_product_detail(self):
        masp = self.get_selected_product()
        if masp:
            self.open_product_detail_by_code(masp)

    def open_product_detail(self, row, column):
        item = self.table.item(row, 0)
        if item:
            self.open_product_detail_by_code(item.text())

    def open_product_detail_by_code(self, masp):
        cursor = None
        try:
            cursor = self.db.get_connection().cursor()
            cursor.execute("""
                SELECT
                    SP.MASP, SP.TENSP,
                    CASE
                        WHEN S.MASP IS NOT NULL THEN N'Sách'
                        WHEN SPK.MASP IS NOT NULL THEN N'Sản phẩm khác'
                        ELSE N'Chưa phân loại'
                    END AS LOAI,
                    SP.DVT, SP.GIANHAP, SP.GIABAN, SP.SLTON, SP.VAT
                FROM dbo.SAN_PHAM SP
                LEFT JOIN dbo.SACH S ON S.MASP = SP.MASP
                LEFT JOIN dbo.SAN_PHAM_KHAC SPK ON SPK.MASP = SP.MASP
                WHERE SP.MASP = ?
                  AND ISNULL(SP.IS_DELETED, 0) = 0
            """, masp)
            row = cursor.fetchone()
            if row is None:
                QMessageBox.warning(self, "Thông báo", "Không tìm thấy sản phẩm!")
                return
            product = {
                "masp": row[0], "tensp": row[1], "loai": row[2],
                "dvt": row[3], "gianhap": row[4], "giaban": row[5],
                "slton": row[6], "vat": row[7]
            }
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lấy chi tiết sản phẩm!\n{e}")
            return
        finally:
            if cursor is not None:
                cursor.close()

        dialog = ProductDetailDialog(
            self.db, product, self,
            can_edit=self.can_edit_products,
            can_delete=self.can_delete_products
        )
        show_minimizable_dialog(
            self,
            dialog,
            lambda result: self.load_products()
            if result == QDialog.DialogCode.Accepted else None
        )

    def delete_product_by_code(self, masp, product_name=None):
        """Xóa mềm sản phẩm theo mã; được gọi từ popup chi tiết."""
        if not self.can_delete_products:
            QMessageBox.warning(
                self, "Không có quyền",
                "Tài khoản của bạn không có quyền xóa sản phẩm."
            )
            return False

        display_name = product_name or masp
        confirm = QMessageBox.warning(
            self,
            "Xác nhận xóa sản phẩm",
            f"Bạn có chắc muốn xóa sản phẩm {masp} - {display_name}?\n\n"
            "Sản phẩm sẽ được đánh dấu xóa mềm (IS_DELETED = 1). "
            "Thông tin sách/sản phẩm khác và lịch sử hóa đơn, phiếu nhập vẫn được giữ.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return False

        cursor = None
        conn = self.db.get_connection()
        try:
            if conn is None:
                raise Exception("Chưa có kết nối database!")

            cursor = conn.cursor()
            cursor.execute("""
                UPDATE dbo.SAN_PHAM
                SET IS_DELETED = 1
                OUTPUT inserted.MASP
                WHERE MASP = ? AND ISNULL(IS_DELETED, 0) = 0
            """, masp)

            if cursor.fetchone() is None:
                raise Exception(
                    "Sản phẩm không tồn tại hoặc đã được xóa trước đó!"
                )

            conn.commit()
            QMessageBox.information(
                self, "Thành công", f"Đã xóa sản phẩm {masp}."
            )
            self.load_products()
            return True

        except Exception as e:
            if conn is not None:
                conn.rollback()
            QMessageBox.critical(
                self, "Lỗi xóa sản phẩm", str(e)
            )
            return False

        finally:
            if cursor is not None:
                cursor.close()

    def open_add_dialog(self):
        dialog = ProductFormDialog(self.db, self)
        show_minimizable_dialog(
            self,
            dialog,
            lambda result: self.load_products()
            if result == QDialog.DialogCode.Accepted else None
        )

    def open_edit_selected_product(self):
        masp = self.get_selected_product()
        if not masp:
            return

        try:
            dialog = ProductFormDialog(
                self.db, self, product_code=masp
            )
            show_minimizable_dialog(
                self,
                dialog,
                lambda result: self.load_products()
                if result == QDialog.DialogCode.Accepted else None
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Lỗi mở chỉnh sửa sản phẩm", str(e)
            )

