import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

import type { AccessTokenResponse, ApiError, ApiSuccess } from "@/types/auth";
import { getAccessToken, getCsrfToken, setAccessToken, setCsrfToken } from "@/lib/token-store";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // send the httpOnly refresh-token cookie
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // /auth/refresh and /auth/logout are cookie-authenticated (not Bearer) and CSRF-protected via
  // a double-submit token (see backend/app/core/csrf.py): the value comes from the login/
  // register/refresh response body via setCsrfToken, not from reading the cookie directly —
  // the backend runs on a different origin, so this origin's JS could never read that cookie.
  if (config.url?.includes("/auth/refresh") || config.url?.includes("/auth/logout")) {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      config.headers["X-CSRF-Token"] = csrfToken;
    }
  }
  return config;
});

let refreshPromise: Promise<string | null> | null = null;

/**
 * Single-flight guard: every caller while a refresh is in progress shares the same promise
 * instead of firing its own /auth/refresh request. This isn't just an optimization — the
 * backend rotates the refresh token/session on every successful call, so two concurrent direct
 * calls (e.g. React 18 StrictMode deliberately double-invoking AuthProvider's bootstrap effect
 * in development) would race: the second one reuses a refresh-token value the first has already
 * rotated away, and gets rejected as if the session were invalid. Exported so AuthProvider's
 * bootstrap effect can share this one code path rather than making its own competing call.
 */
export async function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = api
      .post<ApiSuccess<AccessTokenResponse>>("/auth/refresh")
      .then((res) => {
        const token = res.data.data.access_token;
        setAccessToken(token);
        setCsrfToken(res.data.data.csrf_token);
        return token;
      })
      .catch(() => {
        setAccessToken(null);
        setCsrfToken(null);
        return null;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as
      | (InternalAxiosRequestConfig & { _retry?: boolean })
      | undefined;
    // A 401 from /auth/refresh itself must never trigger another refresh attempt — that would
    // recursively call refreshAccessToken() from inside the very promise chain it's already
    // running (the single-flight `refreshPromise` guard means the recursive call awaits that
    // same still-pending promise), deadlocking forever instead of just reporting "not logged in".
    const isAuthEndpoint =
      original?.url?.includes("/auth/login") ||
      original?.url?.includes("/auth/register") ||
      original?.url?.includes("/auth/refresh");

    if (error.response?.status === 401 && original && !original._retry && !isAuthEndpoint) {
      original._retry = true;
      const newToken = await refreshAccessToken();
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      }
    }
    return Promise.reject(error);
  },
);

export function extractApiErrorMessage(error: unknown, fallback = "Something went wrong"): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as ApiError | undefined;
    return data?.error?.message ?? fallback;
  }
  return fallback;
}
