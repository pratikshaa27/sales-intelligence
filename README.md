# AI-Powered Sales Intelligence Platform

A multi-tenant SaaS platform that helps sales teams research public company/contact signals,
match them against a company's own products, score leads transparently, and generate
human-reviewed sales briefs. See
[`AI_Sales_Intelligence_Platform_Implementation_Spec.md`](./AI_Sales_Intelligence_Platform_Implementation_Spec.md)
for the full product spec this implementation follows.

Built incrementally, phase by phase (spec §26/§30) — see **Build status** below for what's real
today versus what's still to come. All ten build phases are now complete; see
`DEFINITION_OF_DONE.md` for the spec §27 checklist this build was scored against, and
`SECURITY.md` for the production security checklist.

## Stack

- **Backend**: FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL 16 + pgvector, Redis, Celery.
- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, TanStack Query, React Hook Form
  + Zod.
- **Infra**: Docker Compose for local dev, GitHub Actions CI.

## Quick start (local development)

Prerequisites: Docker Desktop, Node.js 20+ (only needed if you want to run frontend tooling
outside Docker), Python 3.11+ (only needed for the same reason on the backend).

```bash
cp .env.example .env
# Edit .env and set a real JWT_SECRET_KEY (a long random string) before anything but pure
# local experimentation — the example value is not safe to use as-is.

docker compose up --build
```

This starts:

| Service    | URL                              | Notes                                   |
|------------|-----------------------------------|------------------------------------------|
| frontend   | http://localhost:3002             | Next.js dev server, hot reload            |
| backend    | http://localhost:8010             | FastAPI, hot reload, runs migrations on boot |
| API docs   | http://localhost:8010/docs        | Swagger UI                                |
| postgres   | localhost:5434                    | `pgvector/pgvector:pg16`                  |
| redis      | localhost:6379                    | broker + cache                            |
| worker     | —                                  | Celery worker (no jobs registered yet)    |

Host ports default to 3002/8010/5434 (instead of the usual 3000/8000/5432) because this machine
already had other projects bound to those — override any of `FRONTEND_PORT` / `BACKEND_PORT` /
`POSTGRES_PORT` / `REDIS_PORT` in `.env` if you'd rather use the defaults on a clean machine.

The backend container's entrypoint runs `alembic upgrade head` automatically before starting
uvicorn, so the schema (and seeded RBAC roles/permissions) is always up to date on boot.

Register your organization at http://localhost:3002/register, then sign in and land on
`/dashboard`.

### Running tests

```bash
# Backend: unit + API integration tests, real Postgres, no mocks
docker compose exec backend pytest -v --cov=app --cov-report=term-missing
docker compose exec backend black --check .
docker compose exec backend mypy app --ignore-missing-imports
docker compose exec backend ruff check .

# Frontend: unit/component tests (Vitest + Testing Library), lint, typecheck, production build
docker compose exec frontend npm test
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run build

# End-to-end: drives the real running stack in a real Chromium browser (Playwright)
cd frontend
npm run test:e2e            # requires `docker compose up` running with the default ports
```

Backend tests spin up (and truncate between tests) a real `sales_intelligence_test` Postgres
database on the same `postgres` container — they exercise real persistence, not mocks, including
a dedicated cross-organization tenant-isolation test (`app/tests/test_tenant_isolation.py`).

The E2E suite (`frontend/e2e/golden-path.spec.ts`) exercises one full user journey end to end
against the real dev stack (register → login → create a product → discover and create a company →
run research → review evidence → score a lead → generate a brief → assign → change status →
export → review audit logs) — see `playwright.config.ts` for the base URL (`E2E_BASE_URL`,
defaults to `http://localhost:3002`) and CI wiring. All three suites run in CI on every push/PR;
see `.github/workflows/ci.yml`'s `backend`/`frontend`/`e2e`/`docker-build` jobs.

### Health checks

- `GET /health` — liveness (process is up).
- `GET /ready` — readiness (checks Postgres + Redis connectivity).

## Project layout

```text
backend/    FastAPI app — see backend/app/{core,ai,research,api,models,schemas,repositories,services,workers}
frontend/   Next.js app — see frontend/{app,components,lib,hooks,types}
docker-compose.yml
.github/workflows/ci.yml
```

Within the backend, business logic lives in `services/`, DB access in `repositories/`, HTTP
concerns in `api/v1/`, and ORM models in `models/` — route handlers stay thin.

## Build status

This is being built phase by phase per the spec's own instruction not to move on until a phase
actually works end to end. **Done and verified** (real Postgres persistence, no mocked data):

- ✅ **Phase 1 — Project setup**: repo, Docker Compose, CI, health/ready checks, linting.
- ✅ **Phase 2 — Auth & organization/RBAC foundation**: register org + admin, login (with account
  lockout after 5 failed attempts), JWT access token + rotating httpOnly-cookie refresh token,
  logout, forgot/reset password, change password, email verification token flow, `/auth/me`,
  session listing/revocation, 6-role RBAC catalog (super_admin/org_admin/sales_manager/
  sales_representative/research_analyst/read_only) enforced via a backend permission dependency
  (never just in the frontend), organization member management, audit logging of auth/org events,
  auth-endpoint rate limiting, and a cross-tenant isolation test suite. Frontend: register/login/
  forgot/reset pages, in-memory access token (never localStorage) with silent refresh on reload,
  protected routes, permission-aware nav.
- ✅ **Phase 3 — Product management**: full CRUD with a draft → active → archived lifecycle
  (restore returns to draft; hard delete only allowed from draft), a global product-category
  taxonomy seeded with sane defaults, server-side search/filter/pagination (name/code text search,
  category, industry, status), file uploads for product documents (type/size validated, stored on
  local disk behind a swappable `FileStorage` interface), and AI-provider-backed embedding
  generation (`app/ai/provider.py` — a `mock` provider by default, or any OpenAI-compatible
  embeddings endpoint) run as a real async Celery job via `POST /products/{id}/reindex`, storing
  vectors in a pgvector column ready for the lead-matching phase. Frontend: product list with
  search/filter/pagination, a shared create/edit form (tag-input fields for the ICP/features/
  industries-style array fields), and a detail page with archive/restore/delete, document upload,
  and a "regenerate embeddings" action reflecting live status.
- ✅ **Phase 4 — Company & contact management**: company CRUD with domain-based deduplication
  (normalizes `https://www.Acme.com/about` → `acme.com`; duplicate-domain creates/renames are
  rejected with a 409 pointing at the existing record), a lightweight `company_sources`/
  `contact_sources` provenance model (add/list/remove a source URL per company or contact — the
  fact-level evidence system from spec §15 is a Phase 5 concern), contact CRUD scoped to a company
  with a verify action, and server-side search/filter/pagination for both (name/domain/industry/
  size/confidence for companies; name/job-title/company/verification-status for contacts).
  Frontend: company and contact list/search/detail/create/edit pages, a company detail page
  listing its contacts and sources inline, and a "new contact" flow pre-selecting the company when
  reached from a company page.
- ✅ **Phase 5 — Research engine**: real `research_jobs`/`research_evidence` tables with progress
  tracking, structured logs, and cooperative cancellation (a worker checks the job's status
  between pipeline steps rather than being killed mid-request). SSRF protection
  (`app/core/ssrf_protection.py`) validates every URL's *resolved* IP — not just the hostname
  string — against private/loopback/link-local/reserved ranges and the cloud metadata address,
  re-checked on every redirect hop; verified live against `169.254.169.254` and a set of
  parametrized unit tests. A real SSRF-protected website fetcher (`app/research/website_fetcher.py`,
  httpx + BeautifulSoup, streamed with a hard byte cap) feeds a structured-extraction step via the
  same AI-provider abstraction as embeddings (`app/ai/provider.py`'s new `CompletionProvider`; a
  keyword-spotting `mock` by default, or any OpenAI-compatible chat-completions endpoint with the
  response always validated against a strict Pydantic schema before being trusted) — verified live
  end to end against the real `https://example.com`, including real evidence rows, a company
  profile merge that never discards manually-entered data, and a source record. Company discovery
  (`POST /companies/discover`) only ever proposes candidates for human review in the job's result
  (spec §6 steps 11/12) — it never creates Company rows itself, and every mock candidate is
  labeled `is_mock_data`/`[MOCK DATA]` so it can never be mistaken for a real prospect. Frontend:
  a company-detail "Run research" button with live progress polling and an evidence list (each
  item labeled AI-generated with its source and confidence), a discovery page, and a research-jobs
  list/detail view with logs and cancellation.
- ✅ **Phase 6 — Lead intelligence**: `leads`/`lead_scores`/`sales_briefs`/`lead_notes`/
  `lead_activities` tables. Lead scoring (`app/services/lead_scoring.py`) is deliberately
  **rule-based, not AI-generated** (spec §5 explicitly forbids an unexplained AI score): every
  point (fit 30 + need 25 + authority 15 + timing 15 + confidence 15 = 100) is tied to a concrete,
  inspectable condition (industry/size/region/tech-stack match, keyword overlap between company
  challenges and product problems-solved, hiring/expansion signal evidence, contact seniority +
  verification status, company research confidence) and comes with a plain-English reason string
  plus a "missing information" list — verified live end to end (create → score → recalculate →
  status/assign → notes/activity log). The *only* AI-generated content anywhere in this phase is
  the sales brief's opener + discovery questions (`ConversationStarters`, via the same
  `mock`/`openai_compatible` provider pattern as prior phases), and every brief carries an explicit
  disclaimer plus an `ai_provider` field so it's never mistaken for verified fact — everything else
  in the brief (company overview, why-relevant, matched product, evidence summary, missing
  information) is assembled directly from recorded data. A stateless `GET /leads/product-matches`
  endpoint reuses the same scoring engine to rank a company's active products by projected fit
  before a lead is even created. Frontend: lead list with status/priority/search filters, a create
  form (company → product → contact-optional selects), and a detail page showing the score
  breakdown as bars with reasons/missing-information, the brief with its disclaimer, a status
  dropdown with a reason field, an assignment dropdown backed by the real org member list, notes,
  and a full activity timeline.
- ✅ **Phase 7 — Dashboard and analytics**: `GET /analytics/{dashboard,leads,products,team}`, all
  real aggregate SQL over the existing leads/companies/products/research-jobs tables (`GROUP BY`/
  `COUNT`/`AVG`/conditional `SUM` — no fabricated numbers). `/analytics/dashboard` and
  `/analytics/leads` are permission-shaped rather than route-gated: any role with
  `analytics.view_team` (every seeded role) gets the spec §8 **Sales Representative Dashboard**
  shape scoped to leads assigned to them; a caller who also holds `analytics.view_org` (sales
  manager, org admin, or platform super-admin) instead gets the full **Organization Dashboard**
  shape — same endpoint, same response schema, `scope: "organization" | "me"` tells the frontend
  which it received and whether `team_performance` (a cross-user view, org-scope only) is
  populated. `/analytics/products` and `/analytics/team` are plain cross-org-member views and are
  route-gated on `analytics.view_org`. Verified live end to end against real leads (multi-product,
  multi-status, assigned/won/lost) with hand-checked arithmetic (average scores, win rates, funnel
  counts, per-product and per-rep breakdowns all cross-checked against the seeded data by hand).
  Frontend: the dashboard page now renders real stat cards, a Recharts bar chart (leads by status),
  pie chart (leads by product), and horizontal bar chart (leads by industry) — each paired with an
  accessible HTML `<table>` of the same data alongside it (spec §8's "provide accessible data
  tables as alternatives"), plus a recent-activity feed and, for managers/admins, team- and
  product-performance tables.

**Known simplifications in the current phase** (called out explicitly rather than silently
under-building):

- The spec's **Admin Dashboard** (total organizations, total users, API usage, AI job usage,
  failed jobs, system health, security events, storage usage) is a platform-wide, cross-tenant
  super-admin view — a genuinely different subsystem from the org-scoped analytics built this
  phase, and one that needs instrumentation that doesn't exist yet (no security-event table
  distinct from the audit log, no API/AI-usage metering, no storage accounting). Building it now
  would mean either fabricating those numbers or silently under-scoping them, both of which the
  spec explicitly forbids — it's deferred to a dedicated admin-panel phase instead. Only the
  Organization Dashboard and Sales Representative Dashboard from spec §8 are built.
- The Sales Representative Dashboard's "Upcoming tasks" isn't implemented — there's no task/
  reminder/due-date subsystem anywhere in the data model (leads have no due date, notes have no
  reminder field) for a task list to be real data rather than a fabricated placeholder.
- `total_companies_researched` is always organization-wide even in "me" scope — research status is
  a property of the company, not of whichever rep happens to have a lead assigned there, so a
  per-rep breakdown wouldn't mean anything.
- Research-job counts in "me" scope reflect jobs the calling user personally started
  (`research_jobs.user_id`), not jobs related to leads assigned to them — the current data model
  doesn't tie a research job to a specific rep's book of business, only to whoever triggered it.
- There's no separate `/analytics` frontend route; all four endpoints are surfaced on the single
  "Dashboard" page, since spec §9's authenticated-page list names only "Dashboard," not a distinct
  analytics page.
- ✅ **Phase 8 — Import, export, and integrations**: real background CSV import for all four spec
  §17 entity types (companies, contacts, products, leads) via a dedicated `import_jobs` table and
  Celery task (`app/workers/import_tasks.py`), plus lead export to CSV, Excel-compatible CSV
  (UTF-8 BOM), and JSON (`POST /leads/export`, matching spec's own API list literally). Column
  mapping is name-based (headers matched case-insensitively against each entity's known columns;
  missing-required and unrecognized columns are both surfaced) rather than an interactive
  drag-and-drop remapper — `POST /imports/{entity_type}/preview` validates and previews before
  anything is queued, `POST /imports/{entity_type}` queues the real background job. Contacts and
  leads reference their parent company/product by natural key in the CSV (company website domain,
  product code, contact email) rather than internal UUIDs, since a CSV author has no reason to know
  a UUID. Duplicate prevention reuses each entity's existing rule (company: domain; product: code;
  contact: email-or-name within the company; lead: an already-open lead for the same company/
  product pair) and a duplicate is *skipped with a reason*, never silently dropped or treated as an
  error. Row-level failures never abort the whole import — every row is independently
  validated/attempted, and both the running counts and a capped list of per-row error messages are
  visible on the job the whole time. **A real concurrency bug was caught and fixed during live
  verification**: SQLAlchemy expires every ORM object in a session on rollback (needed to discard a
  failed row's pending insert), so reading a `job` attribute synchronously right after a rollback —
  exactly what happened processing the row *after* an early duplicate — raised `MissingGreenlet`;
  fixed by always re-fetching the job fresh from the DB around every rollback boundary, with a
  regression test (an early duplicate followed by two successful rows) added specifically to catch
  it again. Frontend: an "Import data" page (entity picker, file input, preview with validation
  feedback, start-import, and a live-polling job history table with per-row error detail), and
  Export CSV/Export CSV (Excel)/Export JSON buttons on the leads list that respect the current
  status/priority filter and trigger a real browser download.

**Known simplifications in the current phase** (called out explicitly rather than silently
under-building):

- Only companies/contacts/products/leads are importable and only leads are exportable — matching
  spec's own written scope exactly (§17 names those four for import; the API list names only
  `POST /leads/export`, and only a `leads.export` permission exists). Import authorization reuses
  each entity's existing `.create` permission rather than adding four new `*.import` permissions
  that would just duplicate it.
- Export is synchronous, not a background job, and capped at 5000 rows — it's a single bounded
  read (the same filtered query the lead list already uses) rather than a multi-step pipeline, so
  there was nothing to make async; a real "many tens of thousands of leads" org would need this
  revisited.
- CSV import size is capped at 10MB and requires valid UTF-8 (a leading BOM from an Excel save is
  tolerated and stripped). List-type fields (tags, locations, technology stack, etc.) use a
  semicolon to separate multiple values within one CSV cell.
- No CRM integration (spec mentions "an approved CRM integration" as a third export target
  alongside CSV/Excel) — no CRM has been named or credentialed, so there is nothing real to
  integrate with yet; JSON export is the closest general-purpose equivalent available today.
- ✅ **Phase 9 — Security hardening**: a distinct `security_events` table (spec §11 lists it
  separately from `audit_logs`) capturing failed logins, account lockouts, permission denials,
  blocked SSRF fetch attempts, and rejected CSRF validations — each with severity, IP, user
  agent, and org/user attribution where one can be resolved. `GET /admin/{audit-logs,
  security-events}` (new `app/api/v1/admin.py`, org-scoped, gated on the existing
  `audit_logs.view` permission) make both logs actually readable for the first time. CSRF
  double-submit protection (`app/core/csrf.py`) now covers the two cookie-authenticated auth
  endpoints (`/auth/refresh`, `/auth/logout`) — every other endpoint is Bearer-token
  authenticated and was never CSRF-exposed in the first place, so the fix is scoped to the
  actual attack surface rather than a blanket global CSRF middleware. File uploads (product
  documents) now check the *actual file bytes* against a magic-byte signature for PDF/DOC/DOCX
  rather than trusting the client-supplied `Content-Type` header alone — a spoofed header with
  mismatched content is rejected. CSV export now escapes leading `=`/`+`/`-`/`@` in any field
  (classic CSV/Excel formula-injection). The API layer now sends `X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`, and (in production) `Strict-Transport-Security` on
  every response. The app refuses to start in `APP_ENV=production` if `JWT_SECRET_KEY` is
  still the default placeholder or under 32 characters. Audit-log coverage was extended to
  `auth.logout`, `member.role_changed`, and `leads.exported`, which weren't logged before.
  New tests: a mocked-transport end-to-end SSRF redirect test (proving the *whole fetch
  pipeline* re-validates on redirect, not just the validator function in isolation), a
  rate-limit-exceeded test (re-enabling slowapi just for that one test, since it's disabled
  suite-wide to keep the rest of the tests non-flaky), and file-signature spoofing tests. See
  `SECURITY.md` at the repo root for the full checklist this phase was scoped against, including
  what's still open.

**Known simplifications in the current phase** (called out explicitly rather than silently
under-building):

- No malware/antivirus scanning of uploaded files — there's no AV engine (e.g. ClamAV) deployed
  in this environment, and adding a "scan" step with nothing real behind it would be security
  theater rather than an actual control.
- No Content-Security-Policy header anywhere (API or frontend) — a real CSP has to be tuned
  against the actual script/style/connect sources the frontend loads and verified live; shipping
  a guessed policy risks silently breaking the app for a control that hasn't been tested.
- CSRF-rejected events are logged to `security_events` without organization/user attribution,
  since the cookie hasn't been resolved to a session yet at the point the check fails — they
  exist in the table but aren't yet visible through the org-scoped `/admin/security-events`
  endpoint. Low priority: the rejection itself (blocking the request) already happened regardless.
- The platform-wide, cross-tenant super-admin dashboard/APIs (`/admin/users`,
  `/admin/organizations`, `/admin/jobs`, `/admin/system-health` — total orgs/users, API/AI usage,
  storage) remain out of scope, same as documented in Phase 7 — this phase's admin endpoints are
  deliberately the narrower, org-scoped audit-log/security-event readers the Phase 9 checklist
  itself asks for ("Audit logs work", "Security events"), not the full admin panel.
- Two-factor authentication is still not implemented (already noted below, carried forward).

- Team invitations create the membership row directly (status `invited`) instead of a separate
  tokenized `invitations` table with its own accept/resend/cancel lifecycle — that needs real
  email delivery to be meaningful, and no SMTP provider is configured yet (`notification_service`
  logs what *would* be sent). The resend/cancel invitation endpoints from spec §10 aren't built
  yet for the same reason.
- Two-factor authentication and device/session naming are not implemented (session listing is).
- A user is assumed to belong to one active organization; the schema supports more, but login
  picks the first active membership found.
- `npm audit` currently reports ~10 advisories against the Next.js 14.x line itself (e.g. request
  smuggling in rewrites, Server Action DoS/SSRF, next/image cache growth) that are only fixed by
  a major-version upgrade to Next 15/16 — none of the affected surfaces (next/image, custom
  middleware, Server Actions) are in use yet, but this needs a real decision (upgrade vs. accept
  risk) during the Phase 9 security-hardening pass rather than being silently carried forward.
- Product documents are stored but their contents aren't parsed/embedded — only the product's own
  structured fields (name, descriptions, features, ICP, etc.) feed the embedding. Real PDF/DOCX
  text extraction wasn't part of the research engine build and remains a larger feature on its own.
- Product categories are a flat, global list (create-only via a super-admin-only endpoint) rather
  than a full admin CRUD UI — that lands with the admin panel phase.
- Deleting a company cascades to its contacts, sources, evidence, *and now any leads referencing
  it* (`ondelete="CASCADE"` on `leads.company_id`) with no "in use" guard or confirmation beyond
  the frontend's button — same simplification as before, now extended to leads rather than fixed.
- Spec's separate `lead_product_matches` and `tags`/`lead_tags` normalized tables were skipped in
  favor of simpler equivalents: product-match suggestions are computed on demand (stateless,
  nothing persisted until a lead is actually created) and `tags` is a JSONB string list directly on
  `Lead` — sufficient for the current UI (no tag-based filtering/autocomplete yet) without a join
  table that nothing else reads.
- Score recalculation and brief generation run synchronously inside the request (not a Celery job)
  — both only do CPU-bound arithmetic or a single provider call, unlike research's multi-step
  fetch/extract pipeline, so there was nothing to make async yet. This will need revisiting if a
  real (non-mock) AI provider call turns out to be slow enough to want a job + polling UI.
- The lead status workflow accepts any status → any other status (no enforced transition graph) as
  long as it's not a no-op; the reason field is optional and freeform. A stricter state machine
  (e.g. blocking `won`/`lost` → `new`) can be added later if the business rules turn out to need
  one.
- Assigning a lead auto-transitions `new` → `assigned` (a reasonable default so a fresh assignment
  is visible in the pipeline) but never overrides a status the lead has already moved past — it
  won't, for example, silently move a `negotiation` lead back to `assigned`.
- Research only fetches and reads the company's own provided website — no crawling beyond that one
  page, no job postings/news/social-profile connectors yet (spec §4.4/§4.6 list these as sources;
  only "website" is implemented, and decision-maker discovery from public profiles isn't built).
  `SourceType`/`EvidenceCategory` already model the other categories so a connector can be added
  later without a schema change, but nothing currently populates them.
- Discovery's mock provider returns a small, obviously-synthetic candidate list (deterministic,
  labeled `is_mock_data`); there's no real business-data-provider integration (spec §30 requires a
  provider interface + mock for exactly this situation, which is what's implemented) — swapping in
  a real one only requires a new `DiscoveryProvider` implementation.
- The AI provider's real (`openai_compatible`) path for structured extraction is implemented and
  schema-validated but unexercised in this environment (no API key configured) — only the `mock`
  keyword-spotting path has actually been run.

- ✅ **Phase 10 — Testing and deployment**: a real browser-based E2E suite
  (`frontend/e2e/golden-path.spec.ts`, Playwright) driving the full spec §22 flow — register →
  login → create product → discover companies → create company → run research → review evidence →
  score a lead → generate a brief → assign → change status → export leads → review audit logs —
  against the actual running stack, plus 28 new frontend unit/component tests (Vitest +
  Testing Library: permissions/API/validation logic, `ProtectedRoute`, the permission-aware nav
  shell, the leads list page) and 2 new backend tests. **Building this E2E suite surfaced and fixed
  three real, previously-undiscovered production auth bugs that 119 backend tests and months of
  manual `curl` verification never caught**, because all of that verification ran outside a real
  browser's security model: (1) `/auth/refresh` returning 401 was itself treated as an
  auth-expiry, recursively re-triggering the token-refresh interceptor and deadlocking the app on
  "Loading…" forever; (2) the CSRF double-submit cookie is set by the backend's own origin, which
  frontend JS running on a different origin/port can never read via `document.cookie` — silent
  re-authentication on page reload was broken for every real user in this cross-origin deployment
  until the backend started also returning the token in the JSON response body for the frontend to
  store; (3) React 18 StrictMode's deliberate double-invocation of effects raced two concurrent
  direct refresh calls against the backend's refresh-token rotation, intermittently invalidating
  the second call — fixed by routing the bootstrap effect through the same single-flighted
  `refreshAccessToken()` used by the request interceptor. A fourth bug (missing `id`/`name` on
  `Controller`-wrapped Select/TagInput fields, breaking both screen-reader label association and
  Playwright's label-based queries) was also found and fixed across every affected form. Both
  backend and frontend Dockerfiles' `production` targets were verified to not just *build* but
  actually *start* correctly (migrations apply, health checks pass) as standalone containers, not
  just as part of the dev Compose stack; a `docker-compose.prod.yml` (resource limits, restart
  policies, required-env-var guards, no bind mounts) was added for a production-shaped deployment.
  Sentry error tracking (`sentry-sdk[fastapi]`) is wired into `app/main.py`, activating only if
  `SENTRY_DSN` is set — a no-op in dev/CI/test, same opt-in pattern as the AI provider. CI
  (`.github/workflows/ci.yml`) now gates on `black --check`/`mypy` in addition to `ruff`/`pytest`
  for the backend, runs the new Vitest suite for the frontend, and has two new jobs: `e2e` (boots
  the full `docker compose` stack, polls for readiness, runs the real Playwright suite against it)
  and `docker-build` (builds both `production` Docker targets). `scripts/backup.sh` /
  `scripts/restore.sh` were written and **verified with a real backup → restore → row-count-match
  round trip** against the dev database (see "Backups" below). See `DEFINITION_OF_DONE.md` for the
  full spec §27 checklist this phase was scored against.

**Known simplifications in this phase** (called out explicitly rather than silently under-building):

- No real staging/production target has actually been deployed to — no live domain, TLS
  certificate, object storage, SMTP provider, or AI provider key exists in this environment. Every
  claim above was verified against the local Docker Compose stack; the production deployment guide
  below is necessarily instructional rather than something that was executed against a real host.
- Backups are tested scripts, not a scheduled job — there's no cron/managed-backup infrastructure
  in this environment to schedule them on yet.
- The E2E suite covers one comprehensive golden-path flow, not per-feature negative-path E2E specs
  (permission-denied UI states, form-validation-error UI states, etc.) — those are already covered
  at the unit/component level (Vitest) and the API level (pytest); a full E2E matrix would mostly
  duplicate that coverage at 100x the runtime cost for little additional confidence.

**Not started / permanently out of scope for this build**: decision-maker/contact discovery from
public profiles, the platform-wide super-admin dashboard/panel, and two-factor authentication —
each already called out in earlier phases above as needing infrastructure (a real people-data
provider, usage/security-event metering at platform scale, an SMS/TOTP provider) that doesn't
exist in this environment. Building them would mean fabricating the data behind them, which the
spec explicitly forbids.

## Security defaults already in place

- Argon2id password hashing; passwords never logged (structured logger redacts password/token/
  secret/authorization keys).
- Short-lived (15 min) JWT access tokens; refresh tokens are opaque, hashed at rest, rotated on
  every use, and revocable (logout, password reset/change revoke all sessions for the user).
- CSRF double-submit protection on the two cookie-authenticated auth endpoints (refresh, logout).
- `organization_id` is always derived from the authenticated JWT, never accepted from the client.
- Every protected route requires an explicit backend permission check (`require_permission(...)`
  dependency) — RBAC is not frontend-only; a denial is also logged to `security_events`.
- File uploads are validated against both an allowed-list Content-Type and the actual file bytes
  (magic-byte signature), not the client-supplied header alone.
- `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` (and HSTS in production) are set
  on every API response; the app refuses to start in production with a default/weak JWT secret.
- Consistent error envelope (`{"success": false, "error": {code, message, details}}`) and a
  redacting JSON logger with per-request IDs.
- Optional Sentry error tracking (`SENTRY_DSN` env var) — inactive unless explicitly configured.
- See `SECURITY.md` for the full production security checklist.

## Production deployment

`docker-compose.prod.yml` targets each service's `production` Dockerfile stage (non-root user,
multi-stage build, health checks) rather than the dev stage's hot-reload setup, and requires every
secret/URL to be supplied explicitly — it uses `${VAR:?error message}` syntax so it refuses to
start with a missing value instead of silently falling back to a dev default.

```bash
cp .env.example .env.prod
# Fill in real values: a long random JWT_SECRET_KEY, real Postgres/Redis credentials, your real
# domain(s) in CORS_ALLOWED_ORIGINS, NEXT_PUBLIC_API_BASE_URL pointed at your real API domain,
# and (optionally) SENTRY_DSN and a real AI_PROVIDER + API key.

docker compose -f docker-compose.prod.yml --env-file .env.prod up --build -d
```

This environment has no real domain, TLS certificate, or hosting target to deploy to, so the
following are documented rather than executed here:

- **TLS/reverse proxy**: put a reverse proxy (nginx, Caddy, or your cloud provider's load
  balancer) in front of the `frontend`/`backend` containers to terminate HTTPS — neither container
  serves TLS itself. `Strict-Transport-Security` is already sent by the backend when
  `APP_ENV=production` (see `app/main.py`), so this only works correctly once TLS is actually
  terminated somewhere in front of it.
- **Environment separation**: use a distinct `.env` per environment (dev/staging/production) with
  distinct secrets, database, and `CORS_ALLOWED_ORIGINS` — never reuse a production `JWT_SECRET_KEY`
  or database in staging.
- **Monitoring**: set `SENTRY_DSN` to enable error tracking (`app/main.py` initializes
  `sentry_sdk` only if it's non-empty); container-level health (`GET /health`, `GET /ready`, and
  the frontend's `GET /api/health`) is already wired into each Dockerfile's `HEALTHCHECK`, so any
  container orchestrator (Docker Swarm, Kubernetes, ECS) can use them directly for restart/
  readiness decisions without extra configuration.
- **Migrations**: the backend's entrypoint runs `alembic upgrade head` automatically on boot, same
  as dev — for a multi-replica production deployment, run the migration once (e.g. as a separate
  one-off job/init container) rather than relying on every replica racing to apply it.

### Backups

```bash
./scripts/backup.sh     # pg_dump's the running postgres container to backups/<timestamp>.sql.gz
./scripts/restore.sh backups/<timestamp>.sql.gz   # restores into a *_restore_test scratch DB by default
```

Both scripts read `POSTGRES_USER`/`POSTGRES_DB` from `.env` and operate against the Dockerized
Postgres via `docker compose exec`. `restore.sh` defaults to a `<db>_restore_test` scratch
database specifically so running it never overwrites live data by accident — pass the real
database name explicitly if you actually intend to restore over it. This round trip (backup, then
restore into the scratch DB, then compare row counts against the original) was run live against
this project's dev database during Phase 10 and produced an exact match.

## Contributing / conventions

- Backend: `ruff check backend`, `black backend` (config in `backend/pyproject.toml`).
- Frontend: `npm run lint`, `npm run typecheck` in `frontend/`.
- New DB schema changes go through Alembic (`docker compose exec backend alembic revision -m "..."`)
  — never edit a running database schema by hand.
