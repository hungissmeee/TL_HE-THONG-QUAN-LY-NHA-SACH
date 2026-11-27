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


class ProductWindow(QWidget):
    """Trang tra cứu, thêm mới, xem và chỉnh sửa sản phẩm."""
    """Trang danh sách sản phẩm, xem chi tiết, thêm và chỉnh sửa sản phẩm."""

    def __init__(self, db):
        """Khởi tạo trang sản phẩm, tải dữ liệu và áp dụng quyền của nhân viên."""
        super().__init__()
        self.db = db
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
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Mã sản phẩm", "Tên sản phẩm", "Loại sản phẩm", "Đơn vị tính",
            "Giá nhập", "Giá bán", "Số lượng tồn", "VAT (%)",
            "Mã vạch", "ISBN"
        ])
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
            self.add_button.setVisible(bool(row[0]))
            self.can_edit_products = bool(row[1])
            self.can_delete_products = bool(row[2])
        except Exception:
            is_admin = (self.db.username or "").lower() == "admin"
            self.add_button.setVisible(is_admin)
            self.can_edit_products = is_admin
            self.can_delete_products = is_admin
        finally:
            if cursor is not None:
                cursor.close()

    def load_products(self):
        """Tải danh sách sản phẩm theo từ khóa tìm kiếm."""
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
                    SP.VAT,
                    SP.BARCODE,
                    S.ISBN
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
                        OR SP.BARCODE LIKE ?
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
                    pattern, pattern, pattern, pattern, pattern,
                    pattern, pattern, pattern,
                    pattern, pattern,
                    pattern, pattern,
                    pattern, pattern, pattern
                )
            else:
                query += " ORDER BY SP.MASP"
                cursor.execute(query)

            products = cursor.fetchall()

            pause_table_sorting(self.table)

            self.table.setRowCount(0)

            for row_index, product in enumerate(products):
                self.table.insertRow(row_index)
                values = [
                    product[0], product[1], product[2], product[3],
                    self.format_number(product[4]),
                    self.format_number(product[5]),
                    product[6], self.format_number(product[7]),
                    product[8], product[9]
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
        """Tìm sản phẩm theo mã rồi mở cửa sổ chi tiết."""
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
                    SP.DVT, SP.GIANHAP, SP.GIABAN, SP.SLTON, SP.VAT,
                    SP.BARCODE
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
                "slton": row[6], "vat": row[7], "barcode": row[8]
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
        if dialog.exec():
            self.load_products()

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

            # Khóa dòng sản phẩm trong transaction để không thể phát sinh
            # giao dịch nhập/bán làm thay đổi tồn kho giữa lúc kiểm tra và xóa.
            cursor.execute("""
                SELECT TENSP, ISNULL(SLTON, 0)
                FROM dbo.SAN_PHAM WITH (UPDLOCK, HOLDLOCK)
                WHERE MASP = ?
                  AND ISNULL(IS_DELETED, 0) = 0
            """, masp)
            product_row = cursor.fetchone()

            if product_row is None:
                raise RuntimeError(
                    "Sản phẩm không tồn tại hoặc đã được xóa trước đó!"
                )

            stock_quantity = int(product_row[1] or 0)
            if stock_quantity > 0:
                conn.rollback()
                QMessageBox.warning(
                    self,
                    "Không thể xóa sản phẩm",
                    f"Sản phẩm {masp} - {product_row[0] or display_name} "
                    f"vẫn còn {stock_quantity} sản phẩm trong kho. "
                    "Vui lòng xử lý hết tồn kho trước khi xóa.",
                )
                return False

            cursor.execute("""
                UPDATE dbo.SAN_PHAM
                SET IS_DELETED = 1
                OUTPUT inserted.MASP
                WHERE MASP = ?
                  AND ISNULL(IS_DELETED, 0) = 0
                  AND ISNULL(SLTON, 0) = 0
            """, masp)

            if cursor.fetchone() is None:
                raise RuntimeError(
                    "Không thể xóa sản phẩm. Vui lòng tải lại dữ liệu và thử lại."
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



