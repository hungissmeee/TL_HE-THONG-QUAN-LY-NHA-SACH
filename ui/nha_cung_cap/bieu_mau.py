"""SupplierFormDialog: thành phần giao diện nghiệp vụ."""

from core.nha_cung_cap.truy_van_sql import NhaCungCapRepository
from core.nha_cung_cap.xu_ly_du_lieu import NhaCungCapService

from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QMessageBox,
    QGroupBox,
)


class SupplierFormDialog(QDialog):
    """Thu thập và kiểm tra thông tin trước khi lưu nhà cung cấp."""

    def __init__(self, db, parent=None, supplier=None):
        """Khởi tạo biểu mẫu và nạp dữ liệu nhà cung cấp nếu đang ở chế độ chỉnh sửa."""
        super().__init__(parent)
        self.db = db
        self.service = NhaCungCapService(NhaCungCapRepository(db))
        self.supplier = supplier
        self.is_edit = supplier is not None
        self.saved_supplier = None

        self.setWindowTitle("Chỉnh sửa nhà cung cấp" if self.is_edit else "Thêm nhà cung cấp")
        self.setMinimumWidth(500)
        self._build_ui()

        if self.is_edit:
            self._populate()
        else:
            self._refresh_code_preview()

    def _build_ui(self):
        """Tạo các trường nhập thông tin, nút lưu và nút hủy."""
        root = QVBoxLayout(self)
        root.setSpacing(12)

        title = QLabel("THÔNG TIN NHÀ CUNG CẤP")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        root.addWidget(title)

        group = QGroupBox("Thông tin chung")
        form = QFormLayout(group)
        form.setSpacing(10)

        self.code_input = QLineEdit()
        self.code_input.setReadOnly(True)
        self.code_input.setPlaceholderText("Mã được tạo tự động")

        self.name_input = QLineEdit()
        self.name_input.setMaxLength(100)
        self.name_input.setPlaceholderText("Nhập tên nhà cung cấp")

        self.phone_input = QLineEdit()
        self.phone_input.setMaxLength(15)
        self.phone_input.setPlaceholderText("Số điện thoại")

        self.address_input = QLineEdit()
        self.address_input.setMaxLength(255)
        self.address_input.setPlaceholderText("Địa chỉ nhà cung cấp")

        self.tax_input = QLineEdit()
        self.tax_input.setMaxLength(20)
        self.tax_input.setPlaceholderText("Mã số thuế (nếu có)")

        form.addRow("Mã nhà cung cấp:", self.code_input)
        form.addRow("Tên nhà cung cấp *:", self.name_input)
        form.addRow("Số điện thoại:", self.phone_input)
        form.addRow("Địa chỉ:", self.address_input)
        form.addRow("Mã số thuế:", self.tax_input)
        root.addWidget(group)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Đóng")
        cancel.clicked.connect(self.reject)
        self.save_button = QPushButton("Lưu thay đổi" if self.is_edit else "Thêm nhà cung cấp")
        self.save_button.setProperty("buttonRole", "primary")
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(self.save)
        buttons.addWidget(cancel)
        buttons.addWidget(self.save_button)
        root.addLayout(buttons)

    def _populate(self):
        """Đưa dữ liệu nhà cung cấp hiện tại lên biểu mẫu chỉnh sửa."""
        row = self.supplier
        self.code_input.setText(str(row[0] or ""))
        self.name_input.setText(str(row[1] or ""))
        self.phone_input.setText(str(row[2] or ""))
        self.address_input.setText(str(row[3] or ""))
        self.tax_input.setText(str(row[4] or ""))

    def _refresh_code_preview(self):
        try:
            self.code_input.setText(self.service.preview_next_code())
        except Exception as error:
            self.code_input.setText("Tự động khi lưu")
            QMessageBox.warning(self, "Không tạo được mã", str(error))

    def save(self):
        data = {
            "name": self.name_input.text(),
            "phone": self.phone_input.text(),
            "address": self.address_input.text(),
            "tax": self.tax_input.text(),
        }
        try:
            code = self.service.save_supplier(
                data,
                supplier_code=self.supplier[0] if self.is_edit else None,
            )
            self.saved_supplier = (code, str(data["name"]).strip())
            QMessageBox.information(
                self, "Thành công",
                f"Đã {'cập nhật' if self.is_edit else 'thêm'} nhà cung cấp {code}.",
            )
            self.accept()
        except (ValueError, LookupError) as error:
            QMessageBox.warning(self, "Thông tin chưa hợp lệ", str(error))
        except Exception as error:
            QMessageBox.critical(self, "Không thể lưu nhà cung cấp", str(error))
