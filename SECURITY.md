# Security Checklist

This tracks the platform against spec §20 (API Security), §26 (Phase 9: Security Hardening), and
§27's "production security checklist is completed" item in the Definition of Done. Status as of
Phase 9. Re-review before any real production deployment — this is not a substitute for a real
external security review or penetration test.

## Authentication & session security

- [x] Argon2id password hashing (`passlib[argon2]`, `app/core/security.py`)
- [x] Short-lived JWT access tokens (15 min default), never persisted client-side
      (in-memory only, `frontend/lib/token-store.ts`)
- [x] Opaque, hashed-at-rest refresh tokens in an httpOnly, `Secure`-in-production,
      `SameSite=Lax` cookie scoped to `/api/v1/auth`, rotated on every refresh
- [x] CSRF double-submit token for the two cookie-authenticated endpoints
      (`/auth/refresh`, `/auth/logout`) — see `app/core/csrf.py`
- [x] Account lockout after 5 failed logins (15 minute lockout)
- [x] No account-existence leakage on login failure or password reset
- [x] Refresh tokens revoked on logout and on password reset/change
- [x] Rate limiting on all auth endpoints (register/login/refresh/logout/forgot-password/
      reset-password/verify-email/change-password) via slowapi
- [ ] Two-factor authentication — not implemented (documented simplification, see README)

## Multi-tenant isolation

- [x] `organization_id` always derived server-side from the JWT (`app/api/v1/deps.py`), never
      accepted from client input
- [x] Every protected route enforces an explicit permission via `require_permission(...)` /
      `require_superadmin` — RBAC is not frontend-only
- [x] Cross-org access attempts tested per domain (companies, contacts, products, leads,
      analytics, imports, admin) — see the `*_tenant_isolat*` tests across `app/tests/`
- [x] Permission-denied attempts are logged as a `security_events` row (spec §12 "log
      access-denied events") — see `app/api/v1/deps.py`

## Audit logging & security events

- [x] `audit_logs` table covers routine CRUD/action history across every module (auth, orgs,
      members/roles, companies, contacts, products, leads, imports, exports)
- [x] `security_events` table (distinct from `audit_logs` per spec §11) covers narrower,
      higher-signal events: failed logins, account lockouts, permission denials, blocked SSRF
      fetch attempts, rejected CSRF validation
- [x] `GET /admin/audit-logs` and `GET /admin/security-events` — org-scoped, gated on
      `audit_logs.view` (org admin / super admin only)
- [x] Neither log ever records a password, token, or API key — the validation-error handler
      also strips submitted field values from 422 responses so a bad password isn't echoed back
- [ ] CSRF-rejected events are logged without organization/user attribution (the cookie hasn't
      been resolved to a session yet at that point) — visible in the table directly, not yet
      through the org-scoped admin endpoint. Low priority: CSRF rejections are rare and the
      narrower win (blocking the request) already happened.

## Network & input security

- [x] SSRF protection (`app/core/ssrf_protection.py`) validates the *resolved* IP (not just the
      hostname string) against private/loopback/link-local/reserved/multicast ranges and the
      cloud metadata address, re-validated on every redirect hop
      (`app/research/website_fetcher.py`) — covered by both unit tests
      (`test_ssrf_protection.py`) and an end-to-end mocked-transport redirect test
      (`test_website_fetcher.py`)
- [x] File upload validation: allowed-list content types, 10MB size cap, filename
      sanitization + path-traversal guard, and **magic-byte signature checking** for binary
      types (PDF/DOC/DOCX) so a spoofed `Content-Type` header can't smuggle arbitrary content
      through (`app/core/storage.py`)
- [ ] Malware/antivirus scanning of uploads — not implemented. No AV engine (e.g. ClamAV) is
      deployed in this environment; adding a scan step without a real engine behind it would be
      security theater, not a control. Flagged for whoever provisions the production
      infrastructure.
- [x] CSV export formula-injection escaping (`app/services/export_service.py`) — a value
      starting with `=`, `+`, `-`, `@`, tab, or CR is prefixed with `'` so Excel/Sheets render it
      as text instead of executing it as a formula
- [x] SQL injection: not applicable by construction — every query goes through SQLAlchemy's
      query builder, no raw string-interpolated SQL anywhere in the codebase

## Transport & headers

- [x] CORS is an explicit allowlist from `CORS_ALLOWED_ORIGINS`, not a wildcard
      (`app/main.py`, `app/core/config.py`)
- [x] API responses carry `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
      `Referrer-Policy: strict-origin-when-cross-origin` on every response; `Strict-Transport-
      Security` is added when `APP_ENV=production`
- [x] Frontend (Next.js) sets the same browser-facing headers on its own pages
      (`frontend/next.config.mjs`)
- [ ] Content-Security-Policy — not set anywhere (API or frontend). A real CSP needs to be
      tuned against the actual script/style sources the frontend loads and verified live; a
      guessed policy risks silently breaking the app. Deferred rather than shipping an
      untested policy.
- [x] Every response carries a request ID (`X-Request-Id`) for tracing
      (`app/main.py`'s `request_id_middleware`)

## Secrets management

- [x] `JWT_SECRET_KEY` has no usable default in production: the app refuses to start if
      `APP_ENV=production` and the secret is empty, the literal placeholder, or under 32
      characters (`app/main.py`)
- [x] `.env` is gitignored and confirmed untracked; `.env.example` contains only placeholders
- [x] Password reset/verification tokens are random (`secrets.token_urlsafe(32)`) and stored
      at rest as a hash, never in plaintext
- [x] No hardcoded credentials anywhere in the codebase (the only literal secret-like string is
      a test-only fixture value in `conftest.py`, explicitly not usable in production)

## Error handling

- [x] Centralized exception handling (`app/core/exceptions.py`) — no stack traces or internal
      detail leak to the client; the catch-all handler returns a generic message and logs the
      real exception server-side
- [x] Validation-error responses strip the submitted `input` value so a password typo isn't
      echoed back verbatim

## Known deferrals (see README "Known simplifications" for the full running list)

- The platform-wide, cross-tenant super-admin dashboard (`/admin/users`, `/admin/organizations`,
  `/admin/jobs`, `/admin/system-health` — total users/orgs, API/AI usage, storage) is a separate
  subsystem from this pass's org-scoped audit-log/security-event visibility and needs real
  usage-metering infrastructure that doesn't exist yet.
- Two-factor authentication.
- Malware scanning and Content-Security-Policy, as noted above.

**Before a real production deployment**, in addition to the unchecked items above: rotate
`JWT_SECRET_KEY` to a freshly generated value, confirm `CORS_ALLOWED_ORIGINS` lists only the
real production frontend origin(s), confirm `APP_ENV=production` (this is what enables the
`Secure` cookie flag, HSTS header, and the JWT-secret startup guard), and run this checklist
past someone who isn't the person who wrote the code it's checking.
