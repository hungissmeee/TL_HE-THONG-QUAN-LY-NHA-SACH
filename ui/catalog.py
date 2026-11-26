from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QFormLayout,
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


class CatalogPage(QWidget):
    """Trang danh mục dùng chung cho Tác giả, Thể loại, Nhà xuất bản và Thương hiệu."""

    def __init__(self, db, catalog_type):
        super().__init__()

        if catalog_type not in CATALOGS:
            raise ValueError(f"Loại danh mục không hợp lệ: {catalog_type}")

        self.db = db
        self.catalog_type = catalog_type
        self.config = CATALOGS[catalog_type]
        self.inputs = {}
        self.loaded = False
        self.editing_record_id = None

        self.setup_ui()
        self.refresh_code_preview()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel(self.config["title"])
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        description = QLabel(
            "Thêm mới, chỉnh sửa, xóa mềm và xem danh sách trong cơ sở dữ liệu."
        )
        description.setStyleSheet("color: #AAB7C8; font-size: 11px;")
        layout.addWidget(description)

        form = QFormLayout()
        form.setSpacing(12)

        for column, label_text, placeholder, max_length, required in self.config["fields"]:
            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            edit.setMaxLength(max_length)
            if column == self.config["id_column"]:
                edit.setReadOnly(True)
                edit.setPlaceholderText("Mã được tạo tự động")
            self.inputs[column] = edit
            form.addRow(label_text, edit)

        button_layout = QHBoxLayout()

        self.add_button = QPushButton("Thêm mới")
        self.add_button.clicked.connect(self.submit_form)

        self.clear_button = QPushButton("Xóa nội dung")
        self.clear_button.clicked.connect(self.clear_form)

        self.edit_button = QPushButton("Chỉnh sửa mục đã chọn")
        self.edit_button.setEnabled(False)
        self.edit_button.clicked.connect(self.start_edit_selected_record)

        self.delete_button = QPushButton("Xóa mục đã chọn")
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.delete_selected_record)
        self.delete_button.setStyleSheet("""
            QPushButton:enabled {
                background-color: #A83232;
                color: white;
            }
            QPushButton:disabled {
                color: #888888;
            }
        """)

        self.refresh_button = QPushButton("Làm mới danh sách")
        self.refresh_button.clicked.connect(self.load_data)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.refresh_button)

        layout.addLayout(form)
        layout.addLayout(button_layout)

        # Thanh tìm kiếm danh mục
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

        search_layout.addWidget(self.search_input)
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
        self.table.itemSelectionChanged.connect(
            self.update_selection_button_state
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

    def refresh_code_preview(self):
        """Hiển thị trước mã kế tiếp; mã được tính lại khi nhấn Thêm mới."""
        conn = self.db.get_connection()
        if conn is None:
            self.inputs[self.config["id_column"]].clear()
            return

        cursor = None
        try:
            cursor = conn.cursor()
            code = self._next_code(cursor, lock_table=False)
            self.inputs[self.config["id_column"]].setText(code)
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.inputs[self.config["id_column"]].setText("Không tạo được mã")
            QMessageBox.warning(
                self,
                "Không thể tạo mã tự động",
                f"Không lấy được mã cho {self.config['table']}.\n{e}"
            )
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
            self.update_selection_button_state()

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
        if self.editing_record_id is not None:
            self.update_record()
        else:
            self.add_record()

    def add_record(self):
        values = []
        missing_fields = []

        for column, label_text, placeholder, max_length, required in self.config["fields"]:
            value = self.inputs[column].text().strip()
            if required and column != self.config["id_column"] and not value:
                missing_fields.append(label_text.replace(":", ""))
            values.append(value if value else None)

        if missing_fields:
            QMessageBox.warning(
                self,
                "Thiếu thông tin",
                "Vui lòng nhập: " + ", ".join(missing_fields)
            )
            return

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
            self.inputs[self.config["id_column"]].setText(new_code)

            cursor.execute(self.config["insert_sql"], *values)
            conn.commit()

            QMessageBox.information(
                self,
                "Thành công",
                f"Đã thêm {new_code} vào bảng {self.config['table']}!"
            )

            self.clear_form()
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

    def start_edit_selected_record(self):
        """Đưa dữ liệu của dòng đang chọn lên form để chỉnh sửa."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(
                self,
                "Chưa chọn dữ liệu",
                "Vui lòng chọn một dòng cần chỉnh sửa."
            )
            return

        values = {}
        for column_index, (column, *_rest) in enumerate(self.config["fields"]):
            item = self.table.item(row, column_index)
            values[column] = item.text() if item is not None else ""

        record_id = values.get(self.config["id_column"], "").strip()
        if not record_id:
            QMessageBox.warning(
                self,
                "Thiếu mã dữ liệu",
                "Không thể xác định mã của dòng được chọn."
            )
            return

        self.editing_record_id = record_id

        for column, value in values.items():
            self.inputs[column].setText(value)

        # Không cho sửa khóa chính trong chế độ chỉnh sửa.
        self.inputs[self.config["id_column"]].setReadOnly(True)
        self.add_button.setText("Lưu chỉnh sửa")
        self.clear_button.setText("Hủy chỉnh sửa")
        self.table.setEnabled(False)
        self.search_input.setEnabled(False)
        self.search_button.setEnabled(False)
        self.clear_search_button.setEnabled(False)
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)

        # Đưa con trỏ vào trường thông tin đầu tiên không phải mã.
        for column, *_rest in self.config["fields"]:
            if column != self.config["id_column"]:
                self.inputs[column].setFocus()
                break

    def update_record(self):
        """Cập nhật nội dung bản ghi, giữ nguyên mã và trạng thái IS_DELETED."""
        values = []
        missing_fields = []

        for column, label_text, placeholder, max_length, required in self.config["fields"]:
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
                "Vui lòng nhập: " + ", ".join(missing_fields)
            )
            return

        answer = QMessageBox.question(
            self,
            "Xác nhận chỉnh sửa",
            f"Bạn có chắc muốn lưu thay đổi cho {self.editing_record_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
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
            cursor.execute(
                self.config["update_sql"],
                *values,
                self.editing_record_id
            )

            if cursor.rowcount == 0:
                conn.rollback()
                QMessageBox.warning(
                    self,
                    "Không có thay đổi",
                    "Bản ghi không tồn tại hoặc đã bị xóa."
                )
                self.clear_form()
                self.load_data()
                return

            conn.commit()
            QMessageBox.information(
                self,
                "Thành công",
                f"Đã cập nhật thông tin {self.editing_record_id}!"
            )

            self.clear_form()
            self.load_data()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(
                self,
                "Không thể chỉnh sửa dữ liệu",
                f"Cập nhật thất bại!\n{e}"
            )
        finally:
            if cursor is not None:
                cursor.close()

    def update_selection_button_state(self):
        """Bật nút chỉnh sửa/xóa khi có dòng được chọn và không ở chế độ sửa."""
        has_selection = self.table.currentRow() >= 0
        not_editing = self.editing_record_id is None
        self.edit_button.setEnabled(has_selection and not_editing)
        self.delete_button.setEnabled(has_selection and not_editing)

    def delete_selected_record(self):
        """Xóa mềm bản ghi đang chọn bằng cách đặt IS_DELETED = 1."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(
                self,
                "Chưa chọn dữ liệu",
                "Vui lòng chọn một dòng cần xóa."
            )
            return

        id_item = self.table.item(row, 0)
        name_item = self.table.item(row, 1)
        if id_item is None:
            QMessageBox.warning(
                self,
                "Thiếu mã dữ liệu",
                "Không thể xác định mã của dòng được chọn."
            )
            return

        record_id = id_item.text().strip()
        record_name = name_item.text().strip() if name_item else ""

        answer = QMessageBox.question(
            self,
            "Xác nhận xóa",
            (
                f"Bạn có chắc muốn xóa {record_id}"
                + (f" - {record_name}" if record_name else "")
                + "?\n\nBản ghi sẽ được đánh dấu đã xóa (IS_DELETED = 1), "
                  "không bị xóa vĩnh viễn khỏi cơ sở dữ liệu."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(
                self,
                "Thông báo",
                "Chưa có kết nối database!"
            )
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
                    "Bản ghi không tồn tại hoặc đã được xóa trước đó."
                )
                self.load_data()
                return

            conn.commit()
            QMessageBox.information(
                self,
                "Thành công",
                f"Đã đánh dấu xóa {record_id}.\n"
                "Dữ liệu vẫn được giữ trong SQL Server."
            )
            self.load_data()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(
                self,
                "Không thể xóa dữ liệu",
                f"Cập nhật IS_DELETED thất bại!\n{e}"
            )
        finally:
            if cursor is not None:
                cursor.close()

    def clear_form(self):
        """Xóa form; mã danh mục tự sinh và luôn không cho nhập tay."""
        for edit in self.inputs.values():
            edit.clear()
            edit.setReadOnly(False)

        id_input = self.inputs[self.config["id_column"]]
        id_input.setReadOnly(True)

        self.editing_record_id = None
        self.add_button.setText("Thêm mới")
        self.clear_button.setText("Xóa nội dung")
        self.table.setEnabled(True)
        self.search_input.setEnabled(True)
        self.search_button.setEnabled(True)
        self.clear_search_button.setEnabled(True)
        self.table.clearSelection()
        self.update_selection_button_state()

        self.refresh_code_preview()

        for column, *_rest in self.config["fields"]:
            if column != self.config["id_column"]:
                self.inputs[column].setFocus()
                break
