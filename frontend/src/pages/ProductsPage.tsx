import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  DatePicker,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Modal,
  Pagination,
  Popconfirm,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
  message,
  type TableColumnsType,
  type TableProps,
} from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import type { Dayjs } from "dayjs";

import { ApiError } from "@/services/api";
import {
  productApi,
  type LookupOption,
  type Product,
  type ProductDetail,
  type ProductEditData,
  type ProductLookups,
  type ProductSavePayload,
} from "@/features/products/productsApi";
import { useAuth } from "@/features/auth/AuthContext";

const { Title, Text } = Typography;

type ProductTypeFilter = "all" | "book" | "other" | "unclassified";
type ProductFormValues = {
  tensp: string;
  dvt: string;
  giaban: number;
  vat: number;
  barcode?: string;
  product_type: "book" | "other";
  isbn?: string;
  namxb?: number;
  manxb?: string;
  authors?: string[];
  genres?: string[];
  ngaysx?: Dayjs | null;
  math?: string;
};

function formatMoney(value: number | string | null | undefined): string {
  const amount = Number(value ?? 0);
  return Number.isFinite(amount) ? amount.toLocaleString("vi-VN") + " ₫" : "—";
}

function formatNumber(value: number | string | null | undefined): string {
  const amount = Number(value ?? 0);
  return Number.isFinite(amount) ? amount.toLocaleString("vi-VN") : "—";
}

function displayDate(value?: string | null): string {
  if (!value) return "—";
  const parsed = dayjs(value);
  return parsed.isValid() ? parsed.format("DD/MM/YYYY") : "—";
}

function getErrorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Không thể hoàn tất yêu cầu. Vui lòng thử lại.";
}

function lookupOptions(items: LookupOption[]) {
  return items.map((item) => ({
    value: item.code,
    label: item.code + " - " + item.name + (item.is_deleted ? " (đã xóa mềm)" : ""),
    disabled: item.is_deleted,
  }));
}

export function ProductsPage() {
  const { user } = useAuth();
  const canManage = ["admin", "rl_QuanLy", "rl_NhanVienKho"].includes(user?.role_code || "");

  const [rows, setRows] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [keywordInput, setKeywordInput] = useState("");
  const [keyword, setKeyword] = useState("");
  const [productType, setProductType] = useState<ProductTypeFilter>("all");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [sortBy, setSortBy] = useState("masp");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  const [formOpen, setFormOpen] = useState(false);
  const [formLoading, setFormLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editingCode, setEditingCode] = useState<string | null>(null);
  const [previewCode, setPreviewCode] = useState("");
  const [lookups, setLookups] = useState<ProductLookups | null>(null);
  const [form] = Form.useForm<ProductFormValues>();

  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<ProductDetail | null>(null);

  const loadProducts = useCallback(async () => {
    setLoading(true);
    try {
      const response = await productApi.list({
        keyword,
        product_type: productType,
        page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      });
      setTotal(response.total);
      const lastPage = Math.max(1, response.total_pages);
      if (page > lastPage) {
        setPage(lastPage);
        return;
      }
      setRows(response.items);
    } catch (error) {
      message.error(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, [keyword, productType, page, pageSize, sortBy, sortOrder]);

  useEffect(() => {
    void loadProducts();
  }, [loadProducts]);

  async function openDetail(code: string) {
    setDetailOpen(true);
    setDetailLoading(true);
    setSelectedProduct(null);
    try {
      setSelectedProduct(await productApi.detail(code));
    } catch (error) {
      message.error(getErrorMessage(error));
      setDetailOpen(false);
    } finally {
      setDetailLoading(false);
    }
  }

  async function openForm(code?: string) {
    setEditingCode(code || null);
    setFormOpen(true);
    setFormLoading(true);
    setLookups(null);
    form.resetFields();
    try {
      let editing: ProductEditData | null = null;
      if (code) editing = await productApi.editData(code);

      const options = await productApi.lookups({
        selectedPublisher: editing?.manxb,
        selectedBrand: editing?.math,
        authorCodes: editing?.selected_author_codes || [],
        genreCodes: editing?.selected_genre_codes || [],
      });
      setLookups(options);

      if (editing) {
        const productType = editing.loai === "Sách" ? "book" : "other";
        form.setFieldsValue({
          tensp: editing.tensp,
          dvt: editing.dvt,
          giaban: Number(editing.giaban || 0),
          vat: Number(editing.vat || 0),
          barcode: editing.barcode || "",
          product_type: productType,
          isbn: editing.isbn || "",
          namxb: editing.namxb ?? undefined,
          manxb: editing.manxb || undefined,
          authors: editing.selected_author_codes,
          genres: editing.selected_genre_codes,
          ngaysx: editing.ngaysx ? dayjs(editing.ngaysx) : null,
          math: editing.math || undefined,
        });
      } else {
        const next = await productApi.nextCode();
        setPreviewCode(next.masp);
        form.setFieldsValue({
          product_type: "book",
          tensp: "",
          dvt: "Quyển",
          giaban: 0,
          vat: 0,
          barcode: "",
          isbn: "",
          authors: [],
          genres: [],
        });
      }
    } catch (error) {
      message.error(getErrorMessage(error));
      setFormOpen(false);
    } finally {
      setFormLoading(false);
    }
  }

  async function saveProduct(values: ProductFormValues) {
    if (values.product_type === "book" && !values.manxb) {
      message.warning("Vui lòng chọn nhà xuất bản.");
      return;
    }
    if (values.product_type === "other" && !values.math) {
      message.warning("Vui lòng chọn thương hiệu.");
      return;
    }

    const payload: ProductSavePayload = {
      tensp: values.tensp.trim(),
      dvt: values.dvt.trim(),
      giaban: Number(values.giaban),
      vat: Number(values.vat ?? 0),
      barcode: values.barcode?.trim() || null,
      product_type: values.product_type,
      isbn: values.isbn?.trim() || null,
      namxb: values.namxb === undefined ? null : Number(values.namxb),
      manxb: values.product_type === "book" ? values.manxb || null : null,
      authors: values.product_type === "book" ? values.authors || [] : [],
      genres: values.product_type === "book" ? values.genres || [] : [],
      ngaysx: values.product_type === "other" && values.ngaysx
        ? values.ngaysx.format("YYYY-MM-DD")
        : null,
      math: values.product_type === "other" ? values.math || null : null,
    };

    setSaving(true);
    try {
      const response = editingCode
        ? await productApi.update(editingCode, payload)
        : await productApi.create(payload);
      message.success(response.message);
      setFormOpen(false);
      await loadProducts();
    } catch (error) {
      message.error(getErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  async function deleteProduct(product: Product) {
    try {
      const response = await productApi.remove(product.masp);
      message.success(response.message);
      await loadProducts();
    } catch (error) {
      message.error(getErrorMessage(error));
    }
  }

  const columns: TableColumnsType<Product> = [
      {
        title: "Mã sản phẩm",
        dataIndex: "masp",
        key: "masp",
        width: 120,
        sorter: true,
        fixed: "left",
      },
      {
        title: "Tên sản phẩm",
        dataIndex: "tensp",
        key: "tensp",
        width: 240,
        sorter: true,
        ellipsis: true,
      },
      {
        title: "Loại",
        dataIndex: "loai",
        key: "loai",
        width: 135,
        sorter: true,
        render: (value: string) => <Tag color={value === "Sách" ? "blue" : "default"}>{value}</Tag>,
      },
      { title: "ĐVT", dataIndex: "dvt", key: "dvt", width: 90, sorter: true },
      {
        title: "Giá nhập",
        dataIndex: "gianhap",
        key: "gianhap",
        width: 135,
        align: "right",
        sorter: true,
        render: formatMoney,
      },
      {
        title: "Giá bán",
        dataIndex: "giaban",
        key: "giaban",
        width: 135,
        align: "right",
        sorter: true,
        render: formatMoney,
      },
      {
        title: "Tồn kho",
        dataIndex: "slton",
        key: "slton",
        width: 95,
        align: "right",
        sorter: true,
        render: formatNumber,
      },
      {
        title: "VAT",
        dataIndex: "vat",
        key: "vat",
        width: 75,
        align: "right",
        sorter: true,
        render: (value: number | string | null) => formatNumber(value) + "%",
      },
      {
        title: "Mã vạch",
        dataIndex: "barcode",
        key: "barcode",
        width: 150,
        sorter: true,
        render: (value: string | null) => value || "—",
      },
      {
        title: "ISBN",
        dataIndex: "isbn",
        key: "isbn",
        width: 145,
        render: (value: string | null | undefined) => value || "—",
      },
      {
        title: "Thao tác",
        key: "actions",
        width: canManage ? 190 : 100,
        fixed: "right",
        render: (_value, record) => (
          <Space size={4}>
            <Button size="small" icon={<EyeOutlined />} onClick={() => void openDetail(record.masp)}>
              Chi tiết
            </Button>
            {canManage && (
              <Button size="small" icon={<EditOutlined />} onClick={() => void openForm(record.masp)} />
            )}
            {canManage && (
              <Popconfirm
                title="Xóa sản phẩm này?"
                description="Chỉ có thể xóa khi số lượng tồn bằng 0."
                okText="Xóa"
                cancelText="Hủy"
                okButtonProps={{ danger: true }}
                onConfirm={() => void deleteProduct(record)}
              >
                <Button size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            )}
          </Space>
        ),
      },
  ];

  const handleTableChange: TableProps<Product>["onChange"] = (_pagination, _filters, sorter) => {
    const selectedSorter = Array.isArray(sorter) ? sorter[0] : sorter;
    if (selectedSorter?.field) {
      const nextKey = String(selectedSorter.field);
      if (["masp", "tensp", "loai", "dvt", "gianhap", "giaban", "slton", "vat", "barcode"].includes(nextKey)) {
        setSortBy(nextKey);
        setSortOrder(selectedSorter.order === "descend" ? "desc" : "asc");
      }
    } else {
      setSortBy("masp");
      setSortOrder("asc");
    }
    setPage(1);
  };

  function applySearch() {
    setPage(1);
    setKeyword(keywordInput.trim());
  }

  return (
    <div className="products-page">
      <div className="products-heading">
        <div>
          <Text className="eyebrow">QUẢN LÝ KHO</Text>
          <Title level={2}>Danh sách sản phẩm</Title>
          <Text className="muted-text">Tra cứu theo mã sản phẩm, tên, mã vạch, ISBN và thông tin danh mục.</Text>
        </div>
        {canManage && (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => void openForm()}>
            Thêm sản phẩm
          </Button>
        )}
      </div>

      <Card className="products-card" bordered={false}>
        <div className="products-toolbar">
          <Space.Compact className="products-search">
            <Input
              allowClear
              value={keywordInput}
              placeholder="Nhập mã, tên, barcode, ISBN, tác giả, thể loại..."
              onChange={(event) => setKeywordInput(event.target.value)}
              onPressEnter={applySearch}
              onClear={() => {
                setKeywordInput("");
                setKeyword("");
                setPage(1);
              }}
            />
            <Button type="primary" icon={<SearchOutlined />} onClick={applySearch}>Tìm kiếm</Button>
          </Space.Compact>
          <Select<ProductTypeFilter>
            value={productType}
            style={{ width: 190 }}
            options={[
              { value: "all", label: "Tất cả sản phẩm" },
              { value: "book", label: "Sách" },
              { value: "other", label: "Sản phẩm khác" },
              { value: "unclassified", label: "Chưa phân loại" },
            ]}
            onChange={(value) => {
              setProductType(value);
              setPage(1);
            }}
          />
          <Button icon={<ReloadOutlined />} onClick={() => void loadProducts()}>Làm mới</Button>
        </div>

        <Table<Product>
          rowKey="masp"
          columns={columns}
          dataSource={rows}
          loading={loading}
          pagination={false}
          onChange={handleTableChange}
          onRow={(record) => ({
            onDoubleClick: () => void openDetail(record.masp),
          })}
          scroll={{ x: 1450 }}
          size="middle"
          locale={{ emptyText: "Không tìm thấy sản phẩm phù hợp." }}
        />

        <div className="products-table-footer">
          <Text className="muted-text">Tổng số sản phẩm: {total.toLocaleString("vi-VN")}</Text>
          <Pagination
            current={page}
            pageSize={pageSize}
            total={total}
            showSizeChanger
            pageSizeOptions={[10, 20, 50, 100]}
            showTotal={(count, range) => range[0] + "–" + range[1] + " / " + count}
            onChange={(nextPage, nextSize) => {
              setPage(nextPage);
              if (nextSize !== pageSize) {
                setPageSize(nextSize);
                setPage(1);
              }
            }}
          />
        </div>
      </Card>

      <Modal
        title={editingCode ? "Chỉnh sửa sản phẩm " + editingCode : "Thêm sản phẩm mới"}
        open={formOpen}
        onCancel={() => setFormOpen(false)}
        onOk={() => form.submit()}
        okText={editingCode ? "Lưu thay đổi" : "Thêm sản phẩm"}
        cancelText="Hủy"
        confirmLoading={saving}
        width={680}
        destroyOnClose
        className="product-form-modal"
      >
        {formLoading ? (
          <div className="product-modal-loading"><Spin /></div>
        ) : (
          <Form<ProductFormValues>
            form={form}
            className="desktop-dialog-form product-desktop-form"
            layout="horizontal"
            labelCol={{ xs: { span: 24 }, sm: { span: 7 } }}
            wrapperCol={{ xs: { span: 24 }, sm: { span: 17 } }}
            onFinish={(values) => void saveProduct(values)}
            initialValues={{ vat: 0, giaban: 0, product_type: "book" }}
          >
            <Form.Item name="product_type" label="Loại sản phẩm" rules={[{ required: true }]}>
              <Select
                disabled={Boolean(editingCode)}
                options={[{ value: "book", label: "Sách" }, { value: "other", label: "Sản phẩm khác" }]}
              />
            </Form.Item>
            <Card size="small" title="Thông tin chung" className="desktop-form-section">
              <Form.Item label="Mã sản phẩm"><Input value={editingCode || previewCode} readOnly /></Form.Item>
              <Form.Item name="tensp" label="Tên sản phẩm" rules={[{ required: true, whitespace: true, message: "Vui lòng nhập tên sản phẩm." }, { max: 150 }]}>
                <Input maxLength={150} placeholder="Nhập tên sản phẩm" />
              </Form.Item>
              <Form.Item name="barcode" label="Mã vạch"><Input maxLength={50} placeholder="Quét hoặc nhập mã vạch" /></Form.Item>
              <Form.Item name="dvt" label="Đơn vị tính" rules={[{ required: true, whitespace: true, message: "Vui lòng nhập đơn vị tính." }, { max: 30 }]}>
                <Input maxLength={30} placeholder="Quyển, Cái, Chiếc..." />
              </Form.Item>
              <Form.Item label="Giá nhập (tự động)"><Input value={editingCode ? "Tính từ phiếu nhập" : "Tự động cập nhật"} readOnly /></Form.Item>
              <Form.Item name="giaban" label="Giá bán" rules={[{ required: true, message: "Vui lòng nhập giá bán." }]}>
                <InputNumber min={0} precision={2} style={{ width: "100%" }} />
              </Form.Item>
              <Form.Item label="Số lượng tồn (tự động)"><Input value={editingCode ? "Quản lý theo giao dịch kho" : "Cập nhật khi nhập hàng"} readOnly /></Form.Item>
              <Form.Item name="vat" label="VAT (%)" rules={[{ required: true, message: "Vui lòng nhập VAT." }]}>
                <InputNumber min={0} max={100} precision={2} style={{ width: "100%" }} />
              </Form.Item>
              <Alert type="info" showIcon message="Giá nhập bình quân và số lượng tồn được hệ thống tự cập nhật từ phiếu nhập, hóa đơn và đổi trả; không chỉnh sửa tại biểu mẫu sản phẩm." />
            </Card>
            <Form.Item noStyle shouldUpdate={(previous, current) => previous.product_type !== current.product_type}>
              {({ getFieldValue }) => getFieldValue("product_type") === "book" ? (
                <Card size="small" title="Thông tin sách" className="desktop-form-section">
                  <Form.Item name="isbn" label="ISBN"><Input maxLength={20} placeholder="Nhập mã ISBN" /></Form.Item>
                  <Form.Item name="namxb" label="Năm xuất bản"><InputNumber min={0} max={9999} precision={0} style={{ width: "100%" }} /></Form.Item>
                  <Form.Item name="manxb" label="Nhà xuất bản" rules={[{ required: true, message: "Vui lòng chọn nhà xuất bản." }]}>
                    <Select showSearch optionFilterProp="label" placeholder="Tìm mã hoặc tên nhà xuất bản" options={lookups ? lookupOptions(lookups.publishers) : []} />
                  </Form.Item>
                  <Form.Item name="authors" label="Tác giả">
                    <Select mode="multiple" showSearch optionFilterProp="label" maxTagCount="responsive" placeholder="Tìm và chọn tác giả" options={lookups ? lookupOptions(lookups.authors) : []} />
                  </Form.Item>
                  <Form.Item name="genres" label="Thể loại">
                    <Select mode="multiple" showSearch optionFilterProp="label" maxTagCount="responsive" placeholder="Tìm và chọn thể loại" options={lookups ? lookupOptions(lookups.genres) : []} />
                  </Form.Item>
                </Card>
              ) : (
                <Card size="small" title="Thông tin sản phẩm khác" className="desktop-form-section">
                  <Form.Item name="ngaysx" label="Ngày sản xuất"><DatePicker format="DD/MM/YYYY" style={{ width: "100%" }} /></Form.Item>
                  <Form.Item name="math" label="Thương hiệu" rules={[{ required: true, message: "Vui lòng chọn thương hiệu." }]}>
                    <Select showSearch optionFilterProp="label" placeholder="Tìm mã hoặc tên thương hiệu" options={lookups ? lookupOptions(lookups.brands) : []} />
                  </Form.Item>
                </Card>
              )}
            </Form.Item>
          </Form>
        )}
      </Modal>

      <Modal
        title="Chi tiết sản phẩm"
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={<Button onClick={() => setDetailOpen(false)}>Đóng</Button>}
        width={760}
      >
        {detailLoading ? (
          <div className="product-modal-loading"><Spin /></div>
        ) : selectedProduct ? (
          <>
            <Card size="small" title="Thông tin chung" className="desktop-form-section">
              <Descriptions bordered column={1} size="small">
                <Descriptions.Item label="Mã sản phẩm">{selectedProduct.masp}</Descriptions.Item>
                <Descriptions.Item label="Mã vạch">{selectedProduct.barcode || "Chưa có"}</Descriptions.Item>
                <Descriptions.Item label="Tên sản phẩm">{selectedProduct.tensp}</Descriptions.Item>
                <Descriptions.Item label="Loại sản phẩm">{selectedProduct.loai}</Descriptions.Item>
                <Descriptions.Item label="Đơn vị tính">{selectedProduct.dvt || "—"}</Descriptions.Item>
                <Descriptions.Item label="Giá nhập">{formatMoney(selectedProduct.gianhap)}</Descriptions.Item>
                <Descriptions.Item label="Giá bán">{formatMoney(selectedProduct.giaban)}</Descriptions.Item>
                <Descriptions.Item label="Số lượng tồn">{formatNumber(selectedProduct.slton)}</Descriptions.Item>
                <Descriptions.Item label="VAT (%)">{formatNumber(selectedProduct.vat)}</Descriptions.Item>
              </Descriptions>
            </Card>
            <Card size="small" title={selectedProduct.loai === "Sách" ? "Thông tin sách" : "Thông tin sản phẩm khác"} className="desktop-form-section">
              <Descriptions bordered column={1} size="small">
                {selectedProduct.loai === "Sách" ? (
                  <>
                    <Descriptions.Item label="ISBN">{selectedProduct.isbn || "—"}</Descriptions.Item>
                    <Descriptions.Item label="Năm xuất bản">{selectedProduct.namxb ?? "—"}</Descriptions.Item>
                    <Descriptions.Item label="Nhà xuất bản">{selectedProduct.ten_nxb || "—"}</Descriptions.Item>
                    <Descriptions.Item label="Tác giả">{selectedProduct.authors?.join(", ") || "Chưa có thông tin"}</Descriptions.Item>
                    <Descriptions.Item label="Thể loại">{selectedProduct.genres?.join(", ") || "Chưa có thông tin"}</Descriptions.Item>
                  </>
                ) : (
                  <>
                    <Descriptions.Item label="Ngày sản xuất">{displayDate(selectedProduct.ngaysx)}</Descriptions.Item>
                    <Descriptions.Item label="Thương hiệu">{selectedProduct.brand_name || "—"}</Descriptions.Item>
                    <Descriptions.Item label="Xuất xứ">{selectedProduct.brand_origin || "—"}</Descriptions.Item>
                  </>
                )}
              </Descriptions>
            </Card>
          </>
        ) : (
          <Alert type="warning" message="Không có dữ liệu chi tiết." />
        )}
      </Modal>
    </div>
  );
}
