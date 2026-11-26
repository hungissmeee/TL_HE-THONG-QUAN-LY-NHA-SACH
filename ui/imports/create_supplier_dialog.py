"""CreateSupplierDialog: thành phần giao diện nghiệp vụ phiếu nhập."""

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
    """Thêm nhanh nhà cung cấp để có thể lập phiếu nhập."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
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
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên nhà cung cấp.")
            return

        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối SQL Server.")
            return

        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT COALESCE(
                    MAX(TRY_CONVERT(BIGINT, SUBSTRING(MANCC, 4, 17))), 0
                )
                FROM dbo.NHA_CUNG_CAP WITH (TABLOCKX, HOLDLOCK)
                WHERE UPPER(LEFT(MANCC, 3)) = 'NCC'
                  AND TRY_CONVERT(BIGINT, SUBSTRING(MANCC, 4, 17)) IS NOT NULL
            """)
            next_number = int(cursor.fetchone()[0] or 0) + 1
            code = f"NCC{next_number:03d}"
            cursor.execute("""
                INSERT INTO dbo.NHA_CUNG_CAP
                    (MANCC, SDT, TENNCC, DIACHI, MST, IS_DELETED)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (
                code,
                self.phone_input.text().strip() or None,
                name,
                self.address_input.text().strip() or None,
                self.tax_input.text().strip() or None,
            ))
            conn.commit()
            self.saved_supplier = (code, name)
            QMessageBox.information(
                self, "Thành công", f"Đã thêm nhà cung cấp {code} - {name}."
            )
            self.accept()
        except Exception as error:
            conn.rollback()
            QMessageBox.critical(self, "Không thể thêm nhà cung cấp", str(error))
        finally:
            cursor.close()





