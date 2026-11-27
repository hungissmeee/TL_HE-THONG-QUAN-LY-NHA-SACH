"""API nghiệp vụ cho bán hàng, kho, danh mục, nhân sự, ca và báo cáo."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.dependencies import get_db_connection
from backend.security import CurrentUser, get_current_user, require_roles
from core.catalog_config import CATALOGS
from core.repositories.bao_cao_repository import BaoCaoRepository
from core.repositories.ca_lam_viec_repository import CaLamViecRepository
from core.repositories.catalog_repository import CatalogRepository
from core.repositories.doi_tra_repository import ReturnRepository
from core.repositories.hoa_don_repository import HoaDonRepository
from core.repositories.khuyen_mai_repository import KhuyenMaiRepository
from core.repositories.nha_cung_cap_repository import NhaCungCapRepository
from core.repositories.nhan_vien_repository import NhanVienRepository
from core.repositories.phieu_nhap_repository import PhieuNhapRepository
from core.services.bao_cao_service import BaoCaoService
from core.services.ca_lam_viec_service import CaLamViecService
from core.services.catalog_service import CatalogService
from core.services.doi_tra_service import ReturnService
from core.services.hoa_don_service import HoaDonService
from core.services.khuyen_mai_service import KhuyenMaiService
from core.services.nha_cung_cap_service import NhaCungCapService
from core.services.phieu_nhap_service import PhieuNhapService

router = APIRouter(tags=["operations"])

MANAGEMENT_ROLES = require_roles("rl_QuanLy", "rl_NhanVienKho")
MANAGER_ONLY = require_roles("rl_QuanLy")
ACCOUNTANT_ONLY = require_roles("rl_KeToan")
EMPLOYEE_ADMIN = require_roles("admin")
SHIFT_EMPLOYEES = require_roles(
    "rl_QuanLy", "rl_ThuNgan", "rl_NhanVienKho", "rl_KeToan"
)
REPORT_ROLES = require_roles("rl_QuanLy", "rl_KeToan")


def _rows(rows, keys):
    return [dict(zip(keys, row)) for row in rows]


def _raise_api(error: Exception):
    if isinstance(error, LookupError):
        raise HTTPException(status_code=404, detail=str(error)) from None
    if isinstance(error, PermissionError):
        raise HTTPException(status_code=403, detail=str(error)) from None
    if isinstance(error, (ValueError, TypeError)):
        raise HTTPException(status_code=422, detail=str(error)) from None
    if isinstance(error, RuntimeError):
        raise HTTPException(status_code=409, detail=str(error)) from None
    raise error


def _is_admin(user: CurrentUser) -> bool:
    return user.role_code == "admin"


def _role_label(user: CurrentUser) -> str:
    return user.role


class SupplierPayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=15)
    address: str | None = Field(default=None, max_length=255)
    tax: str | None = Field(default=None, max_length=20)


class CatalogPayload(BaseModel):
    values: list[str | None] = Field(min_length=1, max_length=5)


class PromotionPayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    discount_rate: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    start_at: str
    end_at: str


class PromotionRenamePayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ImportLinePayload(BaseModel):
    product_code: str = Field(min_length=1, max_length=20)
    quantity: int = Field(gt=0, le=1000000)
    price: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    vat: Decimal = Field(default=Decimal("0"), ge=0, le=100, max_digits=5, decimal_places=2)


class ImportPayload(BaseModel):
    supplier_code: str = Field(min_length=1, max_length=20)
    supplier_invoice: str | None = Field(default=None, max_length=50)
    import_type: str = Field(min_length=1, max_length=50)
    items: list[ImportLinePayload] = Field(min_length=1, max_length=200)


class InvoiceLinePayload(BaseModel):
    product_code: str = Field(min_length=1, max_length=20)
    quantity: int = Field(gt=0, le=1000000)


class InvoicePayload(BaseModel):
    promotion_code: str | None = Field(default=None, max_length=20)
    cash: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    items: list[InvoiceLinePayload] = Field(min_length=1, max_length=100)


class ReturnLinePayload(BaseModel):
    product_code: str = Field(min_length=1, max_length=20)
    quantity: int = Field(gt=0, le=1000000)
    condition: Literal[0, 1]
    action: Literal[0, 1]


class ReturnPayload(BaseModel):
    invoice_code: str = Field(min_length=1, max_length=20)
    reason: str = Field(min_length=1, max_length=255)
    items: list[ReturnLinePayload] = Field(min_length=1, max_length=100)


class EmployeeProfilePayload(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=15)


class ShiftPayload(BaseModel):
    soca: int = Field(ge=1, le=3)
    ngaylam: date
    tmdauca: Decimal = Field(ge=0, max_digits=15, decimal_places=2)


class ClosingCashPayload(BaseModel):
    amount: Decimal = Field(ge=0, max_digits=15, decimal_places=2)


# ---------------------------------------------------------------------------
# Nhà cung cấp
# ---------------------------------------------------------------------------

@router.get("/suppliers", summary="Danh sách nhà cung cấp")
def list_suppliers(
    keyword: str = Query(default="", max_length=100),
    show_inactive: bool = False,
    _user: CurrentUser = Depends(get_current_user),
    connection=Depends(get_db_connection),
):
    rows = NhaCungCapService(NhaCungCapRepository(connection)).list_suppliers(
        keyword, show_inactive
    )
    return _rows(rows, ("mancc", "tenncc", "sdt", "diachi", "mst", "is_deleted"))


@router.get("/suppliers/next-code", summary="Mã nhà cung cấp tiếp theo")
def supplier_next_code(
    _user: CurrentUser = Depends(MANAGEMENT_ROLES),
    connection=Depends(get_db_connection),
):
    return {"code": NhaCungCapService(NhaCungCapRepository(connection)).preview_next_code()}


@router.get("/suppliers/{supplier_code}", summary="Chi tiết nhà cung cấp")
def get_supplier(
    supplier_code: str,
    _user: CurrentUser = Depends(get_current_user),
    connection=Depends(get_db_connection),
):
    row = NhaCungCapService(NhaCungCapRepository(connection)).get_supplier(supplier_code)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhà cung cấp.")
    return dict(zip(("mancc", "tenncc", "sdt", "diachi", "mst", "is_deleted"), row))


@router.post("/suppliers", status_code=status.HTTP_201_CREATED, summary="Thêm nhà cung cấp")
def create_supplier(
    payload: SupplierPayload,
    _user: CurrentUser = Depends(MANAGEMENT_ROLES),
    connection=Depends(get_db_connection),
):
    try:
        code = NhaCungCapService(NhaCungCapRepository(connection)).save_supplier(payload.dict())
        return {"code": code, "message": "Đã thêm nhà cung cấp."}
    except Exception as error:
        _raise_api(error)


@router.put("/suppliers/{supplier_code}", summary="Cập nhật nhà cung cấp")
def update_supplier(
    supplier_code: str,
    payload: SupplierPayload,
    _user: CurrentUser = Depends(MANAGEMENT_ROLES),
    connection=Depends(get_db_connection),
):
    try:
        code = NhaCungCapService(NhaCungCapRepository(connection)).save_supplier(
            payload.dict(), supplier_code=supplier_code
        )
        return {"code": code, "message": "Đã cập nhật nhà cung cấp."}
    except Exception as error:
        _raise_api(error)


@router.patch("/suppliers/{supplier_code}/status", summary="Ngừng hoặc kích hoạt nhà cung cấp")
def set_supplier_status(
    supplier_code: str,
    inactive: bool = Query(...),
    _user: CurrentUser = Depends(MANAGEMENT_ROLES),
    connection=Depends(get_db_connection),
):
    try:
        changed = NhaCungCapService(NhaCungCapRepository(connection)).set_supplier_status(
            supplier_code, inactive
        )
        if not changed:
            raise HTTPException(status_code=409, detail="Trạng thái nhà cung cấp đã thay đổi. Hãy tải lại.")
        return {"code": supplier_code, "is_deleted": inactive}
    except HTTPException:
        raise
    except Exception as error:
        _raise_api(error)


# ---------------------------------------------------------------------------
# Danh mục tác giả, thể loại, nhà xuất bản, thương hiệu
# ---------------------------------------------------------------------------

@router.get("/catalogs/{catalog_type}", summary="Danh sách danh mục")
def list_catalog(
    catalog_type: str,
    keyword: str = Query(default="", max_length=100),
    _user: CurrentUser = Depends(get_current_user),
    connection=Depends(get_db_connection),
):
    if catalog_type not in CATALOGS:
        raise HTTPException(status_code=404, detail="Loại danh mục không hợp lệ.")
    try:
        service = CatalogService(CatalogRepository(connection, catalog_type))
        config = CATALOGS[catalog_type]
        return {
            "title": config["title"],
            "fields": [
                {"key": f[0], "label": f[1].rstrip(":"), "required": f[4]}
                for f in config["fields"]
            ],
            "items": service.list_records(keyword),
        }
    except Exception as error:
        _raise_api(error)


@router.get("/catalogs/{catalog_type}/next-code", summary="Mã danh mục tiếp theo")
def catalog_next_code(
    catalog_type: str,
    _user: CurrentUser = Depends(MANAGEMENT_ROLES),
    connection=Depends(get_db_connection),
):
    if catalog_type not in CATALOGS:
        raise HTTPException(status_code=404, detail="Loại danh mục không hợp lệ.")
    return {"code": CatalogService(CatalogRepository(connection, catalog_type)).preview_next_code()}


@router.post("/catalogs/{catalog_type}", status_code=status.HTTP_201_CREATED, summary="Thêm danh mục")
def create_catalog(
    catalog_type: str,
    payload: CatalogPayload,
    _user: CurrentUser = Depends(MANAGEMENT_ROLES),
    connection=Depends(get_db_connection),
):
    if catalog_type not in CATALOGS:
        raise HTTPException(status_code=404, detail="Loại danh mục không hợp lệ.")
    try:
        code = CatalogService(CatalogRepository(connection, catalog_type)).create_record(payload.values)
        return {"code": code, "message": "Đã thêm danh mục."}
    except Exception as error:
        _raise_api(error)


@router.put("/catalogs/{catalog_type}/{record_id}", summary="Cập nhật danh mục")
def update_catalog(
    catalog_type: str,
    record_id: str,
    payload: CatalogPayload,
    _user: CurrentUser = Depends(MANAGEMENT_ROLES),
    connection=Depends(get_db_connection),
):
    if catalog_type not in CATALOGS:
        raise HTTPException(status_code=404, detail="Loại danh mục không hợp lệ.")
    try:
        changed = CatalogService(CatalogRepository(connection, catalog_type)).update_record(
            record_id, payload.values
        )
        if not changed:
            raise HTTPException(status_code=404, detail="Danh mục không tồn tại hoặc đã bị xóa.")
        return {"code": record_id, "message": "Đã cập nhật danh mục."}
    except HTTPException:
        raise
    except Exception as error:
        _raise_api(error)


@router.delete("/catalogs/{catalog_type}/{record_id}", summary="Xóa mềm danh mục")
def delete_catalog(
    catalog_type: str,
    record_id: str,
    _user: CurrentUser = Depends(MANAGEMENT_ROLES),
    connection=Depends(get_db_connection),
):
    if catalog_type not in CATALOGS:
        raise HTTPException(status_code=404, detail="Loại danh mục không hợp lệ.")
    try:
        changed = CatalogService(CatalogRepository(connection, catalog_type)).soft_delete(record_id)
        if not changed:
            raise HTTPException(status_code=404, detail="Danh mục không tồn tại hoặc đã bị xóa.")
        return {"code": record_id, "message": "Đã xóa mềm danh mục."}
    except HTTPException:
        raise
    except Exception as error:
        _raise_api(error)


# ---------------------------------------------------------------------------
# Khuyến mãi - dùng role do API xác thực, không dựa vào SQL login dịch vụ.
# ---------------------------------------------------------------------------

class _WebAuthorizedPromotionRepository(KhuyenMaiRepository):
    @staticmethod
    def _require_manager(_cursor):
        return None


@router.get("/promotions", summary="Danh sách khuyến mãi")
def list_promotions(
    keyword: str = Query(default="", max_length=100),
    show_deleted: bool = False,
    _user: CurrentUser = Depends(get_current_user),
    connection=Depends(get_db_connection),
):
    rows = KhuyenMaiService(_WebAuthorizedPromotionRepository(connection)).list_promotions(
        keyword, show_deleted
    )
    return _rows(rows, ("makm", "tenkm", "tylegiam", "ngaybd", "ngaykt", "is_deleted", "status"))


@router.get("/promotions/next-code", summary="Mã khuyến mãi tiếp theo")
def promotion_next_code(
    _user: CurrentUser = Depends(MANAGER_ONLY),
    connection=Depends(get_db_connection),
):
    return {"code": KhuyenMaiService(_WebAuthorizedPromotionRepository(connection)).preview_next_code()}


@router.post("/promotions", status_code=status.HTTP_201_CREATED, summary="Tạo khuyến mãi")
def create_promotion(
    payload: PromotionPayload,
    _user: CurrentUser = Depends(MANAGER_ONLY),
    connection=Depends(get_db_connection),
):
    try:
        code = KhuyenMaiService(_WebAuthorizedPromotionRepository(connection)).create_promotion(
            payload.dict(), can_manage=True
        )
        return {"code": code, "message": "Đã tạo chương trình khuyến mãi."}
    except Exception as error:
        _raise_api(error)


@router.put("/promotions/{promotion_code}", summary="Đổi tên khuyến mãi")
def rename_promotion(
    promotion_code: str,
    payload: PromotionRenamePayload,
    _user: CurrentUser = Depends(MANAGER_ONLY),
    connection=Depends(get_db_connection),
):
    try:
        code = KhuyenMaiService(_WebAuthorizedPromotionRepository(connection)).rename_promotion(
            promotion_code, payload.name, can_manage=True
        )
        return {"code": code, "message": "Đã cập nhật tên khuyến mãi."}
    except Exception as error:
        _raise_api(error)


@router.delete("/promotions/{promotion_code}", summary="Ngừng áp dụng khuyến mãi")
def delete_promotion(
    promotion_code: str,
    _user: CurrentUser = Depends(MANAGER_ONLY),
    connection=Depends(get_db_connection),
):
    try:
        KhuyenMaiService(_WebAuthorizedPromotionRepository(connection)).soft_delete_promotion(
            promotion_code, can_manage=True
        )
        return {"code": promotion_code, "message": "Đã ngừng áp dụng khuyến mãi."}
    except Exception as error:
        _raise_api(error)


# ---------------------------------------------------------------------------
# Phiếu nhập kho
# ---------------------------------------------------------------------------

@router.get("/imports/lookups", summary="Dữ liệu lập phiếu nhập")
def import_lookups(
    _user: CurrentUser = Depends(MANAGEMENT_ROLES),
    connection=Depends(get_db_connection),
):
    service = PhieuNhapService(PhieuNhapRepository(connection))
    return {
        "suppliers": [
            {"code": code, "name": name}
            for code, name in service.list_suppliers_for_import()
        ],
        "products": service.list_products_for_import(),
    }


@router.get("/imports", summary="Danh sách phiếu nhập")
def list_imports(
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    keyword: str = Query(default="", max_length=100),
    _user: CurrentUser = Depends(get_current_user),
    connection=Depends(get_db_connection),
):
    try:
        rows = PhieuNhapService(PhieuNhapRepository(connection)).list_imports(
            start_date.isoformat(), end_date.isoformat(), keyword
        )
        return _rows(
            rows,
            ("mapn", "ngaynhap", "manv", "tennv", "mancc", "tenncc",
             "loai", "shdncc", "tongtrigia", "trangthai"),
        )
    except Exception as error:
        _raise_api(error)


@router.get("/imports/{import_code}", summary="Chi tiết phiếu nhập")
def get_import_detail(
    import_code: str,
    _user: CurrentUser = Depends(get_current_user),
    connection=Depends(get_db_connection),
):
    try:
        return PhieuNhapService(PhieuNhapRepository(connection)).get_import_detail(import_code)
    except Exception as error:
        _raise_api(error)


@router.post("/imports", status_code=status.HTTP_201_CREATED, summary="Lập phiếu nhập")
def create_import(
    payload: ImportPayload,
    user: CurrentUser = Depends(MANAGEMENT_ROLES),
    connection=Depends(get_db_connection),
):
    try:
        data = payload.dict()
        data["employee_code"] = user.employee_code
        code = PhieuNhapService(PhieuNhapRepository(connection)).create_import(data)
        return {"code": code, "message": "Đã lập phiếu nhập thành công."}
    except Exception as error:
        _raise_api(error)


@router.post("/imports/{import_code}/cancel", summary="Hủy phiếu nhập")
def cancel_import(
    import_code: str,
    user: CurrentUser = Depends(MANAGEMENT_ROLES),
    connection=Depends(get_db_connection),
):
    try:
        PhieuNhapService(PhieuNhapRepository(connection)).cancel_import(
            import_code, user.employee_code, _role_label(user), is_admin=_is_admin(user)
        )
        return {"code": import_code, "message": "Đã hủy phiếu nhập và hoàn tác tồn kho."}
    except Exception as error:
        _raise_api(error)


# ---------------------------------------------------------------------------
# Hóa đơn bán hàng
# ---------------------------------------------------------------------------

@router.get("/invoices/lookups", summary="Dữ liệu lập hóa đơn")
def invoice_lookups(
    user: CurrentUser = Depends(get_current_user),
    connection=Depends(get_db_connection),
):
    service = HoaDonService(HoaDonRepository(connection))
    is_admin = _is_admin(user)
    try:
        shift_data = service.get_employee_and_active_shift(user.employee_code, is_admin=is_admin)
        return {
            "employee": shift_data["employee"],
            "active_shift": shift_data["active_shift"],
            "promotions": service.list_active_promotions(),
            "products": service.list_available_products(),
        }
    except Exception as error:
        _raise_api(error)


@router.get("/invoices", summary="Danh sách hóa đơn")
def list_invoices(
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    keyword: str = Query(default="", max_length=100),
    _user: CurrentUser = Depends(get_current_user),
    connection=Depends(get_db_connection),
):
    try:
        rows = HoaDonService(HoaDonRepository(connection)).list_invoices(
            start_date.isoformat(), end_date.isoformat(), keyword
        )
        return _rows(
            rows,
            ("mahd", "ngaylap", "manv", "tennv", "maca", "soca",
             "tienkhachdua", "tongtien", "trangthai"),
        )
    except Exception as error:
        _raise_api(error)


@router.get("/invoices/{invoice_code}", summary="Chi tiết hóa đơn")
def get_invoice_detail(
    invoice_code: str,
    _user: CurrentUser = Depends(get_current_user),
    connection=Depends(get_db_connection),
):
    try:
        detail = HoaDonService(HoaDonRepository(connection)).get_invoice_detail(invoice_code)
        if detail is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy hóa đơn.")
        return detail
    except HTTPException:
        raise
    except Exception as error:
        _raise_api(error)


@router.post("/invoices", status_code=status.HTTP_201_CREATED, summary="Lập hóa đơn")
def create_invoice(
    payload: InvoicePayload,
    user: CurrentUser = Depends(get_current_user),
    connection=Depends(get_db_connection),
):
    try:
        service = HoaDonService(HoaDonRepository(connection))
        is_admin = _is_admin(user)
        shift_data = service.get_employee_and_active_shift(user.employee_code, is_admin=is_admin)
        products = {
            item["masp"]: item
            for item in service.list_available_products()
        }
        cart = {}
        for line in payload.items:
            if line.product_code in cart:
                raise ValueError(f"Sản phẩm {line.product_code} bị lặp trong giỏ hàng.")
            product = products.get(line.product_code)
            if product is None:
                raise ValueError(f"Sản phẩm {line.product_code} không còn bán hoặc hết tồn.")
            cart[line.product_code] = {
                "quantity": line.quantity,
                "price": product["price"],
                "vat": product["vat"],
                "stock": product["stock"],
            }

        promotion_code = payload.promotion_code or None
        discount_rate = Decimal("0")
        if promotion_code:
            active = {
                str(row[0]): Decimal(str(row[2]))
                for row in service.list_active_promotions()
            }
            if promotion_code not in active:
                raise ValueError("Khuyến mãi đã hết hạn hoặc không còn hiệu lực.")
            discount_rate = active[promotion_code]

        data = {
            "employee": shift_data["employee"],
            "active_shift": shift_data["active_shift"],
            "cart": cart,
            "promotion_code": promotion_code,
            "discount_rate": discount_rate,
            "cash": payload.cash,
        }
        code = service.create_invoice(data, is_admin=is_admin)
        return {"code": code, "message": "Đã lập hóa đơn thành công."}
    except Exception as error:
        _raise_api(error)


@router.post("/invoices/{invoice_code}/cancel", summary="Hủy hóa đơn")
def cancel_invoice(
    invoice_code: str,
    user: CurrentUser = Depends(get_current_user),
    connection=Depends(get_db_connection),
):
    if user.role_code not in {"admin", "rl_QuanLy", "rl_ThuNgan"}:
        raise HTTPException(status_code=403, detail="Bạn không có quyền hủy hóa đơn.")
    try:
        HoaDonService(HoaDonRepository(connection)).cancel_invoice(
            invoice_code, user.employee_code, _role_label(user), is_admin=_is_admin(user)
        )
        return {"code": invoice_code, "message": "Đã hủy hóa đơn và hoàn kho."}
    except Exception as error:
        _raise_api(error)


# ---------------------------------------------------------------------------
# Đổi trả - chỉ Quản lý/Admin mới được lập và xóa phiếu theo quy tắc Desktop.
# ---------------------------------------------------------------------------

@router.get("/returns/eligible-invoices", summary="Hóa đơn đủ điều kiện đổi trả")
def eligible_return_invoices(
    _user: CurrentUser = Depends(MANAGER_ONLY),
    connection=Depends(get_db_connection),
):
    return [
        {"mahd": code, "ngaylap": created_at}
        for code, created_at in ReturnService(ReturnRepository(connection)).list_eligible_invoices()
    ]


@router.get("/returns/invoices/{invoice_code}/items", summary="Sản phẩm trên hóa đơn được đổi trả")
def return_invoice_items(
    invoice_code: str,
    _user: CurrentUser = Depends(MANAGER_ONLY),
    connection=Depends(get_db_connection),
):
    try:
        return ReturnService(ReturnRepository(connection)).get_invoice_items(invoice_code)
    except Exception as error:
        _raise_api(error)


@router.get("/returns", summary="Danh sách phiếu đổi trả")
def list_returns(
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    keyword: str = Query(default="", max_length=100),
    _user: CurrentUser = Depends(get_current_user),
    connection=Depends(get_db_connection),
):
    try:
        rows = ReturnService(ReturnRepository(connection)).list_returns(
            start_date.isoformat(), end_date.isoformat(), keyword
        )
        return _rows(rows, ("mapdt", "ngay", "mahd", "tennv", "lydo", "tongsoluong", "tonghoan"))
    except Exception as error:
        _raise_api(error)


@router.get("/returns/{return_code}", summary="Chi tiết phiếu đổi trả")
def get_return_detail(
    return_code: str,
    _user: CurrentUser = Depends(get_current_user),
    connection=Depends(get_db_connection),
):
    try:
        return ReturnService(ReturnRepository(connection)).get_return_detail(return_code)
    except Exception as error:
        _raise_api(error)


@router.post("/returns", status_code=status.HTTP_201_CREATED, summary="Lập phiếu đổi trả")
def create_return(
    payload: ReturnPayload,
    user: CurrentUser = Depends(MANAGER_ONLY),
    connection=Depends(get_db_connection),
):
    try:
        data = payload.dict()
        result = ReturnService(ReturnRepository(connection)).create_return(
            data, user.employee_code, is_admin=True
        )
        return {
            "code": result["return_code"],
            "invoice_code": result["invoice_code"],
            "total_refund": result["total_refund"],
            "message": "Đã lập phiếu đổi trả.",
        }
    except Exception as error:
        _raise_api(error)


@router.delete("/returns/{return_code}", summary="Xóa phiếu đổi trả")
def delete_return(
    return_code: str,
    user: CurrentUser = Depends(MANAGER_ONLY),
    connection=Depends(get_db_connection),
):
    try:
        ReturnService(ReturnRepository(connection)).delete_return(
            return_code, user.employee_code, is_admin=True
        )
        return {"code": return_code, "message": "Đã xóa phiếu và đảo biến động kho."}
    except Exception as error:
        _raise_api(error)


# ---------------------------------------------------------------------------
# Nhân viên. Tài khoản SQL/role/login được quản lý qua quy trình quản trị riêng.
# ---------------------------------------------------------------------------

@router.get("/employees", summary="Danh sách nhân viên")
def list_employees(
    keyword: str = Query(default="", max_length=100),
    _user: CurrentUser = Depends(EMPLOYEE_ADMIN),
    connection=Depends(get_db_connection),
):
    rows = NhanVienRepository(connection).list_employees(keyword)
    return _rows(rows, ("manv", "tennv", "vaitro", "sdt"))


@router.get("/employees/{employee_code}", summary="Chi tiết hồ sơ nhân viên")
def get_employee(
    employee_code: str,
    _user: CurrentUser = Depends(EMPLOYEE_ADMIN),
    connection=Depends(get_db_connection),
):
    row = NhanVienRepository(connection).get_employee(employee_code)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhân viên.")
    return dict(zip(("manv", "tennv", "vaitro", "sdt"), row))


@router.put("/employees/{employee_code}", summary="Cập nhật thông tin liên hệ nhân viên")
def update_employee_profile(
    employee_code: str,
    payload: EmployeeProfilePayload,
    _user: CurrentUser = Depends(EMPLOYEE_ADMIN),
    connection=Depends(get_db_connection),
):
    cursor = connection.cursor()
    try:
        cursor.execute(
            "UPDATE dbo.NHAN_VIEN SET TENNV = ?, SDT = ? WHERE MANV = ?",
            payload.full_name.strip(), str(payload.phone or "").strip() or None, employee_code,
        )
        if cursor.rowcount != 1:
            connection.rollback()
            raise HTTPException(status_code=404, detail="Không tìm thấy nhân viên.")
        connection.commit()
        return {"manv": employee_code, "message": "Đã cập nhật hồ sơ nhân viên."}
    except HTTPException:
        raise
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


# ---------------------------------------------------------------------------
# Ca làm việc
# ---------------------------------------------------------------------------

@router.get("/shifts/summary", summary="Tổng quan ca làm việc")
def shift_summary(
    _user: CurrentUser = Depends(MANAGER_ONLY),
    connection=Depends(get_db_connection),
):
    return CaLamViecService(CaLamViecRepository(connection)).get_manager_summary()


@router.get("/shifts/current", summary="Ca đang diễn ra")
def current_shifts(
    _user: CurrentUser = Depends(MANAGER_ONLY),
    connection=Depends(get_db_connection),
):
    rows = CaLamViecService(CaLamViecRepository(connection)).list_current_shifts()
    return _rows(rows, ("maca", "ngaylam", "soca", "tgmo", "tgdong", "so_nhan_vien", "tmcuoica"))


@router.get("/shifts/history", summary="Lịch sử ca làm việc")
def shift_history(
    period: Literal["all", "today", "7days", "30days"] = "all",
    _user: CurrentUser = Depends(MANAGER_ONLY),
    connection=Depends(get_db_connection),
):
    rows = CaLamViecService(CaLamViecRepository(connection)).list_shift_history(period)
    return _rows(
        rows,
        ("maca", "ngaylam", "soca", "tgmo", "tgdong", "so_nhan_vien",
         "tmdauca", "tmcuoica", "trangthai"),
    )


@router.get("/shifts/me", summary="Ca hiện tại dành cho nhân viên")
def my_shifts(
    user: CurrentUser = Depends(SHIFT_EMPLOYEES),
    connection=Depends(get_db_connection),
):
    is_accountant = user.role_code in {"rl_KeToan", "admin"}
    rows = CaLamViecService(CaLamViecRepository(connection)).list_employee_shifts(
        user.employee_code, is_accountant=is_accountant
    )
    return _rows(
        rows,
        ("maca", "soca", "ngaylam", "tgmo", "tgdong", "so_nhan_vien",
         "is_registered", "tmcuoica", "is_ended"),
    )


@router.get("/shifts/{shift_id}/roster", summary="Danh sách nhân viên trong ca")
def shift_roster(
    shift_id: int,
    _user: CurrentUser = Depends(MANAGER_ONLY),
    connection=Depends(get_db_connection),
):
    rows = CaLamViecService(CaLamViecRepository(connection)).get_shift_roster(shift_id)
    return _rows(rows, ("manv", "tennv", "vaitro", "sdt"))


@router.post("/shifts", status_code=status.HTTP_201_CREATED, summary="Tạo ca làm việc")
def create_shift(
    payload: ShiftPayload,
    user: CurrentUser = Depends(MANAGER_ONLY),
    connection=Depends(get_db_connection),
):
    try:
        shift_id = CaLamViecService(CaLamViecRepository(connection)).create_shift(
            payload.dict(), is_manager=True
        )
        return {"maca": shift_id, "message": "Đã tạo ca làm việc."}
    except Exception as error:
        _raise_api(error)


@router.delete("/shifts/{shift_id}", summary="Xóa ca chưa bắt đầu")
def delete_shift(
    shift_id: int,
    _user: CurrentUser = Depends(MANAGER_ONLY),
    connection=Depends(get_db_connection),
):
    try:
        CaLamViecService(CaLamViecRepository(connection)).delete_shift(
            shift_id, is_manager=True
        )
        return {"maca": shift_id, "message": "Đã xóa ca làm việc."}
    except Exception as error:
        _raise_api(error)


@router.post("/shifts/{shift_id}/register", summary="Đăng ký ca đang diễn ra")
def register_shift(
    shift_id: int,
    user: CurrentUser = Depends(SHIFT_EMPLOYEES),
    connection=Depends(get_db_connection),
):
    """Kiểm tra thời gian/ca trùng theo SQL Server, sử dụng MANV từ JWT."""
    sql = """
        SET XACT_ABORT ON;
        DECLARE @Maca INT = ?;
        DECLARE @Manv VARCHAR(20) = ?;
        DECLARE @Now DATETIME2 = SYSDATETIME();
        DECLARE @WorkDate DATE;
        DECLARE @StartTime TIME;
        DECLARE @EndTime TIME;
        DECLARE @StartAt DATETIME2;
        DECLARE @EndAt DATETIME2;
        DECLARE @ClosingCash DECIMAL(15,2);

        SELECT
            @WorkDate = CAST(NGAYLAM AS DATE),
            @StartTime = TGMO,
            @EndTime = TGDONG,
            @ClosingCash = TMCUOICA
        FROM dbo.CA_LAM_VIEC WITH (UPDLOCK, HOLDLOCK)
        WHERE MACA = @Maca;

        IF @WorkDate IS NULL OR @StartTime IS NULL OR @EndTime IS NULL
            THROW 51101, N'Không tìm thấy ca hoặc ca chưa được cấu hình giờ làm.', 1;

        SET @StartAt = DATEADD(SECOND,
            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), @StartTime),
            CAST(@WorkDate AS DATETIME2));
        SET @EndAt = DATEADD(SECOND,
            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), @EndTime),
            DATEADD(DAY, CASE WHEN @EndTime <= @StartTime THEN 1 ELSE 0 END,
                CAST(@WorkDate AS DATETIME2)));

        IF NOT (@Now >= @StartAt AND @Now < @EndAt)
            THROW 51102, N'Chỉ được đăng ký ca đang diễn ra.', 1;
        IF @ClosingCash IS NOT NULL
            THROW 51103, N'Ca này đã được chốt.', 1;
        IF NOT EXISTS (SELECT 1 FROM dbo.NHAN_VIEN WHERE MANV = @Manv)
            THROW 51106, N'Không tìm thấy hồ sơ nhân viên.', 1;
        IF EXISTS (SELECT 1 FROM dbo.LAMCA WHERE MANV = @Manv AND MACA = @Maca)
            THROW 51104, N'Bạn đã đăng ký ca này rồi.', 1;

        IF EXISTS (
            SELECT 1
            FROM dbo.LAMCA L
            INNER JOIN dbo.CA_LAM_VIEC C ON C.MACA = L.MACA
            CROSS APPLY (
                SELECT
                    DATEADD(SECOND, DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGMO),
                        CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)) AS ExistingStartAt,
                    DATEADD(SECOND, DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGDONG),
                        DATEADD(DAY, CASE WHEN C.TGDONG <= C.TGMO THEN 1 ELSE 0 END,
                            CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2))) AS ExistingEndAt
            ) E
            WHERE L.MANV = @Manv AND C.MACA <> @Maca
              AND C.TGMO IS NOT NULL AND C.TGDONG IS NOT NULL
              AND @StartAt < E.ExistingEndAt AND @EndAt > E.ExistingStartAt
        )
            THROW 51105, N'Ca này bị trùng thời gian với ca bạn đã đăng ký.', 1;

        INSERT INTO dbo.LAMCA (MANV, MACA) VALUES (@Manv, @Maca);
    """
    cursor = connection.cursor()
    try:
        cursor.execute(sql, int(shift_id), user.employee_code)
        connection.commit()
        return {"maca": shift_id, "message": "Đã đăng ký ca."}
    except Exception as error:
        connection.rollback()
        _raise_api(ValueError(str(error)))
    finally:
        cursor.close()


@router.post("/shifts/{shift_id}/closing-cash", summary="Ghi tiền cuối ca")
def record_shift_cash(
    shift_id: int,
    payload: ClosingCashPayload,
    user: CurrentUser = Depends(get_current_user),
    connection=Depends(get_db_connection),
):
    if user.role_code not in {"admin", "rl_KeToan"}:
        raise HTTPException(status_code=403, detail="Chỉ Kế toán/Admin được ghi tiền cuối ca.")
    sql = """
        SET XACT_ABORT ON;
        DECLARE @Maca INT = ?;
        DECLARE @Manv VARCHAR(20) = ?;
        DECLARE @Cash DECIMAL(15,2) = ?;
        DECLARE @Now DATETIME2 = SYSDATETIME();
        DECLARE @WorkDate DATE;
        DECLARE @StartTime TIME;
        DECLARE @EndTime TIME;
        DECLARE @EndAt DATETIME2;
        DECLARE @ExistingCash DECIMAL(15,2);

        IF LOWER(@Manv) <> N'admin' AND NOT EXISTS (
            SELECT 1 FROM dbo.NHAN_VIEN
            WHERE MANV = @Manv AND LTRIM(RTRIM(VAITRO)) = N'Kế toán'
        )
            THROW 51201, N'Chỉ nhân viên có vai trò Kế toán được ghi tiền cuối ca.', 1;

        SELECT @WorkDate = CAST(NGAYLAM AS DATE), @StartTime = TGMO,
               @EndTime = TGDONG, @ExistingCash = TMCUOICA
        FROM dbo.CA_LAM_VIEC WITH (UPDLOCK, HOLDLOCK)
        WHERE MACA = @Maca;

        IF @WorkDate IS NULL OR @EndTime IS NULL OR @StartTime IS NULL
            THROW 51202, N'Không tìm thấy ca hoặc ca chưa có giờ làm hợp lệ.', 1;

        SET @EndAt = DATEADD(SECOND,
            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), @EndTime),
            DATEADD(DAY, CASE WHEN @EndTime <= @StartTime THEN 1 ELSE 0 END,
                CAST(@WorkDate AS DATETIME2)));

        IF @Now < @EndAt
            THROW 51203, N'Chỉ được ghi tiền sau khi ca đã kết thúc.', 1;
        IF @ExistingCash IS NOT NULL
            THROW 51204, N'Tiền cuối ca đã được ghi trước đó.', 1;

        UPDATE dbo.CA_LAM_VIEC
        SET TMCUOICA = @Cash
        WHERE MACA = @Maca AND TMCUOICA IS NULL;
        IF @@ROWCOUNT <> 1
            THROW 51205, N'Ca đã được chốt bởi kế toán khác.', 1;
    """
    cursor = connection.cursor()
    try:
        cursor.execute(sql, shift_id, user.employee_code, payload.amount)
        connection.commit()
        return {"maca": shift_id, "message": "Đã ghi tiền cuối ca."}
    except Exception as error:
        connection.rollback()
        _raise_api(ValueError(str(error)))
    finally:
        cursor.close()


# ---------------------------------------------------------------------------
# Báo cáo
# ---------------------------------------------------------------------------

REPORT_COLUMNS = {
    "report_trend": (
        "ngay", "so_hoa_don", "so_luong_ban", "doanh_thu", "tien_hoan",
        "doanh_thu_sau_hoan",
    ),
    "report_top_products": ("masp", "tensp", "so_luong", "doanh_thu"),
    "report_revenue": (
        "ky", "so_hoa_don", "tien_hang", "tien_giam", "doanh_thu",
        "tien_hoan", "doanh_thu_sau_hoan",
    ),
    "report_promotions": (
        "makm", "tenkm", "tylegiam", "so_hoa_don", "tien_hang",
        "tien_giam", "doanh_thu", "tien_hoan", "doanh_thu_sau_hoan",
    ),
    "report_invoice": (
        "mahd", "ngaylap", "nhan_vien", "ca", "tien_hang", "tyle_giam",
        "tien_giam", "doanh_thu_truoc_hoan", "doanh_thu_thuc",
        "so_phieu_doi_tra", "sl_hoan_tien", "sl_doi_hang", "tien_hoan",
        "doanh_thu_sau_hoan", "tien_khach_dua", "trangthai",
    ),
    "report_import": (
        "mapn", "ngaynhap", "loai_phieu", "nha_cung_cap",
        "so_hoa_don_ncc", "nhan_vien", "tong_so_luong", "tong_tri_gia",
    ),
    "report_import_suppliers": (
        "mancc", "tenncc", "sdt", "so_phieu_nhap", "tong_so_luong", "tong_tri_gia",
    ),
    "report_return": (
        "mapdt", "ngay_doi_tra", "mahd", "nhan_vien", "ly_do",
        "sl_hoan_tien", "sl_doi_hang", "sl_nguyen_ven", "sl_hang_hong", "tong_tien_hoan",
    ),
    "report_inventory": (
        "masp", "tensp", "dvt", "slton", "gianhap", "giaban", "gia_tri_ton", "trangthai",
    ),
    "report_product": (
        "xep_hang", "masp", "tensp", "so_hoa_don", "sl_ban", "sl_hoan_tien",
        "sl_doi_hang", "tien_hang", "tien_giam", "doanh_thu", "tien_hoan",
        "doanh_thu_sau_hoan", "slton",
    ),
    "report_shifts": (
        "maca", "ngaylam", "soca", "tgmo", "tgdong", "so_nhan_vien",
        "tmdauca", "tmcuoica", "trangthai",
    ),
}


@router.get("/reports/{report_type}", summary="Dữ liệu báo cáo")
def get_report(
    report_type: str,
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    period: Literal["day", "month", "year"] = "day",
    sort: Literal["quantity_desc", "quantity_asc", "revenue_desc"] = "revenue_desc",
    threshold: int = Query(default=5, ge=1, le=100000),
    inventory_status: Literal["all", "low", "out"] = "all",
    keyword: str = Query(default="", max_length=100),
    user: CurrentUser = Depends(REPORT_ROLES),
    connection=Depends(get_db_connection),
):
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="Ngày bắt đầu không được lớn hơn ngày kết thúc.")
    try:
        service = BaoCaoService(BaoCaoRepository(connection))
        start, end = start_date.isoformat(), end_date.isoformat()
        if report_type == "report_overview":
            summary = service.overview_summary(start, end) or (0, 0, 0)
            refunds = service.overview_refunds(start, end)
            imports = service.overview_imports(start, end)
            return {
                "summary": {
                    "hoa_don_hieu_luc": summary[0],
                    "hoa_don_da_huy": summary[1],
                    "doanh_thu": summary[2],
                    "tien_hoan": (refunds[0] if refunds else 0),
                    "gia_tri_nhap": (imports[0] if imports else 0),
                },
                "trend": _rows(service.overview_trend(start, end), REPORT_COLUMNS["report_trend"]),
                "top_products": _rows(service.overview_top_products(start, end), REPORT_COLUMNS["report_top_products"]),
            }
        if report_type == "report_revenue":
            return {
                "items": _rows(
                    service.revenue_by_period(start, end, period),
                    REPORT_COLUMNS["report_revenue"],
                )
            }
        if report_type == "report_promotions":
            return {
                "items": _rows(
                    service.promotion_effectiveness(start, end),
                    REPORT_COLUMNS["report_promotions"],
                )
            }
        if report_type == "report_invoice":
            return {"items": _rows(service.invoice_report(start, end), REPORT_COLUMNS["report_invoice"])}
        if report_type == "report_import":
            result = service.import_report(start, end)
            return {
                "items": _rows(result["imports"], REPORT_COLUMNS["report_import"]),
                "suppliers": _rows(result["suppliers"], REPORT_COLUMNS["report_import_suppliers"]),
            }
        if report_type == "report_return":
            return {"items": _rows(service.return_report(start, end), REPORT_COLUMNS["report_return"])}
        if report_type == "report_inventory":
            result = service.inventory_report(threshold, inventory_status, keyword)
            return {
                "summary": {
                    "total_products": result["summary"][0],
                    "low_stock": result["summary"][1],
                    "out_of_stock": result["summary"][2],
                    "inventory_value": result["summary"][3],
                },
                "items": _rows(result["rows"], REPORT_COLUMNS["report_inventory"]),
            }
        if report_type == "report_product":
            return {"items": _rows(service.product_report(start, end, sort, keyword), REPORT_COLUMNS["report_product"])}
        if report_type == "report_shifts":
            return {"items": _rows(service.shift_report(start, end), REPORT_COLUMNS["report_shifts"])}
        raise HTTPException(status_code=404, detail="Loại báo cáo không tồn tại.")
    except HTTPException:
        raise
    except Exception as error:
        _raise_api(error)
