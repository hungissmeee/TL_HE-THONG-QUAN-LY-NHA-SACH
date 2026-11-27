"""ProductFormDialog: thành phần giao diện quản lý sản phẩm."""

from decimal import (
    Decimal,
    InvalidOperation,
)
from PySide6.QtCore import (
    Qt,
    QDate,
    QLocale,
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
    QFrame,
    QScrollArea,
)
from .bo_chon import SearchableSingleSelect, SearchableMultiSelect
from core.san_pham.repository import SanPhamRepository
from core.san_pham.service import SanPhamService


class ProductFormDialog(QDialog):
    """Biểu mẫu nhập và kiểm tra thông tin khi thêm mới hoặc chỉnh sửa sản phẩm."""
    """Form thêm mới hoặc chỉnh sửa sản phẩm."""

    def __init__(self, db, parent=None, product_code=None):
        """Khởi tạo biểu mẫu sản phẩm và chọn chế độ thêm mới hoặc chỉnh sửa."""
        super().__init__(parent)
        self.db = db
        self.service = SanPhamService(SanPhamRepository(db))
        self.product_code = product_code
        self.is_edit = product_code is not None
        self.existing = None

        self.setWindowTitle("Chỉnh sửa sản phẩm" if self.is_edit else "Thêm sản phẩm mới")
        self.setMinimumSize(580, 480)
        self.resize(640, 720)

        if self.is_edit:
            self.load_existing_product()

        self.setup_ui()
        self.load_lookup_data()

        if self.is_edit:
            self.populate_form()
        else:
            self.refresh_product_code_preview()

    def refresh_product_code_preview(self):
        try:
            self.masp.setText(self.service.preview_next_product_code())
        except Exception as error:
            self.masp.setText('Không tạo được mã')
            QMessageBox.warning(self, 'Không thể tạo mã sản phẩm', str(error))

    def load_existing_product(self):
        self.existing = self.service.get_product_for_edit(self.product_code)
        self.selected_author_codes = set(self.existing.get('selected_author_codes', set()))
        self.selected_genre_codes = set(self.existing.get('selected_genre_codes', set()))

    def setup_ui(self):
        """Tạo các trường thông tin chung và trường riêng theo loại sản phẩm."""
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # Cuộn phần trường nhập khi form dài; nút thao tác luôn ở cuối hộp thoại.
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        form_content = QWidget()
        content_layout = QVBoxLayout(form_content)
        content_layout.setContentsMargins(4, 4, 4, 4)
        content_layout.setSpacing(9)

        title = QLabel("CHỈNH SỬA SẢN PHẨM" if self.is_edit else "THÊM SẢN PHẨM MỚI")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        content_layout.addWidget(title)

        self.type_combo = QComboBox()
        self.type_combo.addItem("Sách", "book")
        self.type_combo.addItem("Sản phẩm khác", "other")
        content_layout.addWidget(QLabel("Loại sản phẩm:"))
        content_layout.addWidget(self.type_combo)

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

        self.barcode = QLineEdit()
        self.barcode.setMaxLength(50)
        self.barcode.setPlaceholderText("Quét hoặc nhập mã vạch (không bắt buộc)")

        self.dvt = QLineEdit()
        self.dvt.setMaxLength(30)
        self.dvt.setPlaceholderText("Ví dụ: Quyển, Cái, Chiếc")

        self.gianhap = QLineEdit("0.00")
        self.gianhap.setReadOnly(True)
        self.gianhap.setToolTip(
            "Giá nhập được hệ thống tính tự động từ các phiếu nhập."
        )

        # Các ô tiền dùng dấu chấm làm dấu thập phân, không diễn giải
        # dấu chấm thành dấu phân tách hàng nghìn theo locale Windows.
        number_locale = QLocale.c()
        number_locale.setNumberOptions(
            number_locale.numberOptions()
            | QLocale.NumberOption.RejectGroupSeparator
        )

        self.giaban = QLineEdit()
        self.giaban.setPlaceholderText("0.00")
        price_validator = QDoubleValidator(
            0, 9999999999999.99, 2, self
        )
        price_validator.setLocale(number_locale)
        price_validator.setNotation(
            QDoubleValidator.Notation.StandardNotation
        )
        self.giaban.setValidator(price_validator)

        self.slton = QLineEdit("0")
        self.slton.setReadOnly(True)
        self.slton.setToolTip(
            "Tồn kho được hệ thống cập nhật tự động từ phiếu nhập, hóa đơn và đổi trả."
        )

        self.vat = QLineEdit("0")
        vat_validator = QDoubleValidator(0, 100, 2, self)
        vat_validator.setLocale(number_locale)
        vat_validator.setNotation(
            QDoubleValidator.Notation.StandardNotation
        )
        self.vat.setValidator(vat_validator)

        common_form.addRow("Mã sản phẩm:", self.masp)
        common_form.addRow("Tên sản phẩm:", self.tensp)
        common_form.addRow("Mã vạch:", self.barcode)
        common_form.addRow("Đơn vị tính:", self.dvt)
        common_form.addRow("Giá nhập (tự động):", self.gianhap)
        common_form.addRow("Giá bán:", self.giaban)
        common_form.addRow("Số lượng tồn (tự động):", self.slton)
        common_form.addRow("VAT (%):", self.vat)

        inventory_note = QLabel(
            "Giá nhập bình quân và số lượng tồn không chỉnh sửa tại biểu mẫu "
            "sản phẩm. Hệ thống tự cập nhật khi lập/hủy phiếu nhập, hóa đơn "
            "và xử lý đổi trả."
        )
        inventory_note.setWordWrap(True)
        inventory_note.setStyleSheet("color: #AAB7C8; font-size: 11px;")
        common_form.addRow("", inventory_note)
        content_layout.addWidget(common_group)

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

        content_layout.addWidget(self.type_stack)
        self.type_combo.currentIndexChanged.connect(self.type_stack.setCurrentIndex)

        scroll_area.setWidget(form_content)
        root.addWidget(scroll_area, 1)

        buttons = QHBoxLayout()
        save_button = QPushButton("Lưu thay đổi" if self.is_edit else "Thêm sản phẩm")
        save_button.setProperty("buttonRole", "primary")
        save_button.setObjectName("primaryButton")
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

    def load_lookup_data(self):
        selected_publisher = self.existing.get('manxb') if self.is_edit and self.existing['loai'] == 'Sách' else None
        selected_brand = self.existing.get('math') if self.is_edit and self.existing['loai'] == 'Sản phẩm khác' else None
        data = self.service.get_lookup_data(
            selected_publisher=selected_publisher, selected_brand=selected_brand,
            selected_authors=self.selected_author_codes if self.is_edit else set(),
            selected_genres=self.selected_genre_codes if self.is_edit else set(),
        )
        self.publisher_combo.set_options(data['publishers'], selected_publisher)
        self.authors_list.set_options(data['authors'], self.selected_author_codes if self.is_edit else set())
        self.genres_list.set_options(data['genres'], self.selected_genre_codes if self.is_edit else set())
        self.brand_combo.set_options(data['brands'], selected_brand)

    def populate_form(self):
        """Đưa dữ liệu sản phẩm hiện có lên các trường nhập."""
        p = self.existing
        self.masp.setText(str(p["masp"]))
        self.tensp.setText(p["tensp"] or "")
        self.barcode.setText(p.get("barcode") or "")
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
        """Kiểm tra và chuyển nội dung số thành Decimal để tính tiền chính xác."""
        try:
            result = Decimal(value.strip().replace(",", "."))
        except (InvalidOperation, AttributeError):
            raise ValueError(f"{field_name} phải là số hợp lệ!")
        if result < 0:
            raise ValueError(f"{field_name} không được âm!")
        return result

    def save_product(self):
        tensp = self.tensp.text().strip()
        dvt = self.dvt.text().strip()
        if not tensp or not dvt:
            QMessageBox.warning(self, 'Thiếu thông tin', 'Vui lòng nhập tên sản phẩm và đơn vị tính.')
            return
        if not self.giaban.text().strip():
            QMessageBox.warning(self, 'Thiếu thông tin', 'Vui lòng nhập giá bán.')
            self.giaban.setFocus()
            return
        try:
            giaban = self.parse_decimal(self.giaban.text(), 'Giá bán')
            vat = self.parse_decimal(self.vat.text() or '0', 'VAT')
            namxb_text = self.namxb.text().strip()
            namxb = int(namxb_text) if namxb_text else None
        except (ValueError, InvalidOperation) as error:
            QMessageBox.warning(self, 'Dữ liệu không hợp lệ', str(error))
            return
        product_type = self.type_combo.currentData()
        if product_type == 'book' and self.publisher_combo.currentData() is None:
            QMessageBox.warning(self, 'Thiếu thông tin', 'Vui lòng chọn nhà xuất bản.')
            return
        if product_type == 'other' and self.brand_combo.currentData() is None:
            QMessageBox.warning(self, 'Thiếu thông tin', 'Vui lòng chọn thương hiệu.')
            return
        payload = {
            'tensp': tensp, 'dvt': dvt, 'giaban': giaban, 'vat': vat,
            'barcode': self.barcode.text().strip() or None,
            'product_type': product_type,
            'isbn': self.isbn.text().strip() or None, 'namxb': namxb,
            'manxb': self.publisher_combo.currentData(),
            'authors': self.authors_list.checked_codes(),
            'genres': self.genres_list.checked_codes(),
            'ngaysx': self.ngaysx.date().toPython(),
            'math': self.brand_combo.currentData(),
        }
        try:
            code = self.service.save_product(payload, product_code=self.product_code)
            self.masp.setText(code)
            message = f'Đã cập nhật sản phẩm {code} thành công!' if self.is_edit else f'Đã thêm sản phẩm thành công!\nMã sản phẩm: {code}'
            QMessageBox.information(self, 'Thành công', message)
            self.accept()
        except Exception as error:
            QMessageBox.critical(
                self, 'Lỗi cập nhật sản phẩm' if self.is_edit else 'Lỗi thêm sản phẩm',
                str(error)
            )
