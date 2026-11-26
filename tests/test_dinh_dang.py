"""Kiểm thử các hàm định dạng không phụ thuộc giao diện Qt."""

import unittest
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation

from ui.formatters import (
    format_decimal_money,
    to_invoice_decimal,
    to_import_decimal,
    format_invoice_date,
    format_import_date,
    format_time,
    format_report_money,
    format_number,
    format_report_date,
    format_product_number,
)


class FormatterTests(unittest.TestCase):
    """Kiểm thử kết quả định dạng tiền, ngày tháng và số liệu hiển thị."""
    """Kiểm thử định dạng tiền, ngày giờ và số liệu."""
    def test_money_uses_vietnamese_separators(self):
        self.assertEqual(format_decimal_money("1234567.5"), "1.234.567,50")

    def test_money_invalid_value_falls_back_to_zero(self):
        self.assertEqual(format_decimal_money("invalid"), "0,00")
        self.assertEqual(format_decimal_money(None), "0,00")

    def test_invoice_decimal_rejects_invalid_value(self):
        with self.assertRaises(InvalidOperation):
            to_invoice_decimal("not-a-number")

    def test_import_decimal_keeps_previous_fallback(self):
        self.assertEqual(to_import_decimal("not-a-number"), Decimal("0.00"))

    def test_invoice_date_format(self):
        self.assertEqual(
            format_invoice_date(datetime(2026, 11, 26, 9, 5, 7)),
            "26/11/2026 09:05:07",
        )
        self.assertEqual(
            format_invoice_date(date(2026, 11, 26)),
            "26/11/2026",
        )
        self.assertEqual(format_invoice_date(None), "")

    def test_import_date_format(self):
        self.assertEqual(
            format_import_date(datetime(2026, 11, 26, 9, 5, 7)),
            "26/11/2026 09:05:07",
        )
        self.assertEqual(format_import_date(None), "")

    def test_time_format(self):
        self.assertEqual(format_time(time(9, 5, 7)), "09:05")
        self.assertEqual(format_time("09:05:59"), "09:05")
        self.assertEqual(format_time(None), "")

    def test_report_formatters(self):
        self.assertEqual(format_report_money(2500), "2.500 đ")
        self.assertEqual(format_report_money(2500, decimals=2), "2.500,00 đ")
        self.assertEqual(format_number(2500), "2.500")
        self.assertEqual(
            format_report_date(datetime(2026, 11, 26, 9, 5)),
            "26/11/2026 09:05",
        )
        self.assertEqual(
            format_report_date(date(2026, 11, 26), include_time=False),
            "26/11/2026",
        )

    def test_product_number_format(self):
        self.assertEqual(format_product_number(1234.5), "1.234,50")
        self.assertEqual(format_product_number(None), "")
        self.assertEqual(format_product_number("unknown"), "unknown")


if __name__ == "__main__":
    unittest.main()
