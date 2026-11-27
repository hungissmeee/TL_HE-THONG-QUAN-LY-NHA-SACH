import { ConfigProvider, Spin, theme } from "antd";

import { AuthProvider, useAuth } from "@/features/auth/AuthContext";
import { AppShell } from "@/layouts/AppShell";
import { LoginPage } from "@/pages/LoginPage";

function AppContent() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="app-loading">
        <Spin size="large" />
        <span>Đang kiểm tra phiên đăng nhập...</span>
      </div>
    );
  }

  return user ? <AppShell /> : <LoginPage />;
}

export default function App() {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: "#2563EB",
          colorInfo: "#2563EB",
          colorBgBase: "#171B24",
          colorBgContainer: "#202938",
          colorBgElevated: "#263448",
          colorText: "#E5E7EB",
          colorTextSecondary: "#AAB7C8",
          colorBorder: "#39465A",
          borderRadius: 7,
          fontFamily: "Inter, 'Segoe UI', Arial, sans-serif",
        },
      }}
    >
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ConfigProvider>
  );
}
