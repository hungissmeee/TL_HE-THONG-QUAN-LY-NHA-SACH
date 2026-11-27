import { useCallback, useEffect, useState } from "react";
import {
  Alert, Button, Card, Col, DatePicker, Descriptions, Form, Input, InputNumber,
  Modal, Popconfirm, Row, Select, Space, Spin, Statistic, Table, Tag, Typography,
  message, type TableColumnsType,
} from "antd";
import { DeleteOutlined, PlusOutlined, ReloadOutlined, TeamOutlined } from "@ant-design/icons";
import dayjs, { type Dayjs } from "dayjs";
import { ApiError } from "@/services/api";
import { operationsApi, type Row as DataRow } from "@/features/operations/operationsApi";
import { tableSorter } from "@/services/tableSort";
import { useAuth } from "@/features/auth/AuthContext";

const { Title, Text } = Typography;
const err = (e: unknown) => e instanceof ApiError ? e.message : "Không thể hoàn tất yêu cầu.";
const money = (v: unknown) => Number(v ?? 0).toLocaleString("vi-VN") + " ₫";
const dateText = (v: unknown) => v ? dayjs(String(v)).format("DD/MM/YYYY") : "—";

const SHIFT_TIMES: Record<number, [string, string]> = {
  1: ["07:00", "12:00"],
  2: ["12:00", "17:00"],
  3: ["17:00", "22:00"],
};

function ShiftsPage() {
  const { user } = useAuth();
  const isManager = ["admin", "rl_QuanLy"].includes(user?.role_code || "");
  const isAccountant = ["admin", "rl_KeToan"].includes(user?.role_code || "");
  const [summary, setSummary] = useState<DataRow | null>(null);
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
  const [closingShift, setClosingShift] = useState<DataRow | null>(null);
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

  const managerColumns: TableColumnsType<DataRow> = [
    { title: "Mã ca", dataIndex: "maca", key: "maca", width: 85, sorter: tableSorter<DataRow>("maca") },
    { title: "Ngày", dataIndex: "ngaylam", key: "ngaylam", width: 120, sorter: tableSorter<DataRow>("ngaylam"), render: dateText },
    { title: "Ca", dataIndex: "soca", key: "soca", width: 65, sorter: tableSorter<DataRow>("soca"), render: (v: unknown) => "Ca " + String(v) },
    { title: "Giờ làm", key: "hours", width: 145, sorter: tableSorter<DataRow>((row) => String(row.tgmo || "") + String(row.tgdong || "")), render: (_: unknown, row: DataRow) => String(row.tgmo || "").slice(0, 5) + " – " + String(row.tgdong || "").slice(0, 5) },
    { title: "Nhân viên", dataIndex: "so_nhan_vien", key: "count", width: 100, align: "right", sorter: tableSorter<DataRow>("so_nhan_vien") },
    { title: "Tiền đầu ca", dataIndex: "tmdauca", key: "opening", width: 140, align: "right", sorter: tableSorter<DataRow>("tmdauca"), render: money },
    { title: "Tiền cuối ca", dataIndex: "tmcuoica", key: "closing", width: 140, align: "right", sorter: tableSorter<DataRow>("tmcuoica"), render: (v: unknown) => v === null ? "Chưa chốt" : money(v) },
    { title: "Trạng thái", dataIndex: "trangthai", key: "status", width: 130, sorter: tableSorter<DataRow>("trangthai"), render: (v: string) => <Tag color={v === "Đang diễn ra" ? "success" : v === "Đã kết thúc" ? "default" : "blue"}>{v}</Tag> },
    { title: "Thao tác", key: "actions", width: 170, render: (_: unknown, row: DataRow) => <Space>
      <Button size="small" icon={<TeamOutlined />} onClick={() => void showRoster(Number(row.maca))}>Nhân viên</Button>
      {isManager && row.trangthai === "Sắp bắt đầu" && <Popconfirm title="Xóa ca này?" okText="Xóa" cancelText="Hủy" onConfirm={() => void deleteShift(Number(row.maca))}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm>}
      {isAccountant && row.trangthai === "Đã kết thúc" && row.tmcuoica === null && <Button size="small" onClick={() => { setClosingShift(row); setCash(null); }}>Ghi tiền cuối ca</Button>}
    </Space> },
  ];

  const currentColumns: TableColumnsType<DataRow> = [
    { title: "Mã ca", dataIndex: "maca", key: "maca", width: 85, sorter: tableSorter<DataRow>("maca") },
    { title: "Ngày", dataIndex: "ngaylam", key: "ngaylam", width: 120, sorter: tableSorter<DataRow>("ngaylam"), render: dateText },
    { title: "Ca", dataIndex: "soca", key: "soca", width: 65, sorter: tableSorter<DataRow>("soca"), render: (v: unknown) => "Ca " + String(v) },
    { title: "Giờ làm", key: "hours", width: 145, sorter: tableSorter<DataRow>((row) => String(row.tgmo || "") + String(row.tgdong || "")), render: (_: unknown, row: DataRow) => String(row.tgmo || "").slice(0, 5) + " – " + String(row.tgdong || "").slice(0, 5) },
    { title: "Nhân viên", dataIndex: "so_nhan_vien", key: "count", width: 100, align: "right", sorter: tableSorter<DataRow>("so_nhan_vien") },
    { title: "Trạng thái", key: "status", width: 130, render: () => <Tag color="success">Đang diễn ra</Tag> },
    { title: "Thao tác", key: "actions", width: 140, render: (_: unknown, row: DataRow) => (
      <Button size="small" icon={<TeamOutlined />} onClick={() => void showRoster(Number(row.maca))}>Nhân viên</Button>
    ) },
  ];

  const employeeColumns: TableColumnsType<DataRow> = [
    { title: "Mã ca", dataIndex: "maca", key: "maca", width: 85, sorter: tableSorter<DataRow>("maca") },
    { title: "Ngày", dataIndex: "ngaylam", key: "ngaylam", width: 130, sorter: tableSorter<DataRow>("ngaylam"), render: dateText },
    { title: "Ca", dataIndex: "soca", key: "soca", width: 70, sorter: tableSorter<DataRow>("soca"), render: (v: unknown) => "Ca " + String(v) },
    { title: "Giờ làm", key: "hours", width: 150, sorter: tableSorter<DataRow>((row) => String(row.tgmo || "") + String(row.tgdong || "")), render: (_: unknown, row: DataRow) => String(row.tgmo || "").slice(0, 5) + " – " + String(row.tgdong || "").slice(0, 5) },
    { title: "Số nhân viên", dataIndex: "so_nhan_vien", key: "count", width: 115, sorter: tableSorter<DataRow>("so_nhan_vien") },
    { title: "Trạng thái", key: "status", sorter: tableSorter<DataRow>((row) => Boolean(row.is_registered) ? "Đã đăng ký" : Boolean(row.is_ended) ? "Đã kết thúc" : "Chưa đăng ký"), render: (_: unknown, row: DataRow) => <Tag color={Boolean(row.is_registered) ? "success" : "default"}>{Boolean(row.is_registered) ? "Đã đăng ký" : Boolean(row.is_ended) ? "Đã kết thúc" : "Chưa đăng ký"}</Tag> },
    { title: "Thao tác", key: "actions", width: 175, render: (_: unknown, row: DataRow) => <Space>
      {!Boolean(row.is_registered) && !Boolean(row.is_ended) && <Button size="small" type="primary" onClick={() => void registerShift(Number(row.maca))}>Đăng ký</Button>}
      {isAccountant && Boolean(row.is_ended) && row.tmcuoica === null && <Button size="small" onClick={() => { setClosingShift(row); setCash(null); }}>Ghi tiền cuối ca</Button>}
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
        <Table<DataRow> rowKey="maca" columns={currentColumns} dataSource={current} loading={loading} pagination={false} locale={{ emptyText: "Hiện không có ca đang diễn ra." }}  scroll={{ x: "max-content" }} tableLayout="auto" />
      </Card>
      <Card bordered={false} className="operation-card">
        <div className="operation-toolbar"><Title level={4}>Lịch sử ca</Title><Select value={period} style={{ width: 180 }} options={[{ value: "all", label: "Tất cả" }, { value: "today", label: "Hôm nay" }, { value: "7days", label: "7 ngày gần nhất" }, { value: "30days", label: "30 ngày gần nhất" }]} onChange={setPeriod} /></div>
        <Table<DataRow> rowKey="maca" columns={managerColumns} dataSource={history} loading={loading} pagination={{ pageSize: 10, showSizeChanger: true }}  scroll={{ x: "max-content" }} tableLayout="auto" />
      </Card>
    </> : <Card bordered={false} className="operation-card">
      <Alert type="info" showIcon message={isAccountant ? "Kế toán có thể đăng ký ca đang diễn ra và ghi tiền cuối ca sau khi ca kết thúc." : "Chỉ đăng ký được ca đang diễn ra; không thể đăng ký trùng ca."} />
      <div className="operation-list-heading"><Title level={4}>Ca của bạn</Title><Button icon={<ReloadOutlined />} onClick={() => void load()}>Làm mới</Button></div>
      <Table<DataRow> rowKey="maca" columns={employeeColumns} dataSource={mine} loading={loading} pagination={false} locale={{ emptyText: "Hiện không có ca phù hợp để đăng ký hoặc chốt." }}  scroll={{ x: "max-content" }} tableLayout="auto" />
    </Card>}
    <Modal
      title="Tạo ca làm việc"
      open={openCreate}
      onCancel={() => setOpenCreate(false)}
      onOk={() => createForm.submit()}
      okText="Tạo ca"
      cancelText="Hủy"
      confirmLoading={createSaving}
      width={560}
      className="desktop-entity-modal"
    >
      <Form
        form={createForm}
        className="desktop-dialog-form"
        layout="horizontal"
        labelCol={{ xs: { span: 24 }, sm: { span: 8 } }}
        wrapperCol={{ xs: { span: 24 }, sm: { span: 16 } }}
        onFinish={(values) => void createShift(values)}
      >
        <Card size="small" title="Thông tin ca làm việc" className="desktop-form-section">
          <Form.Item name="soca" label="Ca làm việc" rules={[{ required: true }]}>
            <Select options={[
              { value: 1, label: "Ca 1 (07:00 – 12:00)" },
              { value: 2, label: "Ca 2 (12:00 – 17:00)" },
              { value: 3, label: "Ca 3 (17:00 – 22:00)" },
            ]} />
          </Form.Item>
          <Form.Item name="ngaylam" label="Ngày làm" rules={[{ required: true }]}>
            <DatePicker format="DD/MM/YYYY" style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(previous, current) => previous.soca !== current.soca}>
            {({ getFieldValue }) => {
              const shiftNumber = Number(getFieldValue("soca") || 1);
              const times = SHIFT_TIMES[shiftNumber] || SHIFT_TIMES[1];
              return (
                <>
                  <Form.Item label="Giờ mở">
                    <Input value={times[0]} readOnly />
                  </Form.Item>
                  <Form.Item label="Giờ đóng">
                    <Input value={times[1]} readOnly />
                  </Form.Item>
                </>
              );
            }}
          </Form.Item>
          <Form.Item name="tmdauca" label="Tiền đầu ca" rules={[{ required: true }]}>
            <InputNumber min={0} precision={2} style={{ width: "100%" }} />
          </Form.Item>
          <Alert
            type="info"
            showIcon
            message="Mỗi ngày có tối đa 3 ca cố định. Không thể tạo trùng số ca trong cùng ngày."
          />
        </Card>
      </Form>
    </Modal>
    <Modal title={rosterTitle} open={rosterOpen} onCancel={() => setRosterOpen(false)} footer={<Button onClick={() => setRosterOpen(false)}>Đóng</Button>} width={720} className="desktop-transaction-modal">
      <Card size="small" title="Danh sách nhân viên trong ca" className="desktop-form-section">
        <Table<DataRow> rowKey="manv" pagination={false} dataSource={roster} columns={[
          { title: "Mã NV", dataIndex: "manv", key: "manv", width: 100, sorter: tableSorter<DataRow>("manv") },
          { title: "Họ tên", dataIndex: "tennv", key: "tennv", sorter: tableSorter<DataRow>("tennv") },
          { title: "Vai trò", dataIndex: "vaitro", key: "vaitro", width: 140, sorter: tableSorter<DataRow>("vaitro") },
          { title: "SĐT", dataIndex: "sdt", key: "sdt", width: 130, sorter: tableSorter<DataRow>("sdt") },
        ]}  scroll={{ x: "max-content" }} tableLayout="auto" />
      </Card>
    </Modal>
    <Modal title="Ghi tiền cuối ca" open={Boolean(closingShift)} onCancel={() => setClosingShift(null)} onOk={() => void submitClosingCash()} okText="Ghi nhận" cancelText="Hủy" confirmLoading={closingSaving} width={560} className="desktop-entity-modal">
      <Card size="small" title="Thông tin ca" className="desktop-form-section">
        <Descriptions bordered size="small" column={1}>
          <Descriptions.Item label="Ngày làm">{closingShift ? dateText(closingShift.ngaylam) : "—"}</Descriptions.Item>
          <Descriptions.Item label="Ca làm việc">{closingShift ? "Ca " + String(closingShift.soca) : "—"}</Descriptions.Item>
        </Descriptions>
      </Card>
      <Card size="small" title="Ghi nhận tiền cuối ca" className="desktop-form-section">
        <InputNumber min={0} precision={2} value={cash} onChange={(value) => setCash(value === null ? null : Number(value))} style={{ width: "100%" }} placeholder="Nhập số tiền cuối ca" />
        <Alert className="operation-info" type="warning" showIcon message="Mỗi ca chỉ được ghi tiền cuối ca một lần và chỉ sau khi ca kết thúc." />
      </Card>
    </Modal>
  </div>;
}

const REPORT_LABELS: Record<string, string> = {
  report_overview: "Tổng quan",
  report_revenue: "Doanh thu",
  report_invoice: "Hóa đơn bán hàng",
  report_import: "Nhập hàng",
  report_return: "Đổi trả",
  report_inventory: "Tồn kho",
  report_product: "Sản phẩm",
  report_shifts: "Ca làm việc",
};

const REPORT_DESCRIPTIONS: Record<string, string> = {
  report_overview: "Tổng hợp số hóa đơn, doanh thu, tiền hoàn và giá trị nhập trong khoảng thời gian đã chọn.",
  report_revenue: "Theo dõi doanh thu theo ngày, tháng hoặc năm; số liệu đã tách riêng tiền giảm và tiền hoàn.",
  report_invoice: "Danh sách hóa đơn bán hàng, tình trạng hiệu lực, khoản giảm giá, đổi trả và số tiền thực nhận.",
  report_import: "Theo dõi các phiếu nhập, nhà cung cấp, số lượng hàng nhập và tổng giá trị nhập.",
  report_return: "Thống kê phiếu đổi trả, số lượng hàng hoàn tiền, hàng đổi và tổng tiền hoàn khách.",
  report_inventory: "Kiểm tra số lượng còn trong kho, giá trị hàng tồn và các sản phẩm sắp hết hoặc đã hết hàng.",
  report_product: "So sánh số lượng bán và doanh thu của từng sản phẩm trong khoảng thời gian đã chọn.",
  report_shifts: "Tổng hợp ca làm việc, thời gian mở/đóng ca và thông tin nhân viên tham gia.",
};

const REPORT_COLUMN_LABELS: Record<string, string> = {
  ngay: "Ngày",
  ky: "Kỳ báo cáo",
  so_hoa_don: "Số hóa đơn",
  so_luong_ban: "Số lượng bán",
  doanh_thu: "Doanh thu",
  tien_hoan: "Tiền hoàn khách",
  doanh_thu_sau_hoan: "Doanh thu sau hoàn",
  masp: "Mã sản phẩm",
  tensp: "Tên sản phẩm",
  so_luong: "Số lượng",
  makm: "Mã khuyến mãi",
  tenkm: "Tên chương trình",
  tylegiam: "Mức giảm (%)",
  tien_hang: "Tiền hàng",
  tien_giam: "Tiền giảm giá",
  ngaylap: "Ngày lập hóa đơn",
  nhan_vien: "Nhân viên lập",
  ca: "Ca làm việc",
  tyle_giam: "Mức giảm (%)",
  doanh_thu_truoc_hoan: "Doanh thu trước hoàn",
  doanh_thu_thuc: "Doanh thu thực nhận",
  so_phieu_doi_tra: "Số phiếu đổi trả",
  sl_hoan_tien: "SL hàng hoàn tiền",
  sl_doi_hang: "SL hàng đổi",
  tien_khach_dua: "Tiền khách thanh toán",
  trangthai: "Trạng thái hóa đơn",
  mapn: "Mã phiếu nhập",
  ngaynhap: "Ngày nhập",
  loai_phieu: "Loại phiếu nhập",
  nha_cung_cap: "Nhà cung cấp",
  so_hoa_don_ncc: "Số hóa đơn nhà cung cấp",
  tong_so_luong: "Tổng số lượng nhập",
  tong_tri_gia: "Tổng giá trị nhập",
  mancc: "Mã nhà cung cấp",
  tenncc: "Tên nhà cung cấp",
  sdt: "Số điện thoại",
  so_phieu_nhap: "Số phiếu nhập",
  mapdt: "Mã phiếu đổi trả",
  ngay_doi_tra: "Ngày đổi trả",
  mahd: "Mã hóa đơn",
  ly_do: "Lý do đổi trả",
  sl_nguyen_ven: "Số lượng còn nguyên vẹn",
  sl_hang_hong: "Số lượng hàng hỏng",
  tong_tien_hoan: "Tổng tiền hoàn",
  dvt: "Đơn vị tính",
  slton: "Số lượng tồn",
  gianhap: "Giá nhập",
  giaban: "Giá bán",
  gia_tri_ton: "Giá trị hàng tồn",
  xep_hang: "Xếp hạng",
  sl_ban: "Số lượng bán",
  sl_hoan_tien_sp: "Số lượng hoàn tiền",
  maca: "Mã ca",
  ngaylam: "Ngày làm",
  soca: "Ca",
  tgmo: "Giờ bắt đầu",
  tgdong: "Giờ kết thúc",
  so_nhan_vien: "Số nhân viên",
  tmdauca: "Tiền đầu ca",
  tmcuoica: "Tiền cuối ca",
};

const REPORT_MONEY_FIELDS = new Set([
  "doanh_thu", "tien_hoan", "doanh_thu_sau_hoan", "tien_hang", "tien_giam",
  "doanh_thu_truoc_hoan", "doanh_thu_thuc", "tien_khach_dua", "tong_tri_gia",
  "tong_tien_hoan", "gia_tri_ton", "gianhap", "giaban", "tmdauca", "tmcuoica",
]);
const REPORT_PERCENT_FIELDS = new Set(["tylegiam", "tyle_giam", "vat"]);
const REPORT_DATE_FIELDS = new Set(["ngay", "ngaylap", "ngaynhap", "ngay_doi_tra", "ngaylam"]);
const REPORT_COUNT_FIELDS = new Set([
  "so_hoa_don", "so_luong_ban", "so_luong", "so_phieu_doi_tra", "sl_hoan_tien",
  "sl_doi_hang", "tong_so_luong", "so_phieu_nhap", "sl_nguyen_ven", "sl_hang_hong",
  "slton", "xep_hang", "sl_ban", "so_nhan_vien",
]);

function reportPeriodText(value: unknown) {
  const raw = String(value ?? "");
  if (/^\d{4}-\d{2}$/.test(raw)) return "Tháng " + raw.slice(5, 7) + "/" + raw.slice(0, 4);
  if (/^\d{4}$/.test(raw)) return "Năm " + raw;
  return raw || "—";
}

function cellRender(key: string, value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  if (REPORT_MONEY_FIELDS.has(key)) return money(value);
  if (REPORT_PERCENT_FIELDS.has(key)) return String(Number(value || 0).toLocaleString("vi-VN")) + "%";
  if (key === "ky") return reportPeriodText(value);
  if (REPORT_DATE_FIELDS.has(key)) return dateText(value);
  if (key === "trangthai") {
    if (typeof value === "boolean" || value === 0 || value === 1 || value === "true" || value === "false") {
      const active = value === true || value === 1 || value === "true";
      return <Tag color={active ? "success" : "default"}>{active ? "Có hiệu lực" : "Đã hủy"}</Tag>;
    }
    const status = String(value);
    const color = status.toLowerCase().includes("hết") ? "warning" : status.toLowerCase().includes("đang") ? "success" : "default";
    return <Tag color={color}>{status}</Tag>;
  }
  if (typeof value === "boolean") return <Tag color={value ? "success" : "default"}>{value ? "Có" : "Không"}</Tag>;
  if (key === "xep_hang") return "Hạng " + String(Number(value).toLocaleString("vi-VN"));
  if (REPORT_COUNT_FIELDS.has(key) && typeof value === "number") return value.toLocaleString("vi-VN");
  if (typeof value === "number") return value.toLocaleString("vi-VN");
  if (key === "ca" && /^\d+$/.test(String(value))) return "Ca " + String(value);
  return String(value);
}

function reportColumnWidth(key: string) {
  if (["tensp", "tenkm", "tenncc", "nha_cung_cap", "nhan_vien", "ly_do"].includes(key)) return 190;
  if (REPORT_MONEY_FIELDS.has(key)) return 160;
  if (REPORT_DATE_FIELDS.has(key)) return 150;
  if (["doanh_thu_truoc_hoan", "doanh_thu_sau_hoan", "doanh_thu_thuc", "so_hoa_don_ncc", "so_phieu_doi_tra"].includes(key)) return 185;
  if (["trangthai", "loai_phieu"].includes(key)) return 145;
  if (["mahd", "mapn", "mapdt", "masp", "mancc", "maca"].includes(key)) return 135;
  if (REPORT_PERCENT_FIELDS.has(key)) return 115;
  return 135;
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

  function makeColumns(items: DataRow[]): TableColumnsType<DataRow> {
    if (!items.length) return [];
    return Object.keys(items[0]).map((key) => ({
      title: key === "trangthai"
        ? reportType === "report_inventory" ? "Tình trạng tồn kho" : reportType === "report_shifts" ? "Trạng thái ca" : "Trạng thái hóa đơn"
        : REPORT_COLUMN_LABELS[key] || key.replace(/_/g, " "),
      dataIndex: key,
      key,
      sorter: tableSorter<DataRow>(key),
      width: reportColumnWidth(key),
      align: (REPORT_MONEY_FIELDS.has(key) || REPORT_COUNT_FIELDS.has(key) || REPORT_PERCENT_FIELDS.has(key)) ? "right" as const : "left" as const,
      render: (value: unknown) => cellRender(key, value),
    }));
  }

  const reportTitle = REPORT_LABELS[reportType] || "Báo cáo";
  const items = result?.items || [];
  const sumField = (key: string) => items.reduce((sum, row) => sum + Number(row[key] || 0), 0);
  const validInvoiceCount = items.filter((row) => row.trangthai === true || row.trangthai === 1 || row.trangthai === "true").length;

  const summaryCards: { title: string; value: number; currency?: boolean }[] =
    reportType === "report_invoice" ? [
      { title: "Tổng số hóa đơn", value: items.length },
      { title: "Hóa đơn có hiệu lực", value: validInvoiceCount },
      { title: "Doanh thu sau hoàn", value: sumField("doanh_thu_sau_hoan"), currency: true },
      { title: "Tiền đã hoàn khách", value: sumField("tien_hoan"), currency: true },
    ] : reportType === "report_revenue" ? [
      { title: "Tổng số hóa đơn", value: sumField("so_hoa_don") },
      { title: "Doanh thu sau hoàn", value: sumField("doanh_thu_sau_hoan"), currency: true },
      { title: "Tiền đã hoàn khách", value: sumField("tien_hoan"), currency: true },
    ] : reportType === "report_import" ? [
      { title: "Số phiếu nhập", value: items.length },
      { title: "Tổng số lượng nhập", value: sumField("tong_so_luong") },
      { title: "Tổng giá trị nhập", value: sumField("tong_tri_gia"), currency: true },
    ] : reportType === "report_return" ? [
      { title: "Số phiếu đổi trả", value: items.length },
      { title: "Hàng hoàn tiền", value: sumField("sl_hoan_tien") },
      { title: "Hàng đổi", value: sumField("sl_doi_hang") },
      { title: "Tổng tiền hoàn", value: sumField("tong_tien_hoan"), currency: true },
    ] : reportType === "report_product" ? [
      { title: "Sản phẩm có phát sinh", value: items.length },
      { title: "Tổng số lượng bán", value: sumField("sl_ban") },
      { title: "Doanh thu sau hoàn", value: sumField("doanh_thu_sau_hoan"), currency: true },
    ] : reportType === "report_shifts" ? [
      { title: "Số ca làm việc", value: items.length },
      { title: "Lượt nhân viên tham gia", value: sumField("so_nhan_vien") },
    ] : [];

  const reportDescription = REPORT_DESCRIPTIONS[reportType] || "Dữ liệu được tổng hợp từ các chứng từ và giao dịch trong hệ thống.";

  return <div className="operation-page">
    <div className="operation-heading"><div><Text className="eyebrow">BÁO CÁO</Text><Title level={2}>Báo cáo {reportTitle.toLowerCase()}</Title><Text className="muted-text">{reportDescription}</Text></div><Button icon={<ReloadOutlined />} onClick={() => void load()}>Làm mới</Button></div>
    <Card bordered={false} className="operation-card">
      <div className="operation-toolbar">
        {reportType !== "report_inventory" && <DatePicker.RangePicker value={range} format="DD/MM/YYYY" onChange={(v) => { if (v?.[0] && v[1]) setRange([v[0], v[1]]); }} />}
        {reportType === "report_revenue" && <Select value={period} style={{ width: 150 }} options={[{ value: "day", label: "Theo ngày" }, { value: "month", label: "Theo tháng" }, { value: "year", label: "Theo năm" }]} onChange={setPeriod} />}
        {reportType === "report_product" && <Select value={sort} style={{ width: 210 }} options={[{ value: "revenue_desc", label: "Doanh thu giảm dần" }, { value: "quantity_desc", label: "Số lượng bán giảm dần" }, { value: "quantity_asc", label: "Số lượng bán tăng dần" }]} onChange={setSort} />}
        {reportType === "report_inventory" && <>
          <Select value={inventoryStatus} style={{ width: 160 }} options={[{ value: "all", label: "Tất cả tồn kho" }, { value: "low", label: "Sắp hết hàng" }, { value: "out", label: "Hết hàng" }]} onChange={setInventoryStatus} />
          <InputNumber min={1} max={100000} value={threshold} onChange={(v) => setThreshold(Number(v || 5))} />
          <Input allowClear value={keyword} placeholder="Tìm mã hoặc tên..." style={{ width: 200 }} onChange={(e) => setKeyword(e.target.value)} />
        </>}
      </div>
      {loading ? <div className="product-modal-loading"><Spin /></div> : <>
        {summaryCards.length > 0 && <Row gutter={[14, 14]} className="operation-stats report-summary-stats">
          {summaryCards.map((item) => <Col xs={24} sm={12} lg={summaryCards.length === 4 ? 6 : summaryCards.length === 3 ? 8 : 12} key={item.title}>
            <Card bordered={false}><Statistic title={item.title} value={item.value} suffix={item.currency ? "₫" : undefined} formatter={(value) => Number(value).toLocaleString("vi-VN")} /></Card>
          </Col>)}
        </Row>}
        {reportType === "report_overview" && result?.summary && <Row gutter={[14, 14]} className="operation-stats">
          <Col xs={24} md={8}><Card bordered={false}><Statistic title="Hóa đơn có hiệu lực" value={Number(result.summary.hoa_don_hieu_luc || 0)} /></Card></Col>
          <Col xs={24} md={8}><Card bordered={false}><Statistic title="Doanh thu" value={Number(result.summary.doanh_thu || 0)} suffix="₫" formatter={(v) => Number(v).toLocaleString("vi-VN")} /></Card></Col>
          <Col xs={24} md={8}><Card bordered={false}><Statistic title="Tiền hoàn" value={Number(result.summary.tien_hoan || 0)} suffix="₫" formatter={(v) => Number(v).toLocaleString("vi-VN")} /></Card></Col>
          <Col xs={24} md={8}><Card bordered={false}><Statistic title="Hóa đơn đã hủy" value={Number(result.summary.hoa_don_da_huy || 0)} /></Card></Col>
          <Col xs={24} md={8}><Card bordered={false}><Statistic title="Giá trị nhập" value={Number(result.summary.gia_tri_nhap || 0)} suffix="₫" formatter={(v) => Number(v).toLocaleString("vi-VN")} /></Card></Col>
          <Col xs={24} md={8}><Card bordered={false}><Statistic title="Doanh thu sau hoàn" value={Number(result.summary.doanh_thu || 0) - Number(result.summary.tien_hoan || 0)} suffix="₫" formatter={(v) => Number(v).toLocaleString("vi-VN")} /></Card></Col>
        </Row>}
        {reportType === "report_inventory" && result?.summary && <Row gutter={[14, 14]} className="operation-stats">
          <Col xs={24} md={8}><Card bordered={false}><Statistic title="Tổng sản phẩm" value={Number(result.summary.total_products || 0)} /></Card></Col>
          <Col xs={24} md={8}><Card bordered={false}><Statistic title="Sắp hết hàng" value={Number(result.summary.low_stock || 0)} /></Card></Col>
          <Col xs={24} md={8}><Card bordered={false}><Statistic title="Hết hàng" value={Number(result.summary.out_of_stock || 0)} /></Card></Col>
          <Col xs={24} md={8}><Card bordered={false}><Statistic title="Giá trị tồn kho" value={Number(result.summary.inventory_value || 0)} suffix="₫" formatter={(v) => Number(v).toLocaleString("vi-VN")} /></Card></Col>
        </Row>}
        {reportType === "report_overview" ? <>
          <Title level={4} className="report-table-section-title">Doanh thu theo ngày</Title>
          <Text className="muted-text">Số liệu dưới đây được gom theo từng ngày trong khoảng thời gian đã chọn.</Text>
          <Table<DataRow> className="report-data-table" rowKey={(r) => String(r.ngay)} dataSource={result?.trend || []} columns={makeColumns(result?.trend || [])} pagination={{ pageSize: 8 }} scroll={{ x: "max-content" }} tableLayout="auto" />
          <Title level={4} className="report-table-section-title">Sản phẩm bán chạy</Title>
          <Table<DataRow> className="report-data-table" rowKey="masp" dataSource={result?.top_products || []} columns={makeColumns(result?.top_products || [])} pagination={false} scroll={{ x: "max-content" }} tableLayout="auto" />
        </> : <>
          <Alert className="report-table-hint" type="info" showIcon message="Các cột được hiển thị đầy đủ. Kéo thanh cuộn ngang bên dưới bảng để xem các thông tin nằm bên phải." />
          <Title level={4} className="report-table-section-title">{reportType === "report_invoice" ? "Chi tiết từng hóa đơn" : reportType === "report_import" ? "Danh sách phiếu nhập" : reportType === "report_return" ? "Danh sách phiếu đổi trả" : reportType === "report_inventory" ? "Danh sách sản phẩm trong kho" : reportType === "report_product" ? "Hiệu quả bán hàng theo sản phẩm" : reportType === "report_revenue" ? "Chi tiết doanh thu theo kỳ" : "Danh sách ca làm việc"}</Title>
          <Table<DataRow> className="report-data-table" rowKey={(r, index) => String(r.mahd || r.mapn || r.mapdt || r.masp || r.maca || r.ky || index)} dataSource={items} columns={makeColumns(items)} loading={loading} pagination={{ pageSize: 15, showSizeChanger: true, pageSizeOptions: [10, 15, 30, 50] }} locale={{ emptyText: "Không có dữ liệu trong khoảng thời gian đã chọn." }} scroll={{ x: "max-content" }} tableLayout="auto" />
          {reportType === "report_import" && Boolean(result?.suppliers?.length) && <>
            <Title level={4} className="report-table-section-title">Tổng hợp theo nhà cung cấp</Title>
            <Table<DataRow> className="report-data-table" rowKey="mancc" dataSource={result?.suppliers || []} columns={makeColumns(result?.suppliers || [])} pagination={{ pageSize: 8 }} scroll={{ x: "max-content" }} tableLayout="auto" />
          </>}
        </>}
      </>}
    </Card>
  </div>;
}

export function ShiftsOrReportsPage({ pageKey }: { pageKey: "shifts" | "report_overview" | "report_revenue" | "report_invoice" | "report_import" | "report_return" | "report_inventory" | "report_product" | "report_shifts" }) {
  return pageKey === "shifts" ? <ShiftsPage /> : <ReportsPage reportType={pageKey} />;
}
