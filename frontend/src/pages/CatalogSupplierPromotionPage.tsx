import { useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";

import { ApiError } from "@/services/api";
import {
  operationsApi,
  type CatalogData,
  type Row,
} from "@/features/operations/operationsApi";

const { Title, Text } = Typography;

function errorText(error: unknown) {
  return error instanceof ApiError ? error.message : "Không thể hoàn tất yêu cầu.";
}

function CatalogPage({ catalogType }: { catalogType: string }) {
  const [data, setData] = useState<CatalogData | null>(null);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Row | null>(null);
  const [code, setCode] = useState("");
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await operationsApi.catalog(catalogType, search));
    } catch (error) {
      message.error(errorText(error));
    } finally {
      setLoading(false);
    }
  }, [catalogType, search]);

  useEffect(() => { void load(); }, [load]);

  async function openCreate() {
    setEditing(null);
    setOpen(true);
    setSaving(false);
    form.resetFields();
    try {
      const result = await operationsApi.catalogNextCode(catalogType);
      setCode(result.code);
      form.setFieldsValue({ [data?.fields[0]?.key || ""]: result.code });
    } catch (error) {
      setOpen(false);
      message.error(errorText(error));
    }
  }

  function openEdit(record: Row) {
    setEditing(record);
    setOpen(true);
    setCode(String(record[data?.fields[0]?.key || ""] || ""));
    form.resetFields();
    form.setFieldsValue(record);
  }

  async function save(values: Record<string, unknown>) {
    if (!data) return;
    const idField = data.fields[0]?.key;
    const ordered = data.fields
      .filter((field) => editing ? field.key !== idField : true)
      .map((field) => {
        if (!editing && field.key === idField) return code;
        const value = values[field.key];
        return value === undefined || value === null ? null : String(value).trim();
      });
    setSaving(true);
    try {
      await operationsApi.saveCatalog(catalogType, ordered, editing ? String(editing[idField] || "") : undefined);
      message.success(editing ? "Đã cập nhật danh mục." : "Đã thêm danh mục.");
      setOpen(false);
      await load();
    } catch (error) {
      message.error(errorText(error));
    } finally {
      setSaving(false);
    }
  }

  async function remove(record: Row) {
    const id = data?.fields[0]?.key;
    if (!id) return;
    try {
      await operationsApi.deleteCatalog(catalogType, String(record[id]));
      message.success("Đã xóa mềm danh mục.");
      await load();
    } catch (error) {
      message.error(errorText(error));
    }
  }

  const columns = (data?.fields || []).map((field) => ({
    title: field.label,
    dataIndex: field.key,
    key: field.key,
    ellipsis: true,
  }));
  if (data) {
    columns.push({
      title: "Thao tác",
      dataIndex: "__actions",
      key: "__actions",
      ellipsis: false,
      render: (_: unknown, record: Row) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>Sửa</Button>
          <Popconfirm title="Xóa danh mục này?" okText="Xóa" cancelText="Hủy" onConfirm={() => void remove(record)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    } as typeof columns[number]);
  }

  return (
    <div className="operation-page">
      <div className="operation-heading">
        <div>
          <Text className="eyebrow">QUẢN LÝ DANH MỤC</Text>
          <Title level={2}>{data?.title || "Danh mục"}</Title>
          <Text className="muted-text">Quản lý danh mục được sử dụng trong thông tin sản phẩm.</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => void load()}>Làm mới</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => void openCreate()}>Thêm mới</Button>
        </Space>
      </div>
      <Card bordered={false} className="operation-card">
        <div className="operation-toolbar">
          <Input.Search
            allowClear
            value={keyword}
            placeholder="Tìm theo mã hoặc nội dung..."
            enterButton={<><SearchOutlined /> Tìm kiếm</>}
            onChange={(event) => setKeyword(event.target.value)}
            onSearch={(value) => setSearch(value.trim())}
            className="operation-search"
          />
        </div>
        <Table<Row>
          rowKey={(record) => String(record[data?.fields[0]?.key || ""] || "")}
          columns={columns}
          dataSource={data?.items || []}
          loading={loading}
          pagination={{ pageSize: 10, showSizeChanger: true }}
          locale={{ emptyText: "Không có dữ liệu danh mục." }}
        />
      </Card>
      <Modal
        title={editing ? "Chỉnh sửa danh mục" : data?.title || "Thêm danh mục"}
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => form.submit()}
        okText={editing ? "Lưu thay đổi" : "Thêm mới"}
        cancelText="Hủy"
        confirmLoading={saving}
        destroyOnClose
      >
        {!data ? <Spin /> : (
          <Form form={form} className="desktop-dialog-form" layout="horizontal" labelCol={{ xs: { span: 24 }, sm: { span: 8 } }} wrapperCol={{ xs: { span: 24 }, sm: { span: 16 } }} onFinish={(values) => void save(values)}>
            <Card size="small" title="Thông tin danh mục" className="desktop-form-section">
              {data.fields.map((field, index) => (
                <Form.Item
                  key={field.key}
                  name={field.key}
                  label={field.label}
                  rules={field.required && index > 0 ? [{ required: true, whitespace: true, message: "Vui lòng nhập " + field.label.toLowerCase() }] : []}
                >
                  <Input
                    maxLength={field.key === data.fields[0].key ? 20 : field.key === "DIACHI" ? 255 : 100}
                    readOnly={index === 0}
                    placeholder={index === 0 ? "Mã tự động: " + code : "Nhập " + field.label.toLowerCase()}
                  />
                </Form.Item>
              ))}
            </Card>
          </Form>
        )}
      </Modal>
    </div>
  );
}

function SuppliersPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [nextCode, setNextCode] = useState("");
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await operationsApi.suppliers(keyword, showInactive));
    } catch (error) {
      message.error(errorText(error));
    } finally {
      setLoading(false);
    }
  }, [keyword, showInactive]);

  useEffect(() => { void load(); }, [load]);

  async function openAdd() {
    setEditing(null);
    form.resetFields();
    setOpen(true);
    try {
      const result = await operationsApi.supplierNextCode();
      setNextCode(result.code);
    } catch (error) {
      setOpen(false);
      message.error(errorText(error));
    }
  }

  async function openEdit(code: string) {
    setEditing(code);
    setOpen(true);
    form.resetFields();
    try {
      const row = await operationsApi.supplier(code);
      form.setFieldsValue({
        name: row.tenncc,
        phone: row.sdt,
        address: row.diachi,
        tax: row.mst,
      });
    } catch (error) {
      setOpen(false);
      message.error(errorText(error));
    }
  }

  async function save(values: Record<string, unknown>) {
    setSaving(true);
    try {
      await operationsApi.saveSupplier(values, editing || undefined);
      message.success(editing ? "Đã cập nhật nhà cung cấp." : "Đã thêm nhà cung cấp.");
      setOpen(false);
      await load();
    } catch (error) {
      message.error(errorText(error));
    } finally {
      setSaving(false);
    }
  }

  async function toggleStatus(record: Row) {
    try {
      await operationsApi.supplierStatus(String(record.mancc), !Boolean(record.is_deleted));
      message.success(Boolean(record.is_deleted) ? "Đã kích hoạt nhà cung cấp." : "Đã ngừng hoạt động nhà cung cấp.");
      await load();
    } catch (error) {
      message.error(errorText(error));
    }
  }

  const columns = [
    { title: "Mã NCC", dataIndex: "mancc", key: "mancc", width: 120 },
    { title: "Tên nhà cung cấp", dataIndex: "tenncc", key: "tenncc", ellipsis: true },
    { title: "Số điện thoại", dataIndex: "sdt", key: "sdt", width: 140 },
    { title: "Mã số thuế", dataIndex: "mst", key: "mst", width: 150 },
    { title: "Địa chỉ", dataIndex: "diachi", key: "diachi", ellipsis: true },
    {
      title: "Trạng thái", dataIndex: "is_deleted", key: "status", width: 140,
      render: (value: boolean) => <Tag color={value ? "default" : "success"}>{value ? "Ngừng hoạt động" : "Đang hoạt động"}</Tag>,
    },
    {
      title: "Thao tác", key: "actions", width: 210,
      render: (_: unknown, record: Row) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => void openEdit(String(record.mancc))}>Sửa</Button>
          <Button size="small" onClick={() => void toggleStatus(record)}>
            {record.is_deleted ? "Kích hoạt" : "Ngừng"}
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="operation-page">
      <div className="operation-heading">
        <div>
          <Text className="eyebrow">QUẢN LÝ KHO</Text>
          <Title level={2}>Nhà cung cấp</Title>
          <Text className="muted-text">Quản lý thông tin và trạng thái nhà cung cấp.</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => void load()}>Làm mới</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => void openAdd()}>Thêm nhà cung cấp</Button>
        </Space>
      </div>
      <Card bordered={false} className="operation-card">
        <div className="operation-toolbar">
          <Input.Search
            allowClear
            placeholder="Tìm mã, tên, số điện thoại, MST..."
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            onSearch={(value) => setKeyword(value.trim())}
            enterButton="Tìm kiếm"
            className="operation-search"
          />
          <Select
            value={showInactive ? "all" : "active"}
            style={{ width: 190 }}
            options={[{ value: "active", label: "Đang hoạt động" }, { value: "all", label: "Bao gồm đã ngừng" }]}
            onChange={(value) => setShowInactive(value === "all")}
          />
        </div>
        <Table<Row> rowKey="mancc" columns={columns} dataSource={rows} loading={loading} pagination={{ pageSize: 10, showSizeChanger: true }} />
      </Card>
      <Modal
        title={editing ? "Chỉnh sửa nhà cung cấp " + editing : "Thêm nhà cung cấp"}
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => form.submit()}
        okText={editing ? "Lưu thay đổi" : "Thêm nhà cung cấp"}
        cancelText="Hủy"
        confirmLoading={saving}
        destroyOnClose
        width={560}
        className="desktop-entity-modal"
      >
        <Form form={form} className="desktop-dialog-form" layout="horizontal" labelCol={{ xs: { span: 24 }, sm: { span: 8 } }} wrapperCol={{ xs: { span: 24 }, sm: { span: 16 } }} onFinish={(values) => void save(values)}>
          <Card size="small" title="Thông tin chung" className="desktop-form-section">
            {!editing && <Form.Item label="Mã nhà cung cấp"><Input value={nextCode} readOnly /></Form.Item>}
            <Form.Item name="name" label="Tên nhà cung cấp" rules={[{ required: true, whitespace: true, max: 100 }]}><Input maxLength={100} placeholder="Nhập tên nhà cung cấp" /></Form.Item>
            <Form.Item name="phone" label="Số điện thoại"><Input maxLength={15} placeholder="Số điện thoại" /></Form.Item>
            <Form.Item name="address" label="Địa chỉ"><Input maxLength={255} placeholder="Địa chỉ nhà cung cấp" /></Form.Item>
            <Form.Item name="tax" label="Mã số thuế"><Input maxLength={20} placeholder="Mã số thuế (nếu có)" /></Form.Item>
          </Card>
        </Form>
      </Modal>
    </div>
  );
}

function PromotionsPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [showDeleted, setShowDeleted] = useState(false);
  const [open, setOpen] = useState(false);
  const [nextCode, setNextCode] = useState("");
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const [renameRecord, setRenameRecord] = useState<Row | null>(null);
  const [renameForm] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try { setRows(await operationsApi.promotions(keyword, showDeleted)); }
    catch (error) { message.error(errorText(error)); }
    finally { setLoading(false); }
  }, [keyword, showDeleted]);
  useEffect(() => { void load(); }, [load]);

  async function openCreate() {
    form.resetFields();
    setOpen(true);
    try {
      const result = await operationsApi.promotionNextCode();
      setNextCode(result.code);
    } catch (error) {
      setOpen(false);
      message.error(errorText(error));
    }
  }

  async function create(values: { name: string; discount_rate: number; period: [dayjs.Dayjs, dayjs.Dayjs] }) {
    setSaving(true);
    try {
      await operationsApi.createPromotion({
        name: values.name,
        discount_rate: values.discount_rate,
        start_at: values.period[0].format("YYYY-MM-DDTHH:mm:ss"),
        end_at: values.period[1].format("YYYY-MM-DDTHH:mm:ss"),
      });
      message.success("Đã tạo chương trình khuyến mãi.");
      setOpen(false);
      await load();
    } catch (error) { message.error(errorText(error)); }
    finally { setSaving(false); }
  }

  async function rename(values: { name: string }) {
    if (!renameRecord) return;
    try {
      await operationsApi.renamePromotion(String(renameRecord.makm), values.name);
      message.success("Đã đổi tên khuyến mãi.");
      setRenameRecord(null);
      await load();
    } catch (error) { message.error(errorText(error)); }
  }

  async function remove(code: string) {
    try {
      await operationsApi.deletePromotion(code);
      message.success("Đã ngừng áp dụng khuyến mãi.");
      await load();
    } catch (error) { message.error(errorText(error)); }
  }

  const columns = [
    { title: "Mã KM", dataIndex: "makm", key: "makm", width: 130 },
    { title: "Tên chương trình", dataIndex: "tenkm", key: "tenkm", ellipsis: true },
    { title: "Tỷ lệ giảm", dataIndex: "tylegiam", key: "tylegiam", width: 120, render: (v: unknown) => Number(v || 0) + "%" },
    { title: "Bắt đầu", dataIndex: "ngaybd", key: "ngaybd", width: 170, render: (v: string) => v ? dayjs(v).format("DD/MM/YYYY HH:mm") : "—" },
    { title: "Kết thúc", dataIndex: "ngaykt", key: "ngaykt", width: 170, render: (v: string) => v ? dayjs(v).format("DD/MM/YYYY HH:mm") : "—" },
    {
      title: "Trạng thái", dataIndex: "status", key: "status", width: 145,
      render: (v: string, row: Row) => <Tag color={row.is_deleted ? "default" : v === "Đang áp dụng" ? "success" : "blue"}>{v}</Tag>,
    },
    {
      title: "Thao tác", key: "action", width: 160,
      render: (_: unknown, row: Row) => (
        <Space>
          {!row.is_deleted && <Button size="small" icon={<EditOutlined />} onClick={() => {
            renameForm.setFieldsValue({ name: row.tenkm });
            setRenameRecord(row);
          }}>Đổi tên</Button>}
          {!row.is_deleted && <Popconfirm title="Ngừng chương trình khuyến mãi?" okText="Ngừng" cancelText="Hủy" onConfirm={() => void remove(String(row.makm))}>
            <Button danger size="small" icon={<DeleteOutlined />} />
          </Popconfirm>}
        </Space>
      ),
    },
  ];

  return (
    <div className="operation-page">
      <div className="operation-heading">
        <div><Text className="eyebrow">BÁN HÀNG</Text><Title level={2}>Chương trình khuyến mãi</Title><Text className="muted-text">Quản lý thời gian và tỷ lệ giảm giá áp dụng trên hóa đơn.</Text></div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => void load()}>Làm mới</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => void openCreate()}>Thêm khuyến mãi</Button>
        </Space>
      </div>
      <Card bordered={false} className="operation-card">
        <div className="operation-toolbar">
          <Input.Search className="operation-search" allowClear value={keyword} placeholder="Tìm mã hoặc tên chương trình..." onChange={(e) => setKeyword(e.target.value)} onSearch={(v) => setKeyword(v.trim())} enterButton="Tìm kiếm" />
          <Select value={showDeleted ? "all" : "active"} style={{ width: 190 }} options={[{ value: "active", label: "Đang sử dụng" }, { value: "all", label: "Bao gồm đã ngừng" }]} onChange={(v) => setShowDeleted(v === "all")} />
        </div>
        <Table<Row> rowKey="makm" columns={columns} dataSource={rows} loading={loading} pagination={{ pageSize: 10, showSizeChanger: true }} />
      </Card>
      <Modal title="Tạo chương trình khuyến mãi" open={open} onCancel={() => setOpen(false)} onOk={() => form.submit()} okText="Tạo chương trình" cancelText="Hủy" confirmLoading={saving} width={560} destroyOnClose className="desktop-entity-modal">
        <Form form={form} className="desktop-dialog-form" layout="horizontal" labelCol={{ xs: { span: 24 }, sm: { span: 8 } }} wrapperCol={{ xs: { span: 24 }, sm: { span: 16 } }} onFinish={(v) => void create(v)}>
          <Card size="small" title="Thông tin chương trình" className="desktop-form-section">
            <Form.Item name="name" label="Tên khuyến mãi" rules={[{ required: true, max: 100 }]}><Input maxLength={100} placeholder="Nhập tên chương trình" /></Form.Item>
            <Form.Item name="discount_rate" label="Tỷ lệ giảm (%)" rules={[{ required: true }]}><InputNumber min={0} max={100} precision={2} style={{ width: "100%" }} /></Form.Item>
            <Form.Item name="period" label="Thời gian áp dụng" rules={[{ required: true, message: "Chọn thời gian bắt đầu và kết thúc." }]}>
              <DatePicker.RangePicker showTime format="DD/MM/YYYY HH:mm" style={{ width: "100%" }} />
            </Form.Item>
            <Alert type="info" showIcon message="Sau khi tạo, tỷ lệ giảm và thời hạn được giữ cố định để không làm thay đổi cách tính của hóa đơn cũ. Muốn ngừng áp dụng, hãy ngừng chương trình tại danh sách." />
          </Card>
        </Form>
      </Modal>
      <Modal title="Đổi tên chương trình" open={Boolean(renameRecord)} onCancel={() => setRenameRecord(null)} onOk={() => renameForm.submit()} okText="Lưu" cancelText="Hủy" width={540} className="desktop-entity-modal">
        <Form form={renameForm} className="desktop-dialog-form" layout="horizontal" labelCol={{ span: 8 }} wrapperCol={{ span: 16 }} onFinish={(v) => void rename(v)}>
          <Card size="small" title="Thông tin chương trình" className="desktop-form-section">
            <Form.Item name="name" label="Tên chương trình" rules={[{ required: true, max: 100 }]}><Input maxLength={100} /></Form.Item>
          </Card>
        </Form>
      </Modal>
    </div>
  );
}

export function CatalogSupplierPromotionPage({ pageKey }: { pageKey: "authors" | "genres" | "publishers" | "brands" | "suppliers" | "promotions" }) {
  if (pageKey === "suppliers") return <SuppliersPage />;
  if (pageKey === "promotions") return <PromotionsPage />;
  return <CatalogPage catalogType={pageKey} />;
}
