"""ProductWindow: thành phần giao diện quản lý sản phẩm."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QHeaderView,
    QMessageBox,
    QAbstractItemView,
)
from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table,
    pause_table_sorting,
    resume_table_sorting,
)
from .chi_tiet import ProductDetailDialog
from .bieu_mau import ProductFormDialog
from ui.formatters import format_product_number
from core.repositories.san_pham_repository import SanPhamRepository, ProductHasStockError
from core.services.san_pham_service import SanPhamService


PRODUCT_TABLE_HEADERS = (
    "Mã sản phẩm", "Tên sản phẩm", "Loại sản phẩm", "Đơn vị tính",
    "Giá nhập", "Giá bán", "Số lượng tồn", "VAT (%)", "Mã vạch",
)


class ProductWindow(QWidget):
    """Trang tra cứu, thêm mới, xem và chỉnh sửa sản phẩm."""

    def __init__(self, db):
        """Khởi tạo trang sản phẩm, tải dữ liệu và áp dụng quyền của nhân viên."""
        super().__init__()
        self.db = db
        self.service = SanPhamService(SanPhamRepository(db))
        self.can_edit_products = False
        self.can_delete_products = False
        self.setObjectName("productPage")
        self.setup_ui()
        # Xác định quyền thao tác trước khi tải dữ liệu trang.
        self.update_permissions()
        self.load_products()

    @staticmethod
    def format_number(value):
        """Định dạng số lượng hoặc đơn giá để hiển thị thống nhất."""
        return format_product_number(value)

    def setup_ui(self):
        """Tạo thanh tìm kiếm, bảng sản phẩm và các nút thao tác."""
        root = QVBoxLayout(self)

        top = QHBoxLayout()
        title = QLabel("DANH SÁCH SẢN PHẨM")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        top.addWidget(title)
        top.addStretch()

        self.add_button = QPushButton("+ Thêm sản phẩm")
        self.add_button.setProperty("buttonRole", "primary")
        self.add_button.setObjectName("primaryButton")
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
            "Tìm theo mã, mã vạch, tên, ISBN, tác giả, thể loại, NXB hoặc thương hiệu..."
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
        self.table.setColumnCount(len(PRODUCT_TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(PRODUCT_TABLE_HEADERS)
        prepare_sortable_table(self.table)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(self.open_product_detail)
        root.addWidget(self.table)

        self.total_label = QLabel("Tổng số sản phẩm: 0")
        root.addWidget(self.total_label)

    def update_permissions(self):
        try:
            permissions = self.service.get_permissions()
            self.add_button.setVisible(permissions['can_add'])
            self.can_edit_products = permissions['can_edit']
            self.can_delete_products = permissions['can_delete']
        except Exception:
            is_admin = (self.db.username or '').lower() == 'admin'
            self.add_button.setVisible(is_admin)
            self.can_edit_products = is_admin
            self.can_delete_products = is_admin

    def load_products(self):
        try:
            products = self.service.list_products(self.search_input.text().strip())
            pause_table_sorting(self.table)
            self.table.setRowCount(0)
            for row_index, product in enumerate(products):
                self.table.insertRow(row_index)
                values = [
                    product['masp'], product['tensp'], product['loai'], product['dvt'],
                    self.format_number(product['gianhap']),
                    self.format_number(product['giaban']),
                    product['slton'], self.format_number(product['vat']), product['barcode']
                ]
                for col_index, value in enumerate(values):
                    item = QTableWidgetItem('' if value is None else str(value))
                    if col_index in (4, 5, 6, 7):
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.table.setItem(row_index, col_index, item)
            self.total_label.setText(f'Tổng số sản phẩm: {len(products)}')
        except Exception as error:
            QMessageBox.critical(self, 'Lỗi', f'Không thể tải danh sách sản phẩm!\\n{error}')
        finally:
            resume_table_sorting(self.table)

    def clear_search(self):
        """Xóa từ khóa và tải lại toàn bộ sản phẩm."""
        self.search_input.clear()
        self.load_products()

    def get_selected_product(self):
        """Lấy mã và dữ liệu sản phẩm đang được chọn trong bảng."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Thông báo", "Vui lòng chọn một sản phẩm!")
            return None
        item = self.table.item(row, 0)
        return item.text() if item else None

    def open_selected_product_detail(self):
        """Mở chi tiết sản phẩm đang được chọn."""
        masp = self.get_selected_product()
        if masp:
            self.open_product_detail_by_code(masp)

    def open_product_detail(self, row, column):
        """Hiển thị thông tin chi tiết sản phẩm và các thao tác được phép."""
        item = self.table.item(row, 0)
        if item:
            self.open_product_detail_by_code(item.text())

    def open_product_detail_by_code(self, masp):
        try:
            product = self.service.get_product_detail(masp)
            if product is None:
                QMessageBox.warning(self, 'Thông báo', 'Không tìm thấy sản phẩm!')
                return
        except Exception as error:
            QMessageBox.critical(self, 'Lỗi', f'Không thể lấy chi tiết sản phẩm!\\n{error}')
            return
        dialog = ProductDetailDialog(
            self.db, product, self,
            can_edit=self.can_edit_products,
            can_delete=self.can_delete_products
        )
        if dialog.exec():
            self.load_products()

    def delete_product_by_code(self, masp, product_name=None):
        if not self.can_delete_products:
            QMessageBox.warning(self, 'Không có quyền', 'Tài khoản của bạn không có quyền xóa sản phẩm.')
            return False
        display_name = product_name or masp
        answer = QMessageBox.warning(
            self, 'Xác nhận xóa sản phẩm',
            f'Bạn có chắc muốn xóa sản phẩm {masp} - {display_name}?\\n\\nSản phẩm sẽ được đánh dấu xóa mềm.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False
        try:
            self.service.soft_delete_product(masp)
            QMessageBox.information(self, 'Thành công', f'Đã xóa sản phẩm {masp}.')
            self.load_products()
            return True
        except ProductHasStockError as error:
            QMessageBox.warning(self, 'Không thể xóa sản phẩm', str(error))
            return False
        except Exception as error:
            QMessageBox.critical(self, 'Lỗi xóa sản phẩm', str(error))
            return False


    def open_add_dialog(self):
        """Mở biểu mẫu thêm sản phẩm mới."""
        dialog = ProductFormDialog(self.db, self)
        if dialog.exec():
            self.load_products()

    def open_edit_selected_product(self):
        """Mở biểu mẫu chỉnh sửa sản phẩm đang được chọn."""
        masp = self.get_selected_product()
        if not masp:
            return

        try:
            dialog = ProductFormDialog(
                self.db, self, product_code=masp
            )
            if dialog.exec():
                self.load_products()
        except Exception as e:
            QMessageBox.critical(
                self, "Lỗi mở chỉnh sửa sản phẩm", str(e)
            )



