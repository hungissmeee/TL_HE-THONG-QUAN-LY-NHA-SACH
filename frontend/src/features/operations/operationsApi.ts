import { apiRequest } from "@/services/api";

export type Row = Record<string, unknown>;
export interface CatalogField { key: string; label: string; required: boolean }
export interface CatalogData { title: string; fields: CatalogField[]; items: Row[] }
export interface ImportLookup {
  suppliers: { code: string; name: string }[];
  products: { masp: string; tensp: string; dvt: string; price: number; stock: number; vat: number; barcode: string | null; isbn: string | null }[];
}
export interface InvoiceLookup {
  employee: { manv: string | null; tennv: string; vaitro: string };
  active_shift: { maca: number; soca: number; ngaylam: string; tgmo: string; tgdong: string } | null;
  promotions: [string, string, number][];
  products: { masp: string; tensp: string; dvt: string; price: number; stock: number; vat: number; barcode: string | null; isbn: string | null }[];
}
export interface PageResult { items: Row[] }
export interface ReturnInvoiceItems {
  invoice_code: string;
  invoice_date: string;
  discount_rate: number;
  items: {
    product_code: string; product_name: string; unit: string;
    purchased: number; processed: number; remaining: number;
    net_price: number; vat: number;
  }[];
}
export interface ReportPayload {
  summary?: Row;
  trend?: Row[];
  top_products?: Row[];
  items?: Row[];
  suppliers?: Row[];
}

const params = (values: Record<string, string | number | boolean | undefined>) => {
  const query = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  return query.toString();
};

export const operationsApi = {
  suppliers: (keyword = "", showInactive = false) =>
    apiRequest<Row[]>("/suppliers?" + params({ keyword, show_inactive: showInactive }), { method: "GET" }, true),
  supplier: (code: string) =>
    apiRequest<Row>("/suppliers/" + encodeURIComponent(code), { method: "GET" }, true),
  supplierNextCode: () => apiRequest<{ code: string }>("/suppliers/next-code", { method: "GET" }, true),
  saveSupplier: (payload: Row, code?: string) =>
    apiRequest<{ code: string; message: string }>(
      code ? "/suppliers/" + encodeURIComponent(code) : "/suppliers",
      { method: code ? "PUT" : "POST", body: JSON.stringify(payload) }, true,
    ),
  supplierStatus: (code: string, inactive: boolean) =>
    apiRequest<Row>("/suppliers/" + encodeURIComponent(code) + "/status?inactive=" + inactive, { method: "PATCH" }, true),

  catalog: (type: string, keyword = "") =>
    apiRequest<CatalogData>("/catalogs/" + type + "?" + params({ keyword }), { method: "GET" }, true),
  catalogNextCode: (type: string) =>
    apiRequest<{ code: string }>("/catalogs/" + type + "/next-code", { method: "GET" }, true),
  saveCatalog: (type: string, values: (string | null)[], code?: string) =>
    apiRequest<Row>(
      code ? "/catalogs/" + type + "/" + encodeURIComponent(code) : "/catalogs/" + type,
      { method: code ? "PUT" : "POST", body: JSON.stringify({ values }) }, true,
    ),
  deleteCatalog: (type: string, code: string) =>
    apiRequest<Row>("/catalogs/" + type + "/" + encodeURIComponent(code), { method: "DELETE" }, true),

  promotions: (keyword = "", showDeleted = false) =>
    apiRequest<Row[]>("/promotions?" + params({ keyword, show_deleted: showDeleted }), { method: "GET" }, true),
  promotionNextCode: () => apiRequest<{ code: string }>("/promotions/next-code", { method: "GET" }, true),
  createPromotion: (payload: Row) =>
    apiRequest<Row>("/promotions", { method: "POST", body: JSON.stringify(payload) }, true),
  renamePromotion: (code: string, name: string) =>
    apiRequest<Row>("/promotions/" + encodeURIComponent(code), { method: "PUT", body: JSON.stringify({ name }) }, true),
  deletePromotion: (code: string) =>
    apiRequest<Row>("/promotions/" + encodeURIComponent(code), { method: "DELETE" }, true),

  imports: (startDate: string, endDate: string, keyword = "") =>
    apiRequest<Row[]>("/imports?" + params({ start_date: startDate, end_date: endDate, keyword }), { method: "GET" }, true),
  importLookups: () => apiRequest<ImportLookup>("/imports/lookups", { method: "GET" }, true),
  importDetail: (code: string) =>
    apiRequest<{ header: Row; items: Row[] }>("/imports/" + encodeURIComponent(code), { method: "GET" }, true),
  createImport: (payload: Row) =>
    apiRequest<Row>("/imports", { method: "POST", body: JSON.stringify(payload) }, true),
  cancelImport: (code: string) =>
    apiRequest<Row>("/imports/" + encodeURIComponent(code) + "/cancel", { method: "POST" }, true),

  invoices: (startDate: string, endDate: string, keyword = "") =>
    apiRequest<Row[]>("/invoices?" + params({ start_date: startDate, end_date: endDate, keyword }), { method: "GET" }, true),
  invoiceLookups: () => apiRequest<InvoiceLookup>("/invoices/lookups", { method: "GET" }, true),
  invoiceDetail: (code: string) =>
    apiRequest<{ header: Row; items: Row[] }>("/invoices/" + encodeURIComponent(code), { method: "GET" }, true),
  createInvoice: (payload: Row) =>
    apiRequest<Row>("/invoices", { method: "POST", body: JSON.stringify(payload) }, true),
  cancelInvoice: (code: string) =>
    apiRequest<Row>("/invoices/" + encodeURIComponent(code) + "/cancel", { method: "POST" }, true),

  eligibleReturnInvoices: () => apiRequest<{ mahd: string; ngaylap: string }[]>("/returns/eligible-invoices", { method: "GET" }, true),
  returnInvoiceItems: (code: string) =>
    apiRequest<ReturnInvoiceItems>("/returns/invoices/" + encodeURIComponent(code) + "/items", { method: "GET" }, true),
  returns: (startDate: string, endDate: string, keyword = "") =>
    apiRequest<Row[]>("/returns?" + params({ start_date: startDate, end_date: endDate, keyword }), { method: "GET" }, true),
  returnDetail: (code: string) =>
    apiRequest<{ header: Row; items: Row[] }>("/returns/" + encodeURIComponent(code), { method: "GET" }, true),
  createReturn: (payload: Row) =>
    apiRequest<Row>("/returns", { method: "POST", body: JSON.stringify(payload) }, true),
  deleteReturn: (code: string) =>
    apiRequest<Row>("/returns/" + encodeURIComponent(code), { method: "DELETE" }, true),

  employees: (keyword = "") =>
    apiRequest<Row[]>("/employees?" + params({ keyword }), { method: "GET" }, true),
  employee: (code: string) =>
    apiRequest<Row>("/employees/" + encodeURIComponent(code), { method: "GET" }, true),
  updateEmployee: (code: string, payload: Row) =>
    apiRequest<Row>("/employees/" + encodeURIComponent(code), { method: "PUT", body: JSON.stringify(payload) }, true),

  shiftSummary: () => apiRequest<Row>("/shifts/summary", { method: "GET" }, true),
  currentShifts: () => apiRequest<Row[]>("/shifts/current", { method: "GET" }, true),
  shiftHistory: (period: string) =>
    apiRequest<Row[]>("/shifts/history?" + params({ period }), { method: "GET" }, true),
  myShifts: () => apiRequest<Row[]>("/shifts/me", { method: "GET" }, true),
  shiftRoster: (id: number) => apiRequest<Row[]>("/shifts/" + id + "/roster", { method: "GET" }, true),
  createShift: (payload: Row) => apiRequest<Row>("/shifts", { method: "POST", body: JSON.stringify(payload) }, true),
  deleteShift: (id: number) => apiRequest<Row>("/shifts/" + id, { method: "DELETE" }, true),
  registerShift: (id: number) => apiRequest<Row>("/shifts/" + id + "/register", { method: "POST" }, true),
  closingCash: (id: number, amount: number) =>
    apiRequest<Row>("/shifts/" + id + "/closing-cash", { method: "POST", body: JSON.stringify({ amount }) }, true),

  report: (type: string, values: Record<string, string | number>) =>
    apiRequest<ReportPayload>("/reports/" + type + "?" + params(values), { method: "GET" }, true),
};
