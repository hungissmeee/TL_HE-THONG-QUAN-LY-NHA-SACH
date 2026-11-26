"""Các trang báo cáo của BookHub."""

from ui.bao_cao.bao_cao_tong_quan import OverviewReportPage
from ui.bao_cao.bao_cao_doanh_thu import RevenueReportPage
from ui.bao_cao.bao_cao_hoa_don import InvoiceReportPage
from ui.bao_cao.bao_cao_phieu_nhap import ImportReportPage
from ui.bao_cao.bao_cao_doi_tra import ReturnReportPage
from ui.bao_cao.bao_cao_ton_kho import InventoryReportPage
from ui.bao_cao.bao_cao_san_pham import ProductReportPage

__all__ = [
    "OverviewReportPage",
    "RevenueReportPage",
    "InvoiceReportPage",
    "ImportReportPage",
    "ReturnReportPage",
    "InventoryReportPage",
    "ProductReportPage",
]
