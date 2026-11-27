"""SupplierFormDialog: thành phần giao diện nghiệp vụ."""

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

    @staticmethod
    def _next_code(cursor, lock_table=False):
        """Sinh mã nhà cung cấp kế tiếp theo dữ liệu đã có trong SQL Server."""
        hint = " WITH (TABLOCKX, HOLDLOCK)" if lock_table else ""
        cursor.execute(f"""
            SELECT COALESCE(
                MAX(TRY_CONVERT(BIGINT, SUBSTRING(MANCC, 4, 17))), 0
            )
            FROM dbo.NHA_CUNG_CAP{hint}
            WHERE UPPER(LEFT(MANCC, 3)) = 'NCC'
              AND TRY_CONVERT(BIGINT, SUBSTRING(MANCC, 4, 17)) IS NOT NULL
        """)
        next_number = int(cursor.fetchone()[0] or 0) + 1
        code = f"NCC{next_number:03d}"
        if len(code) > 20:
            raise ValueError("Mã nhà cung cấp đã vượt quá 20 ký tự.")
        return code

    def _refresh_code_preview(self):
        """Hiển thị trước mã nhà cung cấp sẽ được cấp khi lưu."""
        conn = self.db.get_connection()
        if conn is None:
            return
        cursor = None
        try:
            cursor = conn.cursor()
            self.code_input.setText(self._next_code(cursor))
            conn.commit()
        except Exception as error:
            conn.rollback()
            self.code_input.setText("Tự động khi lưu")
            QMessageBox.warning(self, "Không tạo được mã", str(error))
        finally:
            if cursor is not None:
                cursor.close()

    def save(self):
        """Kiểm tra dữ liệu bắt buộc rồi thêm mới hoặc cập nhật nhà cung cấp."""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên nhà cung cấp.")
            self.name_input.setFocus()
            return

        phone = self.phone_input.text().strip() or None
        address = self.address_input.text().strip() or None
        tax = self.tax_input.text().strip() or None

        conn = self.db.get_connection()
        if conn is None:
            QMessageBox.warning(self, "Thông báo", "Chưa có kết nối SQL Server.")
            return

        cursor = None
        try:
            cursor = conn.cursor()
            if self.is_edit:
                code = str(self.supplier[0])
                cursor.execute("""
                    UPDATE dbo.NHA_CUNG_CAP
                    SET TENNCC = ?, SDT = ?, DIACHI = ?, MST = ?
                    WHERE MANCC = ? AND ISNULL(IS_DELETED, 0) = 0
                """, (name, phone, address, tax, code))
                if cursor.rowcount != 1:
                    raise RuntimeError("Nhà cung cấp không tồn tại hoặc đã ngừng hoạt động.")
            else:
                # Khóa bảng trong transaction để không sinh trùng mã khi có nhiều người thêm cùng lúc.
                code = self._next_code(cursor, lock_table=True)
                cursor.execute("""
                    INSERT INTO dbo.NHA_CUNG_CAP
                        (MANCC, TENNCC, SDT, DIACHI, MST, IS_DELETED)
                    VALUES (?, ?, ?, ?, ?, 0)
                """, (code, name, phone, address, tax))

            conn.commit()
            self.saved_supplier = (code, name)
            QMessageBox.information(
                self, "Thành công",
                f"Đã {'cập nhật' if self.is_edit else 'thêm'} nhà cung cấp {code}."
            )
            self.accept()
        except Exception as error:
            conn.rollback()
            message = str(error)
            if "permission" in message.casefold() or "denied" in message.casefold():
                message += "\n\nTài khoản cần quyền INSERT/UPDATE trên dbo.NHA_CUNG_CAP."
            QMessageBox.critical(self, "Không thể lưu nhà cung cấp", message)
        finally:
            if cursor is not None:
                cursor.close()



