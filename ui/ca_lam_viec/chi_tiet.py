"""Các hộp thoại chi tiết ca làm việc và danh sách nhân viên thuộc ca."""

from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)


class ShiftDetailDialog(QDialog):
    """Hiển thị thông tin một ca và các thao tác được phép theo vai trò."""

    def __init__(
        self,
        shift,
        parent=None,
        on_register=None,
        on_closing_cash=None,
        employees=None,
    ):
        super().__init__(parent)
        self.on_register = on_register
        self.on_closing_cash = on_closing_cash
        self.setWindowTitle(f"Chi tiết ca làm việc - {shift.get('maca', '')}")
        self.resize(650, 520)
        self.setMinimumSize(520, 420)

        root = QVBoxLayout(self)
        title = QLabel(f"CHI TIẾT CA LÀM VIỆC - {shift.get('maca', '')}")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        root.addWidget(title)

        info_group = QGroupBox("Thông tin ca")
        info_form = QFormLayout(info_group)
        labels = (
            ("soca", "Ca:"),
            ("ngaylam", "Ngày làm:"),
            ("tgmo", "Giờ mở:"),
            ("tgdong", "Giờ đóng:"),
            ("so_nhan_vien", "Số nhân viên:"),
            ("trang_thai", "Trạng thái:"),
            ("dang_ky", "Trạng thái đăng ký:"),
            ("tien_dau_ca", "Tiền đầu ca:"),
            ("tien_cuoi_ca", "Tiền cuối ca:"),
        )
        for key, label in labels:
            value = shift.get(key)
            if value not in (None, ""):
                value_label = QLabel(str(value))
                value_label.setWordWrap(True)
                info_form.addRow(label, value_label)
        root.addWidget(info_group)

        if employees is not None:
            employee_group = QGroupBox(f"Nhân viên thuộc ca ({len(employees)})")
            employee_layout = QVBoxLayout(employee_group)
            employee_table = QTableWidget(0, 4)
            employee_table.setHorizontalHeaderLabels(
                ["Mã nhân viên", "Họ tên", "Vai trò", "Số điện thoại"]
            )
            employee_table.setEditTriggers(
                QAbstractItemView.EditTrigger.NoEditTriggers
            )
            employee_table.setSelectionBehavior(
                QAbstractItemView.SelectionBehavior.SelectRows
            )
            employee_table.setAlternatingRowColors(True)
            employee_table.verticalHeader().setVisible(False)
            employee_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )
            employee_table.horizontalHeader().setSectionResizeMode(
                1, QHeaderView.ResizeMode.Stretch
            )
            for row_index, employee in enumerate(employees):
                employee_table.insertRow(row_index)
                for column, value in enumerate(employee):
                    employee_table.setItem(
                        row_index, column,
                        QTableWidgetItem("" if value is None else str(value)),
                    )
            employee_layout.addWidget(employee_table)
            root.addWidget(employee_group, 1)

        actions = QHBoxLayout()
        if self.on_register is not None:
            register_button = QPushButton("Đăng ký ca")
            register_button.clicked.connect(self._register)
            actions.addWidget(register_button)

        if self.on_closing_cash is not None:
            cash_button = QPushButton("Ghi tiền cuối ca")
            cash_button.clicked.connect(self._record_closing_cash)
            actions.addWidget(cash_button)

        actions.addStretch()
        close_button = QPushButton("Đóng")
        close_button.clicked.connect(self.reject)
        actions.addWidget(close_button)
        root.addLayout(actions)

    def _register(self):
        """Đóng popup rồi gọi quy trình đăng ký ca hiện có."""
        if self.on_register is None:
            return
        callback = self.on_register
        self.accept()
        callback()

    def _record_closing_cash(self):
        """Đóng popup rồi gọi quy trình ghi tiền cuối ca hiện có."""
        if self.on_closing_cash is None:
            return
        callback = self.on_closing_cash
        self.accept()
        callback()
