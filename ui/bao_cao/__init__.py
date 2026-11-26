"""Các trang báo cáo của BookHub."""

from giao_dien.bao_cao.bao_cao_tong_quan import OverviewReportPage
from giao_dien.bao_cao.bao_cao_doanh_thu import RevenueReportPage
from giao_dien.bao_cao.bao_cao_hoa_don import InvoiceReportPage
from giao_dien.bao_cao.bao_cao_phieu_nhap import ImportReportPage
from giao_dien.bao_cao.bao_cao_doi_tra import ReturnReportPage
from giao_dien.bao_cao.bao_cao_ton_kho import InventoryReportPage
from giao_dien.bao_cao.bao_cao_san_pham import ProductReportPage

__all__ = [
    "OverviewReportPage",
    "RevenueReportPage",
    "InvoiceReportPage",
    "ImportReportPage",
    "ReturnReportPage",
    "InventoryReportPage",
    "ProductReportPage",
]
