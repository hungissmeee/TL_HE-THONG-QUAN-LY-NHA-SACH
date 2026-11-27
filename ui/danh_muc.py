"""Trang quản lý các danh mục dùng chung của sản phẩm."""

from PySide6.QtWidgets import (
    QWidget, QDialog, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QTableWidget, QHeaderView,
    QMessageBox, QAbstractItemView
)
from PySide6.QtCore import Qt

from core.catalog_config import CATALOGS
from core.repositories.catalog_repository import CatalogRepository
from core.services.catalog_service import CatalogService

from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table,
    pause_table_sorting,
    resume_table_sorting
)


class CatalogAddDialog(QDialog):
    """Popup thêm mới dùng chung cho Tác giả, Thể loại, NXB và Thương hiệu."""

    def __init__(self, config, code_preview="", parent=None):
        super().__init__(parent)
        self.config = config
        self.inputs = {}
        self.values = None
        self.setWindowTitle(config["add_label"])
        self.setMinimumWidth(460)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        heading = QLabel(config["add_label"].upper())
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
                edit.setText(str(code_preview or ""))
                if not code_preview:
                    edit.setPlaceholderText("Mã sẽ được tự động tạo khi lưu")
            self.inputs[column] = edit
            form.addRow(label_text, edit)

        root.addWidget(group)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel_button = QPushButton("Hủy")
        cancel_button.clicked.connect(self.reject)
        self.add_button = QPushButton(config["add_label"])
        self.add_button.setProperty("buttonRole", "primary")
        self.add_button.setObjectName("primaryButton")
        self.add_button.clicked.connect(self._submit)
        actions.addWidget(cancel_button)
        actions.addWidget(self.add_button)
        root.addLayout(actions)

    def get_values(self):
        """Lấy dữ liệu theo thứ tự fields và kiểm tra trường bắt buộc."""
        values = []
        missing_fields = []
        first_missing = None

        for column, label_text, _placeholder, _max_length, required in self.config["fields"]:
            value = self.inputs[column].text().strip()
            if required and column != self.config["id_column"] and not value:
                missing_fields.append(label_text.replace(":", ""))
                if first_missing is None:
                    first_missing = self.inputs[column]
            values.append(value if value else None)

        if missing_fields:
            QMessageBox.warning(
                self,
                "Thiếu thông tin",
                "Vui lòng nhập: " + ", ".join(missing_fields),
            )
            if first_missing is not None:
                first_missing.setFocus()
            return None

        return values

    def _submit(self):
        """Chỉ đóng popup khi các trường bắt buộc đã hợp lệ."""
        values = self.get_values()
        if values is not None:
            self.values = values
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
        self.service = CatalogService(CatalogRepository(db, catalog_type))
        self.loaded = False

        self.setup_ui()

    def setup_ui(self):
        """Tạo thanh thao tác, bộ lọc tìm kiếm và bảng danh mục."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel(self.config["title"])
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        self.add_button = QPushButton(f"+ {self.config['add_label']}")
        self.add_button.setProperty("buttonRole", "primary")
        self.add_button.setObjectName("primaryButton")
        self.add_button.clicked.connect(self.open_add_dialog)
        header.addWidget(self.add_button)

        self.refresh_button = QPushButton("Làm mới")
        self.refresh_button.clicked.connect(self.load_data)
        header.addWidget(self.refresh_button)
        layout.addLayout(header)

        description = QLabel(
            "Nhấp đúp vào một dòng để xem chi tiết và thực hiện chỉnh sửa hoặc xóa."
        )
        description.setStyleSheet("color: #AAB7C8; font-size: 11px;")
        layout.addWidget(description)

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
        self.table.cellDoubleClicked.connect(self.open_selected_record_detail)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        if len(self.config["headers"]) > 1:
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        if self.catalog_type in ("publishers", "brands"):
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.table, 1)

        self.total_label = QLabel("Tổng số: 0")
        layout.addWidget(self.total_label)

    def _get_code_preview(self):
        try:
            return self.service.preview_next_code()
        except Exception as error:
            QMessageBox.warning(self, "Không thể tạo mã tự động", str(error))
            return ""

    def load_data(self):
        try:
            rows = self.service.list_records(self.search_input.text().strip())
            pause_table_sorting(self.table)
            self.table.setRowCount(0)
            columns = [field[0] for field in self.config["fields"]]
            for row_index, record in enumerate(rows):
                self.table.insertRow(row_index)
                for col_index, column in enumerate(columns):
                    value = record.get(column)
                    item = QTableWidgetItem("" if value is None else str(value))
                    if col_index == 0:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                    self.table.setItem(row_index, col_index, item)
            self.total_label.setText(f"Tổng số: {len(rows)}")
            self.loaded = True
        except Exception as error:
            QMessageBox.critical(self, "Lỗi tải dữ liệu", str(error))
        finally:
            resume_table_sorting(self.table)

    def clear_search(self):
        """Xóa từ khóa và hiển thị lại toàn bộ danh sách chưa xóa mềm."""
        self.search_input.clear()
        self.load_data()

    def open_add_dialog(self):
        """Mở popup thêm danh mục và tải lại danh sách sau khi lưu."""
        dialog = CatalogAddDialog(
            self.config,
            code_preview=self._get_code_preview(),
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.add_record(dialog.values)

    def add_record(self, values):
        try:
            new_code = self.service.create_record(values)
            QMessageBox.information(self, "Thành công", f"Đã thêm {new_code} vào bảng {self.config[chr(116)+chr(97)+chr(98)+chr(108)+chr(101)]}!")
            self.load_data()
        except Exception as error:
            QMessageBox.critical(self, "Không thể thêm dữ liệu", str(error))

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
        dialog = CatalogEditDialog(self.config, current_values, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.get_update_values()
        if values is None:
            return
        try:
            if not self.service.update_record(record_id, values):
                QMessageBox.warning(self, "Không có thay đổi", "Bản ghi không tồn tại hoặc đã bị xóa.")
            else:
                QMessageBox.information(self, "Thành công", f"Đã cập nhật thông tin {record_id}!")
            self.load_data()
        except Exception as error:
            QMessageBox.critical(self, "Không thể chỉnh sửa dữ liệu", str(error))

    def delete_record_by_id(self, record_id, record_name=""):
        message = f"Bạn có chắc muốn xóa {record_id}" + (f" - {record_name}" if record_name else "") + "?\\n\\nBản ghi sẽ được đánh dấu xóa mềm."
        answer = QMessageBox.question(self, "Xác nhận xóa", message, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            if self.service.soft_delete(record_id):
                QMessageBox.information(self, "Thành công", f"Đã đánh dấu xóa {record_id}.")
            else:
                QMessageBox.information(self, "Không có thay đổi", "Bản ghi không tồn tại hoặc đã được xóa.")
            self.load_data()
        except Exception as error:
            QMessageBox.critical(self, "Không thể xóa dữ liệu", str(error))
