"""Bảng sản phẩm dùng chung cho giỏ hàng và biểu mẫu đổi trả."""

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
)

from ui.table_sort import DEFAULT_MIN_SECTION_SIZE


class ProductTableWidget(QTableWidget):
    """Bảng sản phẩm thống nhất, giữ thứ tự thêm và kích thước hàng/cột."""

    DEFAULT_ROW_HEIGHT = 44

    def __init__(
        self,
        headers,
        stretch_column=1,
        fixed_column_widths=None,
        parent=None,
        minimum_section_size=DEFAULT_MIN_SECTION_SIZE,
    ):
        headers = list(headers)
        super().__init__(0, len(headers), parent)

        self.setHorizontalHeaderLabels(headers)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)

        # Các bảng nghiệp vụ này luôn theo thứ tự sản phẩm được thêm vào.
        self.setSortingEnabled(False)

        header = self.horizontalHeader()
        header.setMinimumSectionSize(
            max(0, int(minimum_section_size))
        )
        header.setSectionsClickable(False)
        header.setSortIndicatorShown(False)
        header.setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )

        if (
            stretch_column is not None
            and 0 <= int(stretch_column) < self.columnCount()
        ):
            header.setSectionResizeMode(
                int(stretch_column), QHeaderView.ResizeMode.Stretch
            )

        for column, width in (fixed_column_widths or {}).items():
            column = int(column)
            if not 0 <= column < self.columnCount():
                raise ValueError(
                    f"Chỉ số cột cố định không hợp lệ: {column}"
                )
            header.setSectionResizeMode(
                column, QHeaderView.ResizeMode.Fixed
            )
            self.setColumnWidth(
                column,
                max(int(minimum_section_size), int(width)),
            )

    def insert_product_row(self, row=None):
        """Thêm một dòng sản phẩm với chiều cao thống nhất."""
        if row is None:
            row = self.rowCount()
        row = int(row)
        if not 0 <= row <= self.rowCount():
            raise IndexError(f"Vị trí dòng không hợp lệ: {row}")

        self.insertRow(row)
        self.setRowHeight(row, self.DEFAULT_ROW_HEIGHT)
        return row
