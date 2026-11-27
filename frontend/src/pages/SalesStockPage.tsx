import { useCallback, useEffect, useState } from "react";
import {
  Alert, Button, Card, Col, DatePicker, Descriptions, Form, Input, InputNumber,
  Modal, Popconfirm, Row, Select, Space, Spin, Table, Tag, Typography, message,
  type TableColumnsType,
} from "antd";
import { EyeOutlined, PlusOutlined, ReloadOutlined, StopOutlined } from "@ant-design/icons";
import dayjs, { type Dayjs } from "dayjs";
import { ApiError } from "@/services/api";
import { operationsApi, type ImportLookup, type InvoiceLookup, type Row } from "@/features/operations/operationsApi";
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
  const [rows, setRows] = useState<Row[]>([]);
  const [keyword, setKeyword] = useState("");
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [lookups, setLookups] = useState<ImportLookup | null>(null);
  const [detail, setDetail] = useState<{ header: Row; items: Row[] } | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [formLoading, setFormLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

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

  async function save(values: Row) {
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

  const columns: TableColumnsType<Row> = [
    { title: "Mã phiếu", dataIndex: "mapn", key: "mapn", width: 125 },
    { title: "Ngày nhập", dataIndex: "ngaynhap", key: "ngaynhap", width: 170, render: dt },
    { title: "Nhà cung cấp", dataIndex: "tenncc", key: "tenncc", ellipsis: true },
    { title: "Nhân viên", dataIndex: "tennv", key: "tennv", width: 160 },
    { title: "Số HĐ NCC", dataIndex: "shdncc", key: "shdncc", width: 120 },
    { title: "Tổng trị giá", dataIndex: "tongtrigia", key: "tongtrigia", width: 145, align: "right", render: money },
    { title: "Trạng thái", dataIndex: "trangthai", key: "status", width: 120, render: (v: boolean) => <Tag color={v ? "success" : "default"}>{v ? "Có hiệu lực" : "Đã hủy"}</Tag> },
    { title: "Thao tác", key: "actions", width: 175, render: (_: unknown, row: Row) => <Space>
      <Button size="small" icon={<EyeOutlined />} onClick={() => void showDetail(String(row.mapn))}>Chi tiết</Button>
      {canWrite && row.trangthai && <Popconfirm title="Hủy phiếu nhập?" description="Tồn kho sẽ được hoàn tác nếu hiện còn đủ số lượng." okText="Hủy phiếu" cancelText="Đóng" onConfirm={() => void cancel(String(row.mapn))}><Button size="small" danger icon={<StopOutlined />} /></Popconfirm>}
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
      <Table<Row> rowKey="mapn" columns={columns} dataSource={rows} loading={loading} pagination={{ pageSize: 10, showSizeChanger: true }} />
    </Card>
    <Modal title="Lập phiếu nhập kho" open={open} onCancel={() => setOpen(false)} onOk={() => form.submit()} okText="Lập phiếu nhập" cancelText="Hủy" confirmLoading={saving} width={920} destroyOnClose>
      {formLoading || !lookups ? <div className="product-modal-loading"><Spin /></div> : <Form form={form} layout="vertical" onFinish={(v) => void save(v)}>
        <Row gutter={16}>
          <Col xs={24} md={12}><Form.Item name="supplier_code" label="Nhà cung cấp" rules={[{ required: true }]}><Select showSearch optionFilterProp="label" options={lookups.suppliers.map((s) => ({ value: s.code, label: s.code + " - " + s.name }))} /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="import_type" label="Loại phiếu nhập" rules={[{ required: true }]}><Select options={[{ value: "Nhập hàng", label: "Nhập hàng" }, { value: "Nhập bổ sung", label: "Nhập bổ sung" }, { value: "Nhập điều chỉnh", label: "Nhập điều chỉnh" }]} /></Form.Item></Col>
          <Col span={24}><Form.Item name="supplier_invoice" label="Số hóa đơn nhà cung cấp"><Input maxLength={50} /></Form.Item></Col>
        </Row>
        <Form.List name="items">
          {(fields, { add, remove }) => <>
            <div className="operation-list-heading"><Text strong>Chi tiết sản phẩm</Text><Button size="small" icon={<PlusOutlined />} onClick={() => add({ quantity: 1, vat: 0 })}>Thêm dòng</Button></div>
            {fields.map((field) => <Row gutter={10} align="middle" key={field.key}>
              <Col xs={24} md={11}><Form.Item name={[field.name, "product_code"]} rules={[{ required: true }]}><Select showSearch optionFilterProp="label" placeholder="Chọn sản phẩm" options={lookups.products.map((p) => ({ value: p.masp, label: p.masp + " - " + p.tensp + " · Tồn " + p.stock }))} onChange={(v) => {
                const p = lookups.products.find((item) => item.masp === v);
                if (p) {
                  const items = form.getFieldValue("items") || [];
                  items[field.name] = { ...items[field.name], price: Number(p.price || 0), vat: Number(p.vat || 0), quantity: items[field.name]?.quantity || 1 };
                  form.setFieldsValue({ items });
                }
              }} /></Form.Item></Col>
              <Col xs={8} md={4}><Form.Item name={[field.name, "quantity"]} rules={[{ required: true }]}><InputNumber min={1} precision={0} style={{ width: "100%" }} placeholder="SL" /></Form.Item></Col>
              <Col xs={8} md={4}><Form.Item name={[field.name, "price"]} rules={[{ required: true }]}><InputNumber min={0.01} precision={2} style={{ width: "100%" }} placeholder="Đơn giá" /></Form.Item></Col>
              <Col xs={5} md={3}><Form.Item name={[field.name, "vat"]}><InputNumber min={0} max={100} precision={2} style={{ width: "100%" }} placeholder="VAT" /></Form.Item></Col>
              <Col xs={3} md={2}><Button danger type="text" icon={<StopOutlined />} onClick={() => remove(field.name)} /></Col>
            </Row>)}
          </>}
        </Form.List>
        <Alert type="info" showIcon message="Giá nhập bình quân và tồn kho được cập nhật tự động trong cùng giao dịch khi lập phiếu." />
      </Form>}
    </Modal>
    <Modal title="Chi tiết phiếu nhập" open={detailOpen} onCancel={() => setDetailOpen(false)} footer={<Button onClick={() => setDetailOpen(false)}>Đóng</Button>} width={820}>
      {!detail ? <Spin /> : <>
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="Mã phiếu">{String(detail.header.mapn)}</Descriptions.Item>
          <Descriptions.Item label="Ngày nhập">{dt(detail.header.ngaynhap)}</Descriptions.Item>
          <Descriptions.Item label="Nhà cung cấp">{String(detail.header.tenncc || detail.header.mancc)}</Descriptions.Item>
          <Descriptions.Item label="Nhân viên">{String(detail.header.tennv || detail.header.manv || "—")}</Descriptions.Item>
          <Descriptions.Item label="Số HĐ NCC">{String(detail.header.shdncc || "—")}</Descriptions.Item>
          <Descriptions.Item label="Tổng trị giá">{money(detail.header.total)}</Descriptions.Item>
          <Descriptions.Item label="Trạng thái">{Number(detail.header.status) ? "Có hiệu lực" : "Đã hủy"}</Descriptions.Item>
        </Descriptions>
        <Table<Row> className="detail-table" rowKey="masp" pagination={false} dataSource={detail.items} columns={[
          { title: "Mã SP", dataIndex: "masp", key: "masp" }, { title: "Tên sản phẩm", dataIndex: "tensp", key: "tensp" },
          { title: "SL", dataIndex: "quantity", key: "quantity", align: "right" }, { title: "Đơn giá", dataIndex: "price", key: "price", align: "right", render: money },
          { title: "VAT", dataIndex: "vat", key: "vat", align: "right", render: (v: unknown) => String(v) + "%" },
        ]} />
      </>}
    </Modal>
  </div>;
}

type CartLine = { product_code: string; quantity: number };
function InvoicesPage() {
  const { user } = useAuth();
  const canCreate = ["admin", "rl_ThuNgan", "rl_QuanLy"].includes(user?.role_code || "");
  const { period, setPeriod } = usePeriod();
  const [rows, setRows] = useState<Row[]>([]);
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
  const [detail, setDetail] = useState<{ header: Row; items: Row[] } | null>(null);
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
    { title: "Sản phẩm", dataIndex: "product_code", key: "product_code", render: (code: string) => lookup?.products.find((p) => p.masp === code)?.tensp || code },
    { title: "Đơn giá", key: "price", align: "right", render: (_: unknown, line) => money(lookup?.products.find((p) => p.masp === line.product_code)?.price) },
    { title: "Tồn", key: "stock", align: "right", render: (_: unknown, line) => String(lookup?.products.find((p) => p.masp === line.product_code)?.stock ?? 0) },
    { title: "Số lượng", key: "quantity", width: 130, render: (_: unknown, line) => <InputNumber min={1} max={lookup?.products.find((p) => p.masp === line.product_code)?.stock} precision={0} value={line.quantity} onChange={(v) => setCart((list) => list.map((x) => x.product_code === line.product_code ? { ...x, quantity: Number(v || 1) } : x))} /> },
    { title: "Thành tiền", key: "amount", align: "right", render: (_: unknown, line) => money(Number(lookup?.products.find((p) => p.masp === line.product_code)?.price || 0) * line.quantity) },
    { title: "", key: "remove", width: 60, render: (_: unknown, line) => <Button danger type="text" icon={<StopOutlined />} onClick={() => setCart((list) => list.filter((x) => x.product_code !== line.product_code))} /> },
  ];

  const columns: TableColumnsType<Row> = [
    { title: "Mã hóa đơn", dataIndex: "mahd", key: "mahd", width: 140 },
    { title: "Ngày lập", dataIndex: "ngaylap", key: "ngaylap", width: 170, render: dt },
    { title: "Nhân viên", dataIndex: "tennv", key: "tennv" },
    { title: "Ca", dataIndex: "soca", key: "soca", width: 65, render: (v: unknown) => v ? "Ca " + String(v) : "—" },
    { title: "Tổng tiền", dataIndex: "tongtien", key: "tongtien", width: 150, align: "right", render: money },
    { title: "Tiền khách đưa", dataIndex: "tienkhachdua", key: "tienkhachdua", width: 155, align: "right", render: money },
    { title: "Trạng thái", dataIndex: "trangthai", key: "status", width: 110, render: (v: boolean) => <Tag color={v ? "success" : "default"}>{v ? "Có hiệu lực" : "Đã hủy"}</Tag> },
    { title: "Thao tác", key: "actions", width: 190, render: (_: unknown, row: Row) => <Space>
      <Button size="small" icon={<EyeOutlined />} onClick={() => void showDetail(String(row.mahd))}>Chi tiết</Button>
      {canCreate && row.trangthai && <Popconfirm title="Hủy hóa đơn?" description="Hóa đơn đã có phiếu đổi trả không thể hủy." okText="Hủy hóa đơn" cancelText="Đóng" onConfirm={() => void cancel(String(row.mahd))}><Button danger size="small" icon={<StopOutlined />} /></Popconfirm>}
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
      <Table<Row> rowKey="mahd" columns={columns} dataSource={rows} loading={loading} pagination={{ pageSize: 10, showSizeChanger: true }} />
    </Card>
    <Modal title="Lập hóa đơn bán hàng" open={open} onCancel={() => setOpen(false)} onOk={() => void checkout()} okText="Thanh toán" cancelText="Hủy" confirmLoading={saving} width={980} destroyOnClose>
      {lookupLoading || !lookup ? <div className="product-modal-loading"><Spin /></div> : <>
        <Alert className="operation-info" type="info" showIcon message={lookup.active_shift ? "Nhân viên: " + lookup.employee.tennv + " · Ca " + lookup.active_shift.soca + " (" + lookup.active_shift.tgmo + "–" + lookup.active_shift.tgdong + ")" : "Lập hóa đơn theo quyền Admin · " + lookup.employee.tennv} />
        <div className="operation-toolbar">
          <Select showSearch optionFilterProp="label" style={{ flex: 1, minWidth: 280 }} placeholder="Quét hoặc tìm mã vạch / ISBN / tên sản phẩm" value={selectedProduct} onChange={setSelectedProduct} options={lookup.products.map((p) => ({ value: p.masp, label: p.masp + " · " + p.tensp + " · " + (p.barcode || p.isbn || "") + " · Tồn " + p.stock }))} />
          <Button type="primary" onClick={addLine}>Thêm vào giỏ</Button>
        </div>
        <Table<CartLine> rowKey="product_code" columns={cartColumns} dataSource={cart} pagination={false} locale={{ emptyText: "Chưa có sản phẩm trong giỏ." }} />
        <Row gutter={16} className="invoice-checkout">
          <Col xs={24} md={12}><Text type="secondary">Khuyến mãi</Text><Select allowClear value={promotionCode} onChange={setPromotionCode} style={{ width: "100%" }} placeholder="Không áp dụng" options={lookup.promotions.map((p) => ({ value: String(p[0]), label: String(p[1]) + " · giảm " + p[2] + "%" }))} /></Col>
          <Col xs={24} md={12}><Text type="secondary">Tiền khách đưa</Text><InputNumber min={0} precision={2} value={cash} onChange={(v) => setCash(v === null ? null : Number(v))} style={{ width: "100%" }} /></Col>
        </Row>
        <Descriptions bordered size="small" column={2} className="invoice-totals">
          <Descriptions.Item label="Tiền hàng">{money(subtotal)}</Descriptions.Item>
          <Descriptions.Item label={"Giảm giá (" + discount + "%)"}>{money(subtotal - total)}</Descriptions.Item>
          <Descriptions.Item label="Khách cần trả"><Text strong>{money(total)}</Text></Descriptions.Item>
          <Descriptions.Item label="Tiền thừa"><Text strong>{cash === null ? "—" : money(Math.max(cash - total, 0))}</Text></Descriptions.Item>
        </Descriptions>
      </>}
    </Modal>
    <Modal title="Chi tiết hóa đơn" open={detailOpen} onCancel={() => setDetailOpen(false)} footer={<Button onClick={() => setDetailOpen(false)}>Đóng</Button>} width={820}>
      {!detail ? <Spin /> : <>
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="Mã hóa đơn">{String(detail.header.mahd)}</Descriptions.Item><Descriptions.Item label="Ngày lập">{dt(detail.header.ngaylap)}</Descriptions.Item>
          <Descriptions.Item label="Nhân viên">{String(detail.header.tennv || detail.header.manv || "Admin")}</Descriptions.Item><Descriptions.Item label="Ca">{detail.header.soca ? "Ca " + String(detail.header.soca) : "Admin"}</Descriptions.Item>
          <Descriptions.Item label="Khuyến mãi">{String(detail.header.tenkm || "Không áp dụng")}</Descriptions.Item><Descriptions.Item label="Giảm giá">{String(detail.header.discount_rate || 0)}%</Descriptions.Item>
          <Descriptions.Item label="Tiền khách đưa">{money(detail.header.cash)}</Descriptions.Item><Descriptions.Item label="Trạng thái">{Number(detail.header.status) ? "Có hiệu lực" : "Đã hủy"}</Descriptions.Item>
        </Descriptions>
        <Table<Row> className="detail-table" rowKey="masp" pagination={false} dataSource={detail.items} columns={[
          { title: "Mã SP", dataIndex: "masp", key: "masp" }, { title: "Tên sản phẩm", dataIndex: "tensp", key: "tensp" },
          { title: "Đơn giá", dataIndex: "price", key: "price", align: "right", render: money }, { title: "SL", dataIndex: "quantity", key: "quantity", align: "right" },
          { title: "VAT", dataIndex: "vat", key: "vat", align: "right", render: (v: unknown) => String(v) + "%" },
        ]} />
      </>}
    </Modal>
  </div>;
}

export function SalesStockPage({ pageKey }: { pageKey: "invoices" | "imports" }) {
  return pageKey === "invoices" ? <InvoicesPage /> : <ImportsPage />;
}
