"""SupplierDetailDialog: thành phần giao diện nghiệp vụ."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
)


class SupplierDetailDialog(QDialog):
    """Hiển thị thông tin liên hệ và trạng thái của nhà cung cấp."""

    def __init__(
        self, supplier, parent=None, can_manage=False,
        on_edit=None, on_deactivate=None, on_restore=None
    ):
        super().__init__(parent)
        self.supplier = supplier
        self.can_manage = can_manage
        self.on_edit = on_edit
        self.on_deactivate = on_deactivate
        self.on_restore = on_restore
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

        buttons = QHBoxLayout()
        if self.can_manage:
            edit_button = QPushButton("Chỉnh sửa")
            edit_button.clicked.connect(self._edit_supplier)
            buttons.addWidget(edit_button)

            if bool(supplier[5]):
                status_button = QPushButton("Kích hoạt lại")
                status_button.clicked.connect(self._restore_supplier)
            else:
                status_button = QPushButton("Ngừng hoạt động")
                status_button.setStyleSheet(
                    "QPushButton { background-color: #A83232; color: white; }"
                )
                status_button.clicked.connect(self._deactivate_supplier)
            buttons.addWidget(status_button)

        buttons.addStretch()
        close_button = QPushButton("Đóng")
        close_button.clicked.connect(self.reject)
        buttons.addWidget(close_button)
        root.addLayout(buttons)

    def _run_action(self, callback):
        """Đóng popup chi tiết trước khi mở biểu mẫu hoặc xác nhận thao tác tiếp theo."""
        if callback is None:
            return
        self.accept()
        callback()

    def _edit_supplier(self):
        self._run_action(self.on_edit)

    def _deactivate_supplier(self):
        self._run_action(self.on_deactivate)

    def _restore_supplier(self):
        self._run_action(self.on_restore)



