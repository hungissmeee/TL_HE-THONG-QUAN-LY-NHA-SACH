"""Các trang báo cáo của BookHub."""

from ui.reports.report_overview import OverviewReportPage
from ui.reports.report_revenue import RevenueReportPage
from ui.reports.report_invoice import InvoiceReportPage
from ui.reports.report_import import ImportReportPage
from ui.reports.report_return import ReturnReportPage
from ui.reports.report_inventory import InventoryReportPage
from ui.reports.report_product import ProductReportPage

__all__ = [
    "OverviewReportPage",
    "RevenueReportPage",
    "InvoiceReportPage",
    "ImportReportPage",
    "ReturnReportPage",
    "InventoryReportPage",
    "ProductReportPage",
]
