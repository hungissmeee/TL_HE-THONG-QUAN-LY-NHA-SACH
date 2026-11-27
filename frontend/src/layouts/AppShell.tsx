import { useMemo, useState, type ReactNode } from "react";
import {
  Avatar,
  Button,
  Card,
  Form,
  Input,
  Layout,
  Menu,
  message,
  Modal,
  Space,
  Tag,
  Typography,
  type MenuProps,
} from "antd";
import {
  AppstoreOutlined,
  BarChartOutlined,
  BookOutlined,
  ClockCircleOutlined,
  FileAddOutlined,
  FileDoneOutlined,
  GiftOutlined,
  HomeOutlined,
  LockOutlined,
  LogoutOutlined,
  ShopOutlined,
  TagsOutlined,
  TeamOutlined,
  UserOutlined,
} from "@ant-design/icons";

import { useAuth } from "@/features/auth/AuthContext";
import { ApiError, authApi } from "@/services/api";
import { ProductsPage } from "@/pages/ProductsPage";
import { CatalogSupplierPromotionPage } from "@/pages/CatalogSupplierPromotionPage";
import { SalesStockPage } from "@/pages/SalesStockPage";
import { PeopleAndReturnsPage } from "@/pages/PeopleAndReturnsPage";
import { ShiftsOrReportsPage } from "@/pages/ShiftsOrReportsPage";

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;

type PageKey =
  | "home" | "invoices" | "returns" | "promotions"
  | "products" | "suppliers" | "imports"
  | "authors" | "genres" | "publishers" | "brands"
  | "employees" | "shifts"
  | "report_overview" | "report_revenue" | "report_invoice"
  | "report_import" | "report_return" | "report_inventory"
  | "report_product" | "report_shifts";

interface ChangePasswordFormValues {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

interface NavigationItem {
  key: PageKey;
  label: string;
  icon: ReactNode;
}

interface NavigationGroup {
  key: string;
  label: string;
  items: NavigationItem[];
}

const ROLE_PAGES: Record<string, PageKey[]> = {
  admin: [
    "home", "invoices", "returns", "promotions", "products", "suppliers",
    "imports", "authors", "genres", "publishers", "brands", "employees",
    "shifts", "report_overview", "report_revenue", "report_invoice",
    "report_import", "report_return", "report_inventory", "report_product", "report_shifts",
  ],
  rl_QuanLy: [
    "home", "products", "suppliers", "imports", "invoices", "returns",
    "promotions", "authors", "genres", "publishers", "brands", "shifts",
    "report_overview", "report_revenue", "report_invoice", "report_import",
    "report_return", "report_inventory", "report_product", "report_shifts",
  ],
  rl_ThuNgan: ["home", "products", "invoices", "shifts"],
  rl_NhanVienKho: [
    "home", "products", "suppliers", "imports", "authors", "genres",
    "publishers", "brands", "shifts",
  ],
  rl_KeToan: [
    "home", "products", "suppliers", "imports", "invoices", "shifts",
    "report_overview", "report_revenue", "report_invoice", "report_import",
    "report_return", "report_inventory", "report_product", "report_shifts",
  ],
};

const NAVIGATION: NavigationGroup[] = [
  { key: "overview", label: "TỔNG QUAN", items: [
    { key: "home", label: "Trang chủ", icon: <HomeOutlined /> },
  ] },
  { key: "sales", label: "BÁN HÀNG", items: [
    { key: "invoices", label: "Hóa đơn", icon: <FileDoneOutlined /> },
    { key: "returns", label: "Đổi trả", icon: <FileAddOutlined /> },
    { key: "promotions", label: "Khuyến mãi", icon: <GiftOutlined /> },
  ] },
  { key: "inventory", label: "QUẢN LÝ KHO", items: [
    { key: "products", label: "Sản phẩm", icon: <BookOutlined /> },
    { key: "suppliers", label: "Nhà cung cấp", icon: <ShopOutlined /> },
    { key: "imports", label: "Phiếu nhập", icon: <FileAddOutlined /> },
  ] },
  { key: "catalogs", label: "QUẢN LÝ DANH MỤC", items: [
    { key: "authors", label: "Tác giả", icon: <UserOutlined /> },
    { key: "genres", label: "Thể loại", icon: <TagsOutlined /> },
    { key: "publishers", label: "Nhà xuất bản", icon: <BookOutlined /> },
    { key: "brands", label: "Thương hiệu", icon: <AppstoreOutlined /> },
  ] },
  { key: "people", label: "QUẢN LÝ NHÂN SỰ", items: [
    { key: "employees", label: "Nhân viên", icon: <TeamOutlined /> },
    { key: "shifts", label: "Ca làm việc", icon: <ClockCircleOutlined /> },
  ] },
  { key: "reports", label: "BÁO CÁO", items: [
    { key: "report_overview", label: "Tổng quan", icon: <BarChartOutlined /> },
    { key: "report_revenue", label: "Doanh thu", icon: <BarChartOutlined /> },
    { key: "report_invoice", label: "Hóa đơn", icon: <FileDoneOutlined /> },
    { key: "report_import", label: "Nhập hàng", icon: <FileAddOutlined /> },
    { key: "report_return", label: "Đổi trả", icon: <FileAddOutlined /> },
    { key: "report_inventory", label: "Tồn kho", icon: <ShopOutlined /> },
    { key: "report_product", label: "Sản phẩm", icon: <BookOutlined /> },
    { key: "report_shifts", label: "Ca làm việc", icon: <ClockCircleOutlined /> },
  ] },
];

const PAGE_TITLES = Object.fromEntries(
  NAVIGATION.flatMap((group) => group.items.map((item) => [item.key, item.label])),
) as Record<PageKey, string>;

function Dashboard({ name, role }: { name: string; role: string }) {
  return (
    <div className="dashboard-content">
      <div className="dashboard-heading">
        <div>
          <Text className="eyebrow">TỔNG QUAN HỆ THỐNG</Text>
          <Title level={2}>Xin chào, {name || "bạn"}!</Title>
          <Text className="muted-text">Bạn đã đăng nhập vào Hệ thống quản lý nhà sách.</Text>
        </div>
        <Tag color="blue">{role}</Tag>
      </div>
      <div className="dashboard-grid">
        <Card className="status-card" bordered={false}>
          <div className="status-icon"><UserOutlined /></div>
          <Text className="muted-text">Tài khoản</Text>
          <Title level={4}>Đã xác thực</Title>
          <Text className="muted-text">Danh tính được xác minh bởi SQL Server.</Text>
        </Card>
        <Card className="status-card" bordered={false}>
          <div className="status-icon"><AppstoreOutlined /></div>
          <Text className="muted-text">Giao diện Web</Text>
          <Title level={4}>Đã khởi tạo</Title>
          <Text className="muted-text">Các phân hệ sẽ được chuyển đổi lần lượt.</Text>
        </Card>
        <Card className="status-card" bordered={false}>
          <div className="status-icon"><BarChartOutlined /></div>
          <Text className="muted-text">Dữ liệu</Text>
          <Title level={4}>Đã kết nối dữ liệu</Title>
          <Text className="muted-text">Các phân hệ nghiệp vụ đã được kết nối API SQL Server.</Text>
        </Card>
      </div>
      <Card className="welcome-card" bordered={false}>
        <Title level={4}>Hệ thống quản lý nhà sách</Title>
        <Text className="muted-text">
          Khung điều hướng và phân quyền hiển thị đã sẵn sàng. Các trang nghiệp vụ
          sẽ được kết nối dữ liệu thật theo từng giai đoạn.
        </Text>
      </Card>
    </div>
  );
}

export function AppShell() {
  const { user, logout } = useAuth();
  const [pageKey, setPageKey] = useState<PageKey>("home");
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordForm] = Form.useForm<ChangePasswordFormValues>();
  const permittedPages = ROLE_PAGES[user?.role_code || ""] || [];

  const menuItems = useMemo<MenuProps["items"]>(() => {
    return NAVIGATION.map((group) => {
      const visible = group.items.filter((item) => permittedPages.includes(item.key));
      if (visible.length === 0) return null;
      return {
        key: group.key,
        type: "group" as const,
        label: group.label,
        children: visible.map((item) => ({
          key: item.key,
          label: item.label,
          icon: item.icon,
        })),
      };
    }).filter((item) => item !== null);
  }, [permittedPages]);

  const pageTitle = PAGE_TITLES[pageKey] || "Trang chủ";

  async function submitPasswordChange(values: ChangePasswordFormValues) {
    setPasswordSaving(true);
    try {
      const result = await authApi.changePassword({
        current_password: values.current_password,
        new_password: values.new_password,
      });
      message.success(result.message);
      setPasswordOpen(false);
      passwordForm.resetFields();
    } catch (error) {
      message.error(
        error instanceof ApiError
          ? error.message
          : "Không thể đổi mật khẩu. Vui lòng thử lại.",
      );
    } finally {
      setPasswordSaving(false);
    }
  }

  function closePasswordDialog() {
    setPasswordOpen(false);
    passwordForm.resetFields();
  }

  return (
    <>
    <Layout className="app-layout">
      <Sider className="app-sider" width={235} breakpoint="lg" collapsedWidth={72} theme="dark">
        <div className="sidebar-brand">
          <div className="sidebar-brand-mark"><BookOutlined /></div>
          <div className="sidebar-brand-text">HỆ THỐNG QUẢN LÝ<small>NHÀ SÁCH</small></div>
        </div>

        <Menu
          className="app-menu"
          mode="inline"
          theme="dark"
          selectedKeys={[pageKey]}
          items={menuItems}
          onClick={({ key }) => setPageKey(key as PageKey)}
        />

        <div className="sidebar-account">
          <Button className="sidebar-password" type="text" icon={<LockOutlined />} block onClick={() => setPasswordOpen(true)}>
            Đổi mật khẩu
          </Button>
          <div className="sidebar-user">
            <Avatar icon={<UserOutlined />} />
            <div className="sidebar-user-meta">
              <Text className="sidebar-user-name">{user?.full_name || user?.employee_code}</Text>
              <Text className="sidebar-user-role">{user?.employee_code} · {user?.role}</Text>
            </div>
          </div>
          <Button className="sidebar-logout" type="text" icon={<LogoutOutlined />} block onClick={logout}>
            Đăng xuất
          </Button>
        </div>
      </Sider>

      <Layout className="app-main">
        <Header className="app-header">
          <div className="header-title">{pageTitle}</div>
          <Space className="header-actions" size={12}>
            <Tag color="blue">{user?.role}</Tag>
            <Avatar size="small" icon={<UserOutlined />} />
            <Text className="header-user">{user?.full_name || user?.employee_code}</Text>
          </Space>
        </Header>
        <Content className="app-content">
          {pageKey === "home" ? (
            <Dashboard name={user?.full_name || ""} role={user?.role || ""} />
          ) : pageKey === "products" ? (
            <ProductsPage />
          ) : pageKey === "invoices" || pageKey === "imports" ? (
            <SalesStockPage pageKey={pageKey} />
          ) : pageKey === "returns" || pageKey === "employees" ? (
            <PeopleAndReturnsPage pageKey={pageKey} />
          ) : pageKey === "suppliers" || pageKey === "promotions" ||
              pageKey === "authors" || pageKey === "genres" ||
              pageKey === "publishers" || pageKey === "brands" ? (
            <CatalogSupplierPromotionPage pageKey={pageKey} />
          ) : pageKey === "shifts" || pageKey.startsWith("report_") ? (
            <ShiftsOrReportsPage pageKey={pageKey as
              | "shifts" | "report_overview" | "report_revenue" | "report_invoice"
              | "report_import" | "report_return" | "report_inventory"
              | "report_product" | "report_shifts"} />
          ) : (
            <Card className="coming-soon-card" bordered={false}>
              <div className="coming-soon-icon"><AppstoreOutlined /></div>
              <Title level={3}>{pageTitle}</Title>
              <Text className="muted-text">Không tìm thấy trang nghiệp vụ tương ứng.</Text>
            </Card>
          )}
        </Content>
      </Layout>
    </Layout>

    <Modal
      title="Đổi mật khẩu"
      open={passwordOpen}
      onCancel={closePasswordDialog}
      onOk={() => passwordForm.submit()}
      okText="Đổi mật khẩu"
      cancelText="Hủy"
      confirmLoading={passwordSaving}
      destroyOnClose
      width={460}
      className="password-change-modal"
    >
      <Form
        form={passwordForm}
        layout="vertical"
        requiredMark={false}
        onFinish={(values) => void submitPasswordChange(values)}
      >
        <Form.Item
          name="current_password"
          label="Mật khẩu hiện tại"
          rules={[{ required: true, message: "Vui lòng nhập mật khẩu hiện tại." }]}
        >
          <Input.Password autoComplete="current-password" maxLength={128} />
        </Form.Item>
        <Form.Item
          name="new_password"
          label="Mật khẩu mới"
          extra="Tối thiểu 8 ký tự; tối đa 128 ký tự."
          rules={[
            { required: true, message: "Vui lòng nhập mật khẩu mới." },
            { min: 8, message: "Mật khẩu mới phải có ít nhất 8 ký tự." },
            { max: 128, message: "Mật khẩu mới không được vượt quá 128 ký tự." },
            {
              validator: (_, value) =>
                !value || value !== passwordForm.getFieldValue("current_password")
                  ? Promise.resolve()
                  : Promise.reject(new Error("Mật khẩu mới phải khác mật khẩu hiện tại.")),
            },
          ]}
        >
          <Input.Password autoComplete="new-password" maxLength={128} />
        </Form.Item>
        <Form.Item
          name="confirm_password"
          label="Xác nhận mật khẩu mới"
          dependencies={["new_password"]}
          rules={[
            { required: true, message: "Vui lòng xác nhận mật khẩu mới." },
            {
              validator: (_, value) =>
                !value || value === passwordForm.getFieldValue("new_password")
                  ? Promise.resolve()
                  : Promise.reject(new Error("Mật khẩu xác nhận không khớp.")),
            },
          ]}
        >
          <Input.Password autoComplete="new-password" maxLength={128} />
        </Form.Item>
      </Form>
    </Modal>
    </>
  );
}
