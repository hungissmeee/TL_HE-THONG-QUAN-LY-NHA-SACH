"""SupplierDetailDialog: thành phần giao diện nghiệp vụ."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QFormLayout,
    QGroupBox,
)


class SupplierDetailDialog(QDialog):
    """Hiển thị thông tin chi tiết nhà cung cấp."""

    def __init__(self, supplier, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chi tiết nhà cung cấp")
        self.setMinimumWidth(440)

        root = QVBoxLayout(self)
        title = QLabel("CHI TIẾT NHÀ CUNG CẤP")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        root.addWidget(title)

        form_box = QGroupBox("Thông tin chung")
        form = QFormLayout(form_box)
        labels = ["Mã nhà cung cấp:", "Tên nhà cung cấp:", "Số điện thoại:", "Địa chỉ:", "Mã số thuế:"]
        for label, value in zip(labels, supplier[:5]):
            display = QLabel("" if value is None else str(value))
            display.setWordWrap(True)
            form.addRow(label, display)
        status = QLabel("Ngừng hoạt động" if bool(supplier[5]) else "Đang hoạt động")
        form.addRow("Trạng thái:", status)
        root.addWidget(form_box)

        close_button = QPushButton("Đóng")
        close_button.clicked.connect(self.accept)
        root.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)



