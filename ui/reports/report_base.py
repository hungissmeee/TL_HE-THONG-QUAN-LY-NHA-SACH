"""Thành phần dùng chung cho các trang báo cáo BookHub."""

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFrame, QDateEdit, QTableWidget, QHeaderView,
    QAbstractItemView, QMessageBox, QFileDialog, QComboBox,
)

from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table,
)

MONEY_QUANT = Decimal("0.01")


def money_text(value, decimals=0):
    """Định dạng tiền Việt Nam; mặc định không hiển thị phần thập phân."""
    try:
        amount = Decimal(str(value or 0)).quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP
        )
    except (InvalidOperation, ValueError, TypeError):
        amount = Decimal("0.00")

    if decimals <= 0:
        return f"{amount:,.0f} đ".replace(",", ".")
    return f"{amount:,.{decimals}f} đ".replace(",", "X").replace(".", ",").replace("X", ".")


def number_text(value):
    try:
        return f"{int(value or 0):,}".replace(",", ".")
    except (ValueError, TypeError):
        return "0"


def date_text(value, include_time=True):
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y %H:%M" if include_time else "%d/%m/%Y")
    return str(value)


class ReportBasePage(QWidget):
    """Lớp nền: bộ lọc ngày, truy vấn, bảng và xuất CSV dùng chung."""

    def __init__(self, db, title, description, use_date_filter=True, parent=None):
        super().__init__(parent)
        self.db = db
        self.use_date_filter = use_date_filter
        self.export_tables = {}
        self.kpi_labels = {}
        self._build_base_ui(title, description)

    def _build_base_ui(self, title, description):
        root = QVBoxLayout(self)
        root.setContentsMargins(5, 5, 5, 5)
        root.setSpacing(10)

        title_label = QLabel(title.upper())
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #F3F4F6;")
        root.addWidget(title_label)

        description_label = QLabel(description)
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #AAB7C8;")
        root.addWidget(description_label)

        filter_frame = QFrame()
        filter_frame.setObjectName("reportFilterFrame")
        filter_frame.setStyleSheet(
            "QFrame#reportFilterFrame { background-color: #202938; "
            "border: 1px solid #39465A; border-radius: 7px; }"
        )
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(10, 8, 10, 8)
        filter_layout.setSpacing(8)

        today = QDate.currentDate()
        if self.use_date_filter:
            self.date_from = QDateEdit()
            self.date_from.setCalendarPopup(True)
            self.date_from.setDisplayFormat("dd/MM/yyyy")
            self.date_from.setDate(QDate(today.year(), today.month(), 1))

            self.date_to = QDateEdit()
            self.date_to.setCalendarPopup(True)
            self.date_to.setDisplayFormat("dd/MM/yyyy")
            self.date_to.setDate(today)

            filter_layout.addWidget(QLabel("Từ ngày:"))
            filter_layout.addWidget(self.date_from)
            filter_layout.addWidget(QLabel("Đến ngày:"))
            filter_layout.addWidget(self.date_to)

        self.refresh_button = QPushButton("Xem báo cáo")
        self.refresh_button.clicked.connect(self.refresh_data)
        filter_layout.addWidget(self.refresh_button)
        filter_layout.addStretch(1)

        self.export_selector = QComboBox()
        self.export_selector.setMinimumWidth(150)
        self.export_button = QPushButton("Xuất CSV")
        self.export_button.clicked.connect(self.export_selected_table)
        self.export_button.setEnabled(False)
        filter_layout.addWidget(self.export_selector)
        filter_layout.addWidget(self.export_button)
        root.addWidget(filter_frame)

        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(10)
        root.addLayout(self.content_layout, 1)

        self.status_label = QLabel("Chọn khoảng thời gian và nhấn Xem báo cáo.")
        self.status_label.setStyleSheet("color: #AAB7C8;")
        root.addWidget(self.status_label)

    def date_parameters(self):
        if not self.use_date_filter:
            return None, None
        start = self.date_from.date()
        end = self.date_to.date()
        if start > end:
            raise ValueError("Ngày bắt đầu không được lớn hơn ngày kết thúc.")
        return start.toString("yyyy-MM-dd"), end.toString("yyyy-MM-dd")

    def fetch_all(self, sql, params=()):
        connection = self.db.get_connection()
        if connection is None:
            raise RuntimeError("Chưa có kết nối SQL Server.")

        cursor = connection.cursor()
        try:
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()

    def fetch_one(self, sql, params=()):
        rows = self.fetch_all(sql, params)
        return rows[0] if rows else None

    def make_table(self, headers, min_height=190):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        table.horizontalHeader().setStretchLastSection(True)
        table.setMinimumHeight(min_height)
        prepare_sortable_table(table)
        return table

    def register_export_table(self, label, table):
        self.export_tables[label] = table
        self.export_selector.addItem(label, label)
        self.export_button.setEnabled(True)

    def fill_table(self, table, rows):
        table.setSortingEnabled(False)
        table.setRowCount(0)
        for values in rows:
            row_index = table.rowCount()
            table.insertRow(row_index)
            for column, value in enumerate(values):
                text = "" if value is None else str(value)
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if isinstance(value, (int, float, Decimal)):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                table.setItem(row_index, column, item)
        table.setSortingEnabled(True)

        header = table.horizontalHeader()
        column = header.sortIndicatorSection()

        if 0 <= column < table.columnCount():
            table.sortItems(column, header.sortIndicatorOrder())

    def add_stat_cards(self, definitions, columns=3):
        """definitions: [(key, title, initial_value), ...]"""
        grid = QGridLayout()
        grid.setSpacing(8)
        for index, (key, title, initial_value) in enumerate(definitions):
            card = QFrame()
            card.setObjectName("reportStatCard")
            card.setStyleSheet(
                "QFrame#reportStatCard { background-color: #202938; "
                "border: 1px solid #39465A; border-radius: 8px; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 9, 10, 9)
            title_label = QLabel(title)
            title_label.setStyleSheet(
                "color: #AAB7C8; font-size: 10px; font-weight: bold;"
            )
            value_label = QLabel(str(initial_value))
            value_label.setWordWrap(True)
            value_label.setStyleSheet(
                "color: #F3F4F6; font-size: 17px; font-weight: bold;"
            )
            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)
            grid.addWidget(card, index // columns, index % columns)
            self.kpi_labels[key] = value_label
        self.content_layout.addLayout(grid)

    def set_stat(self, key, value):
        label = self.kpi_labels.get(key)
        if label is not None:
            label.setText(str(value))

    def refresh_data(self):
        try:
            self.refresh_button.setEnabled(False)
            self.status_label.setText("Đang tải dữ liệu...")
            self.load_report()
            if self.use_date_filter:
                start = self.date_from.date().toString("dd/MM/yyyy")
                end = self.date_to.date().toString("dd/MM/yyyy")
                self.status_label.setText(f"Đã cập nhật dữ liệu từ {start} đến {end}.")
            else:
                self.status_label.setText("Đã cập nhật dữ liệu tồn kho hiện tại.")
        except Exception as exc:
            self.status_label.setText("Không thể tải báo cáo.")
            QMessageBox.critical(self, "Lỗi báo cáo", str(exc))
        finally:
            self.refresh_button.setEnabled(True)

    def load_report(self):
        raise NotImplementedError("Trang báo cáo phải triển khai load_report().")

    def export_selected_table(self):
        label = self.export_selector.currentData()
        table = self.export_tables.get(label)
        if table is None:
            QMessageBox.warning(self, "Xuất báo cáo", "Không tìm thấy bảng dữ liệu.")
            return

        default_name = (label or "bao_cao").strip().lower().replace(" ", "_") + ".csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Lưu báo cáo CSV", default_name, "CSV (*.csv)"
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".csv"):
            file_path += ".csv"

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as output:
                writer = csv.writer(output)
                writer.writerow([
                    table.horizontalHeaderItem(column).text()
                    for column in range(table.columnCount())
                ])
                for row in range(table.rowCount()):
                    writer.writerow([
                        table.item(row, column).text()
                        if table.item(row, column) is not None else ""
                        for column in range(table.columnCount())
                    ])
            QMessageBox.information(
                self, "Xuất báo cáo", f"Đã xuất báo cáo thành công:\n{file_path}"
            )
        except OSError as exc:
            QMessageBox.critical(self, "Lỗi xuất báo cáo", str(exc))
