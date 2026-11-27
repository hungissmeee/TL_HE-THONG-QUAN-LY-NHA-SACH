import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

const projectRoot = fileURLToPath(new URL("../", import.meta.url));

export default defineConfig(({ mode }) => {
  // Đọc chung .env ở thư mục gốc dự án.
  const env = loadEnv(mode, projectRoot, "");
  const apiPrefix = env.BOOKHUB_WEB_API_PREFIX || "/api/v1";
  const configuredHost = env.BOOKHUB_WEB_HOST || "127.0.0.1";
  const proxyHost = configuredHost === "0.0.0.0" ? "127.0.0.1" : configuredHost;
  const backendPort = Number(env.BOOKHUB_WEB_PORT || "8000");

  return {
    root: path.resolve(projectRoot, "frontend"),
    envDir: projectRoot,
    plugins: [react()],
    resolve: {
      alias: { "@": path.resolve(projectRoot, "frontend/src") },
    },
    server: {
      host: env.BOOKHUB_WEB_FRONTEND_HOST || "127.0.0.1",
      port: Number(env.BOOKHUB_WEB_FRONTEND_PORT || "5173"),
      strictPort: true,
      proxy: {
        [apiPrefix]: {
          target: `http://${proxyHost}:${backendPort}`,
          changeOrigin: true,
        },
      },
    },
    preview: {
      host: env.BOOKHUB_WEB_FRONTEND_HOST || "127.0.0.1",
      port: Number(env.BOOKHUB_WEB_FRONTEND_PORT || "5173"),
      strictPort: true,
    },
  };
});
