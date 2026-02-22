"use client";

import { useEffect, useState } from "react";
import { authApi } from "@/lib/api/auth";
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
    authApi.me().then((res) => {
      if (res.success) {
        setState({ user: res.data, isLoading: false, isAuthenticated: true });
      } else {
        setState({ user: null, isLoading: false, isAuthenticated: false });
      }
    });
  }, []);

  return state;
}
