"""API tra cứu và quản lý sản phẩm."""

from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.dependencies import get_db_connection
from backend.security import CurrentUser, get_current_user, require_roles
from core.repositories.san_pham_repository import (
    DuplicateProductBarcodeError,
    ProductHasStockError,
    SanPhamRepository,
)
from core.services.san_pham_service import SanPhamService

router = APIRouter(prefix="/products", tags=["products"])
CAN_MANAGE_PRODUCTS = require_roles("rl_QuanLy", "rl_NhanVienKho")


class ProductSavePayload(BaseModel):
    tensp: str = Field(min_length=1, max_length=150)
    dvt: str = Field(min_length=1, max_length=30)
    giaban: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    vat: Decimal = Field(default=Decimal("0"), ge=0, le=100, max_digits=5, decimal_places=2)
    barcode: str | None = Field(default=None, max_length=50)
    product_type: Literal["book", "other"]
    isbn: str | None = Field(default=None, max_length=20)
    namxb: int | None = Field(default=None, ge=0, le=9999)
    manxb: str | None = Field(default=None, max_length=20)
    authors: list[str] = Field(default_factory=list, max_length=100)
    genres: list[str] = Field(default_factory=list, max_length=100)
    ngaysx: date | None = None
    math: str | None = Field(default=None, max_length=20)

    class Config:
        extra = "forbid"


def get_product_service(connection=Depends(get_db_connection)) -> SanPhamService:
    """Tạo service sản phẩm dùng kết nối Backend riêng cho request."""
    return SanPhamService(SanPhamRepository(connection))


def _handle_product_error(error: Exception) -> None:
    if isinstance(error, LookupError):
        raise HTTPException(status_code=404, detail=str(error)) from None
    if isinstance(error, (ProductHasStockError, DuplicateProductBarcodeError)):
        raise HTTPException(status_code=409, detail=str(error)) from None
    if isinstance(error, ValueError):
        raise HTTPException(status_code=422, detail=str(error)) from None
    raise error


def _lookup_rows(rows):
    return [
        {"code": row[0], "name": row[1], "is_deleted": bool(row[2])}
        for row in rows
    ]


@router.get("", summary="Danh sách và tìm kiếm sản phẩm")
def list_products(
    keyword: str = Query(default="", max_length=100),
    product_type: Literal["all", "book", "other", "unclassified"] = "all",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=5, le=100),
    sort_by: str = Query(default="masp", max_length=20),
    sort_order: Literal["asc", "desc"] = "asc",
    _current_user: CurrentUser = Depends(get_current_user),
    service: SanPhamService = Depends(get_product_service),
):
    """Tìm theo mã, tên, mã vạch, ISBN và các thông tin danh mục liên quan."""
    allowed_sort = {
        "masp", "tensp", "loai", "dvt", "gianhap",
        "giaban", "slton", "vat", "barcode",
    }
    if sort_by.casefold() not in allowed_sort:
        raise HTTPException(status_code=422, detail="Cột sắp xếp không hợp lệ.")

    result = service.list_products_page(
        keyword=keyword,
        product_type=product_type,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return {
        **result,
        "page": page,
        "page_size": page_size,
        "total_pages": (result["total"] + page_size - 1) // page_size,
    }


@router.get("/next-code", summary="Mã sản phẩm dự kiến tiếp theo")
def preview_next_product_code(
    _current_user: CurrentUser = Depends(CAN_MANAGE_PRODUCTS),
    service: SanPhamService = Depends(get_product_service),
):
    """Xem trước mã sản phẩm; mã thực tế được khóa và sinh lại khi lưu."""
    return {"masp": service.preview_next_product_code()}


@router.get("/lookups", summary="Danh mục dùng trong biểu mẫu sản phẩm")
def get_product_lookups(
    selected_publisher: str | None = Query(default=None, max_length=20),
    selected_brand: str | None = Query(default=None, max_length=20),
    author_codes: list[str] = Query(default=[]),
    genre_codes: list[str] = Query(default=[]),
    _current_user: CurrentUser = Depends(CAN_MANAGE_PRODUCTS),
    service: SanPhamService = Depends(get_product_service),
):
    """Trả về danh mục hiện hành và giữ lựa chọn cũ nếu danh mục đã xóa mềm."""
    data = service.get_lookup_data(
        selected_publisher=selected_publisher,
        selected_brand=selected_brand,
        selected_authors=author_codes,
        selected_genres=genre_codes,
    )
    return {
        "publishers": _lookup_rows(data["publishers"]),
        "authors": _lookup_rows(data["authors"]),
        "genres": _lookup_rows(data["genres"]),
        "brands": _lookup_rows(data["brands"]),
    }


@router.get("/{product_code}/edit", summary="Dữ liệu biểu mẫu chỉnh sửa")
def get_product_for_edit(
    product_code: str,
    _current_user: CurrentUser = Depends(CAN_MANAGE_PRODUCTS),
    service: SanPhamService = Depends(get_product_service),
):
    """Lấy dữ liệu form và chuyển tập mã tác giả/thể loại thành danh sách JSON."""
    try:
        product = service.get_product_for_edit(product_code)
        product["selected_author_codes"] = sorted(product["selected_author_codes"])
        product["selected_genre_codes"] = sorted(product["selected_genre_codes"])
        return product
    except Exception as error:
        _handle_product_error(error)


@router.get("/{product_code}", summary="Chi tiết sản phẩm")
def get_product_detail(
    product_code: str,
    _current_user: CurrentUser = Depends(get_current_user),
    service: SanPhamService = Depends(get_product_service),
):
    """Lấy thông tin chung và thông tin riêng của sách/sản phẩm khác."""
    product = service.get_product_detail(product_code)
    if product is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    return product


@router.post("", status_code=status.HTTP_201_CREATED, summary="Thêm sản phẩm")
def create_product(
    payload: ProductSavePayload,
    _current_user: CurrentUser = Depends(CAN_MANAGE_PRODUCTS),
    service: SanPhamService = Depends(get_product_service),
):
    """Thêm sản phẩm và các thông tin subtype trong cùng một transaction."""
    try:
        code = service.save_product(payload.dict())
        return {"masp": code, "message": "Đã thêm sản phẩm thành công."}
    except Exception as error:
        _handle_product_error(error)


@router.put("/{product_code}", summary="Cập nhật sản phẩm")
def update_product(
    product_code: str,
    payload: ProductSavePayload,
    _current_user: CurrentUser = Depends(CAN_MANAGE_PRODUCTS),
    service: SanPhamService = Depends(get_product_service),
):
    """Cập nhật thông tin chung và liên kết tác giả/thể loại/thương hiệu."""
    try:
        code = service.save_product(payload.dict(), product_code=product_code)
        return {"masp": code, "message": "Đã cập nhật sản phẩm thành công."}
    except Exception as error:
        _handle_product_error(error)


@router.delete("/{product_code}", summary="Xóa mềm sản phẩm")
def delete_product(
    product_code: str,
    _current_user: CurrentUser = Depends(CAN_MANAGE_PRODUCTS),
    service: SanPhamService = Depends(get_product_service),
):
    """Chỉ xóa mềm khi sản phẩm không còn tồn kho."""
    try:
        name = service.soft_delete_product(product_code)
        return {"masp": product_code, "tensp": name, "message": "Đã xóa sản phẩm."}
    except Exception as error:
        _handle_product_error(error)
