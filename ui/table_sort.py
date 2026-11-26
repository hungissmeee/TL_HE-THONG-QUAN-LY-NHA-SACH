"""Các tiện ích sắp xếp dữ liệu trong QTableWidget theo kiểu dữ liệu phù hợp."""


import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
)


SORT_ROLE = Qt.ItemDataRole.UserRole + 100


class SortableTableWidgetItem(QTableWidgetItem):
    """Thành phần này phụ trách chức năng SortableTableWidgetItem trong hệ thống."""

    def _sort_key(self):
        explicit_value = self.data(SORT_ROLE)

        if explicit_value is not None:
            return (0, explicit_value)

        text = self.text().strip()

        if not text:
            return (4, "")

        # Sắp xếp ngày tháng
        date_formats = [
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
        ]

        for date_format in date_formats:
            try:
                value = datetime.strptime(text, date_format)
                return (0, value)
            except ValueError:
                pass

        # Sắp xếp giờ
        for time_format in ("%H:%M:%S", "%H:%M"):
            try:
                value = datetime.strptime(text, time_format)
                return (1, value)
            except ValueError:
                pass

        # Sắp xếp số và tiền tệ theo giá trị thật
        number = (
            text.replace("VNĐ", "")
            .replace("VND", "")
            .replace("đ", "")
            .replace("₫", "")
            .replace("%", "")
            .replace(" ", "")
        )

        try:
            if "," in number and "." in number:
                if number.rfind(",") > number.rfind("."):
                    # Ví dụ: 1.250.000,50
                    number = number.replace(".", "").replace(",", ".")
                else:
                    # Ví dụ: 1,250,000.50
                    number = number.replace(",", "")

            elif "," in number:
                number = number.replace(",", ".")

            value = Decimal(number)

            if value.is_finite():
                return (2, value)

        except (InvalidOperation, ValueError):
            pass

        # Sắp xếp văn bản và mã có chứa số tự nhiên
        parts = re.split(r"(\d+)", text.casefold())

        natural_key = tuple(
            (0, int(part)) if part.isdigit()
            else (1, part)
            for part in parts if part
        )

        return (3, natural_key)

    def __lt__(self, other):
        if not isinstance(other, QTableWidgetItem):
            return super().__lt__(other)

        left = self._sort_key()

        if isinstance(other, SortableTableWidgetItem):
            right = other._sort_key()
        else:
            right = (3, other.text().casefold())

        return left < right


def prepare_sortable_table(
    table,
    default_column=0,
    default_order=Qt.SortOrder.AscendingOrder
):
    """Bật sắp xếp và hiển thị mũi tên ở cột mặc định."""

    if table.columnCount() <= 0:
        return

    column = max(0, min(default_column, table.columnCount() - 1))

    header = table.horizontalHeader()
    header.setSectionsClickable(True)
    header.setSortIndicatorShown(True)

    header.setSortIndicator(column, default_order)

    table.setSortingEnabled(True)


def create_table_action_panel(message, parent=None):
    """Tạo vùng thông tin và nút thao tác thống nhất bên dưới bảng dữ liệu."""
    panel = QFrame(parent)
    panel.setObjectName("tableActionPanel")

    layout = QHBoxLayout(panel)
    layout.setContentsMargins(14, 10, 14, 10)
    layout.setSpacing(10)

    hint_label = QLabel(message, panel)
    hint_label.setObjectName("tableActionHint")
    hint_label.setWordWrap(True)
    layout.addWidget(hint_label, 1)

    return panel, layout, hint_label


def pause_table_sorting(table: QTableWidget):
    """Tạm dừng sắp xếp khi đang thêm hoặc tải lại dữ liệu."""

    if hasattr(table, "_sort_restore_state"):
        return

    header = table.horizontalHeader()

    table._sort_restore_state = {
        "enabled": table.isSortingEnabled(),
        "column": header.sortIndicatorSection(),
        "order": header.sortIndicatorOrder(),
    }

    table.setSortingEnabled(False)


def resume_table_sorting(table: QTableWidget):
    """Khôi phục sắp xếp sau khi tải dữ liệu."""

    state = getattr(table, "_sort_restore_state", None)

    if state is None:
        return

    del table._sort_restore_state

    if not state["enabled"]:
        return

    table.setSortingEnabled(True)

    column = state["column"]
    order = state["order"]

    if 0 <= column < table.columnCount():
        table.horizontalHeader().setSortIndicator(column, order)
        table.sortItems(column, order)
