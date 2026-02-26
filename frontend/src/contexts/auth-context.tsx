"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { authApi } from "@/lib/api/auth";
import { getToken, setToken, clearToken } from "@/lib/api/client";
import type { User } from "@/types";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  /** Store token + user after login/register — updates state immediately (no /me call). */
  login: (token: string, user: User) => void;
  /** Call POST /auth/logout, clear token, reset state. */
  logout: () => Promise<void>;
  /** Re-fetch current user from /me (e.g. after profile update). */
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const res = await authApi.me();
      if (res.success) {
        setUser(res.data);
      } else {
        clearToken();
        setUser(null);
      }
    } catch {
      clearToken();
      setUser(null);
    }
    setIsLoading(false);
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  // Listen for 401 responses from the API client and clear auth state
  useEffect(() => {
    const handleAuthExpired = () => setUser(null);
    window.addEventListener("whydud:auth-expired", handleAuthExpired);
    return () => window.removeEventListener("whydud:auth-expired", handleAuthExpired);
  }, []);

  const login = useCallback((token: string, userData: User) => {
    setToken(token);
    setUser(userData);
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Server may be unreachable — still clear local state
    }
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    await fetchUser();
  }, [fetchUser]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within <AuthProvider>");
  }
  return ctx;
}
