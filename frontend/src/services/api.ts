import type { EmployeeSummary, LoginCredentials, LoginResponse } from "@/types/auth";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/+$/, "");
const ACCESS_TOKEN_KEY = "bookhub.web.access_token";
let memoryAccessToken: string | null = null;

export class ApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export function getAccessToken(): string | null {
  try {
    const storedToken = window.sessionStorage.getItem(ACCESS_TOKEN_KEY);
    if (storedToken) {
      memoryAccessToken = storedToken;
      return storedToken;
    }
  } catch {
    // Dùng token trong bộ nhớ nếu trình duyệt chặn sessionStorage.
  }
  return memoryAccessToken;
}

export function saveAccessToken(token: string): void {
  memoryAccessToken = token;
  try {
    window.sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
  } catch {
    // Phiên hiện tại vẫn hoạt động bằng token trong bộ nhớ của tab.
  }
}

export function clearAccessToken(): void {
  memoryAccessToken = null;
  try {
    window.sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  } catch {
    // Kết thúc phiên trong bộ nhớ ngay cả khi trình duyệt chặn sessionStorage.
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  authenticated = false,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (authenticated) {
    const token = getAccessToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
      credentials: "same-origin",
    });
  } catch {
    throw new ApiError(0, "Không thể kết nối Backend. Hãy kiểm tra máy chủ đang chạy.");
  }

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    if (authenticated && response.status === 401) {
      clearAccessToken();
      window.dispatchEvent(new Event("bookhub:unauthorized"));
    }

    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? (payload as { detail?: unknown }).detail
        : null;
    const message =
      typeof detail === "string"
        ? detail
        : response.status === 401
          ? "Phiên đăng nhập không hợp lệ hoặc đã hết hạn."
          : "Yêu cầu không thể hoàn tất. Vui lòng thử lại.";
    throw new ApiError(response.status, message);
  }

  return payload as T;
}

export const authApi = {
  login(credentials: LoginCredentials): Promise<LoginResponse> {
    return apiRequest<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(credentials),
    });
  },

  me(): Promise<EmployeeSummary> {
    return apiRequest<EmployeeSummary>("/auth/me", { method: "GET" }, true);
  },
};
