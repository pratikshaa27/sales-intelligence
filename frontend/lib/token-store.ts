/**
 * Access token lives in memory only (never localStorage/sessionStorage) so it cannot be
 * read by injected scripts or persisted across a full page reload. The refresh token is an
 * httpOnly cookie the browser handles automatically; on reload, AuthProvider calls
 * /auth/refresh once to silently re-establish an in-memory access token from that cookie.
 */
let accessToken: string | null = null;
type Listener = (token: string | null) => void;
const listeners = new Set<Listener>();

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
  listeners.forEach((listener) => listener(token));
}

export function subscribeToAccessToken(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/**
 * The CSRF double-submit token (see backend/app/core/csrf.py) is handed back in the login/
 * register/refresh response body, not read from its cookie: the frontend and backend run on
 * different origins/ports, so JS here could never read a cookie the backend's origin set.
 * Held in localStorage (not memory-only, unlike the access token above) so a silent
 * refresh-on-page-reload has a value to send — sessionStorage/memory wouldn't survive the
 * reload. This is fine to keep readable to same-origin JS: a CSRF token's job is to prove the
 * request came from this origin's own script, not to act as a secret credential the way the
 * access/refresh tokens are (an XSS attacker who can read this can already forge same-origin
 * requests directly, with or without the token).
 */
const CSRF_TOKEN_STORAGE_KEY = "csrf_token";

export function getCsrfToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(CSRF_TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setCsrfToken(token: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (token) {
      window.localStorage.setItem(CSRF_TOKEN_STORAGE_KEY, token);
    } else {
      window.localStorage.removeItem(CSRF_TOKEN_STORAGE_KEY);
    }
  } catch {
    // Storage unavailable (private browsing, etc.) — the request will simply lack a CSRF
    // header and get a 403, same as any other transient failure to refresh.
  }
}
