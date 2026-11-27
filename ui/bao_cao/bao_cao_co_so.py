"""Thành phần dùng chung cho các trang báo cáo BookHub."""

import csv
from decimal import Decimal

from PySide6.QtCore import Qt, QDate, QPointF, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFrame, QDateEdit, QTableWidget, QHeaderView,
    QAbstractItemView, QMessageBox, QFileDialog, QComboBox,
    QScrollArea, QSizePolicy,
)

from ui.calendar_utils import configure_date_edit_calendar
from core.bao_cao.truy_van_sql import BaoCaoRepository
from core.bao_cao.xu_ly_du_lieu import BaoCaoService
from ui.table_sort import (
    SortableTableWidgetItem as QTableWidgetItem,
    prepare_sortable_table,
)

from ui.formatters import (
    format_report_money as money_text,
    format_number as number_text,
    format_report_date as date_text,
)



class ReportLineChart(QWidget):
    """Biểu đồ đường tối giản dùng cho xu hướng doanh thu theo thời gian."""

    def __init__(self, title, series, parent=None):
        super().__init__(parent)
        self.title = title
        self.series = list(series)
        self.points = []
        self.setMinimumHeight(235)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )

    def set_data(self, points):
        """Nhận danh sách (nhãn kỳ, giá trị theo thứ tự series)."""
        self.points = [
            (str(row[0]), *(float(value or 0) for value in row[1:]))
            for row in points
        ]
        self.update()

    @staticmethod
    def _compact_value(value):
        value = float(value or 0)
        absolute = abs(value)
        if absolute >= 1_000_000_000:
            return f"{value / 1_000_000_000:.1f} tỷ"
        if absolute >= 1_000_000:
            return f"{value / 1_000_000:.0f} tr"
        if absolute >= 1_000:
            return f"{value / 1_000:.0f} k"
        return f"{value:.0f}"

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#1B2432"))

        outer = self.rect().adjusted(0, 0, -1, -1)
        painter.setPen(QPen(QColor("#303E50"), 1))
        painter.setBrush(QColor("#1B2432"))
        painter.drawRoundedRect(outer, 8, 8)

        painter.setPen(QColor("#E2E8F0"))
        painter.drawText(18, 25, self.title)

        legend_x = 18
        legend_y = 48
        for label, value_index, color in self.series:
            painter.setPen(QPen(QColor(color), 3))
            painter.drawLine(legend_x, legend_y - 4, legend_x + 16, legend_y - 4)
            painter.setPen(QColor("#AAB7C8"))
            painter.drawText(legend_x + 22, legend_y, label)
            legend_x += 22 + painter.fontMetrics().horizontalAdvance(label) + 20

        if not self.points:
            painter.setPen(QColor("#8291A5"))
            painter.drawText(
                outer,
                Qt.AlignmentFlag.AlignCenter,
                "Không có dữ liệu trong khoảng thời gian đã chọn.",
            )
            painter.end()
            return

        left = 78
        right = 18
        top = 68
        bottom = 34
        plot_width = max(1, self.width() - left - right)
        plot_height = max(1, self.height() - top - bottom)
        values = [
            point[index + 1]
            for point in self.points
            for _label, index, _color in self.series
        ]
        minimum = min([0.0, *values])
        maximum = max([0.0, *values])
        if maximum == minimum:
            maximum = minimum + 1.0
        padding = (maximum - minimum) * 0.08
        minimum -= padding
        maximum += padding

        for tick in range(5):
            ratio = tick / 4
            y = top + plot_height * ratio
            value = maximum - (maximum - minimum) * ratio
            painter.setPen(QPen(QColor("#344256"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(int(left), int(y), int(left + plot_width), int(y))
            painter.setPen(QColor("#8291A5"))
            painter.drawText(
                QRectF(5, y - 9, left - 13, 18),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                self._compact_value(value),
            )

        count = len(self.points)
        x_step = plot_width / max(count - 1, 1)
        for series_label, value_index, color in self.series:
            path = QPainterPath()
            coordinates = []
            for index, point in enumerate(self.points):
                x = left + index * x_step if count > 1 else left + plot_width / 2
                value = point[value_index + 1]
                y = top + (maximum - value) / (maximum - minimum) * plot_height
                coordinates.append(QPointF(x, y))
                if index == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)

            painter.setPen(QPen(QColor(color), 2.4))
            painter.drawPath(path)
            painter.setBrush(QColor(color))
            painter.setPen(QPen(QColor("#1B2432"), 1))
            for point in coordinates:
                painter.drawEllipse(point, 3.2, 3.2)

        label_indices = sorted(set(
            [0, count - 1, count // 2]
            + ([count // 4, (count * 3) // 4] if count > 8 else list(range(count)))
        ))
        painter.setPen(QColor("#8291A5"))
        for index in label_indices:
            if index < 0 or index >= count:
                continue
            x = left + index * x_step if count > 1 else left + plot_width / 2
            painter.drawText(
                QRectF(x - 46, top + plot_height + 8, 92, 18),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                self.points[index][0],
            )
        painter.end()


class ReportBasePage(QWidget):
    """Lớp nền cung cấp bộ lọc, bảng dữ liệu và chức năng xuất báo cáo dùng chung."""

    def __init__(self, db, title, description, use_date_filter=True, parent=None):
        """Khởi tạo cấu hình bộ lọc, bảng dữ liệu và các thành phần dùng chung của báo cáo."""
        super().__init__(parent)
        self.db = db
        self.service = BaoCaoService(BaoCaoRepository(db))
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
            configure_date_edit_calendar(self.date_from)
            self.date_from.setDisplayFormat("dd/MM/yyyy")
            self.date_from.setDate(QDate(today.year(), today.month(), 1))

            self.date_to = QDateEdit()
            configure_date_edit_calendar(self.date_to)
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

        self.content_scroll = QScrollArea()
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.content_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 2, 4, 2)
        self.content_layout.setSpacing(12)
        self.content_scroll.setWidget(self.content_container)
        root.addWidget(self.content_scroll, 1)

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
        """Tương thích cho báo cáo mở rộng; SQL chỉ được chạy qua Repository."""
        return self.service.fetch_all(sql, params)

    def fetch_one(self, sql, params=()):
        return self.service.fetch_one(sql, params)

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
        primary_key=None,
    ):
        """Tạo một KPI chính nổi bật và các KPI phụ có thứ bậc thấp hơn.

        Mỗi phần tử có dạng (key, title, value) hoặc
        (key, title, value, description, tone).
        primary_key chỉ định KPI kết quả quan trọng nhất của nhóm.
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

        tone_colors = {
            "primary": "#60A5FA",
            "positive": "#34D399",
            "warning": "#FBBF24",
            "negative": "#F87171",
            "violet": "#A78BFA",
            "neutral": "#94A3B8",
        }

        featured = next(
            (item for item in definitions if item[0] == primary_key),
            None,
        )
        secondary = [
            item for item in definitions
            if featured is None or item[0] != primary_key
        ]

        # KPI quan trọng nhất chiếm toàn chiều ngang, giá trị đặt ở vị trí dễ quét mắt.
        if featured is not None:
            key, title, initial_value = featured[:3]
            description = featured[3] if len(featured) > 3 else ""
            tone = featured[4] if len(featured) > 4 else "primary"
            accent_color = tone_colors.get(tone, tone_colors["primary"])

            primary_card = QFrame()
            primary_card.setObjectName("reportPrimaryKpi")
            primary_card.setMinimumHeight(112)
            primary_card.setStyleSheet(
                "QFrame#reportPrimaryKpi {"
                " background-color: #202B3B;"
                " border: 1px solid #46566D;"
                " border-radius: 9px;"
                "}"
            )

            primary_layout = QHBoxLayout(primary_card)
            primary_layout.setContentsMargins(18, 14, 20, 14)
            primary_layout.setSpacing(16)

            text_layout = QVBoxLayout()
            text_layout.setSpacing(5)

            eyebrow = QLabel("KẾT QUẢ CHÍNH")
            eyebrow.setStyleSheet(
                "color: #94A3B8; font-size: 10px; font-weight: 700;"
                " background: transparent; border: none;"
            )
            text_layout.addWidget(eyebrow)

            title_label = QLabel(title)
            title_label.setWordWrap(True)
            title_label.setStyleSheet(
                "color: #F1F5F9; font-size: 14px; font-weight: 700;"
                " background: transparent; border: none;"
            )
            text_layout.addWidget(title_label)

            if description:
                detail_label = QLabel(description)
                detail_label.setWordWrap(True)
                detail_label.setStyleSheet(
                    "color: #94A3B8; font-size: 10px;"
                    " background: transparent; border: none;"
                )
                text_layout.addWidget(detail_label)

            primary_layout.addLayout(text_layout, 1)

            value_label = QLabel(str(initial_value))
            value_label.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            value_label.setWordWrap(True)
            value_label.setStyleSheet(
                f"color: {accent_color}; font-size: 30px; font-weight: 800;"
                " background: transparent; border: none;"
            )
            primary_layout.addWidget(value_label, 0)

            self.content_layout.addWidget(primary_card)
            self.kpi_labels[key] = value_label

        if not secondary:
            return

        # Các số liệu còn lại là thông tin đối chiếu, dùng thẻ nhỏ và nhẹ hơn.
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 3)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        for index, definition in enumerate(secondary):
            key, title, initial_value = definition[:3]
            description = definition[3] if len(definition) > 3 else ""
            tone = definition[4] if len(definition) > 4 else "neutral"
            accent_color = tone_colors.get(tone, tone_colors["neutral"])

            card = QFrame()
            card.setObjectName("reportSecondaryKpi")
            card.setMinimumHeight(76)
            card.setStyleSheet(
                "QFrame#reportSecondaryKpi {"
                " background-color: #1D2735;"
                " border: 1px solid #303E50;"
                " border-radius: 7px;"
                "}"
            )

            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(0)

            accent = QFrame()
            accent.setFixedWidth(3)
            accent.setStyleSheet(
                f"background-color: {accent_color};"
                " border: none;"
                " border-top-left-radius: 6px;"
                " border-bottom-left-radius: 6px;"
            )
            card_layout.addWidget(accent)

            content = QWidget()
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(10, 7, 10, 7)
            content_layout.setSpacing(2)

            title_label = QLabel(title)
            title_label.setWordWrap(True)
            title_label.setStyleSheet(
                "color: #B8C4D3; font-size: 10px; font-weight: 600;"
                " background: transparent; border: none;"
            )
            content_layout.addWidget(title_label)

            if description:
                detail_label = QLabel(description)
                detail_label.setWordWrap(True)
                detail_label.setStyleSheet(
                    "color: #8291A5; font-size: 9px;"
                    " background: transparent; border: none;"
                )
                content_layout.addWidget(detail_label)

            value_label = QLabel(str(initial_value))
            value_label.setWordWrap(True)
            value_label.setStyleSheet(
                "color: #E2E8F0; font-size: 16px; font-weight: 700;"
                " background: transparent; border: none;"
            )
            content_layout.addWidget(value_label)

            card_layout.addWidget(content, 1)
            grid.addWidget(card, index // columns, index % columns)
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
