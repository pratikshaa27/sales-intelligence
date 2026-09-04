# Definition of Done — spec §27

Each line from the spec's Definition of Done, with what actually satisfies it and where to look.
Written at the end of Phase 10 (the last of the ten build phases); see `README.md` for the
phase-by-phase build log this checklist summarizes, and `SECURITY.md` for the security-specific
checklist referenced in the last line below.

- **Frontend and backend are connected** — the Next.js app calls the real FastAPI backend for
  every page (no mocked/hardcoded data anywhere); verified live throughout every phase and by the
  Playwright E2E suite (`frontend/e2e/golden-path.spec.ts`), which drives the actual UI against
  the actual API.
- **All important APIs are implemented** — auth, organizations/RBAC, products, companies,
  contacts, research jobs, leads, analytics, imports/exports, admin (audit logs/security events).
  See each phase's README section for the endpoint list; `backend/app/api/v1/router.py` wires
  all nine routers.
- **Database migrations work** — 8 Alembic migrations (`backend/alembic/versions/`), applied
  automatically on container start (`backend/entrypoint.sh`) and exercised by every CI run.
- **Authentication works securely** — Argon2id hashing, short-lived JWT access tokens, rotating
  opaque refresh tokens in an httpOnly cookie, account lockout, no email-existence leakage, CSRF
  double-submit protection on the two cookie-authenticated endpoints. See `SECURITY.md`.
- **Role-based permissions work** — `require_permission(...)` on every protected route, 6 seeded
  roles (`backend/app/core/rbac_data.py`), permission-denial logged to `security_events`.
- **Tenant isolation is tested** — `organization_id` always server-derived from the JWT, never
  client input; cross-org access-attempt tests exist per domain (companies, contacts, products,
  leads, analytics, imports, admin) — see the `*_tenant_isolat*` tests across `backend/app/tests/`.
- **Admin management works** — org member invite/role-change/remove
  (`backend/app/api/v1/organizations.py`); org-scoped audit-log/security-event review
  (`backend/app/api/v1/admin.py`, `frontend/app/audit-logs/page.tsx`). The platform-wide,
  cross-tenant super-admin panel (`/admin/users`, `/admin/organizations`, system health/usage) is
  an explicitly deferred, separate subsystem — see README's Phase 7/9 simplification notes.
- **Product management works** — full CRUD, draft→active→archived lifecycle, category taxonomy,
  document upload with file-signature validation, AI-provider-backed embedding generation.
- **Company discovery works through approved sources** — `POST /companies/discover` only ever
  proposes candidates for human review (never auto-creates a Company row); every mock candidate
  is labeled `is_mock_data`/`[MOCK DATA]`.
- **Research jobs work asynchronously** — Celery + Redis; SSRF-protected website fetch with
  per-redirect-hop re-validation (tested end-to-end with a mocked-transport redirect scenario,
  not just the validator function in isolation); cooperative cancellation.
- **Evidence and source URLs are stored** — `research_evidence` rows carry `source_url`,
  `source_type`, `confidence`, `is_ai_generated`, and a timestamp for every extracted fact.
- **Lead scoring is transparent** — `backend/app/services/lead_scoring.py` is rule-based, not an
  AI-generated number: every point (fit/need/authority/timing/confidence, 100 total) ties to a
  concrete condition and a plain-English reason string, plus a "missing information" list.
- **Sales briefs are generated** — the *only* AI-generated content anywhere in the platform is a
  brief's opener + discovery questions; every brief carries an explicit disclaimer and an
  `ai_provider` field.
- **Users can review and edit AI output** — leads can be edited, notes added, scores recalculated,
  briefs regenerated, statuses/assignments changed by a human at any point; nothing AI-derived is
  auto-committed without a human-reviewable trail (activity log).
- **Leads can be assigned and tracked** — assignment, a 12-state status workflow, notes, and a
  full activity timeline per lead.
- **Dashboard analytics work** — org- and rep-scoped dashboards backed by real aggregate SQL
  (no fabricated numbers), Recharts visualizations paired with accessible data tables.
- **Import and export work** — background CSV import (companies/contacts/products/leads) with
  preview/validation/duplicate-detection; lead export to CSV/Excel-compatible CSV/JSON.
- **Audit logs work** — `audit_logs` covers routine CRUD/action history;
  `GET /admin/audit-logs` (and its frontend page) make it actually readable, not just written.
- **Error handling is implemented** — centralized exception handling
  (`backend/app/core/exceptions.py`), no stack-trace/secret leakage, consistent error envelope,
  per-request tracing ID on every response.
- **Automated tests pass** — backend: 119 pytest tests (unit, API integration, auth,
  authorization, tenant isolation, rate-limit, SSRF, file-upload). Frontend: 28 vitest
  unit/component tests (component rendering, form validation, protected routes, permission-based
  rendering, API error handling, loading/empty states) plus a 13-step Playwright E2E test
  covering the full spec §22 flow end-to-end against the real running stack. All wired into CI
  (`.github/workflows/ci.yml`: `backend`, `frontend`, `e2e`, `docker-build` jobs).
- **Docker deployment works** — every service has a multi-stage Dockerfile with a `production`
  target (non-root user, health check); `docker-compose.yml` for local dev,
  `docker-compose.prod.yml` for a production-shaped deployment (resource limits, restart
  policies, no bind mounts). Both production images verified to actually build *and start*
  correctly during this phase (not just build).
- **Environment configuration is documented** — `.env.example` at the repo root covers every
  variable the app reads, with inline comments explaining each group.
- **No secrets are committed** — `.env` is gitignored and confirmed untracked; the app refuses to
  start in `APP_ENV=production` with a default/weak `JWT_SECRET_KEY`.
- **API documentation is available** — FastAPI's automatic OpenAPI docs at `/docs` and
  `/openapi.json` (every route already carries a `response_model` and tag, so the generated docs
  are meaningful, not just present).
- **README contains setup and deployment instructions** — see `README.md`'s Quickstart and the
  Phase 10 "Testing" and "Production deployment" sections added this phase.
- **Production security checklist is completed** — see `SECURITY.md`, written and verified this
  phase; it lists what's done, what's explicitly deferred, and why.

## What this checklist does *not* claim

Being able to check every line above does not mean this is production-hardened in the sense of
"deploy today and walk away." Specifically still open, and called out rather than glossed over:

- No real staging/production environment has actually been deployed to — there's no live domain,
  no TLS certificate, no real object storage, no real SMTP provider, no real AI provider key
  configured anywhere in this build. Every "it works" claim above was verified against the local
  Docker Compose stack, which is the honest limit of what's verifiable in this environment.
- The platform-wide super-admin panel, malware scanning, and a tuned Content-Security-Policy
  remain unimplemented (see `SECURITY.md` for the reasoning on each).
- Automated backups exist as tested scripts (`scripts/backup.sh` / `scripts/restore.sh`,
  round-trip-verified against the real dev database during this phase), not as a scheduled job —
  there's no cron/managed-backup infrastructure to schedule it on yet.
