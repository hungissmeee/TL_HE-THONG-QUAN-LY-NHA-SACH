"""SupplierFormDialog: thành phần giao diện nghiệp vụ."""

from PySide6.QtCore import Qt, QThread, Signal
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


from database.casso_idkit import CassoIdKitClient, CassoIdKitError


class TaxLookupThread(QThread):
    """Tra cứu MST ở luồng nền để không làm treo giao diện."""

    result_ready = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, tax_code, parent=None):
        super().__init__(parent)
        self.tax_code = tax_code

    def run(self):
        try:
            result = CassoIdKitClient().lookup(self.tax_code)
            self.result_ready.emit(result)
        except (CassoIdKitError, ValueError) as error:
            self.error_occurred.emit(str(error))
        except Exception as error:
            self.error_occurred.emit(f"Không thể tra cứu MST: {error}")


class SupplierFormDialog(QDialog):
    """Thu thập và kiểm tra thông tin trước khi lưu nhà cung cấp."""

    def __init__(self, db, parent=None, supplier=None):
        """Khởi tạo biểu mẫu và nạp dữ liệu nhà cung cấp nếu đang ở chế độ chỉnh sửa."""
        super().__init__(parent)
        self.db = db
        self.supplier = supplier
        self.is_edit = supplier is not None
        self.saved_supplier = None
        self.lookup_thread = None

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
        self.tax_input.setPlaceholderText("Nhập mã số thuế để tra cứu")

        self.lookup_button = QPushButton("Tra cứu MST")
        self.lookup_button.setToolTip(
            "Tự động điền tên và địa chỉ từ Casso IDKit."
        )
        self.lookup_button.clicked.connect(self.lookup_tax_code)
        tax_row = QHBoxLayout()
        tax_row.addWidget(self.tax_input, 1)
        tax_row.addWidget(self.lookup_button)

        self.lookup_status = QLabel("")
        self.lookup_status.setWordWrap(True)
        self.lookup_status.setStyleSheet("color: #9aa4b2;")

        form.addRow("Mã nhà cung cấp:", self.code_input)
        form.addRow("Tên nhà cung cấp *:", self.name_input)
        form.addRow("Số điện thoại:", self.phone_input)
        form.addRow("Địa chỉ:", self.address_input)
        form.addRow("Mã số thuế:", tax_row)
        form.addRow("", self.lookup_status)
        root.addWidget(group)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Đóng")
        cancel.clicked.connect(self.reject)
        self.save_button = QPushButton("Lưu thay đổi" if self.is_edit else "Thêm nhà cung cấp")
        self.save_button.clicked.connect(self.save)
        buttons.addWidget(cancel)
        buttons.addWidget(self.save_button)
        root.addLayout(buttons)

    def closeEvent(self, event):
        """Chờ luồng tra cứu kết thúc trước khi đóng hộp thoại."""
        if self.lookup_thread and self.lookup_thread.isRunning():
            self.lookup_thread.wait()
        super().closeEvent(event)

    def lookup_tax_code(self):
        """Gọi Casso IDKit ở luồng nền và điền thông tin tìm được."""
        tax_code = self.tax_input.text().strip()
        try:
            CassoIdKitClient.validate_tax_code(tax_code)
        except ValueError as error:
            QMessageBox.warning(self, "Mã số thuế không hợp lệ", str(error))
            self.tax_input.setFocus()
            return

        if self.lookup_thread and self.lookup_thread.isRunning():
            return

        self.lookup_button.setEnabled(False)
        self.lookup_status.setText("Đang tra cứu thông tin mã số thuế...")
        self.lookup_thread = TaxLookupThread(tax_code, self)
        self.lookup_thread.result_ready.connect(self._apply_tax_lookup)
        self.lookup_thread.error_occurred.connect(self._show_tax_lookup_error)
        self.lookup_thread.finished.connect(self._finish_tax_lookup)
        self.lookup_thread.start()

    def _apply_tax_lookup(self, result):
        """Điền tên, địa chỉ và MST từ kết quả Casso; không ghi đè số điện thoại."""
        self.tax_input.setText(result.get("tax_code") or self.tax_input.text())
        if result.get("name"):
            self.name_input.setText(result["name"])
        if result.get("address"):
            self.address_input.setText(result["address"])

        status = result.get("status") or "Không có thông tin trạng thái"
        department = result.get("tax_department")
        details = [f"Trạng thái: {status}"]
        if department:
            details.append(f"Cơ quan thuế: {department}")
        self.lookup_status.setText(" | ".join(details))

    def _show_tax_lookup_error(self, message):
        """Hiển thị lỗi tra cứu mà không làm mất dữ liệu nhân viên đã nhập."""
        self.lookup_status.setText(message)
        QMessageBox.warning(self, "Không tra cứu được MST", message)

    def _finish_tax_lookup(self):
        """Khôi phục nút tra cứu sau khi luồng nền kết thúc."""
        self.lookup_button.setEnabled(True)
        self.lookup_thread = None

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



