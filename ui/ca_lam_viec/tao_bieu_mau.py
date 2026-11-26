"""ShiftCreateDialog: thành phần giao diện nghiệp vụ."""

from decimal import (
    Decimal,
    InvalidOperation,
)
from PySide6.QtCore import (
    QDate,
    QTime,
)
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QComboBox,
    QFormLayout,
    QDialog,
    QDateEdit,
    QLineEdit,
)


class ShiftCreateDialog(QDialog):
    """Thu thập ngày làm và khung giờ để tạo ca làm việc."""
    """Tạo một trong ba ca cố định mỗi ngày, trong khung 07:00–22:00."""

    SHIFT_SCHEDULE = {
        1: (QTime(7, 0), QTime(12, 0)),
        2: (QTime(12, 0), QTime(17, 0)),
        3: (QTime(17, 0), QTime(22, 0)),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Thêm ca làm việc")
        self.setMinimumWidth(480)

        title = QLabel("THÊM CA LÀM VIỆC")
        title.setStyleSheet("font-size: 19px; font-weight: bold;")

        note = QLabel(
            "Mỗi ngày có tối đa 3 ca cố định: Ca 1 (07:00–12:00), "
            "Ca 2 (12:00–17:00), Ca 3 (17:00–22:00)."
        )
        note.setWordWrap(True)

        self.shift_number = QComboBox()
        self.shift_number.addItem("Ca 1 (07:00 – 12:00)", 1)
        self.shift_number.addItem("Ca 2 (12:00 – 17:00)", 2)
        self.shift_number.addItem("Ca 3 (17:00 – 22:00)", 3)
        self.shift_number.currentIndexChanged.connect(self._update_shift_times)

        self.work_date = QDateEdit()
        self.work_date.setCalendarPopup(True)
        self.work_date.setDisplayFormat("dd/MM/yyyy")
        self.work_date.setDate(QDate.currentDate())
        self.work_date.setMinimumDate(QDate.currentDate())

        self.open_time = QLineEdit()
        self.open_time.setReadOnly(True)

        self.close_time = QLineEdit()
        self.close_time.setReadOnly(True)

        self.opening_cash = QLineEdit("0")
        self.opening_cash.setPlaceholderText("Ví dụ: 500000")

        form = QFormLayout()
        form.setSpacing(12)
        form.addRow("Ca làm việc:", self.shift_number)
        form.addRow("Ngày làm:", self.work_date)
        form.addRow("Giờ mở:", self.open_time)
        form.addRow("Giờ đóng:", self.close_time)
        form.addRow("Tiền đầu ca:", self.opening_cash)

        self.save_button = QPushButton("Tạo ca")
        self.save_button.clicked.connect(self._validate_and_accept)
        self.cancel_button = QPushButton("Hủy")
        self.cancel_button.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.cancel_button)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addSpacing(8)
        layout.addLayout(form)
        layout.addSpacing(12)
        layout.addLayout(buttons)

        self._update_shift_times()

    def _update_shift_times(self, *_):
        shift_number = int(self.shift_number.currentData())
        start, end = self.SHIFT_SCHEDULE[shift_number]
        self.open_time.setText(start.toString("HH:mm"))
        self.close_time.setText(end.toString("HH:mm"))

    @staticmethod
    def _parse_cash(text, field_name):
        text = text.strip().replace(",", "").replace(" ", "")
        if not text:
            raise ValueError(f"Vui lòng nhập {field_name}.")
        try:
            value = Decimal(text)
        except InvalidOperation:
            raise ValueError(f"{field_name} phải là số hợp lệ.")
        if not value.is_finite() or value < 0:
            raise ValueError(f"{field_name} phải lớn hơn hoặc bằng 0.")
        if value > Decimal("9999999999999.99"):
            raise ValueError(f"{field_name} vượt quá giới hạn DECIMAL(15,2).")
        return value.quantize(Decimal("0.01"))

    def _validate_and_accept(self):
        try:
            self.get_values()
        except ValueError as error:
            QMessageBox.warning(self, "Thông tin chưa hợp lệ", str(error))
            return
        self.accept()

    def get_values(self):
        shift_number = int(self.shift_number.currentData())
        start, end = self.SHIFT_SCHEDULE[shift_number]
        opening_cash = self._parse_cash(self.opening_cash.text(), "tiền đầu ca")

        return {
            "soca": shift_number,
            "ngaylam": self.work_date.date().toString("yyyy-MM-dd"),
            "tgmo": start.toString("HH:mm:ss"),
            "tgdong": end.toString("HH:mm:ss"),
            "tmdauca": opening_cash,
            "tmcuoica": None,
        }



