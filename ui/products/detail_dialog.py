"""ProductDetailDialog: thành phần giao diện quản lý sản phẩm."""

from decimal import Decimal, InvalidOperation
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import (
    QWidget, QDialog, QLabel, QLineEdit, QPushButton, QComboBox,
    QVBoxLayout, QHBoxLayout, QFormLayout, QTableWidget,
    QHeaderView, QAbstractItemView, QMessageBox, QSpinBox, QStackedWidget,
    QDoubleSpinBox, QGroupBox, QDateEdit, QCheckBox,
    QListWidget, QListWidgetItem, QCompleter, QFrame,
)
from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table,
    pause_table_sorting,
    resume_table_sorting,
)
from .form_dialog import ProductFormDialog


class ProductDetailDialog(QDialog):
    """Hiển thị chi tiết sản phẩm theo loại sách hoặc sản phẩm khác."""

    def __init__(self, db, product, parent=None, can_edit=False, can_delete=False):
        super().__init__(parent)
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
            if dialog.exec():
                # Báo cho cửa sổ danh sách biết dữ liệu đã được cập nhật.
                self.accept()
        except Exception as e:
            QMessageBox.critical(
                self, "Lỗi mở chỉnh sửa sản phẩm", str(e)
            )


