import { useEffect, useState } from "react";
import { ConfigProvider, Spin, theme } from "antd";

import { AuthProvider, useAuth } from "@/features/auth/AuthContext";
import { AppShell } from "@/layouts/AppShell";
import { LoginPage } from "@/pages/LoginPage";

type ThemeMode = "light" | "dark";

function AppContent({ themeMode, onToggleTheme }: { themeMode: ThemeMode; onToggleTheme: () => void }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="app-loading">
        <Spin size="large" />
        <span>Đang kiểm tra phiên đăng nhập...</span>
      </div>
    );
  }

  return user
    ? <AppShell themeMode={themeMode} onToggleTheme={onToggleTheme} />
    : <LoginPage themeMode={themeMode} onToggleTheme={onToggleTheme} />;
}

export default function App() {
  const [themeMode, setThemeMode] = useState<ThemeMode>(() => {
    try {
      return localStorage.getItem("bookhub-theme") === "light" ? "light" : "dark";
    } catch {
      return "dark";
    }
  });

  useEffect(() => {
    document.documentElement.dataset.theme = themeMode;
    document.documentElement.style.colorScheme = themeMode;
    try {
      localStorage.setItem("bookhub-theme", themeMode);
    } catch {
      // Theme still works for the current session when storage is unavailable.
    }
  }, [themeMode]);

  const onToggleTheme = () => setThemeMode((current) => current === "dark" ? "light" : "dark");
  const isDark = themeMode === "dark";

  return (
    <ConfigProvider
      theme={{
        algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: {
          colorPrimary: isDark ? "#3B82F6" : "#1D4ED8",
          colorInfo: isDark ? "#3B82F6" : "#1D4ED8",
          colorBgBase: isDark ? "#171B24" : "#F4F7FB",
          colorBgContainer: isDark ? "#202938" : "#FFFFFF",
          colorBgElevated: isDark ? "#263448" : "#FFFFFF",
          colorText: isDark ? "#E5E7EB" : "#243247",
          colorTextSecondary: isDark ? "#AAB7C8" : "#5B687A",
          colorBorder: isDark ? "#39465A" : "#D8E0EB",
          colorBorderSecondary: isDark ? "#344256" : "#E5EAF1",
          colorFillAlter: isDark ? "#29374B" : "#F0F4F9",
          borderRadius: 7,
          fontFamily: "Inter, 'Segoe UI', Arial, sans-serif",
        },
      }}
    >
      <AuthProvider>
        <AppContent themeMode={themeMode} onToggleTheme={onToggleTheme} />
      </AuthProvider>
    </ConfigProvider>
  );
}
