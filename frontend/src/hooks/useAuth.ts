"use client";

import { useEffect, useState } from "react";
import { authApi } from "@/lib/api/auth";
import { getToken, clearToken } from "@/lib/api/client";
import type { User } from "@/types";

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

export function useAuth(): AuthState {
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  });

  useEffect(() => {
    // Skip the /me call entirely if there's no stored token
    if (!getToken()) {
      setState({ user: null, isLoading: false, isAuthenticated: false });
      return;
    }

    authApi
      .me()
      .then((res) => {
        if (res.success) {
          setState({ user: res.data, isLoading: false, isAuthenticated: true });
        } else {
          // Token is stale or invalid — clean up
          clearToken();
          setState({ user: null, isLoading: false, isAuthenticated: false });
        }
      })
      .catch(() => {
        clearToken();
        setState({ user: null, isLoading: false, isAuthenticated: false });
      });
  }, []);

  return state;
}
