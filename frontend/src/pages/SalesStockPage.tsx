import { useCallback, useEffect, useState } from "react";
import {
  Alert, Button, Card, Col, DatePicker, Descriptions, Form, Input, InputNumber,
  Modal, Popconfirm, Row, Select, Space, Spin, Table, Tag, Typography, message,
  type TableColumnsType,
} from "antd";
import { EyeOutlined, PlusOutlined, ReloadOutlined, StopOutlined } from "@ant-design/icons";
import dayjs, { type Dayjs } from "dayjs";
import { ApiError } from "@/services/api";
import { operationsApi, type ImportLookup, type InvoiceLookup, type Row as DataRow } from "@/features/operations/operationsApi";
import { useAuth } from "@/features/auth/AuthContext";

const { Title, Text } = Typography;
const err = (e: unknown) => e instanceof ApiError ? e.message : "Không thể hoàn tất yêu cầu.";
const money = (v: unknown) => Number(v ?? 0).toLocaleString("vi-VN") + " ₫";
const dt = (v: unknown) => v ? dayjs(String(v)).format("DD/MM/YYYY HH:mm") : "—";

function usePeriod() {
  const [period, setPeriod] = useState<[Dayjs, Dayjs]>([dayjs().subtract(30, "day").startOf("day"), dayjs().endOf("day")]);
  return { period, setPeriod };
}

function ImportsPage() {
  const { user } = useAuth();
  const canWrite = ["admin", "rl_QuanLy", "rl_NhanVienKho"].includes(user?.role_code || "");
  const { period, setPeriod } = usePeriod();
  const [rows, setRows] = useState<DataRow[]>([]);
  const [keyword, setKeyword] = useState("");
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [lookups, setLookups] = useState<ImportLookup | null>(null);
  const [detail, setDetail] = useState<{ header: DataRow; items: DataRow[] } | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [formLoading, setFormLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const watchedImportItems = Form.useWatch("items", form) as DataRow[] | undefined;
  const importTotal = (watchedImportItems || []).reduce(
    (sum, item) => sum + Number(item?.price || 0) * Number(item?.quantity || 0),
    0,
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await operationsApi.imports(period[0].format("YYYY-MM-DD"), period[1].format("YYYY-MM-DD"), keyword));
    } catch (e) { message.error(err(e)); } finally { setLoading(false); }
  }, [period, keyword]);
  useEffect(() => { void load(); }, [load]);

  async function openAdd() {
    setOpen(true); setFormLoading(true); setLookups(null); form.resetFields();
    try {
      setLookups(await operationsApi.importLookups());
      form.setFieldsValue({ import_type: "Nhập hàng", items: [{ quantity: 1, vat: 0 }] });
    } catch (e) { setOpen(false); message.error(err(e)); }
    finally { setFormLoading(false); }
  }

  async function showDetail(code: string) {
    setDetailOpen(true); setDetail(null);
    try { setDetail(await operationsApi.importDetail(code)); }
    catch (e) { setDetailOpen(false); message.error(err(e)); }
  }

  async function save(values: DataRow) {
    const items = Array.isArray(values.items) ? values.items as DataRow[] : [];
    const seenProducts = new Set<string>();
    for (const item of items) {
      const code = String(item?.product_code || "").trim();
      if (!code) continue;
      if (seenProducts.has(code)) {
        message.error(`Sản phẩm ${code} chỉ được xuất hiện một lần trong phiếu nhập.`);
        return;
      }
      seenProducts.add(code);
    }

    setSaving(true);
    try {
      const result = await operationsApi.createImport(values);
      message.success("Đã lập phiếu nhập " + String(result.code || "") + ".");
      setOpen(false); await load();
    } catch (e) { message.error(err(e)); } finally { setSaving(false); }
  }

  async function cancel(code: string) {
    try { await operationsApi.cancelImport(code); message.success("Đã hủy phiếu nhập và hoàn tác tồn kho."); await load(); }
    catch (e) { message.error(err(e)); }
  }

  const columns: TableColumnsType<DataRow> = [
    { title: "Mã phiếu", dataIndex: "mapn", key: "mapn", width: 125 },
    { title: "Ngày nhập", dataIndex: "ngaynhap", key: "ngaynhap", width: 170, render: dt },
    { title: "Nhà cung cấp", dataIndex: "tenncc", key: "tenncc", ellipsis: true },
    { title: "Nhân viên", dataIndex: "tennv", key: "tennv", width: 160 },
    { title: "Số HĐ NCC", dataIndex: "shdncc", key: "shdncc", width: 120 },
    { title: "Tổng trị giá", dataIndex: "tongtrigia", key: "tongtrigia", width: 145, align: "right", render: money },
    { title: "Trạng thái", dataIndex: "trangthai", key: "status", width: 120, render: (v: boolean) => <Tag color={v ? "success" : "default"}>{v ? "Có hiệu lực" : "Đã hủy"}</Tag> },
    { title: "Thao tác", key: "actions", width: 175, render: (_: unknown, row: DataRow) => <Space>
      <Button size="small" icon={<EyeOutlined />} onClick={() => void showDetail(String(row.mapn))}>Chi tiết</Button>
      {canWrite && Boolean(row.trangthai) && <Popconfirm title="Hủy phiếu nhập?" description="Tồn kho sẽ được hoàn tác nếu hiện còn đủ số lượng." okText="Hủy phiếu" cancelText="Đóng" onConfirm={() => void cancel(String(row.mapn))}><Button size="small" danger icon={<StopOutlined />} /></Popconfirm>}
    </Space> },
  ];

  return <div className="operation-page">
    <div className="operation-heading"><div><Text className="eyebrow">QUẢN LÝ KHO</Text><Title level={2}>Phiếu nhập</Title><Text className="muted-text">Theo dõi hàng nhập, giá nhập bình quân và tồn kho.</Text></div>{canWrite && <Button type="primary" icon={<PlusOutlined />} onClick={() => void openAdd()}>Lập phiếu nhập</Button>}</div>
    <Card bordered={false} className="operation-card">
      <div className="operation-toolbar">
        <DatePicker.RangePicker value={period} format="DD/MM/YYYY" onChange={(v) => { if (v?.[0] && v[1]) setPeriod([v[0], v[1]]); }} />
        <Input.Search className="operation-search" allowClear value={keyword} placeholder="Mã phiếu, nhà cung cấp, nhân viên..." onChange={(e) => setKeyword(e.target.value)} onSearch={(v) => setKeyword(v.trim())} enterButton="Tìm kiếm" />
        <Button icon={<ReloadOutlined />} onClick={() => void load()}>Làm mới</Button>
      </div>
      <Table<DataRow> rowKey="mapn" columns={columns} dataSource={rows} loading={loading} pagination={{ pageSize: 10, showSizeChanger: true }} />
    </Card>
    <Modal
      title="Lập phiếu nhập kho"
      open={open}
      onCancel={() => setOpen(false)}
      onOk={() => form.submit()}
      okText="Lập phiếu nhập"
      cancelText="Hủy"
      confirmLoading={saving}
      width={960}
      destroyOnClose
      className="desktop-transaction-modal"
    >
      {formLoading || !lookups ? <div className="product-modal-loading"><Spin /></div> : (
        <Form
          form={form}
          className="desktop-dialog-form"
          layout="horizontal"
          labelCol={{ xs: { span: 24 }, sm: { span: 8 } }}
          wrapperCol={{ xs: { span: 24 }, sm: { span: 16 } }}
          onFinish={(v) => void save(v)}
        >
          <Card size="small" title="Thông tin phiếu nhập" className="desktop-form-section">
            <Form.Item label="Nhân viên lập">
              <Input
                readOnly
                value={(user?.full_name || "Nhân viên") + " (" + (user?.employee_code || "Tài khoản hệ thống") + ")"}
              />
            </Form.Item>
            <Form.Item name="supplier_code" label="Nhà cung cấp" rules={[{ required: true, message: "Vui lòng chọn nhà cung cấp." }]}>
              <Select
                showSearch
                optionFilterProp="label"
                placeholder="Tìm mã hoặc tên nhà cung cấp"
                options={lookups.suppliers.map((supplier) => ({
                  value: supplier.code,
                  label: supplier.code + " - " + supplier.name,
                }))}
              />
            </Form.Item>
            <Form.Item name="import_type" label="Loại phiếu nhập" rules={[{ required: true }]}>
              <Select options={[
                { value: "Nhập hàng", label: "Nhập hàng" },
                { value: "Nhập bổ sung", label: "Nhập bổ sung" },
                { value: "Nhập điều chỉnh", label: "Nhập điều chỉnh" },
              ]} />
            </Form.Item>
            <Form.Item name="supplier_invoice" label="Số HĐ nhà cung cấp">
              <Input maxLength={50} placeholder="Số hóa đơn/chứng từ của nhà cung cấp (nếu có)" />
            </Form.Item>
          </Card>

          <Card size="small" title="Sản phẩm trong phiếu nhập" className="desktop-form-section">
            <Form.List name="items">
              {(fields, { add, remove }) => (
                <>
                  <div className="operation-list-heading">
                    <Text type="secondary">Thêm sản phẩm, số lượng và đơn giá nhập vào phiếu</Text>
                    <Button size="small" icon={<PlusOutlined />} onClick={() => add({ quantity: 1, vat: 0 })}>
                      Thêm dòng
                    </Button>
                  </div>
                  {fields.map((field) => (
                    <Row gutter={10} align="middle" key={field.key} className="transaction-line-row">
                      <Col xs={24} md={10}>
                        <Form.Item name={[field.name, "product_code"]} label="Sản phẩm" rules={[{ required: true }]}>
                          <Select
                            showSearch
                            optionFilterProp="label"
                            placeholder="Chọn sản phẩm"
                            options={lookups.products.map((product) => ({
                              value: product.masp,
                              label: product.masp + " - " + product.tensp + " · Tồn " + product.stock,
                            }))}
                            onChange={(value) => {
                              const product = lookups.products.find((item) => item.masp === value);
                              if (product) {
                                const items = form.getFieldValue("items") || [];
                                items[field.name] = {
                                  ...items[field.name],
                                  price: Number(product.price || 0),
                                  vat: Number(product.vat || 0),
                                  quantity: items[field.name]?.quantity || 1,
                                };
                                form.setFieldsValue({ items });
                              }
                            }}
                          />
                        </Form.Item>
                      </Col>
                      <Col xs={8} md={4}>
                        <Form.Item name={[field.name, "quantity"]} label="Số lượng" rules={[{ required: true }]}>
                          <InputNumber min={1} precision={0} style={{ width: "100%" }} />
                        </Form.Item>
                      </Col>
                      <Col xs={10} md={5}>
                        <Form.Item name={[field.name, "price"]} label="Đơn giá nhập" rules={[{ required: true }]}>
                          <InputNumber min={0.01} precision={2} style={{ width: "100%" }} />
                        </Form.Item>
                      </Col>
                      <Col xs={4} md={3}>
                        <Form.Item name={[field.name, "vat"]} label="VAT (%)">
                          <InputNumber min={0} max={100} precision={2} style={{ width: "100%" }} />
                        </Form.Item>
                      </Col>
                      <Col xs={2} md={2}>
                        <Button
                          className="transaction-line-remove"
                          danger
                          type="text"
                          icon={<StopOutlined />}
                          aria-label="Xóa dòng sản phẩm"
                          onClick={() => remove(field.name)}
                        />
                      </Col>
                    </Row>
                  ))}
                </>
              )}
            </Form.List>
            <Alert
              type="info"
              showIcon
              message="Giá nhập bình quân và tồn kho được cập nhật tự động trong cùng giao dịch khi lập phiếu."
            />
          </Card>

          <Card size="small" title="Tổng giá trị phiếu nhập" className="desktop-form-section transaction-total-card">
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="Tổng tiền hàng (đã gồm VAT)">
                <Text strong className="transaction-total-value">{money(importTotal)}</Text>
              </Descriptions.Item>
            </Descriptions>
            <Text type="secondary">VAT được lưu để tham chiếu; không cộng lại vào đơn giá.</Text>
          </Card>
        </Form>
      )}
    </Modal>
    <Modal title="Chi tiết phiếu nhập" open={detailOpen} onCancel={() => setDetailOpen(false)} footer={<Button onClick={() => setDetailOpen(false)}>Đóng</Button>} width={820} className="desktop-transaction-modal">
      {!detail ? <Spin /> : <>
        <Card size="small" title="Thông tin phiếu nhập" className="desktop-form-section">
          <Descriptions bordered size="small" column={1}>
            <Descriptions.Item label="Mã phiếu nhập">{String(detail.header.mapn)}</Descriptions.Item>
            <Descriptions.Item label="Ngày nhập">{dt(detail.header.ngaynhap)}</Descriptions.Item>
            <Descriptions.Item label="Loại phiếu">{String(detail.header.loai || "—")}</Descriptions.Item>
            <Descriptions.Item label="Nhà cung cấp">{String(detail.header.tenncc || detail.header.mancc || "—")}</Descriptions.Item>
            <Descriptions.Item label="Số HĐ nhà cung cấp">{String(detail.header.shdncc || "Không có")}</Descriptions.Item>
            <Descriptions.Item label="Nhân viên lập">{String(detail.header.tennv || detail.header.manv || "—")}</Descriptions.Item>
            <Descriptions.Item label="Trạng thái">{Number(detail.header.status) ? "Có hiệu lực" : "Đã hủy"}</Descriptions.Item>
          </Descriptions>
        </Card>
        <Card size="small" title="Chi tiết sản phẩm" className="desktop-form-section">
          <Table<DataRow> className="detail-table" rowKey="masp" pagination={false} dataSource={detail.items} columns={[
            { title: "Mã SP", dataIndex: "masp", key: "masp", width: 90 },
            { title: "Tên sản phẩm", dataIndex: "tensp", key: "tensp" },
            { title: "ĐVT", dataIndex: "dvt", key: "dvt", width: 70 },
            { title: "Số lượng", dataIndex: "quantity", key: "quantity", align: "right", width: 90 },
            { title: "Đơn giá nhập", dataIndex: "price", key: "price", align: "right", render: money, width: 135 },
            { title: "VAT (%)", dataIndex: "vat", key: "vat", align: "right", render: (v: unknown) => String(v ?? 0) + "%", width: 85 },
            { title: "Thành tiền", key: "amount", align: "right", render: (_: unknown, row: DataRow) => money(Number(row.price || 0) * Number(row.quantity || 0)), width: 140 },
          ]} />
        </Card>
        <Card size="small" title="Tổng giá trị" className="desktop-form-section">
          <Descriptions bordered size="small" column={1}>
            <Descriptions.Item label="Tổng tiền hàng (đã gồm VAT)">
              <Text strong className="transaction-total-value">{money(detail.header.total)}</Text>
            </Descriptions.Item>
          </Descriptions>
        </Card>
      </>}
    </Modal>
  </div>;
}

type CartLine = { product_code: string; quantity: number };
function InvoicesPage() {
  const { user } = useAuth();
  const canCreate = ["admin", "rl_ThuNgan", "rl_QuanLy"].includes(user?.role_code || "");
  const { period, setPeriod } = usePeriod();
  const [rows, setRows] = useState<DataRow[]>([]);
  const [keyword, setKeyword] = useState("");
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [lookup, setLookup] = useState<InvoiceLookup | null>(null);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [cart, setCart] = useState<CartLine[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<string>();
  const [promotionCode, setPromotionCode] = useState<string>();
  const [cash, setCash] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [detail, setDetail] = useState<{ header: DataRow; items: DataRow[] } | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { setRows(await operationsApi.invoices(period[0].format("YYYY-MM-DD"), period[1].format("YYYY-MM-DD"), keyword)); }
    catch (e) { message.error(err(e)); } finally { setLoading(false); }
  }, [period, keyword]);
  useEffect(() => { void load(); }, [load]);

  async function openAdd() {
    setOpen(true); setLookupLoading(true); setLookup(null);
    setCart([]); setSelectedProduct(undefined); setPromotionCode(undefined); setCash(null);
    try { setLookup(await operationsApi.invoiceLookups()); }
    catch (e) { setOpen(false); message.error(err(e)); } finally { setLookupLoading(false); }
  }

  async function showDetail(code: string) {
    setDetailOpen(true); setDetail(null);
    try { setDetail(await operationsApi.invoiceDetail(code)); }
    catch (e) { setDetailOpen(false); message.error(err(e)); }
  }

  function addLine() {
    if (!lookup || !selectedProduct) return;
    const p = lookup.products.find((item) => item.masp === selectedProduct);
    if (!p) return;
    setCart((list) => {
      const existing = list.find((line) => line.product_code === selectedProduct);
      return existing
        ? list.map((line) => line.product_code === selectedProduct ? { ...line, quantity: Math.min(line.quantity + 1, p.stock) } : line)
        : [...list, { product_code: selectedProduct, quantity: 1 }];
    });
    setSelectedProduct(undefined);
  }

  const promo = lookup?.promotions.find((p) => String(p[0]) === promotionCode);
  const discount = Number(promo?.[2] || 0);
  const subtotal = cart.reduce((sum, line) => sum + Number(lookup?.products.find((p) => p.masp === line.product_code)?.price || 0) * line.quantity, 0);
  const total = subtotal * (1 - discount / 100);

  async function checkout() {
    if (!cart.length) { message.warning("Hóa đơn chưa có sản phẩm."); return; }
    if (cash === null || cash < total) { message.warning("Tiền khách đưa chưa đủ thanh toán."); return; }
    setSaving(true);
    try {
      const result = await operationsApi.createInvoice({ promotion_code: promotionCode || null, cash, items: cart });
      message.success("Đã lập hóa đơn " + String(result.code || "") + ".");
      setOpen(false); await load();
    } catch (e) { message.error(err(e)); } finally { setSaving(false); }
  }

  async function cancel(code: string) {
    try { await operationsApi.cancelInvoice(code); message.success("Đã hủy hóa đơn và hoàn kho."); await load(); }
    catch (e) { message.error(err(e)); }
  }

  const cartColumns: TableColumnsType<CartLine> = [
    { title: "Mã SP", dataIndex: "product_code", key: "product_code", width: 95 },
    {
      title: "Tên sản phẩm",
      key: "product_name",
      render: (_: unknown, line) => lookup?.products.find((product) => product.masp === line.product_code)?.tensp || line.product_code,
    },
    {
      title: "ĐVT",
      key: "unit",
      width: 70,
      render: (_: unknown, line) => lookup?.products.find((product) => product.masp === line.product_code)?.dvt || "—",
    },
    {
      title: "Số lượng",
      key: "quantity",
      width: 120,
      render: (_: unknown, line) => (
        <InputNumber
          min={1}
          max={lookup?.products.find((product) => product.masp === line.product_code)?.stock}
          precision={0}
          value={line.quantity}
          onChange={(value) => setCart((list) => list.map((item) => item.product_code === line.product_code ? { ...item, quantity: Number(value || 1) } : item))}
          style={{ width: "100%" }}
        />
      ),
    },
    {
      title: "Đơn giá (đã gồm VAT)",
      key: "price",
      align: "right",
      width: 150,
      render: (_: unknown, line) => money(lookup?.products.find((product) => product.masp === line.product_code)?.price),
    },
    {
      title: "VAT (%)",
      key: "vat",
      align: "right",
      width: 90,
      render: (_: unknown, line) => String(lookup?.products.find((product) => product.masp === line.product_code)?.vat ?? 0) + "%",
    },
    {
      title: "Thành tiền",
      key: "amount",
      align: "right",
      width: 140,
      render: (_: unknown, line) => money(Number(lookup?.products.find((product) => product.masp === line.product_code)?.price || 0) * line.quantity),
    },
    {
      title: "Thao tác",
      key: "remove",
      width: 70,
      render: (_: unknown, line) => <Button danger type="text" icon={<StopOutlined />} aria-label="Xóa sản phẩm" onClick={() => setCart((list) => list.filter((item) => item.product_code !== line.product_code))} />,
    },
  ];

  const detailSubtotal = detail?.items.reduce(
    (sum, item) => sum + Number(item.price || 0) * Number(item.quantity || 0),
    0,
  ) || 0;
  const detailDiscountRate = Number(detail?.header.discount_rate || 0);
  const detailDiscount = detailSubtotal * detailDiscountRate / 100;
  const detailTotal = detailSubtotal - detailDiscount;
  const detailCash = Number(detail?.header.cash || 0);
  const detailChange = Math.max(detailCash - detailTotal, 0);

  const columns: TableColumnsType<DataRow> = [
    { title: "Mã hóa đơn", dataIndex: "mahd", key: "mahd", width: 140 },
    { title: "Ngày lập", dataIndex: "ngaylap", key: "ngaylap", width: 170, render: dt },
    { title: "Nhân viên", dataIndex: "tennv", key: "tennv" },
    { title: "Ca", dataIndex: "soca", key: "soca", width: 65, render: (v: unknown) => v ? "Ca " + String(v) : "—" },
    { title: "Tổng tiền", dataIndex: "tongtien", key: "tongtien", width: 150, align: "right", render: money },
    { title: "Tiền khách đưa", dataIndex: "tienkhachdua", key: "tienkhachdua", width: 155, align: "right", render: money },
    { title: "Trạng thái", dataIndex: "trangthai", key: "status", width: 110, render: (v: boolean) => <Tag color={v ? "success" : "default"}>{v ? "Có hiệu lực" : "Đã hủy"}</Tag> },
    { title: "Thao tác", key: "actions", width: 190, render: (_: unknown, row: DataRow) => <Space>
      <Button size="small" icon={<EyeOutlined />} onClick={() => void showDetail(String(row.mahd))}>Chi tiết</Button>
      {canCreate && Boolean(row.trangthai) && <Popconfirm title="Hủy hóa đơn?" description="Hóa đơn đã có phiếu đổi trả không thể hủy." okText="Hủy hóa đơn" cancelText="Đóng" onConfirm={() => void cancel(String(row.mahd))}><Button danger size="small" icon={<StopOutlined />} /></Popconfirm>}
    </Space> },
  ];

  return <div className="operation-page">
    <div className="operation-heading"><div><Text className="eyebrow">BÁN HÀNG</Text><Title level={2}>Hóa đơn</Title><Text className="muted-text">Lập và tra cứu hóa đơn bán hàng.</Text></div>{canCreate && <Button type="primary" icon={<PlusOutlined />} onClick={() => void openAdd()}>Lập hóa đơn</Button>}</div>
    <Card bordered={false} className="operation-card">
      <div className="operation-toolbar">
        <DatePicker.RangePicker value={period} format="DD/MM/YYYY" onChange={(v) => { if (v?.[0] && v[1]) setPeriod([v[0], v[1]]); }} />
        <Input.Search className="operation-search" allowClear value={keyword} placeholder="Mã hóa đơn, nhân viên, sản phẩm, ca..." onChange={(e) => setKeyword(e.target.value)} onSearch={(v) => setKeyword(v.trim())} enterButton="Tìm kiếm" />
        <Button icon={<ReloadOutlined />} onClick={() => void load()}>Làm mới</Button>
      </div>
      <Table<DataRow> rowKey="mahd" columns={columns} dataSource={rows} loading={loading} pagination={{ pageSize: 10, showSizeChanger: true }} />
    </Card>
    <Modal
      title="Lập hóa đơn bán hàng"
      open={open}
      onCancel={() => setOpen(false)}
      onOk={() => void checkout()}
      okText="Thanh toán"
      cancelText="Hủy"
      confirmLoading={saving}
      width={1040}
      destroyOnClose
      className="desktop-transaction-modal"
    >
      {lookupLoading || !lookup ? <div className="product-modal-loading"><Spin /></div> : (
        <>
          <Card size="small" title="Thông tin hóa đơn" className="desktop-form-section">
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="Nhân viên">
                {lookup.employee.tennv} {lookup.employee.manv ? "(" + lookup.employee.manv + ")" : "(Tài khoản hệ thống)"}
              </Descriptions.Item>
              <Descriptions.Item label="Ca làm việc">
                {lookup.active_shift
                  ? "Ca " + lookup.active_shift.soca + " | Mã ca: " + lookup.active_shift.maca + " | " + dayjs(lookup.active_shift.ngaylam).format("DD/MM/YYYY") + " | " + lookup.active_shift.tgmo + " - " + lookup.active_shift.tgdong
                  : "Tài khoản Admin – không giới hạn ca làm việc"}
              </Descriptions.Item>
            </Descriptions>
            <Form className="desktop-dialog-form invoice-promotion-form" layout="horizontal" labelCol={{ xs: { span: 24 }, sm: { span: 7 } }} wrapperCol={{ xs: { span: 24 }, sm: { span: 17 } }}>
              <Form.Item label="Khuyến mãi">
                <Select
                  allowClear
                  value={promotionCode}
                  onChange={setPromotionCode}
                  style={{ width: "100%" }}
                  placeholder="Không áp dụng khuyến mãi"
                  options={lookup.promotions.map((promotion) => ({
                    value: String(promotion[0]),
                    label: String(promotion[1]) + " (" + promotion[2] + "%)",
                  }))}
                />
              </Form.Item>
            </Form>
          </Card>

          <Card size="small" title="Thêm sản phẩm" className="desktop-form-section">
            <div className="transaction-product-search">
              <Select
                showSearch
                optionFilterProp="label"
                style={{ flex: 1, minWidth: 0 }}
                placeholder="Quét hoặc tìm mã vạch / ISBN / tên sản phẩm"
                value={selectedProduct}
                onChange={setSelectedProduct}
                options={lookup.products.map((product) => ({
                  value: product.masp,
                  label: product.masp + " · " + product.tensp + " · " + (product.barcode || product.isbn || "") + " · Tồn " + product.stock,
                }))}
              />
              <Button type="primary" icon={<PlusOutlined />} onClick={addLine}>Thêm vào giỏ</Button>
            </div>
          </Card>

          <Card size="small" title="Giỏ hàng" className="desktop-form-section">
            <Table<CartLine>
              rowKey="product_code"
              columns={cartColumns}
              dataSource={cart}
              pagination={false}
              locale={{ emptyText: "Chưa có sản phẩm trong giỏ." }}
              scroll={{ x: 850 }}
            />
          </Card>

          <Card size="small" title="Thanh toán" className="desktop-form-section transaction-total-card">
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="Tiền hàng (đã gồm VAT)">{money(subtotal)}</Descriptions.Item>
              <Descriptions.Item label={"Giảm giá (" + discount + "%)"}>{money(subtotal - total)}</Descriptions.Item>
              <Descriptions.Item label="Khách cần trả">
                <Text strong className="transaction-total-value">{money(total)}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Tiền khách đưa">
                <InputNumber
                  min={0}
                  precision={2}
                  value={cash}
                  onChange={(value) => setCash(value === null ? null : Number(value))}
                  style={{ width: "100%", maxWidth: 280 }}
                />
              </Descriptions.Item>
              <Descriptions.Item label="Tiền thừa">
                <Text strong>{cash === null ? "—" : money(Math.max(cash - total, 0))}</Text>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </>
      )}
    </Modal>
    <Modal title="Chi tiết hóa đơn" open={detailOpen} onCancel={() => setDetailOpen(false)} footer={<Button onClick={() => setDetailOpen(false)}>Đóng</Button>} width={820} className="desktop-transaction-modal">
      {!detail ? <Spin /> : <>
        <Card size="small" title="Thông tin hóa đơn" className="desktop-form-section">
          <Descriptions bordered size="small" column={1}>
            <Descriptions.Item label="Mã hóa đơn">{String(detail.header.mahd)}</Descriptions.Item>
            <Descriptions.Item label="Ngày lập">{dt(detail.header.ngaylap)}</Descriptions.Item>
            <Descriptions.Item label="Nhân viên">{String(detail.header.tennv || detail.header.manv || "Admin")}</Descriptions.Item>
            <Descriptions.Item label="Vai trò">{String(detail.header.vaitro || "—")}</Descriptions.Item>
            <Descriptions.Item label="Ca làm việc">
              {detail.header.soca ? "Ca " + String(detail.header.soca) + " | " + String(detail.header.tgmo || "").slice(0, 5) + " - " + String(detail.header.tgdong || "").slice(0, 5) : "Admin"}
            </Descriptions.Item>
            <Descriptions.Item label="Khuyến mãi">{String(detail.header.tenkm || "Không áp dụng")}</Descriptions.Item>
            <Descriptions.Item label="Trạng thái">{Number(detail.header.status) ? "Có hiệu lực" : "Đã hủy"}</Descriptions.Item>
          </Descriptions>
        </Card>
        <Card size="small" title="Chi tiết sản phẩm" className="desktop-form-section">
          <Table<DataRow> className="detail-table" rowKey="masp" pagination={false} dataSource={detail.items} columns={[
            { title: "Mã SP", dataIndex: "masp", key: "masp", width: 90 },
            { title: "Tên sản phẩm", dataIndex: "tensp", key: "tensp" },
            { title: "ĐVT", dataIndex: "dvt", key: "dvt", width: 70 },
            { title: "Đơn giá (đã gồm VAT)", dataIndex: "price", key: "price", align: "right", render: money, width: 150 },
            { title: "Số lượng", dataIndex: "quantity", key: "quantity", align: "right", width: 85 },
            { title: "VAT (%)", dataIndex: "vat", key: "vat", align: "right", render: (value: unknown) => String(value ?? 0) + "%", width: 85 },
            { title: "Thành tiền", key: "amount", align: "right", render: (_: unknown, item: DataRow) => money(Number(item.price || 0) * Number(item.quantity || 0)), width: 140 },
          ]} />
        </Card>
        <Card size="small" title="Thanh toán" className="desktop-form-section transaction-total-card">
          <Descriptions bordered size="small" column={1}>
            <Descriptions.Item label="Tiền hàng (đã gồm VAT)">{money(detailSubtotal)}</Descriptions.Item>
            <Descriptions.Item label={"Giảm giá (" + detailDiscountRate + "%)"}>{money(detailDiscount)}</Descriptions.Item>
            <Descriptions.Item label="Khách cần trả"><Text strong className="transaction-total-value">{money(detailTotal)}</Text></Descriptions.Item>
            <Descriptions.Item label="Tiền khách đưa">{money(detailCash)}</Descriptions.Item>
            <Descriptions.Item label="Tiền thừa">{money(detailChange)}</Descriptions.Item>
          </Descriptions>
        </Card>
      </>}
    </Modal>
  </div>;
}

export function SalesStockPage({ pageKey }: { pageKey: "invoices" | "imports" }) {
  return pageKey === "invoices" ? <InvoicesPage /> : <ImportsPage />;
}
