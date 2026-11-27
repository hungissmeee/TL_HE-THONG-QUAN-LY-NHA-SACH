"""ProductDetailDialog: thành phần giao diện quản lý sản phẩm."""

from decimal import Decimal
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QMessageBox,
    QGroupBox,
)
from .bieu_mau import ProductFormDialog
from core.san_pham.truy_van_sql import SanPhamRepository
from core.san_pham.xu_ly_du_lieu import SanPhamService


class ProductDetailDialog(QDialog):
    """Hiển thị thông tin chi tiết sản phẩm và các thao tác chỉnh sửa được cấp quyền."""
    """Hiển thị chi tiết sản phẩm theo loại sách hoặc sản phẩm khác."""

    def __init__(self, db, product, parent=None, can_edit=False, can_delete=False):
        """Khởi tạo hộp thoại chi tiết và xác định các thao tác được phép."""
        super().__init__(parent)
        self.db = db
        self.service = SanPhamService(SanPhamRepository(db))
        self.product = product
        self.can_edit = can_edit
        self.can_delete = can_delete
        self.setWindowTitle("Chi tiết sản phẩm")
        self.setMinimumWidth(540)
        self.setup_ui()

    def add_info(self, form, label, value):
        """Thêm một dòng nhãn và giá trị vào biểu mẫu thông tin."""
        value_label = QLabel("" if value is None else str(value))
        value_label.setWordWrap(True)
        form.addRow(label, value_label)

    @staticmethod
    def format_money(value):
        """Định dạng giá trị tiền để hiển thị."""
        if value is None:
            return ""
        return f"{Decimal(str(value)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def setup_ui(self):
        """Tạo các nhóm thông tin chung và thông tin riêng của sản phẩm."""
        p = self.product
        layout = QVBoxLayout(self)

        title = QLabel("CHI TIẾT SẢN PHẨM")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        common_group = QGroupBox("Thông tin chung")
        common_form = QFormLayout(common_group)
        self.add_info(common_form, "Mã sản phẩm:", p.get("masp"))
        self.add_info(common_form, "Mã vạch:", p.get("barcode") or "Chưa có")
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

        try:
            detail = self.service.get_product_detail(p['masp']) or {}
            if p.get('loai') == 'Sách':
                self.add_info(detail_form, 'ISBN:', detail.get('isbn'))
                self.add_info(detail_form, 'Năm xuất bản:', detail.get('namxb'))
                self.add_info(detail_form, 'Nhà xuất bản:', detail.get('ten_nxb'))
                authors = detail.get('authors') or []
                genres = detail.get('genres') or []
                self.add_info(detail_form, 'Tác giả:', ', '.join(authors) if authors else 'Chưa có thông tin')
                self.add_info(detail_form, 'Thể loại:', ', '.join(genres) if genres else 'Chưa có thông tin')
            else:
                self.add_info(detail_form, 'Ngày sản xuất:', detail.get('ngaysx'))
                self.add_info(detail_form, 'Thương hiệu:', detail.get('brand_name'))
                self.add_info(detail_form, 'Xuất xứ:', detail.get('brand_origin'))
        except Exception as error:
            QMessageBox.warning(self, 'Không thể tải chi tiết', str(error))
        layout.addWidget(detail_group)

        buttons = QHBoxLayout()
        if self.can_edit:
            edit_button = QPushButton("Chỉnh sửa")
            edit_button.clicked.connect(self.open_edit_dialog)
            buttons.addWidget(edit_button)

        if self.can_delete:
            delete_button = QPushButton("Xóa sản phẩm")
            delete_button.setObjectName("dangerButton")
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
        """Mở biểu mẫu chỉnh sửa sản phẩm hiện tại."""
        try:
            dialog = ProductFormDialog(
                self.db, self, product_code=self.product["masp"]
            )
            if dialog.exec():
                # Báo cho cửa sổ danh sách biết dữ liệu đã được cập nhật.
                self.accept()
        except Exception as e:
            QMessageBox.critical(
                self, "Lỗi mở chỉnh sửa sản phẩm", str(e)
            )



