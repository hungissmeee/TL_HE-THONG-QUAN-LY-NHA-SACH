"""SearchableSingleSelect: thành phần giao diện quản lý sản phẩm."""

from decimal import (
    Decimal,
    InvalidOperation,
)
from PySide6.QtCore import (
    Qt,
    QDate,
    QPoint,
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
    QTableWidget,
    QHeaderView,
    QMessageBox,
    QAbstractItemView,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QDateEdit,
    QGroupBox,
)
from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table,
    pause_table_sorting,
    resume_table_sorting,
)


def _show_lookup_popup(anchor, popup):
    """Hiển thị danh sách gợi ý nổi dưới ô tìm kiếm, không chiếm chỗ trong form."""
    if popup.count() <= 0:
        popup.hide()
        return

    row_height = max(popup.sizeHintForRow(0), 24)
    height = min(max(row_height * min(popup.count(), 8) + 6, 72), 220)
    width = max(anchor.width(), 260)
    screen = anchor.screen()
    position = anchor.mapToGlobal(QPoint(0, anchor.height()))

    if screen is not None:
        available = screen.availableGeometry()
        width = min(width, available.width())
        height = min(height, available.height())
        x = max(
            available.left(),
            min(position.x(), available.right() - width + 1),
        )
        y = position.y()
        if y + height > available.bottom() + 1:
            above = anchor.mapToGlobal(QPoint(0, 0))
            y = above.y() - height
        y = max(
            available.top(),
            min(y, available.bottom() - height + 1),
        )
        position = QPoint(x, y)

    popup.resize(width, height)
    popup.move(position)
    popup.show()


class SearchableSingleSelect(QWidget):
    """Widget tìm kiếm và chọn một mục từ danh sách dữ liệu."""
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

        # Popup độc lập, không nằm trong layout nên không làm form nhảy chiều cao.
        self.results = QListWidget(self)
        self.results.setWindowFlags(Qt.WindowType.Popup)
        self.results.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.results.setMaximumHeight(220)
        self.results.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.results.itemClicked.connect(self._select_item)
        self.results.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.search_input)

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
        _show_lookup_popup(self.search_input, self.results)

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




"""SearchableMultiSelect: thành phần giao diện quản lý sản phẩm."""

from decimal import Decimal, InvalidOperation
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import (
    QWidget, QDialog, QLabel, QLineEdit, QPushButton, QComboBox,
    QVBoxLayout, QHBoxLayout, QFormLayout, QTableWidget,
    QHeaderView, QAbstractItemView, QMessageBox, QSpinBox,
    QDoubleSpinBox, QGroupBox, QDateEdit, QCheckBox,
    QListWidget, QListWidgetItem, QCompleter, QFrame,
)
from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table,
    pause_table_sorting,
    resume_table_sorting,
)


class SearchableMultiSelect(QWidget):
    """Widget tìm kiếm và chọn nhiều mục từ danh sách dữ liệu."""
    """Ô tìm kiếm để chọn nhiều mục; nhấn kết quả để thêm/bỏ chọn."""

    def __init__(self, placeholder="Tìm để chọn...", parent=None):
        super().__init__(parent)
        self.options = []
        self.selected_codes = set()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(placeholder)
        self.search_input.textEdited.connect(self._on_search)

        # Popup độc lập, không chiếm diện tích của biểu mẫu sản phẩm.
        self.results = QListWidget(self)
        self.results.setWindowFlags(Qt.WindowType.Popup)
        self.results.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.results.setMaximumHeight(220)
        self.results.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.results.itemClicked.connect(self._toggle_item)
        self.results.hide()

        self.selected_label = QLabel("Chưa chọn mục nào")
        self.selected_label.setWordWrap(False)
        self.selected_label.setMaximumHeight(22)
        self.selected_label.setStyleSheet("color: #AAB7C8; font-size: 13px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.search_input)
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
        _show_lookup_popup(self.search_input, self.results)

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
        _show_lookup_popup(self.search_input, self.results)

    def _update_selected_label(self):
        selected_names = [
            f"{code} - {name}"
            for code, name, _ in self.options
            if code in self.selected_codes
        ]
        text = f"Đã chọn {len(selected_names)} mục" if selected_names else "Chưa chọn mục nào"
        self.selected_label.setText(text)
        self.selected_label.setToolTip(
            "\n".join(selected_names) if selected_names else text
        )

    def checked_codes(self):
        # Giữ tên phương thức cũ để không phải sửa phần lưu dữ liệu.
        return [
            code for code, _, _ in self.options
            if code in self.selected_codes
        ]



