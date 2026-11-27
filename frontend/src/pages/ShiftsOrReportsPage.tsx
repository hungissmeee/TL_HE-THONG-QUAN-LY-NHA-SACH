import { useCallback, useEffect, useState } from "react";
import {
  Alert, Button, Card, Col, DatePicker, Form, Input, InputNumber,
  Modal, Popconfirm, Row, Select, Space, Spin, Statistic, Table, Tag, Typography,
  message, type TableColumnsType,
} from "antd";
import { DeleteOutlined, PlusOutlined, ReloadOutlined, TeamOutlined } from "@ant-design/icons";
import dayjs, { type Dayjs } from "dayjs";
import { ApiError } from "@/services/api";
import { operationsApi, type Row as DataRow } from "@/features/operations/operationsApi";
import { useAuth } from "@/features/auth/AuthContext";

const { Title, Text } = Typography;
const err = (e: unknown) => e instanceof ApiError ? e.message : "Không thể hoàn tất yêu cầu.";
const money = (v: unknown) => Number(v ?? 0).toLocaleString("vi-VN") + " ₫";
const dateText = (v: unknown) => v ? dayjs(String(v)).format("DD/MM/YYYY") : "—";

function ShiftsPage() {
  const { user } = useAuth();
  const isManager = ["admin", "rl_QuanLy"].includes(user?.role_code || "");
  const isAccountant = ["admin", "rl_KeToan"].includes(user?.role_code || "");
  const [summary, setSummary] = useState<Row | null>(null);
  const [current, setCurrent] = useState<DataRow[]>([]);
  const [history, setHistory] = useState<DataRow[]>([]);
  const [mine, setMine] = useState<DataRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [period, setPeriod] = useState("all");
  const [openCreate, setOpenCreate] = useState(false);
  const [createSaving, setCreateSaving] = useState(false);
  const [createForm] = Form.useForm();
  const [roster, setRoster] = useState<DataRow[]>([]);
  const [rosterTitle, setRosterTitle] = useState("");
  const [rosterOpen, setRosterOpen] = useState(false);
  const [closingShift, setClosingShift] = useState<Row | null>(null);
  const [cash, setCash] = useState<number | null>(null);
  const [closingSaving, setClosingSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (isManager) {
        const [s, c, h] = await Promise.all([
          operationsApi.shiftSummary(),
          operationsApi.currentShifts(),
          operationsApi.shiftHistory(period),
        ]);
        setSummary(s); setCurrent(c); setHistory(h);
      } else {
        setMine(await operationsApi.myShifts());
      }
    } catch (e) { message.error(err(e)); }
    finally { setLoading(false); }
  }, [isManager, period]);
  useEffect(() => { void load(); }, [load]);

  async function createShift(values: { soca: number; ngaylam: Dayjs; tmdauca: number }) {
    setCreateSaving(true);
    try {
      const result = await operationsApi.createShift({
        soca: values.soca,
        ngaylam: values.ngaylam.format("YYYY-MM-DD"),
        tmdauca: values.tmdauca,
      });
      message.success("Đã tạo ca " + String(result.maca) + ".");
      setOpenCreate(false); await load();
    } catch (e) { message.error(err(e)); }
    finally { setCreateSaving(false); }
  }

  async function deleteShift(id: number) {
    try { await operationsApi.deleteShift(id); message.success("Đã xóa ca làm việc."); await load(); }
    catch (e) { message.error(err(e)); }
  }

  async function registerShift(id: number) {
    try { await operationsApi.registerShift(id); message.success("Đã đăng ký ca làm việc."); await load(); }
    catch (e) { message.error(err(e)); }
  }

  async function showRoster(id: number) {
    setRosterOpen(true); setRoster([]); setRosterTitle("Danh sách nhân viên · Mã ca " + id);
    try { setRoster(await operationsApi.shiftRoster(id)); }
    catch (e) { setRosterOpen(false); message.error(err(e)); }
  }

  async function submitClosingCash() {
    if (!closingShift || cash === null) { message.warning("Nhập tiền cuối ca."); return; }
    setClosingSaving(true);
    try {
      await operationsApi.closingCash(Number(closingShift.maca), cash);
      message.success("Đã ghi tiền cuối ca.");
      setClosingShift(null); setCash(null); await load();
    } catch (e) { message.error(err(e)); }
    finally { setClosingSaving(false); }
  }

  const managerColumns: TableColumnsType<Row> = [
    { title: "Mã ca", dataIndex: "maca", key: "maca", width: 85 },
    { title: "Ngày", dataIndex: "ngaylam", key: "ngaylam", width: 120, render: dateText },
    { title: "Ca", dataIndex: "soca", key: "soca", width: 65, render: (v: unknown) => "Ca " + String(v) },
    { title: "Giờ làm", key: "hours", width: 145, render: (_: unknown, row: DataRow) => String(row.tgmo || "").slice(0, 5) + " – " + String(row.tgdong || "").slice(0, 5) },
    { title: "Nhân viên", dataIndex: "so_nhan_vien", key: "count", width: 100, align: "right" },
    { title: "Tiền đầu ca", dataIndex: "tmdauca", key: "opening", width: 140, align: "right", render: money },
    { title: "Tiền cuối ca", dataIndex: "tmcuoica", key: "closing", width: 140, align: "right", render: (v: unknown) => v === null ? "Chưa chốt" : money(v) },
    { title: "Trạng thái", dataIndex: "trangthai", key: "status", width: 130, render: (v: string) => <Tag color={v === "Đang diễn ra" ? "success" : v === "Đã kết thúc" ? "default" : "blue"}>{v}</Tag> },
    { title: "Thao tác", key: "actions", width: 170, render: (_: unknown, row: DataRow) => <Space>
      <Button size="small" icon={<TeamOutlined />} onClick={() => void showRoster(Number(row.maca))}>Nhân viên</Button>
      {isManager && row.trangthai === "Sắp bắt đầu" && <Popconfirm title="Xóa ca này?" okText="Xóa" cancelText="Hủy" onConfirm={() => void deleteShift(Number(row.maca))}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm>}
    </Space> },
  ];

  const employeeColumns: TableColumnsType<Row> = [
    { title: "Mã ca", dataIndex: "maca", key: "maca", width: 85 },
    { title: "Ngày", dataIndex: "ngaylam", key: "ngaylam", width: 130, render: dateText },
    { title: "Ca", dataIndex: "soca", key: "soca", width: 70, render: (v: unknown) => "Ca " + String(v) },
    { title: "Giờ làm", key: "hours", width: 150, render: (_: unknown, row: DataRow) => String(row.tgmo || "").slice(0, 5) + " – " + String(row.tgdong || "").slice(0, 5) },
    { title: "Số nhân viên", dataIndex: "so_nhan_vien", key: "count", width: 115 },
    { title: "Trạng thái", key: "status", render: (_: unknown, row: DataRow) => <Tag color={row.is_registered ? "success" : "default"}>{row.is_registered ? "Đã đăng ký" : row.is_ended ? "Đã kết thúc" : "Chưa đăng ký"}</Tag> },
    { title: "Thao tác", key: "actions", width: 175, render: (_: unknown, row: DataRow) => <Space>
      {!row.is_registered && !row.is_ended && <Button size="small" type="primary" onClick={() => void registerShift(Number(row.maca))}>Đăng ký</Button>}
      {isAccountant && row.is_ended && row.tmcuoica === null && <Button size="small" onClick={() => { setClosingShift(row); setCash(null); }}>Ghi tiền cuối ca</Button>}
    </Space> },
  ];

  return <div className="operation-page">
    <div className="operation-heading"><div><Text className="eyebrow">QUẢN LÝ NHÂN SỰ</Text><Title level={2}>Ca làm việc</Title><Text className="muted-text">Lịch ca, đăng ký ca và theo dõi việc chốt tiền.</Text></div>{isManager && <Button type="primary" icon={<PlusOutlined />} onClick={() => { createForm.resetFields(); createForm.setFieldsValue({ soca: 1, ngaylam: dayjs(), tmdauca: 0 }); setOpenCreate(true); }}>Tạo ca làm việc</Button>}</div>
    {isManager ? <>
      <Row gutter={[14, 14]} className="operation-stats">
        <Col xs={24} md={8}><Card bordered={false}><Statistic title="Ca đang diễn ra" value={Number(summary?.active_shifts || 0)} /></Card></Col>
        <Col xs={24} md={8}><Card bordered={false}><Statistic title="Nhân viên đang làm" value={Number(summary?.active_employees || 0)} /></Card></Col>
        <Col xs={24} md={8}><Card bordered={false}><Statistic title="Tổng ca hôm nay" value={Number(summary?.today_shifts || 0)} /></Card></Col>
      </Row>
      <Card bordered={false} className="operation-card">
        <div className="operation-list-heading"><Title level={4}>Ca đang diễn ra</Title><Button icon={<ReloadOutlined />} onClick={() => void load()}>Làm mới</Button></div>
        <Table<DataRow> rowKey="maca" columns={managerColumns} dataSource={current} loading={loading} pagination={false} locale={{ emptyText: "Hiện không có ca đang diễn ra." }} />
      </Card>
      <Card bordered={false} className="operation-card">
        <div className="operation-toolbar"><Title level={4}>Lịch sử ca</Title><Select value={period} style={{ width: 180 }} options={[{ value: "all", label: "Tất cả" }, { value: "today", label: "Hôm nay" }, { value: "7days", label: "7 ngày gần nhất" }, { value: "30days", label: "30 ngày gần nhất" }]} onChange={setPeriod} /></div>
        <Table<DataRow> rowKey="maca" columns={managerColumns} dataSource={history} loading={loading} pagination={{ pageSize: 10, showSizeChanger: true }} />
      </Card>
    </> : <Card bordered={false} className="operation-card">
      <Alert type="info" showIcon message={isAccountant ? "Kế toán có thể đăng ký ca đang diễn ra và ghi tiền cuối ca sau khi ca kết thúc." : "Chỉ đăng ký được ca đang diễn ra; không thể đăng ký trùng ca."} />
      <div className="operation-list-heading"><Title level={4}>Ca của bạn</Title><Button icon={<ReloadOutlined />} onClick={() => void load()}>Làm mới</Button></div>
      <Table<DataRow> rowKey="maca" columns={employeeColumns} dataSource={mine} loading={loading} pagination={false} locale={{ emptyText: "Hiện không có ca phù hợp để đăng ký hoặc chốt." }} />
    </Card>}
    <Modal title="Tạo ca làm việc" open={openCreate} onCancel={() => setOpenCreate(false)} onOk={() => createForm.submit()} okText="Tạo ca" cancelText="Hủy" confirmLoading={createSaving}>
      <Form form={createForm} layout="vertical" onFinish={(v) => void createShift(v)}>
        <Form.Item name="ngaylam" label="Ngày làm" rules={[{ required: true }]}><DatePicker format="DD/MM/YYYY" style={{ width: "100%" }} /></Form.Item>
        <Form.Item name="soca" label="Số ca" rules={[{ required: true }]}><Select options={[{ value: 1, label: "Ca 1 · 07:00–12:00" }, { value: 2, label: "Ca 2 · 12:00–17:00" }, { value: 3, label: "Ca 3 · 17:00–22:00" }]} /></Form.Item>
        <Form.Item name="tmdauca" label="Tiền đầu ca" rules={[{ required: true }]}><InputNumber min={0} precision={2} style={{ width: "100%" }} /></Form.Item>
        <Alert type="info" message="Giờ mở/đóng ca là lịch cố định của hệ thống. Không thể tạo trùng số ca trong cùng ngày." />
      </Form>
    </Modal>
    <Modal title={rosterTitle} open={rosterOpen} onCancel={() => setRosterOpen(false)} footer={<Button onClick={() => setRosterOpen(false)}>Đóng</Button>}>
      <Table<DataRow> rowKey="manv" pagination={false} dataSource={roster} columns={[
        { title: "Mã NV", dataIndex: "manv", key: "manv" }, { title: "Họ tên", dataIndex: "tennv", key: "tennv" },
        { title: "Vai trò", dataIndex: "vaitro", key: "vaitro" }, { title: "SĐT", dataIndex: "sdt", key: "sdt" },
      ]} />
    </Modal>
    <Modal title="Ghi tiền cuối ca" open={Boolean(closingShift)} onCancel={() => setClosingShift(null)} onOk={() => void submitClosingCash()} okText="Ghi nhận" cancelText="Hủy" confirmLoading={closingSaving}>
      <p>{closingShift ? "Ca " + String(closingShift.soca) + " · " + dateText(closingShift.ngaylam) : ""}</p>
      <InputNumber min={0} precision={2} value={cash} onChange={(v) => setCash(v === null ? null : Number(v))} style={{ width: "100%" }} placeholder="Nhập số tiền cuối ca" />
      <Alert className="operation-info" type="warning" message="Mỗi ca chỉ được ghi tiền cuối ca một lần và chỉ sau khi ca kết thúc." />
    </Modal>
  </div>;
}

const REPORT_LABELS: Record<string, string> = {
  report_overview: "Tổng quan",
  report_revenue: "Doanh thu",
  report_invoice: "Hóa đơn",
  report_import: "Nhập hàng",
  report_return: "Đổi trả",
  report_inventory: "Tồn kho",
  report_product: "Sản phẩm",
  report_shifts: "Ca làm việc",
};

function titleCase(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function cellRender(key: string, value: unknown) {
  if (key.includes("ngay") || key === "ky") return dateText(value);
  if (["doanh_thu", "doanh_thu_sau_hoan", "tien_hang", "tien_giam", "tien_hoan", "tong_tien_hoan", "tong_tri_gia", "gia_tri_ton", "gianhap", "giaban", "tien_khach_dua"].includes(key)) return money(value);
  if (key === "trangthai") {
    const status = typeof value === "number" ? (value ? "Có hiệu lực" : "Đã hủy") : String(value);
    return <Tag>{status}</Tag>;
  }
  if (key === "tylegiam" || key === "vat") return String(value ?? 0) + "%";
  return value === null || value === undefined ? "—" : String(value);
}

function ReportsPage({ reportType }: { reportType: string }) {
  const [range, setRange] = useState<[Dayjs, Dayjs]>([dayjs().subtract(30, "day").startOf("day"), dayjs().endOf("day")]);
  const [period, setPeriod] = useState<"day" | "month" | "year">("day");
  const [sort, setSort] = useState<"quantity_desc" | "quantity_asc" | "revenue_desc">("revenue_desc");
  const [threshold, setThreshold] = useState(5);
  const [inventoryStatus, setInventoryStatus] = useState<"all" | "low" | "out">("all");
  const [keyword, setKeyword] = useState("");
  const [result, setResult] = useState<{
    summary?: DataRow; trend?: DataRow[]; top_products?: DataRow[]; items?: DataRow[]; suppliers?: DataRow[];
  } | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setResult(await operationsApi.report(reportType, {
        start_date: range[0].format("YYYY-MM-DD"),
        end_date: range[1].format("YYYY-MM-DD"),
        period, sort, threshold, inventory_status: inventoryStatus, keyword,
      }));
    } catch (e) { message.error(err(e)); }
    finally { setLoading(false); }
  }, [reportType, range, period, sort, threshold, inventoryStatus, keyword]);
  useEffect(() => { void load(); }, [load]);

  function makeColumns(items: DataRow[]): TableColumnsType<Row> {
    if (!items.length) return [];
    return Object.keys(items[0]).map((key) => ({
      title: titleCase(key),
      dataIndex: key,
      key,
      ellipsis: true,
      render: (value: unknown) => cellRender(key, value),
    }));
  }

  const reportTitle = REPORT_LABELS[reportType] || "Báo cáo";
  const items = result?.items || [];

  return <div className="operation-page">
    <div className="operation-heading"><div><Text className="eyebrow">BÁO CÁO</Text><Title level={2}>Báo cáo {reportTitle.toLowerCase()}</Title><Text className="muted-text">Dữ liệu được tổng hợp trực tiếp từ các chứng từ và giao dịch trong SQL Server.</Text></div><Button icon={<ReloadOutlined />} onClick={() => void load()}>Làm mới</Button></div>
    <Card bordered={false} className="operation-card">
      <div className="operation-toolbar">
        <DatePicker.RangePicker value={range} format="DD/MM/YYYY" onChange={(v) => { if (v?.[0] && v[1]) setRange([v[0], v[1]]); }} />
        {reportType === "report_revenue" && <Select value={period} style={{ width: 150 }} options={[{ value: "day", label: "Theo ngày" }, { value: "month", label: "Theo tháng" }, { value: "year", label: "Theo năm" }]} onChange={setPeriod} />}
        {reportType === "report_product" && <Select value={sort} style={{ width: 210 }} options={[{ value: "revenue_desc", label: "Doanh thu giảm dần" }, { value: "quantity_desc", label: "Số lượng bán giảm dần" }, { value: "quantity_asc", label: "Số lượng bán tăng dần" }]} onChange={setSort} />}
        {reportType === "report_inventory" && <>
          <Select value={inventoryStatus} style={{ width: 160 }} options={[{ value: "all", label: "Tất cả tồn kho" }, { value: "low", label: "Sắp hết hàng" }, { value: "out", label: "Hết hàng" }]} onChange={setInventoryStatus} />
          <InputNumber min={1} max={100000} value={threshold} onChange={(v) => setThreshold(Number(v || 5))} />
          <Input allowClear value={keyword} placeholder="Tìm mã hoặc tên..." style={{ width: 200 }} onChange={(e) => setKeyword(e.target.value)} />
        </>}
      </div>
      {loading ? <div className="product-modal-loading"><Spin /></div> : <>
        {reportType === "report_overview" && result?.summary && <Row gutter={[14, 14]} className="operation-stats">
          <Col xs={24} md={8}><Card bordered={false}><Statistic title="Hóa đơn có hiệu lực" value={Number(result.summary.hoa_don_hieu_luc || 0)} /></Card></Col>
          <Col xs={24} md={8}><Card bordered={false}><Statistic title="Doanh thu" value={Number(result.summary.doanh_thu || 0)} suffix="₫" formatter={(v) => Number(v).toLocaleString("vi-VN")} /></Card></Col>
          <Col xs={24} md={8}><Card bordered={false}><Statistic title="Tiền hoàn" value={Number(result.summary.tien_hoan || 0)} suffix="₫" formatter={(v) => Number(v).toLocaleString("vi-VN")} /></Card></Col>
          <Col xs={24} md={8}><Card bordered={false}><Statistic title="Hóa đơn đã hủy" value={Number(result.summary.hoa_don_da_huy || 0)} /></Card></Col>
          <Col xs={24} md={8}><Card bordered={false}><Statistic title="Giá trị nhập" value={Number(result.summary.gia_tri_nhap || 0)} suffix="₫" formatter={(v) => Number(v).toLocaleString("vi-VN")} /></Card></Col>
          <Col xs={24} md={8}><Card bordered={false}><Statistic title="Doanh thu sau hoàn" value={Number(result.summary.doanh_thu || 0) - Number(result.summary.tien_hoan || 0)} suffix="₫" formatter={(v) => Number(v).toLocaleString("vi-VN")} /></Card></Col>
        </Row}
        {reportType === "report_inventory" && result?.summary && <Row gutter={[14, 14]} className="operation-stats">
          <Col xs={24} md={8}><Card bordered={false}><Statistic title="Tổng sản phẩm" value={Number(result.summary.total_products || 0)} /></Card></Col>
          <Col xs={24} md={8}><Card bordered={false}><Statistic title="Sắp hết hàng" value={Number(result.summary.low_stock || 0)} /></Card></Col>
          <Col xs={24} md={8}><Card bordered={false}><Statistic title="Hết hàng" value={Number(result.summary.out_of_stock || 0)} /></Card></Col>
          <Col xs={24} md={8}><Card bordered={false}><Statistic title="Giá trị tồn kho" value={Number(result.summary.inventory_value || 0)} suffix="₫" formatter={(v) => Number(v).toLocaleString("vi-VN")} /></Card></Col>
        </Row}
        {reportType === "report_overview" ? <>
          <Title level={4}>Doanh thu theo ngày</Title>
          <Table<DataRow> rowKey={(r) => String(r.ngay)} dataSource={result?.trend || []} columns={makeColumns(result?.trend || [])} pagination={{ pageSize: 8 }} />
          <Title level={4}>Top sản phẩm</Title>
          <Table<DataRow> rowKey="masp" dataSource={result?.top_products || []} columns={makeColumns(result?.top_products || [])} pagination={false} />
        </> : <>
          <Table<DataRow> rowKey={(r, index) => String(r.mahd || r.mapn || r.mapdt || r.masp || r.maca || r.ky || index)} dataSource={items} columns={makeColumns(items)} loading={loading} pagination={{ pageSize: 15, showSizeChanger: true, pageSizeOptions: [10, 15, 30, 50] }} locale={{ emptyText: "Không có dữ liệu trong khoảng thời gian đã chọn." }} scroll={{ x: 1250 }} />
          {reportType === "report_import" && Boolean(result?.suppliers?.length) && <>
            <Title level={4}>Tổng hợp theo nhà cung cấp</Title>
            <Table<DataRow> rowKey="mancc" dataSource={result?.suppliers || []} columns={makeColumns(result?.suppliers || [])} pagination={{ pageSize: 8 }} />
          </>}
        </>}
      </>}
    </Card>
  </div>;
}

export function ShiftsOrReportsPage({ pageKey }: { pageKey: "shifts" | "report_overview" | "report_revenue" | "report_invoice" | "report_import" | "report_return" | "report_inventory" | "report_product" | "report_shifts" }) {
  return pageKey === "shifts" ? <ShiftsPage /> : <ReportsPage reportType={pageKey} />;
}
