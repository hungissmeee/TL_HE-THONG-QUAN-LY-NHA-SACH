"""Hộp thoại xem chi tiết phiếu đổi trả."""

from PySide6.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFormLayout, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView,
)
from .dung_chung import date_text, money


class ReturnDetailDialog(QDialog):
    """Hiển thị hóa đơn gốc và từng dòng xử lý đổi trả."""

    def __init__(self, db, return_code, parent=None):
        super().__init__(parent)
        self.db = db
        self.return_code = return_code
        self.setWindowTitle(f"Chi tiết phiếu đổi trả {return_code}")
        self.resize(920, 620)
        self.setMinimumSize(780, 520)
        self.header, self.items = self._load_data()
        self._build_ui()

    def _load_data(self):
        cursor = self.db.get_connection().cursor()
        try:
            cursor.execute("""
                SELECT PDT.MAPDT, PDT.NGAY_DOI_TRA, PDT.LY_DO,
                       PDT.TONG_TIEN_HOAN, PDT.MAHD, PDT.MANV,
                       COALESCE(NV.TENNV, N''), HD.NGAYLAP
                FROM dbo.PHIEU_DOI_TRA PDT
                LEFT JOIN dbo.NHAN_VIEN NV ON NV.MANV = PDT.MANV
                LEFT JOIN dbo.HOA_DON HD ON HD.MAHD = PDT.MAHD
                WHERE PDT.MAPDT = ?
            """, self.return_code)
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("Không tìm thấy phiếu đổi trả.")
            header = {
                "mapdt": row[0], "ngay": row[1], "reason": row[2] or "",
                "refund": row[3] or 0, "mahd": row[4] or "",
                "manv": row[5] or "", "tennv": row[6] or "",
                "ngay_hd": row[7],
            }

            cursor.execute("""
                SELECT CT.MASP,
                       COALESCE(SP.TENSP, N'(Sản phẩm không còn trong danh mục)'),
                       CT.SOLUONG, CT.DONGIAHOAN, CT.VAT,
                       CT.TINHTRANGHANG, CT.HINH_THUC_XU_LY
                FROM dbo.CHI_TIET_DOI_TRA CT
                LEFT JOIN dbo.SAN_PHAM SP ON SP.MASP = CT.MASP
                WHERE CT.MAPDT = ?
                ORDER BY CT.MASP
            """, self.return_code)

            items = []
            for row in cursor.fetchall():
                condition, action = row[5], row[6]
                items.append({
                    "masp": row[0], "tensp": row[1] or "",
                    "quantity": int(row[2] or 0), "unit_refund": row[3] or 0,
                    "vat": row[4] or 0,
                    "condition": (
                        "Còn nguyên vẹn" if condition is not None and int(condition) == 1
                        else "Đã hỏng" if condition is not None else "Chưa ghi nhận"
                    ),
                    "action": (
                        "Đổi sản phẩm cùng mã" if action is not None and int(action) == 1
                        else "Hoàn tiền" if action is not None else "Chưa ghi nhận"
                    ),
                })
            return header, items
        finally:
            cursor.close()

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

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Mã SP", "Tên sản phẩm", "SL", "Tình trạng hàng",
            "Hình thức xử lý", "Đơn giá hoàn", "Thành tiền hoàn"
        ])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        for row_index, item in enumerate(self.items):
            self.table.insertRow(row_index)
            line_total = item["unit_refund"] * item["quantity"]
            values = [
                item["masp"], item["tensp"], item["quantity"],
                item["condition"], item["action"],
                money(item["unit_refund"]), money(line_total),
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
        close_button = QPushButton("Đóng")
        close_button.clicked.connect(self.accept)
        buttons.addWidget(close_button)
        root.addLayout(buttons)
