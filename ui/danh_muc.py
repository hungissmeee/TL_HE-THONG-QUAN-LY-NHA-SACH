"""Trang quản lý các danh mục dùng chung của sản phẩm."""

from PySide6.QtWidgets import (
    QWidget, QDialog, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QTableWidget, QHeaderView,
    QMessageBox, QAbstractItemView
)
from PySide6.QtCore import Qt

from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table,
    pause_table_sorting,
    resume_table_sorting
)


# Cấu hình cố định theo cấu trúc CSDL CSDLQLNHASACH.
# Tên bảng và tên cột không lấy từ dữ liệu người dùng nhập.
CATALOGS = {
    "authors": {
        "title": "QUẢN LÝ TÁC GIẢ",
        "table": "TAC_GIA",
        "id_column": "MATG",
        "code_prefix": "TG",
        "search_columns": ["MATG", "TENTG"],
        "select_sql": "SELECT MATG, TENTG FROM dbo.TAC_GIA WHERE ISNULL(IS_DELETED, 0) = 0 ORDER BY MATG",
        "insert_sql": "INSERT INTO dbo.TAC_GIA (MATG, TENTG, IS_DELETED) VALUES (?, ?, 0)",
        "update_sql": "UPDATE dbo.TAC_GIA SET TENTG = ? WHERE MATG = ? AND ISNULL(IS_DELETED, 0) = 0",
        "delete_sql": "UPDATE dbo.TAC_GIA SET IS_DELETED = 1 WHERE MATG = ? AND ISNULL(IS_DELETED, 0) = 0",
        "headers": ["Mã tác giả", "Tên tác giả"],
        "fields": [
            ("MATG", "Mã tác giả:", "Ví dụ: TG001", 20, True),
            ("TENTG", "Tên tác giả:", "Nhập tên tác giả", 100, True),
        ],
    },
    "genres": {
        "title": "QUẢN LÝ THỂ LOẠI",
        "table": "THE_LOAI",
        "id_column": "MATL",
        "code_prefix": "TL",
        "search_columns": ["MATL", "TENTL"],
        "select_sql": "SELECT MATL, TENTL FROM dbo.THE_LOAI WHERE ISNULL(IS_DELETED, 0) = 0 ORDER BY MATL",
        "insert_sql": "INSERT INTO dbo.THE_LOAI (MATL, TENTL, IS_DELETED) VALUES (?, ?, 0)",
        "update_sql": "UPDATE dbo.THE_LOAI SET TENTL = ? WHERE MATL = ? AND ISNULL(IS_DELETED, 0) = 0",
        "delete_sql": "UPDATE dbo.THE_LOAI SET IS_DELETED = 1 WHERE MATL = ? AND ISNULL(IS_DELETED, 0) = 0",
        "headers": ["Mã thể loại", "Tên thể loại"],
        "fields": [
            ("MATL", "Mã thể loại:", "Ví dụ: TL001", 20, True),
            ("TENTL", "Tên thể loại:", "Nhập tên thể loại", 100, True),
        ],
    },
    "publishers": {
        "title": "QUẢN LÝ NHÀ XUẤT BẢN",
        "table": "NHA_XUAT_BAN",
        "id_column": "MANXB",
        "code_prefix": "NXB",
        "search_columns": ["MANXB", "TENNXB", "DIACHI"],
        "select_sql": "SELECT MANXB, TENNXB, DIACHI FROM dbo.NHA_XUAT_BAN WHERE ISNULL(IS_DELETED, 0) = 0 ORDER BY MANXB",
        "insert_sql": "INSERT INTO dbo.NHA_XUAT_BAN (MANXB, TENNXB, DIACHI, IS_DELETED) VALUES (?, ?, ?, 0)",
        "update_sql": "UPDATE dbo.NHA_XUAT_BAN SET TENNXB = ?, DIACHI = ? WHERE MANXB = ? AND ISNULL(IS_DELETED, 0) = 0",
        "delete_sql": "UPDATE dbo.NHA_XUAT_BAN SET IS_DELETED = 1 WHERE MANXB = ? AND ISNULL(IS_DELETED, 0) = 0",
        "headers": ["Mã NXB", "Tên nhà xuất bản", "Địa chỉ"],
        "fields": [
            ("MANXB", "Mã nhà xuất bản:", "Ví dụ: NXB001", 20, True),
            ("TENNXB", "Tên nhà xuất bản:", "Nhập tên nhà xuất bản", 100, True),
            ("DIACHI", "Địa chỉ:", "Nhập địa chỉ (không bắt buộc)", 255, False),
        ],
    },
    "brands": {
        "title": "QUẢN LÝ THƯƠNG HIỆU",
        "table": "THUONG_HIEU",
        "id_column": "MATH",
        "code_prefix": "TH",
        "search_columns": ["MATH", "TENTH", "XUATXU"],
        "select_sql": "SELECT MATH, TENTH, XUATXU FROM dbo.THUONG_HIEU WHERE ISNULL(IS_DELETED, 0) = 0 ORDER BY MATH",
        "insert_sql": "INSERT INTO dbo.THUONG_HIEU (MATH, TENTH, XUATXU, IS_DELETED) VALUES (?, ?, ?, 0)",
        "update_sql": "UPDATE dbo.THUONG_HIEU SET TENTH = ?, XUATXU = ? WHERE MATH = ? AND ISNULL(IS_DELETED, 0) = 0",
        "delete_sql": "UPDATE dbo.THUONG_HIEU SET IS_DELETED = 1 WHERE MATH = ? AND ISNULL(IS_DELETED, 0) = 0",
        "headers": ["Mã thương hiệu", "Tên thương hiệu", "Xuất xứ"],
        "fields": [
            ("MATH", "Mã thương hiệu:", "Ví dụ: TH001", 20, True),
            ("TENTH", "Tên thương hiệu:", "Nhập tên thương hiệu", 100, True),
            ("XUATXU", "Xuất xứ:", "Nhập xuất xứ (không bắt buộc)", 100, False),
        ],
    },
}


class CatalogCreateDialog(QDialog):
    """Popup thêm mới danh mục, thay cho form cố định trên trang danh sách."""

    def __init__(self, config, code_preview="", parent=None):
        super().__init__(parent)
        self.config = config
        self.inputs = {}
        self.insert_values = None

        self.setWindowTitle("Thêm danh mục")
        self.setMinimumWidth(460)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        heading = QLabel("THÊM DANH MỤC MỚI")
        heading.setStyleSheet("font-size: 18px; font-weight: bold;")
        root.addWidget(heading)

        group = QGroupBox("Thông tin danh mục")
        form = QFormLayout(group)
        form.setSpacing(10)

        for column, label_text, placeholder, max_length, _required in config["fields"]:
            edit = QLineEdit()
            edit.setMaxLength(max_length)
            edit.setPlaceholderText(placeholder)
            if column == config["id_column"]:
                edit.setReadOnly(True)
                edit.setText(code_preview or "")
                edit.setPlaceholderText("Mã sẽ được tạo tự động khi lưu")
            self.inputs[column] = edit
            form.addRow(label_text, edit)

        root.addWidget(group)

        actions = QHBoxLayout()
        actions.addStretch()

        cancel_button = QPushButton("Hủy")
        cancel_button.clicked.connect(self.reject)

        add_button = QPushButton("Thêm mới")
        add_button.setProperty("buttonRole", "primary")
        add_button.setObjectName("primaryButton")
        add_button.clicked.connect(self._save)

        actions.addWidget(cancel_button)
        actions.addWidget(add_button)
        root.addLayout(actions)

    def get_insert_values(self):
        """Kiểm tra trường bắt buộc và trả dữ liệu theo thứ tự INSERT."""
        values = []
        missing_fields = []

        for column, label_text, _placeholder, _max_length, required in self.config["fields"]:
            value = self.inputs[column].text().strip()
            if required and column != self.config["id_column"] and not value:
                missing_fields.append(label_text.replace(":", ""))
            values.append(value if value else None)

        if missing_fields:
            QMessageBox.warning(
                self,
                "Thiếu thông tin",
                "Vui lòng nhập: " + ", ".join(missing_fields),
            )
            return None

        return values

    def _save(self):
        """Chỉ đóng popup khi dữ liệu bắt buộc đã được nhập."""
        values = self.get_insert_values()
        if values is not None:
            self.insert_values = values
            self.accept()


class CatalogEditDialog(QDialog):
    """Biểu mẫu popup dùng để chỉnh sửa một bản ghi danh mục."""

    def __init__(self, config, values, parent=None):
        super().__init__(parent)
        self.config = config
        self.inputs = {}
        self.setWindowTitle("Chỉnh sửa danh mục")
        self.setMinimumWidth(460)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        heading = QLabel("CHỈNH SỬA THÔNG TIN")
        heading.setStyleSheet("font-size: 18px; font-weight: bold;")
        root.addWidget(heading)

        group = QGroupBox("Thông tin danh mục")
        form = QFormLayout(group)
        form.setSpacing(10)

        for column, label_text, placeholder, max_length, required in config["fields"]:
            edit = QLineEdit()
            edit.setMaxLength(max_length)
            edit.setPlaceholderText(placeholder)
            edit.setText(str(values.get(column) or ""))
            if column == config["id_column"]:
                edit.setReadOnly(True)
            self.inputs[column] = edit
            form.addRow(label_text, edit)

        root.addWidget(group)
        actions = QHBoxLayout()
        actions.addStretch()

        cancel_button = QPushButton("Hủy")
        cancel_button.clicked.connect(self.reject)
        save_button = QPushButton("Lưu thay đổi")
        save_button.clicked.connect(self._save)

        actions.addWidget(cancel_button)
        actions.addWidget(save_button)
        root.addLayout(actions)

    def get_update_values(self):
        """Trả về các giá trị theo đúng thứ tự update_sql đang sử dụng."""
        values = []
        missing_fields = []
        for column, label_text, _placeholder, _max_length, required in self.config["fields"]:
            if column == self.config["id_column"]:
                continue
            value = self.inputs[column].text().strip()
            if required and not value:
                missing_fields.append(label_text.replace(":", ""))
            values.append(value if value else None)

        if missing_fields:
            QMessageBox.warning(
                self,
                "Thiếu thông tin",
                "Vui lòng nhập: " + ", ".join(missing_fields),
            )
            return None
        return values

    def _save(self):
        """Chỉ đóng popup khi các trường bắt buộc đã hợp lệ."""
        if self.get_update_values() is not None:
            self.accept()


class CatalogDetailDialog(QDialog):
    """Popup chi tiết chứa toàn bộ thao tác sửa và xóa mềm danh mục."""

    def __init__(self, title, values, on_edit, on_delete, parent=None):
        super().__init__(parent)
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.setWindowTitle(f"Chi tiết - {title}")
        self.setMinimumWidth(460)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        heading = QLabel(title)
        heading.setStyleSheet("font-size: 18px; font-weight: bold;")
        root.addWidget(heading)

        group = QGroupBox("Thông tin bản ghi")
        form = QFormLayout(group)
        for label, value in values:
            value_label = QLabel("" if value is None else str(value))
            value_label.setWordWrap(True)
            form.addRow(label, value_label)
        root.addWidget(group)

        actions = QHBoxLayout()
        edit_button = QPushButton("Chỉnh sửa")
        edit_button.clicked.connect(self._edit)
        actions.addWidget(edit_button)

        delete_button = QPushButton("Xóa mềm")
        delete_button.setObjectName("dangerButton")
        delete_button.clicked.connect(self._delete)
        actions.addWidget(delete_button)

        actions.addStretch()
        close_button = QPushButton("Đóng")
        close_button.clicked.connect(self.reject)
        actions.addWidget(close_button)
        root.addLayout(actions)

    def _edit(self):
        """Đóng popup chi tiết rồi mở popup chỉnh sửa."""
        self.accept()
        self.on_edit()

    def _delete(self):
        """Đóng popup chi tiết rồi xác nhận xóa mềm."""
        self.accept()
        self.on_delete()


class CatalogPage(QWidget):
    """Trang danh mục dùng chung cho Tác giả, Thể loại, Nhà xuất bản và Thương hiệu."""

    def __init__(self, db, catalog_type):
        """Khởi tạo trang danh mục theo cấu hình loại danh mục được truyền vào."""
        super().__init__()

        if catalog_type not in CATALOGS:
            raise ValueError(f"Loại danh mục không hợp lệ: {catalog_type}")

        self.db = db
        self.catalog_type = catalog_type
        self.config = CATALOGS[catalog_type]
        self.loaded = False

        self.setup_ui()

    def setup_ui(self):
        """Tạo form, bảng danh mục, bộ lọc tìm kiếm và các nút thao tác."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel(self.config["title"])
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        top.addWidget(title)
        top.addStretch()

        self.add_button = QPushButton("+ Thêm mới")
        self.add_button.setProperty("buttonRole", "primary")
        self.add_button.setObjectName("primaryButton")
        self.add_button.clicked.connect(self.open_add_dialog)
        top.addWidget(self.add_button)

        self.refresh_button = QPushButton("Làm mới")
        self.refresh_button.clicked.connect(self.load_data)
        top.addWidget(self.refresh_button)
        layout.addLayout(top)

        description = QLabel(
            "Nhấp đúp vào một dòng để xem chi tiết và thực hiện chỉnh sửa hoặc xóa."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #AAB7C8; font-size: 11px;")
        layout.addWidget(description)

        # Thanh tìm kiếm dùng chung bố cục với Sản phẩm và Khuyến mãi.
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Tìm theo mã, tên hoặc thông tin liên quan..."
        )
        self.search_input.returnPressed.connect(self.load_data)

        self.search_button = QPushButton("Tìm kiếm")
        self.search_button.clicked.connect(self.load_data)

        self.clear_search_button = QPushButton("Xóa tìm kiếm")
        self.clear_search_button.clicked.connect(self.clear_search)

        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.clear_search_button)
        layout.addLayout(search_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.config["headers"]))
        self.table.setHorizontalHeaderLabels(self.config["headers"])

        prepare_sortable_table(self.table)

        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        # Nhấp đúp để mở popup chi tiết; thao tác sửa/xóa nằm trong popup.
        self.table.cellDoubleClicked.connect(
            self.open_selected_record_detail
        )

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        if len(self.config["headers"]) > 1:
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        if self.catalog_type in ("publishers", "brands"):
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.table)

        self.total_label = QLabel("Tổng số: 0")
        layout.addWidget(self.total_label)

    def _next_code(self, cursor, lock_table=False):
        """Sinh mã kế tiếp; tính cả bản ghi đã xóa mềm.

        Khi thêm mới, TABLOCKX + HOLDLOCK giữ khóa bảng đến khi transaction
        INSERT được commit, tránh hai phiên đồng thời sinh cùng một mã.
        """
        table = self.config["table"]
        id_column = self.config["id_column"]
        prefix = self.config["code_prefix"]
        prefix_len = len(prefix)
        table_hint = " WITH (TABLOCKX, HOLDLOCK)" if lock_table else ""

        # Tên bảng/cột/prefix lấy từ cấu hình cố định trong source code.
        sql = f"""
            SELECT COALESCE(
                MAX(TRY_CONVERT(BIGINT, SUBSTRING({id_column}, {prefix_len + 1}, 20))),
                0
            )
            FROM dbo.{table}{table_hint}
            WHERE UPPER(LEFT({id_column}, {prefix_len})) = ?
              AND TRY_CONVERT(BIGINT, SUBSTRING({id_column}, {prefix_len + 1}, 20)) IS NOT NULL
        """
        cursor.execute(sql, prefix)
        last_number = cursor.fetchone()[0] or 0
        next_number = int(last_number) + 1
        code = f"{prefix}{next_number:03d}"

        if len(code) > 20:
            raise ValueError(f"Mã {self.config['id_column']} vượt quá 20 ký tự.")

        return code

    def preview_next_code(self):
        """Lấy mã dự kiến để hiển thị trong popup; mã thật vẫn được sinh lại khi lưu."""
        conn = self.db.get_connection()
        if conn is None:
            return ""

        cursor = None
        try:
            cursor = conn.cursor()
            code = self._next_code(cursor, lock_table=False)
            conn.commit()
            return code
        except Exception as error:
            conn.rollback()
            QMessageBox.warning(
                self,
                "Không thể tạo mã tự động",
                f"Không lấy được mã cho {self.config['table']}.\n{error}",
            )
            return ""
        finally:
            if cursor is not None:
                cursor.close()

    def load_data(self):
        """Tải danh sách, có thể lọc theo mã/tên/thông tin của danh mục."""
        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối database!")
            return

        cursor = None
        try:
            cursor = conn.cursor()
            keyword = self.search_input.text().strip()

            # select_sql đã có điều kiện IS_DELETED = 0 và ORDER BY.
            # Tách phần ORDER BY để bổ sung điều kiện tìm kiếm an toàn.
            base_sql, order_by = self.config["select_sql"].rsplit(" ORDER BY ", 1)

            params = []
            if keyword:
                search_conditions = []
                for column in self.config["search_columns"]:
                    search_conditions.append(
                        f"CONVERT(NVARCHAR(4000), {column}) LIKE ?"
                    )
                    params.append(f"%{keyword}%")

                sql = (
                    base_sql
                    + " AND ("
                    + " OR ".join(search_conditions)
                    + ") ORDER BY "
                    + order_by
                )
            else:
                sql = self.config["select_sql"]

            cursor.execute(sql, *params)
            rows = cursor.fetchall()

            pause_table_sorting(self.table)

            self.table.setRowCount(0)
            for row_index, row in enumerate(rows):
                self.table.insertRow(row_index)
                for col_index, value in enumerate(row):
                    item = QTableWidgetItem(
                        "" if value is None else str(value)
                    )
                    if col_index == 0:
                        item.setTextAlignment(
                            Qt.AlignmentFlag.AlignCenter |
                            Qt.AlignmentFlag.AlignVCenter
                        )
                    self.table.setItem(row_index, col_index, item)

            self.total_label.setText(f"Tổng số: {len(rows)}")
            self.loaded = True

        except Exception as e:
            QMessageBox.critical(
                self,
                "Lỗi tải dữ liệu",
                f"Không thể tải danh sách {self.config['table']}!\n{e}"
            )
        finally:
            resume_table_sorting(self.table)

            if cursor is not None:
                cursor.close()

    def clear_search(self):
        """Xóa từ khóa và hiển thị lại toàn bộ danh sách chưa xóa mềm."""
        self.search_input.clear()
        self.load_data()

    def submit_form(self):
        """Giữ tên phương thức cũ để tương thích; mở popup thêm mới."""
        self.open_add_dialog()

    def open_add_dialog(self):
        """Mở popup thêm danh mục; form không còn chiếm diện tích cố định trên trang."""
        dialog = CatalogCreateDialog(
            self.config,
            code_preview=self.preview_next_code(),
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.add_record(dialog.insert_values)

    def add_record(self, values):
        """Sinh lại mã dưới khóa bảng và thêm bản ghi trong cùng transaction."""
        if values is None:
            return
        values = list(values)

        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối database!")
            return

        cursor = None
        try:
            cursor = conn.cursor()

            # Khóa bảng và tính lại mã ngay lúc INSERT.
            # Không lọc IS_DELETED nên mã đã xóa vẫn được tính.
            new_code = self._next_code(cursor, lock_table=True)
            id_index = next(
                index for index, field in enumerate(self.config["fields"])
                if field[0] == self.config["id_column"]
            )
            values[id_index] = new_code

            cursor.execute(self.config["insert_sql"], *values)
            conn.commit()

            QMessageBox.information(
                self,
                "Thành công",
                f"Đã thêm {new_code} vào bảng {self.config['table']}!"
            )

            self.load_data()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(
                self,
                "Không thể thêm dữ liệu",
                f"Thêm dữ liệu thất bại!\n{e}"
            )
        finally:
            if cursor is not None:
                cursor.close()

    def open_selected_record_detail(self, row, column):
        """Mở popup chi tiết của dòng được nhấp đúp."""
        if row < 0:
            return

        record_values = {}
        display_values = []
        for index, (column_name, _label, *_rest) in enumerate(self.config["fields"]):
            item = self.table.item(row, index)
            value = item.text() if item is not None else ""
            record_values[column_name] = value
            display_values.append((self.config["headers"][index], value))

        record_id = str(record_values.get(self.config["id_column"], "")).strip()
        if not record_id:
            QMessageBox.warning(
                self, "Thiếu mã dữ liệu",
                "Không thể xác định mã của dòng được chọn.",
            )
            return

        name_column = self.config["fields"][1][0]
        record_name = str(record_values.get(name_column) or "")

        dialog = CatalogDetailDialog(
            self.config["title"],
            display_values,
            on_edit=lambda: self.edit_record(record_id, record_values),
            on_delete=lambda: self.delete_record_by_id(record_id, record_name),
            parent=self,
        )
        dialog.exec()

    def edit_record(self, record_id, current_values):
        """Mở popup chỉnh sửa và cập nhật bản ghi nếu người dùng lưu."""
        dialog = CatalogEditDialog(self.config, current_values, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        values = dialog.get_update_values()
        if values is None:
            return

        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối database!")
            return

        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(self.config["update_sql"], *values, record_id)

            if cursor.rowcount == 0:
                conn.rollback()
                QMessageBox.warning(
                    self,
                    "Không có thay đổi",
                    "Bản ghi không tồn tại hoặc đã bị xóa.",
                )
                self.load_data()
                return

            conn.commit()
            QMessageBox.information(
                self, "Thành công", f"Đã cập nhật thông tin {record_id}!"
            )
            self.load_data()

        except Exception as error:
            conn.rollback()
            QMessageBox.critical(
                self,
                "Không thể chỉnh sửa dữ liệu",
                f"Cập nhật thất bại!\n{error}",
            )
        finally:
            if cursor is not None:
                cursor.close()

    def delete_record_by_id(self, record_id, record_name=""):
        """Xóa mềm bản ghi được chọn trong popup chi tiết."""
        message = (
            f"Bạn có chắc muốn xóa {record_id}"
            + (f" - {record_name}" if record_name else "")
            + "?\n\nBản ghi sẽ được đánh dấu đã xóa (IS_DELETED = 1), "
              "không bị xóa vĩnh viễn khỏi cơ sở dữ liệu."
        )
        answer = QMessageBox.question(
            self,
            "Xác nhận xóa",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối database!")
            return

        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(self.config["delete_sql"], record_id)

            if cursor.rowcount == 0:
                conn.rollback()
                QMessageBox.information(
                    self,
                    "Không có thay đổi",
                    "Bản ghi không tồn tại hoặc đã được xóa trước đó.",
                )
                self.load_data()
                return

            conn.commit()
            QMessageBox.information(
                self,
                "Thành công",
                f"Đã đánh dấu xóa {record_id}.\n"
                "Dữ liệu vẫn được giữ trong SQL Server.",
            )
            self.load_data()

        except Exception as error:
            conn.rollback()
            QMessageBox.critical(
                self,
                "Không thể xóa dữ liệu",
                f"Cập nhật IS_DELETED thất bại!\n{error}",
            )
        finally:
            if cursor is not None:
                cursor.close()


