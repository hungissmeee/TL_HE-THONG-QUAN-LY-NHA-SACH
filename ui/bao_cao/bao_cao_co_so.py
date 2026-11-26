"""Thành phần dùng chung cho các trang báo cáo BookHub."""

import csv
from decimal import Decimal

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

from ui.formatters import (
    format_report_money as money_text,
    format_number as number_text,
    format_report_date as date_text,
)


class ReportBasePage(QWidget):
    """Lớp nền cung cấp bộ lọc, bảng dữ liệu và chức năng xuất báo cáo dùng chung."""

    def __init__(self, db, title, description, use_date_filter=True, parent=None):
        """Khởi tạo cấu hình bộ lọc, bảng dữ liệu và các thành phần dùng chung của báo cáo."""
        super().__init__(parent)
        self.db = db
        self.use_date_filter = use_date_filter
        self.export_tables = {}
        self.kpi_labels = {}
        self._build_base_ui(title, description)

    def _build_base_ui(self, title, description):
        """Tạo vùng bộ lọc ngày, thẻ thống kê, bảng dữ liệu và nút xuất báo cáo."""
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
        """Chuyển khoảng ngày được chọn thành tham số truy vấn SQL."""
        if not self.use_date_filter:
            return None, None
        start = self.date_from.date()
        end = self.date_to.date()
        if start > end:
            raise ValueError("Ngày bắt đầu không được lớn hơn ngày kết thúc.")
        return start.toString("yyyy-MM-dd"), end.toString("yyyy-MM-dd")

    def fetch_all(self, sql, params=()):
        """Thực thi truy vấn và trả về toàn bộ dòng dữ liệu."""
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
        """Thực thi truy vấn và trả về một dòng dữ liệu đầu tiên."""
        rows = self.fetch_all(sql, params)
        return rows[0] if rows else None

    def make_table(self, headers, min_height=190):
        """Tạo bảng báo cáo với tiêu đề và quy tắc sắp xếp."""
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
        """Đăng ký bảng có thể xuất dữ liệu sang tệp báo cáo."""
        self.export_tables[label] = table
        self.export_selector.addItem(label, label)
        self.export_button.setEnabled(True)

    def fill_table(self, table, rows):
        """Xóa dữ liệu cũ và điền các dòng kết quả mới vào bảng."""
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

    def add_stat_cards(
        self,
        definitions,
        columns=3,
        section_title=None,
        section_description=None,
    ):
        """Tạo thẻ KPI với cấp độ nhấn mạnh riêng cho số liệu chính và số liệu phụ.

        Phần tử có dạng:
        (key, title, value, description, tone, emphasis).
        emphasis nhận "highlight" cho kết quả chính, "support" cho số liệu
        thành phần; bỏ qua emphasis để giữ kiểu thẻ tiêu chuẩn ở báo cáo khác.
        """
        if section_title:
            section_label = QLabel(section_title)
            section_label.setStyleSheet(
                "color: #E2E8F0; font-size: 14px; font-weight: 700;"
            )
            self.content_layout.addWidget(section_label)

        if section_description:
            description_label = QLabel(section_description)
            description_label.setWordWrap(True)
            description_label.setStyleSheet(
                "color: #94A3B8; font-size: 11px;"
            )
            self.content_layout.addWidget(description_label)

        grid = QGridLayout()
        grid.setContentsMargins(0, 2, 0, 5)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        tone_colors = {
            "primary": "#60A5FA",
            "positive": "#34D399",
            "warning": "#FBBF24",
            "negative": "#F87171",
            "violet": "#A78BFA",
            "neutral": "#64748B",
        }

        # Bố trí theo tổng số cột để thẻ kết quả chính có diện tích lớn hơn.
        for column in range(columns):
            grid.setColumnStretch(column, 1)

        grid_row = 0
        grid_column = 0

        for definition in definitions:
            key, title, initial_value = definition[:3]
            description = definition[3] if len(definition) > 3 else ""
            tone = definition[4] if len(definition) > 4 else "neutral"
            emphasis = definition[5] if len(definition) > 5 else "normal"
            is_highlight = emphasis == "highlight"
            is_support = emphasis == "support"
            accent_color = tone_colors.get(tone, tone_colors["neutral"])

            # Thẻ kết quả chính chiếm hai phần chiều rộng; thẻ thành phần chiếm một.
            column_span = 2 if is_highlight and columns >= 4 else 1
            if grid_column + column_span > columns:
                grid_row += 1
                grid_column = 0

            card = QFrame()
            card.setObjectName(
                "reportStatCardHighlight" if is_highlight else "reportStatCard"
            )
            card.setFixedHeight(116 if is_highlight else 92 if is_support else 108)

            background = "#24364B" if is_highlight else "#202B3B"
            border_color = "#42658A" if is_highlight else "#344256"
            card.setStyleSheet(
                f"QFrame#{card.objectName()} {{"
                f" background-color: {background};"
                f" border: 1px solid {border_color};"
                " border-radius: 9px;"
                "}"
            )

            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(0)

            accent = QFrame()
            accent.setFixedWidth(5 if is_highlight else 4)
            accent.setStyleSheet(
                f"background-color: {accent_color};"
                " border: none;"
                " border-top-left-radius: 8px;"
                " border-bottom-left-radius: 8px;"
            )
            card_layout.addWidget(accent)

            content = QWidget()
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(
                15 if is_highlight else 12,
                10,
                15 if is_highlight else 12,
                10,
            )
            content_layout.setSpacing(3 if is_support else 4)

            title_label = QLabel(title)
            title_label.setWordWrap(True)
            title_label.setStyleSheet(
                f"color: {'#F1F5F9' if is_highlight else '#C0CCDA'};"
                f" font-size: {'12px' if is_highlight else '10px' if is_support else '11px'};"
                " font-weight: 700;"
                " background: transparent; border: none;"
            )
            content_layout.addWidget(title_label)

            if description:
                detail_label = QLabel(description)
                detail_label.setWordWrap(True)
                detail_label.setStyleSheet(
                    f"color: {'#AFC2D8' if is_highlight else '#8999AD'};"
                    f" font-size: {'10px' if not is_support else '9px'};"
                    " background: transparent; border: none;"
                )
                content_layout.addWidget(detail_label)

            content_layout.addStretch(1)

            value_label = QLabel(str(initial_value))
            value_label.setObjectName(
                "reportStatValueHighlight" if is_highlight else "reportStatValueSupport" if is_support else "reportStatValue"
            )
            value_label.setWordWrap(True)
            value_label.setStyleSheet(
                f"color: {'#FFFFFF' if is_highlight else '#DCE6F2' if is_support else '#F8FAFC'};"
                f" font-size: {'30px' if is_highlight else '16px' if is_support else '21px'};"
                f" font-weight: {'800' if is_highlight else '600' if is_support else '700'};"
                " background: transparent; border: none;"
            )
            content_layout.addWidget(value_label)

            card_layout.addWidget(content, 1)
            grid.addWidget(
                card,
                grid_row,
                grid_column,
                1,
                column_span,
                Qt.AlignmentFlag.AlignVCenter,
            )
            grid_column += column_span
            if grid_column >= columns:
                grid_row += 1
                grid_column = 0

            self.kpi_labels[key] = value_label

        self.content_layout.addLayout(grid)

    def set_stat(self, key, value):
        """Cập nhật nhãn và giá trị của một thẻ thống kê."""
        label = self.kpi_labels.get(key)
        if label is not None:
            label.setText(str(value))

    def refresh_data(self):
        """Tải lại báo cáo sau khi người dùng thay đổi bộ lọc."""
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
        """Phương thức được lớp báo cáo con ghi đè để tải số liệu riêng."""
        raise NotImplementedError("Trang báo cáo phải triển khai load_report().")

    def export_selected_table(self):
        """Xuất bảng báo cáo đang chọn ra định dạng tệp được hỗ trợ."""
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
