import { useCallback, useEffect, useState } from "react";
import {
  Alert, Button, Card, DatePicker, Descriptions, Form, Input, InputNumber,
  Modal, Popconfirm, Select, Space, Spin, Table, Typography, message,
  type TableColumnsType,
} from "antd";
import { DeleteOutlined, EditOutlined, EyeOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import dayjs, { type Dayjs } from "dayjs";
import { ApiError } from "@/services/api";
import {
  operationsApi,
  type ReturnInvoiceItems,
  type Row as DataRow,
} from "@/features/operations/operationsApi";
import { useAuth } from "@/features/auth/AuthContext";

const { Title, Text } = Typography;
const err = (e: unknown) => e instanceof ApiError ? e.message : "Không thể hoàn tất yêu cầu.";
const money = (v: unknown) => Number(v ?? 0).toLocaleString("vi-VN") + " ₫";
const dt = (v: unknown) => v ? dayjs(String(v)).format("DD/MM/YYYY HH:mm") : "—";

function usePeriod() {
  const [period, setPeriod] = useState<[Dayjs, Dayjs]>([dayjs().subtract(30, "day").startOf("day"), dayjs().endOf("day")]);
  return { period, setPeriod };
}

type ReturnLineState = { product_code: string; quantity: number; condition: 0 | 1; action: 0 | 1 };
function ReturnsPage() {
  const { user } = useAuth();
  const canManage = ["admin", "rl_QuanLy"].includes(user?.role_code || "");
  const { period, setPeriod } = usePeriod();
  const [rows, setRows] = useState<DataRow[]>([]);
  const [keyword, setKeyword] = useState("");
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [eligible, setEligible] = useState<{ mahd: string; ngaylap: string }[]>([]);
  const [invoiceCode, setInvoiceCode] = useState<string>();
  const [invoiceData, setInvoiceData] = useState<ReturnInvoiceItems | null>(null);
  const [lines, setLines] = useState<ReturnLineState[]>([]);
  const [reason, setReason] = useState("");
  const [loadingInvoice, setLoadingInvoice] = useState(false);
  const [saving, setSaving] = useState(false);
  const [detail, setDetail] = useState<{ header: DataRow; items: DataRow[] } | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { setRows(await operationsApi.returns(period[0].format("YYYY-MM-DD"), period[1].format("YYYY-MM-DD"), keyword)); }
    catch (e) { message.error(err(e)); } finally { setLoading(false); }
  }, [period, keyword]);
  useEffect(() => { void load(); }, [load]);

  async function openAdd() {
    setOpen(true);
    setEligible([]);
    setInvoiceCode(undefined);
    setInvoiceData(null);
    setLines([]);
    setReason("");
    try { setEligible(await operationsApi.eligibleReturnInvoices()); }
    catch (e) { setOpen(false); message.error(err(e)); }
  }

  async function selectInvoice(code?: string) {
    setInvoiceCode(code);
    setInvoiceData(null);
    setLines([]);
    if (!code) return;
    setLoadingInvoice(true);
    try {
      const result = await operationsApi.returnInvoiceItems(code);
      setInvoiceData(result);
      setLines(result.items.filter((item) => item.remaining > 0).map((item) => ({
        product_code: item.product_code, quantity: 0, condition: 1, action: 0,
      })));
    } catch (e) { message.error(err(e)); }
    finally { setLoadingInvoice(false); }
  }

  function changeLine(code: string, patch: Partial<ReturnLineState>) {
    setLines((current) => current.map((line) => {
      if (line.product_code !== code) return line;
      const next = { ...line, ...patch };
      if (next.action === 1 && next.condition !== 0) next.action = 0;
      return next;
    }));
  }

  async function create() {
    const selected = lines.filter((line) => line.quantity > 0);
    if (!invoiceCode || !reason.trim() || !selected.length) {
      message.warning("Chọn hóa đơn, nhập lý do và số lượng cần xử lý.");
      return;
    }
    setSaving(true);
    try {
      const result = await operationsApi.createReturn({
        invoice_code: invoiceCode, reason: reason.trim(), items: selected,
      });
      message.success("Đã lập phiếu đổi trả " + String(result.code || "") + ".");
      setOpen(false);
      await load();
    } catch (e) { message.error(err(e)); }
    finally { setSaving(false); }
  }

  async function showDetail(code: string) {
    setDetailOpen(true); setDetail(null);
    try { setDetail(await operationsApi.returnDetail(code)); }
    catch (e) { setDetailOpen(false); message.error(err(e)); }
  }

  async function remove(code: string) {
    try { await operationsApi.deleteReturn(code); message.success("Đã xóa phiếu và đảo biến động kho."); await load(); }
    catch (e) { message.error(err(e)); }
  }

  const columns: TableColumnsType<DataRow> = [
    { title: "Mã phiếu", dataIndex: "mapdt", key: "mapdt", width: 140 },
    { title: "Ngày đổi trả", dataIndex: "ngay", key: "ngay", width: 175, render: dt },
    { title: "Hóa đơn gốc", dataIndex: "mahd", key: "mahd", width: 140 },
    { title: "Nhân viên", dataIndex: "tennv", key: "tennv", width: 150 },
    { title: "Lý do", dataIndex: "lydo", key: "lydo" },
    { title: "Số lượng", dataIndex: "tongsoluong", key: "tongsoluong", width: 100, align: "right" },
    { title: "Tiền hoàn", dataIndex: "tonghoan", key: "tonghoan", width: 145, align: "right", render: money },
    { title: "Thao tác", key: "actions", width: 155, render: (_: unknown, row: DataRow) => <Space>
      <Button size="small" icon={<EyeOutlined />} onClick={() => void showDetail(String(row.mapdt))}>Chi tiết</Button>
      {canManage && <Popconfirm title="Xóa phiếu đổi trả?" description="Hệ thống sẽ đảo biến động tồn kho. Nếu tồn hiện tại không đủ, thao tác bị từ chối." okText="Xóa" cancelText="Hủy" onConfirm={() => void remove(String(row.mapdt))}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm>}
    </Space> },
  ];

  const returnColumns: TableColumnsType<ReturnInvoiceItems["items"][number]> = [
    { title: "Sản phẩm", dataIndex: "product_name", key: "name" },
    { title: "Mua", dataIndex: "purchased", key: "purchased", width: 65, align: "right" },
    { title: "Đã xử lý", dataIndex: "processed", key: "processed", width: 85, align: "right" },
    { title: "Còn lại", dataIndex: "remaining", key: "remaining", width: 80, align: "right" },
    { title: "SL đổi/trả", key: "quantity", width: 125, render: (_: unknown, item) => {
      const line = lines.find((x) => x.product_code === item.product_code);
      return <InputNumber min={0} max={item.remaining} precision={0} value={line?.quantity || 0} disabled={item.remaining < 1} onChange={(v) => changeLine(item.product_code, { quantity: Number(v || 0) })} />;
    } },
    { title: "Tình trạng", key: "condition", width: 145, render: (_: unknown, item) => {
      const line = lines.find((x) => x.product_code === item.product_code);
      return <Select size="small" value={line?.condition ?? 1} disabled={!item.remaining} style={{ width: 130 }} options={[{ value: 1, label: "Còn nguyên vẹn" }, { value: 0, label: "Đã hỏng" }]} onChange={(v) => changeLine(item.product_code, { condition: v })} />;
    } },
    { title: "Xử lý", key: "action", width: 145, render: (_: unknown, item) => {
      const line = lines.find((x) => x.product_code === item.product_code);
      return <Select size="small" value={line?.action ?? 0} disabled={!item.remaining} style={{ width: 130 }} options={[{ value: 0, label: "Hoàn tiền" }, { value: 1, label: "Đổi cùng mã", disabled: line?.condition !== 0 }]} onChange={(v) => changeLine(item.product_code, { action: v })} />;
    } },
    { title: "Giá hoàn dự kiến", key: "estimate", align: "right", render: (_: unknown, item) => {
      const line = lines.find((x) => x.product_code === item.product_code);
      return money((line?.action === 1 ? 0 : Number(item.net_price)) * (line?.quantity || 0));
    } },
  ];

  const estimatedRefund = lines.reduce((sum, line) => {
    if (line.action === 1) return sum;
    const item = invoiceData?.items.find((entry) => entry.product_code === line.product_code);
    return sum + Number(item?.net_price || 0) * line.quantity;
  }, 0);

  return <div className="operation-page">
    <div className="operation-heading"><div><Text className="eyebrow">BÁN HÀNG</Text><Title level={2}>Đổi trả</Title><Text className="muted-text">Chỉ hóa đơn còn hiệu lực trong ngày mới đủ điều kiện đổi trả.</Text></div>{canManage && <Button type="primary" icon={<PlusOutlined />} onClick={() => void openAdd()}>Lập phiếu đổi trả</Button>}</div>
    <Card bordered={false} className="operation-card">
      <div className="operation-toolbar">
        <DatePicker.RangePicker value={period} format="DD/MM/YYYY" onChange={(v) => { if (v?.[0] && v[1]) setPeriod([v[0], v[1]]); }} />
        <Input.Search className="operation-search" allowClear value={keyword} placeholder="Mã phiếu, hóa đơn, nhân viên, lý do..." onChange={(e) => setKeyword(e.target.value)} onSearch={(v) => setKeyword(v.trim())} enterButton="Tìm kiếm" />
        <Button icon={<ReloadOutlined />} onClick={() => void load()}>Làm mới</Button>
      </div>
      <Table<DataRow> rowKey="mapdt" columns={columns} dataSource={rows} loading={loading} pagination={{ pageSize: 10, showSizeChanger: true }}  scroll={{ x: "max-content" }} tableLayout="auto" />
    </Card>
    <Modal
      title="Lập phiếu đổi trả"
      open={open}
      onCancel={() => setOpen(false)}
      onOk={() => void create()}
      okText="Lập phiếu"
      cancelText="Hủy"
      confirmLoading={saving}
      width={1120}
      destroyOnClose
      className="desktop-transaction-modal"
    >
      <Card size="small" title="Hóa đơn gốc" className="desktop-form-section">
        <Form className="desktop-dialog-form" layout="horizontal" labelCol={{ xs: { span: 24 }, sm: { span: 7 } }} wrapperCol={{ xs: { span: 24 }, sm: { span: 17 } }}>
          <Form.Item label="Mã hóa đơn">
            <Select
              showSearch
              optionFilterProp="label"
              value={invoiceCode}
              onChange={(value) => void selectInvoice(value)}
              placeholder="Chọn hóa đơn đủ điều kiện trong ngày"
              options={eligible.map((item) => ({
                value: item.mahd,
                label: item.mahd + " · " + dt(item.ngaylap),
              }))}
            />
          </Form.Item>
        </Form>
        {loadingInvoice ? <div className="product-modal-loading"><Spin /></div> : invoiceData ? (
          <Alert type="info" showIcon message={"Hóa đơn " + invoiceData.invoice_code + " · Ngày lập " + dt(invoiceData.invoice_date) + " · Tỷ lệ giảm giá gốc " + invoiceData.discount_rate + "%"} />
        ) : (
          <Text type="secondary">
            {eligible.length ? "Chọn hóa đơn trong ngày để xem các sản phẩm còn đủ điều kiện đổi trả." : "Không có hóa đơn đủ điều kiện trong ngày."}
          </Text>
        )}
      </Card>

      <Card size="small" title="Thông tin xử lý" className="desktop-form-section">
        <Form className="desktop-dialog-form" layout="vertical">
          <Form.Item label="Lý do" required>
            <Input.TextArea
              rows={2}
              maxLength={255}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Nhập lý do khách yêu cầu đổi hoặc trả..."
            />
          </Form.Item>
        </Form>
      </Card>

      <Card size="small" title="Sản phẩm trong hóa đơn" className="desktop-form-section">
        <Text type="secondary" className="return-condition-hint">
          Hàng nguyên vẹn chỉ được hoàn tiền. Đổi sản phẩm chỉ áp dụng với hàng đã hỏng và đổi đúng sản phẩm cùng mã.
        </Text>
        {invoiceData ? (
          <Table
            rowKey="product_code"
            size="small"
            pagination={false}
            dataSource={invoiceData.items}
            columns={returnColumns}
            scroll={{ x: "max-content" }}
           tableLayout="auto" />
        ) : (
          <Text type="secondary">Chọn hóa đơn gốc để hiển thị danh sách sản phẩm.</Text>
        )}
      </Card>

      <Card size="small" title="Tổng kết" className="desktop-form-section transaction-total-card">
        <Descriptions bordered size="small" column={1}>
          <Descriptions.Item label="Tổng tiền hoàn dự kiến">
            <Text strong className="transaction-total-value">{money(estimatedRefund)}</Text>
          </Descriptions.Item>
        </Descriptions>
        <Alert
          type="warning"
          showIcon
          message="Chỉ đổi cùng mã khi hàng trả đã hỏng. Hàng nguyên vẹn chỉ được hoàn tiền và được nhập lại kho."
        />
      </Card>
    </Modal>
    <Modal
      title="Chi tiết phiếu đổi trả"
      open={detailOpen}
      onCancel={() => setDetailOpen(false)}
      footer={<Button onClick={() => setDetailOpen(false)}>Đóng</Button>}
      width={820}
      className="desktop-transaction-modal"
    >
      {!detail ? <Spin /> : <>
        <Card size="small" title="Thông tin phiếu" className="desktop-form-section">
          <Descriptions bordered size="small" column={1}>
            <Descriptions.Item label="Mã phiếu">{String(detail.header.mapdt)}</Descriptions.Item>
            <Descriptions.Item label="Ngày xử lý">{dt(detail.header.ngay)}</Descriptions.Item>
            <Descriptions.Item label="Hóa đơn gốc">{String(detail.header.mahd)}</Descriptions.Item>
            <Descriptions.Item label="Nhân viên xử lý">{String(detail.header.tennv || "—")}</Descriptions.Item>
            <Descriptions.Item label="Lý do">{String(detail.header.reason || detail.header.lydo || "—")}</Descriptions.Item>
          </Descriptions>
        </Card>
        <Card size="small" title="Chi tiết sản phẩm" className="desktop-form-section">
          <Table<DataRow> rowKey="masp" pagination={false} dataSource={detail.items} columns={[
            { title: "Mã SP", dataIndex: "masp", key: "masp", width: 90 },
            { title: "Sản phẩm", dataIndex: "tensp", key: "tensp" },
            { title: "Số lượng", dataIndex: "quantity", key: "quantity", width: 90, align: "right" },
            {
              title: "Tình trạng hàng",
              dataIndex: "condition",
              key: "condition",
              width: 135,
              render: (value: unknown) => Number(value) === 1 ? "Còn nguyên vẹn" : "Đã hỏng",
            },
            {
              title: "Hình thức xử lý",
              dataIndex: "action",
              key: "action",
              width: 135,
              render: (value: unknown) => Number(value) === 1 ? "Đổi cùng mã" : "Hoàn tiền",
            },
            { title: "Đơn giá hoàn", dataIndex: "unit_refund", key: "unit_refund", render: money, align: "right" },
            { title: "Thành tiền hoàn", key: "amount", render: (_: unknown, item: DataRow) => money(Number(item.unit_refund || 0) * Number(item.quantity || 0)), align: "right" },
          ]}  scroll={{ x: "max-content" }} tableLayout="auto" />
        </Card>
        <Card size="small" title="Tổng kết" className="desktop-form-section transaction-total-card">
          <Descriptions bordered size="small" column={1}>
            <Descriptions.Item label="Tổng tiền hoàn">
              <Text strong className="transaction-total-value">{money(detail.header.refund)}</Text>
            </Descriptions.Item>
          </Descriptions>
        </Card>
      </>}
    </Modal>
  </div>;
}

function EmployeesPage() {
  const [rows, setRows] = useState<DataRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [employee, setEmployee] = useState<DataRow | null>(null);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try { setRows(await operationsApi.employees(keyword)); }
    catch (e) { message.error(err(e)); } finally { setLoading(false); }
  }, [keyword]);
  useEffect(() => { void load(); }, [load]);

  function openEdit(row: DataRow) {
    setEmployee(row);
    form.setFieldsValue({ full_name: row.tennv, phone: row.sdt });
  }

  async function save(values: { full_name: string; phone?: string }) {
    if (!employee) return;
    try {
      await operationsApi.updateEmployee(String(employee.manv), values);
      message.success("Đã cập nhật hồ sơ nhân viên.");
      setEmployee(null);
      await load();
    } catch (e) { message.error(err(e)); }
  }

  const columns: TableColumnsType<DataRow> = [
    { title: "Mã nhân viên", dataIndex: "manv", key: "manv", width: 145 },
    { title: "Họ tên", dataIndex: "tennv", key: "tennv" },
    { title: "Vai trò", dataIndex: "vaitro", key: "vaitro", width: 155 },
    { title: "Số điện thoại", dataIndex: "sdt", key: "sdt", width: 150 },
    { title: "Thao tác", key: "actions", width: 100, render: (_: unknown, row: DataRow) => <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)}>Sửa</Button> },
  ];

  return <div className="operation-page">
    <div className="operation-heading"><div><Text className="eyebrow">QUẢN LÝ NHÂN SỰ</Text><Title level={2}>Nhân viên</Title><Text className="muted-text">Tra cứu và cập nhật hồ sơ nhân viên.</Text></div></div>
    <Alert type="info" showIcon message="Trang Web hiện quản lý hồ sơ và thông tin liên hệ. Tạo/xóa SQL Login, đổi role và ngưng tài khoản vẫn cần quy trình quản trị SQL riêng; không cấp quyền máy chủ rộng cho tài khoản dịch vụ Web." />
    <Card bordered={false} className="operation-card">
      <div className="operation-toolbar">
        <Input.Search className="operation-search" allowClear value={keyword} placeholder="Tìm mã nhân viên hoặc họ tên..." onChange={(e) => setKeyword(e.target.value)} onSearch={(v) => setKeyword(v.trim())} enterButton="Tìm kiếm" />
        <Button icon={<ReloadOutlined />} onClick={() => void load()}>Làm mới</Button>
      </div>
      <Table<DataRow> rowKey="manv" columns={columns} dataSource={rows} loading={loading} pagination={{ pageSize: 10, showSizeChanger: true }}  scroll={{ x: "max-content" }} tableLayout="auto" />
    </Card>
    <Modal title={employee ? "Cập nhật nhân viên " + String(employee.manv) : "Nhân viên"} open={Boolean(employee)} onCancel={() => setEmployee(null)} onOk={() => form.submit()} okText="Lưu thay đổi" cancelText="Hủy" width={560} className="desktop-entity-modal">
      <Form form={form} className="desktop-dialog-form" layout="horizontal" labelCol={{ xs: { span: 24 }, sm: { span: 8 } }} wrapperCol={{ xs: { span: 24 }, sm: { span: 16 } }} onFinish={(v) => void save(v)}>
        <Card size="small" title="Thông tin nhân viên" className="desktop-form-section">
          <Form.Item name="full_name" label="Họ tên" rules={[{ required: true, whitespace: true, max: 100 }]}><Input maxLength={100} placeholder="Nhập họ tên" /></Form.Item>
          <Form.Item name="phone" label="Số điện thoại"><Input maxLength={15} placeholder="Số điện thoại" /></Form.Item>
        </Card>
      </Form>
    </Modal>
  </div>;
}

export function PeopleAndReturnsPage({ pageKey }: { pageKey: "returns" | "employees" }) {
  return pageKey === "returns" ? <ReturnsPage /> : <EmployeesPage />;
}
