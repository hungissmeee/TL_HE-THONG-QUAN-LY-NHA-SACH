"""Các bộ chọn danh mục tìm kiếm dùng QCompleter native của Qt."""

from PySide6.QtCore import Qt, QStringListModel, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QCompleter,
)


def _make_completer(parent, model):
    """Tạo completer dùng popup và cơ chế focus/keyboard native của Qt."""
    completer = QCompleter(model, parent)
    completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    completer.setFilterMode(Qt.MatchFlag.MatchContains)
    completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
    completer.setMaxVisibleItems(8)
    completer.setWrapAround(False)
    return completer


class SearchableSingleSelect(QWidget):
    """Ô tìm kiếm và chọn một mục từ danh mục SQL Server."""

    def __init__(self, placeholder="Tìm để chọn...", parent=None):
        super().__init__(parent)
        self.options = []
        self._selected_code = None
        self._selected_label = ""
        self._syncing_text = False
        self._label_to_code = {}

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText(placeholder)
        self.search_input.textEdited.connect(self._on_search)

        self._model = QStringListModel(self)
        self.completer = _make_completer(self, self._model)
        self.search_input.setCompleter(self.completer)
        self.completer.activated[str].connect(self._select_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.search_input)

    @property
    def results(self):
        """Popup QListView native do QCompleter quản lý."""
        return self.completer.popup()

    def set_options(self, options, selected_code=None):
        """options: iterable (code, name, is_deleted)."""
        self.options = [
            (str(code), str(name or ""), bool(is_deleted))
            for code, name, is_deleted in options
        ]
        self._label_to_code = {}
        labels = []
        self._selected_code = None
        self._selected_label = ""

        for code, name, is_deleted in self.options:
            suffix = " (đã xóa mềm)" if is_deleted else ""
            label = f"{code} - {name}{suffix}"
            labels.append(label)
            self._label_to_code[label] = code
            if selected_code is not None and str(selected_code) == code:
                self._selected_code = code
                self._selected_label = label

        self._model.setStringList(labels)
        self._syncing_text = True
        self.search_input.setText(self._selected_label)
        self._syncing_text = False
        self.completer.popup().hide()

    def _on_search(self, text):
        if self._syncing_text:
            return
        if text != self._selected_label:
            self._selected_code = None
            self._selected_label = ""

    def _populate_results(self, keyword=""):
        """Trả về các lựa chọn khớp từ khóa; Qt tự lọc model khi người dùng gõ."""
        keyword = (keyword or "").strip().casefold()
        return [
            label for label in self._label_to_code
            if not keyword or keyword in label.casefold()
        ]

    def _select_item(self, item):
        """Giữ tương thích cho các luồng gọi nội bộ bằng chuỗi hoặc QModelIndex."""
        if hasattr(item, "data"):
            label = item.data(Qt.ItemDataRole.DisplayRole)
        elif hasattr(item, "text"):
            label = item.text()
        else:
            label = str(item)
        self._select_label(str(label or ""))

    def _select_label(self, label):
        code = self._label_to_code.get(str(label))
        if code is None:
            return
        self._selected_code = code
        self._selected_label = str(label)
        self._syncing_text = True
        self.search_input.setText(self._selected_label)
        self._syncing_text = False
        self.search_input.setFocus(Qt.FocusReason.OtherFocusReason)
        self.search_input.setCursorPosition(len(self._selected_label))
        self.completer.popup().hide()

    def currentData(self):
        return self._selected_code


class _CompleterSearchLineEdit(QLineEdit):
    """Ô tìm kiếm mở gợi ý native khi được focus hoặc được bấm vào."""

    def _show_completions(self):
        completer = self.completer()
        if completer is None or not self.isVisible() or not self.hasFocus():
            return
        completer.setCompletionPrefix(self.text())
        completer.complete()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        QTimer.singleShot(0, self._show_completions)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        QTimer.singleShot(0, self._show_completions)


class SearchableMultiSelect(QWidget):
    """Ô tìm kiếm dùng QCompleter native để chọn nhiều mục."""

    def __init__(self, placeholder="Tìm để chọn...", parent=None):
        super().__init__(parent)
        self.options = []
        self.selected_codes = set()
        self._last_query = ""
        self._label_to_code = {}

        self.search_input = _CompleterSearchLineEdit(self)
        self.search_input.setPlaceholderText(placeholder)
        self.search_input.textEdited.connect(self._on_search)

        self._model = QStringListModel(self)
        self.completer = _make_completer(self, self._model)
        self.search_input.setCompleter(self.completer)
        self.completer.activated[str].connect(self._toggle_label)

        self.selected_label = QLabel("Chưa chọn mục nào", self)
        self.selected_label.setWordWrap(True)
        self.selected_label.setStyleSheet("color: #AAB7C8; font-size: 13px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.search_input)
        layout.addWidget(self.selected_label)

    @property
    def results(self):
        """Popup QListView native do QCompleter quản lý."""
        return self.completer.popup()

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
        self._last_query = ""
        self.search_input.clear()
        self.completer.popup().hide()
        self._refresh_completion_model()
        self.completer.setCompletionPrefix("")
        self._update_selected_label()

    def _on_search(self, text):
        self._last_query = text

    def _populate_results(self, keyword=""):
        """Trả về lựa chọn khớp từ khóa mà không tự quản lý popup."""
        keyword = (keyword or "").strip().casefold()
        return [
            label for label, _ in self._completion_entries()
            if not keyword or keyword in label.casefold()
        ]

    def _completion_entries(self):
        entries = []
        self._label_to_code = {}
        for code, name, is_deleted in self.options:
            marker = "✓ " if code in self.selected_codes else ""
            suffix = " (đã xóa mềm)" if is_deleted else ""
            label = f"{marker}{code} - {name}{suffix}"
            entries.append((label, code))
            self._label_to_code[label] = code
        return entries

    def _refresh_completion_model(self):
        self._model.setStringList(
            [label for label, _ in self._completion_entries()]
        )
        self.completer.setCompletionPrefix(self._last_query)

    def _toggle_item(self, item):
        """Giữ tương thích cho các luồng gọi nội bộ bằng chuỗi hoặc QModelIndex."""
        if hasattr(item, "data"):
            label = item.data(Qt.ItemDataRole.DisplayRole)
        elif hasattr(item, "text"):
            label = item.text()
        else:
            label = str(item)
        self._toggle_label(str(label or ""))

    def _toggle_label(self, label):
        code = self._label_to_code.get(str(label))
        if code is None:
            return
        if code in self.selected_codes:
            self.selected_codes.remove(code)
        else:
            self.selected_codes.add(code)

        # Sau khi chọn, xóa từ khóa để người dùng có thể tìm mục tiếp theo.
        self._last_query = ""
        self._refresh_completion_model()
        self.completer.setCompletionPrefix("")
        self.search_input.clear()
        self.search_input.setFocus(Qt.FocusReason.OtherFocusReason)
        self._update_selected_label()

        # Giữ popup native mở lại với toàn bộ lựa chọn, kể cả khi chưa gõ từ khóa.
        QTimer.singleShot(0, self._reopen_completer)

    def _reopen_completer(self):
        if not self.isVisible() or not self.search_input.hasFocus():
            return
        self.completer.setCompletionPrefix(self.search_input.text())
        self.completer.complete()

    def _update_selected_label(self):
        selected_names = [
            name
            for code, name, _ in self.options
            if code in self.selected_codes
        ]
        text = (
            "Đã chọn: " + ", ".join(selected_names)
            if selected_names else "Chưa chọn mục nào"
        )
        self.selected_label.setText(text)
        self.selected_label.setToolTip(text)

    def checked_codes(self):
        return [
            code for code, _, _ in self.options
            if code in self.selected_codes
        ]
