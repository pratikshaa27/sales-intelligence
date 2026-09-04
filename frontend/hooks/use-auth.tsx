"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { api, refreshAccessToken } from "@/lib/api";
import { setAccessToken, setCsrfToken } from "@/lib/token-store";
import type { AccessTokenResponse, ApiSuccess, MeResponse } from "@/types/auth";

interface AuthContextValue {
  me: MeResponse | undefined;
  isLoading: boolean;
  isBootstrapping: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (values: {
    organization_name: string;
    admin_full_name: string;
    admin_email: string;
    admin_password: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const ME_QUERY_KEY = ["auth", "me"];

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const meQuery = useQuery({
    queryKey: ME_QUERY_KEY,
    queryFn: async () => {
      const res = await api.get<ApiSuccess<MeResponse>>("/auth/me");
      return res.data.data;
    },
    enabled: isAuthenticated,
    retry: false,
    staleTime: 60_000,
  });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      // Routed through the shared single-flight refreshAccessToken() rather than a direct
      // api.post("/auth/refresh") here — React 18 StrictMode deliberately runs this effect
      // twice in development, and two independent direct calls would race against the
      // backend's refresh-token rotation (see the comment on refreshAccessToken itself).
      const token = await refreshAccessToken();
      if (!cancelled) {
        setIsAuthenticated(Boolean(token));
        setIsBootstrapping(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await api.post<ApiSuccess<AccessTokenResponse>>("/auth/login", {
        email,
        password,
      });
      setAccessToken(res.data.data.access_token);
      setCsrfToken(res.data.data.csrf_token);
      setIsAuthenticated(true);
      await queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY });
    },
    [queryClient],
  );

  const register = useCallback(
    async (values: {
      organization_name: string;
      admin_full_name: string;
      admin_email: string;
      admin_password: string;
    }) => {
      const res = await api.post<ApiSuccess<AccessTokenResponse>>("/auth/register", values);
      setAccessToken(res.data.data.access_token);
      setCsrfToken(res.data.data.csrf_token);
      setIsAuthenticated(true);
      await queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY });
    },
    [queryClient],
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } finally {
      setAccessToken(null);
      setCsrfToken(null);
      setIsAuthenticated(false);
      queryClient.removeQueries({ queryKey: ME_QUERY_KEY });
    }
  }, [queryClient]);

  return (
    <AuthContext.Provider
      value={{
        me: meQuery.data,
        isLoading: meQuery.isLoading,
        isBootstrapping,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
