import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ApiError, authApi, clearAccessToken, getAccessToken, saveAccessToken } from "@/services/api";
import type { EmployeeSummary } from "@/types/auth";

interface AuthContextValue {
  user: EmployeeSummary | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<EmployeeSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    clearAccessToken();
    setUser(null);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const result = await authApi.login({ username: username.trim(), password });
    saveAccessToken(result.access_token);
    setUser(result.user);
  }, []);

  useEffect(() => {
    let active = true;
    const handleUnauthorized = () => {
      if (active) setUser(null);
    };

    window.addEventListener("bookhub:unauthorized", handleUnauthorized);
    const token = getAccessToken();
    if (!token) {
      setLoading(false);
    } else {
      authApi.me()
        .then((currentUser) => {
          if (active) setUser(currentUser);
        })
        .catch((error: unknown) => {
          if (error instanceof ApiError && error.status === 401) {
            clearAccessToken();
          }
          if (active) setUser(null);
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    }

    return () => {
      active = false;
      window.removeEventListener("bookhub:unauthorized", handleUnauthorized);
    };
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, logout }),
    [user, loading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth phải được gọi bên trong AuthProvider.");
  return context;
}
