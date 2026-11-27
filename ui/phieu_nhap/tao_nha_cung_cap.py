"""CreateSupplierDialog: thành phần giao diện nghiệp vụ phiếu nhập."""

from core.nha_cung_cap.truy_van_sql import NhaCungCapRepository
from core.nha_cung_cap.xu_ly_du_lieu import NhaCungCapService

from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QMessageBox,
    QGroupBox,
)


class CreateSupplierDialog(QDialog):
    """Hộp thoại thêm nhanh nhà cung cấp trong quy trình lập phiếu nhập."""
    """Thêm nhanh nhà cung cấp để có thể lập phiếu nhập."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.service = NhaCungCapService(NhaCungCapRepository(db))
        self.saved_supplier = None
        self.setWindowTitle("Thêm nhà cung cấp")
        self.setMinimumWidth(460)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        title = QLabel("THÊM NHÀ CUNG CẤP")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        root.addWidget(title)

        form_box = QGroupBox("Thông tin nhà cung cấp")
        form = QFormLayout(form_box)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Tên nhà cung cấp")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Số điện thoại")
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Địa chỉ")
        self.tax_input = QLineEdit()
        self.tax_input.setPlaceholderText("Mã số thuế (nếu có)")
        form.addRow("Tên nhà cung cấp *:", self.name_input)
        form.addRow("Số điện thoại:", self.phone_input)
        form.addRow("Địa chỉ:", self.address_input)
        form.addRow("Mã số thuế:", self.tax_input)
        root.addWidget(form_box)

        buttons = QHBoxLayout()
        buttons.addStretch()
        save = QPushButton("Lưu nhà cung cấp")
        save.clicked.connect(self.save_supplier)
        close = QPushButton("Đóng")
        close.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(close)
        root.addLayout(buttons)

    def save_supplier(self):
        """Lưu nhà cung cấp qua Service; giao diện không tự truy vấn SQL."""
        payload = {
            "name": self.name_input.text(),
            "phone": self.phone_input.text(),
            "address": self.address_input.text(),
            "tax": self.tax_input.text(),
        }
        try:
            code = self.service.save_supplier(payload)
            name = str(payload["name"]).strip()
            self.saved_supplier = (code, name)
            QMessageBox.information(
                self, "Thành công", f"Đã thêm nhà cung cấp {code} - {name}."
            )
            self.accept()
        except (ValueError, LookupError) as error:
            QMessageBox.warning(self, "Thông tin chưa hợp lệ", str(error))
        except Exception as error:
            QMessageBox.critical(self, "Không thể thêm nhà cung cấp", str(error))
