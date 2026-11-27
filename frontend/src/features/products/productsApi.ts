import { apiRequest } from "@/services/api";

export interface Product {
  masp: string;
  tensp: string;
  loai: "Sách" | "Sản phẩm khác" | "Chưa phân loại";
  dvt: string | null;
  gianhap: number | string | null;
  giaban: number | string | null;
  slton: number | null;
  vat: number | string | null;
  barcode: string | null;
  isbn?: string | null;
}

export interface ProductPage {
  items: Product[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface LookupOption {
  code: string;
  name: string;
  is_deleted: boolean;
}

export interface ProductLookups {
  publishers: LookupOption[];
  authors: LookupOption[];
  genres: LookupOption[];
  brands: LookupOption[];
}

export interface ProductDetail extends Product {
  isbn?: string | null;
  namxb?: number | null;
  ten_nxb?: string | null;
  authors?: string[];
  genres?: string[];
  ngaysx?: string | null;
  brand_name?: string | null;
  brand_origin?: string | null;
}

export interface ProductEditData {
  masp: string;
  tensp: string;
  dvt: string;
  gianhap: number | string;
  giaban: number | string;
  slton: number;
  vat: number | string;
  loai: "Sách" | "Sản phẩm khác";
  isbn: string | null;
  namxb: number | null;
  manxb: string | null;
  ngaysx: string | null;
  math: string | null;
  barcode: string | null;
  selected_author_codes: string[];
  selected_genre_codes: string[];
}

export interface ProductSavePayload {
  tensp: string;
  dvt: string;
  giaban: number;
  vat: number;
  barcode: string | null;
  product_type: "book" | "other";
  isbn: string | null;
  namxb: number | null;
  manxb: string | null;
  authors: string[];
  genres: string[];
  ngaysx: string | null;
  math: string | null;
}

export interface ProductListParams {
  keyword: string;
  product_type: "all" | "book" | "other" | "unclassified";
  page: number;
  page_size: number;
  sort_by: string;
  sort_order: "asc" | "desc";
}

export const productApi = {
  list(params: ProductListParams): Promise<ProductPage> {
    const search = new URLSearchParams({
      keyword: params.keyword,
      product_type: params.product_type,
      page: String(params.page),
      page_size: String(params.page_size),
      sort_by: params.sort_by,
      sort_order: params.sort_order,
    });
    return apiRequest<ProductPage>("/products?" + search.toString(), { method: "GET" }, true);
  },

  detail(code: string): Promise<ProductDetail> {
    return apiRequest<ProductDetail>("/products/" + encodeURIComponent(code), { method: "GET" }, true);
  },

  editData(code: string): Promise<ProductEditData> {
    return apiRequest<ProductEditData>("/products/" + encodeURIComponent(code) + "/edit", { method: "GET" }, true);
  },

  nextCode(): Promise<{ masp: string }> {
    return apiRequest<{ masp: string }>("/products/next-code", { method: "GET" }, true);
  },

  lookups(params?: {
    selectedPublisher?: string | null;
    selectedBrand?: string | null;
    authorCodes?: string[];
    genreCodes?: string[];
  }): Promise<ProductLookups> {
    const search = new URLSearchParams();
    if (params?.selectedPublisher) search.set("selected_publisher", params.selectedPublisher);
    if (params?.selectedBrand) search.set("selected_brand", params.selectedBrand);
    params?.authorCodes?.forEach((code) => search.append("author_codes", code));
    params?.genreCodes?.forEach((code) => search.append("genre_codes", code));
    const suffix = search.toString() ? "?" + search.toString() : "";
    return apiRequest<ProductLookups>("/products/lookups" + suffix, { method: "GET" }, true);
  },

  create(payload: ProductSavePayload): Promise<{ masp: string; message: string }> {
    return apiRequest<{ masp: string; message: string }>("/products", {
      method: "POST",
      body: JSON.stringify(payload),
    }, true);
  },

  update(code: string, payload: ProductSavePayload): Promise<{ masp: string; message: string }> {
    return apiRequest<{ masp: string; message: string }>("/products/" + encodeURIComponent(code), {
      method: "PUT",
      body: JSON.stringify(payload),
    }, true);
  },

  remove(code: string): Promise<{ masp: string; tensp: string; message: string }> {
    return apiRequest<{ masp: string; tensp: string; message: string }>(
      "/products/" + encodeURIComponent(code),
      { method: "DELETE" },
      true,
    );
  },
};
