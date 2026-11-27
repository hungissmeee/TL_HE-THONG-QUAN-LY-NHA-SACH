"""Hộp thoại xem chi tiết phiếu đổi trả."""

from PySide6.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFormLayout, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView,
)
from .dung_chung import date_text, money
from ui.table_sort import set_table_minimum_section_size
from core.doi_tra.repository import ReturnRepository
from core.doi_tra.service import ReturnService


class ReturnDetailDialog(QDialog):
    """Hiển thị hóa đơn gốc và từng dòng xử lý đổi trả."""

    def __init__(self, db, return_code, parent=None, on_delete=None):
        super().__init__(parent)
        self.db = db
        self.service = ReturnService(ReturnRepository(db))
        self.return_code = return_code
        self.on_delete = on_delete
        self.setWindowTitle(f"Chi tiết phiếu đổi trả {return_code}")
        self.resize(920, 620)
        self.setMinimumSize(780, 520)
        self.header, self.items = self._load_data()
        self._build_ui()

    def _load_data(self):
        data = self.service.get_return_detail(self.return_code)
        return data["header"], data["items"]

    def _delete_return(self):
        """Gọi thao tác xóa từ trang danh sách; đóng chi tiết khi xóa thành công."""
        if self.on_delete and self.on_delete(self.return_code, self):
            self.accept()

    def _build_ui(self):
        root = QVBoxLayout(self)
        title = QLabel(f"PHIẾU ĐỔI TRẢ - {self.header['mapdt']}")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        root.addWidget(title)

        info = QGroupBox("Thông tin phiếu")
        form = QFormLayout(info)
        form.addRow("Mã phiếu:", QLabel(str(self.header["mapdt"])))
        form.addRow("Ngày xử lý:", QLabel(date_text(self.header["ngay"])))
        form.addRow(
            "Hóa đơn gốc:",
            QLabel(f"{self.header['mahd']} | {date_text(self.header['ngay_hd'])}")
        )
        form.addRow(
            "Nhân viên xử lý:",
            QLabel(f"{self.header['tennv']} ({self.header['manv']})")
        )
        form.addRow("Lý do:", QLabel(str(self.header["reason"])))
        root.addWidget(info)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Mã SP", "Tên sản phẩm", "SL", "Tình trạng hàng",
            "Hình thức xử lý", "Thành tiền hoàn"
        ])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        set_table_minimum_section_size(self.table)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        for row_index, item in enumerate(self.items):
            self.table.insertRow(row_index)
            values = [
                item["masp"], item["tensp"], item["quantity"],
                item["condition"], item["action"],
                money(item["line_refund_total"]),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(str(value)))
        root.addWidget(self.table, 1)

        summary = QGroupBox("Tổng kết")
        summary_form = QFormLayout(summary)
        amount = QLabel(f"{money(self.header['refund'])} đ")
        amount.setStyleSheet("font-size: 18px; font-weight: bold; color: #16A34A;")
        summary_form.addRow("Tổng tiền hoàn:", amount)
        root.addWidget(summary)

        buttons = QHBoxLayout()
        buttons.addStretch()
        if self.on_delete is not None:
            delete_button = QPushButton("Xóa phiếu")
            delete_button.setObjectName("dangerButton")
            delete_button.setProperty("buttonRole", "danger")
            delete_button.setToolTip(
                "Xóa phiếu này và đảo ngược biến động tồn kho do phiếu tạo ra."
            )
            delete_button.clicked.connect(self._delete_return)
            buttons.addWidget(delete_button)

        close_button = QPushButton("Đóng")
        close_button.clicked.connect(self.accept)
        buttons.addWidget(close_button)
        root.addLayout(buttons)
