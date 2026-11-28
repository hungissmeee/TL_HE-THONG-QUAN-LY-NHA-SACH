"""Biểu mẫu tạo chương trình khuyến mãi."""

from datetime import datetime
from decimal import Decimal

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QDateTimeEdit,
)
from PySide6.QtCore import QDateTime, QLocale
from core.khuyen_mai.repository import KhuyenMaiRepository
from core.khuyen_mai.service import KhuyenMaiService


class PromotionFormDialog(QDialog):
    """Tạo chương trình khuyến mãi mới; tỷ lệ và thời hạn không sửa sau khi lưu."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.service = KhuyenMaiService(KhuyenMaiRepository(db))
        self.promotion_code = None

        self.setWindowTitle("Thêm chương trình khuyến mãi")
        self.setMinimumWidth(480)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        title = QLabel("THÊM CHƯƠNG TRÌNH KHUYẾN MÃI")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        root.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.name_input = QLineEdit()
        self.name_input.setMaxLength(100)
        self.name_input.setPlaceholderText("Nhập tên chương trình")
        form.addRow("Tên khuyến mãi:", self.name_input)

        self.rate_input = QDoubleSpinBox()
        self.rate_input.setLocale(QLocale.c())
        self.rate_input.setGroupSeparatorShown(False)
        self.rate_input.setRange(0, 100)
        self.rate_input.setDecimals(2)
        self.rate_input.setSingleStep(1)
        self.rate_input.setSuffix(" %")
        form.addRow("Tỷ lệ giảm:", self.rate_input)

        now = QDateTime.currentDateTime()
        self.start_input = QDateTimeEdit(now)
        self.start_input.setCalendarPopup(True)
        self.start_input.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.start_input.setKeyboardTracking(False)
        form.addRow("Ngày và giờ bắt đầu:", self.start_input)

        self.end_input = QDateTimeEdit(now.addDays(30))
        self.end_input.setCalendarPopup(True)
        self.end_input.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.end_input.setKeyboardTracking(False)
        form.addRow("Ngày và giờ kết thúc:", self.end_input)

        time_hint = QLabel(
            "Chọn ngày bằng biểu tượng lịch; chỉnh giờ và phút trực tiếp "
            "trên ô ngày giờ."
        )
        time_hint.setWordWrap(True)
        time_hint.setStyleSheet("color: #AAB7C8; font-size: 13px;")
        form.addRow("", time_hint)

        root.addLayout(form)

        note = QLabel(
            "Sau khi tạo, tỷ lệ giảm và thời hạn được giữ cố định để "
            "không làm thay đổi cách tính của hóa đơn cũ. Muốn ngừng áp dụng, "
            "hãy ngừng áp dụng chương trình trong danh sách."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #AAB7C8; font-size: 13px;")
        root.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save_promotion)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @staticmethod
    def _to_datetime(value):
        """Chuyển QDateTime thành datetime Python để truyền cho pyodbc."""
        return datetime.strptime(
            value.toString("yyyy-MM-dd HH:mm:ss"),
            "%Y-%m-%d %H:%M:%S",
        )

    def save_promotion(self):
        """Kiểm tra và tạo chương trình qua Service/Repository."""
        payload = {
            "name": self.name_input.text(),
            "discount_rate": Decimal(f"{self.rate_input.value():.2f}"),
            "start_at": self._to_datetime(self.start_input.dateTime()),
            "end_at": self._to_datetime(self.end_input.dateTime()),
        }
        try:
            code = self.service.create_promotion(payload, can_manage=True)
            self.promotion_code = code
            QMessageBox.information(
                self, "Thành công",
                f"Đã thêm chương trình khuyến mãi {code}.",
            )
            self.accept()
        except (ValueError, PermissionError) as error:
            QMessageBox.warning(self, "Thông tin chưa hợp lệ", str(error))
        except Exception as error:
            QMessageBox.critical(self, "Không thể thêm khuyến mãi", str(error))
