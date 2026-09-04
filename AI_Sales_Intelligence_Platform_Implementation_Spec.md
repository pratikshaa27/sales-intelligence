# AI-Powered Sales Intelligence Platform
## Production-Ready End-to-End Implementation Specification

## 1. Project Overview

Build a production-ready AI-powered Sales Intelligence Platform that helps sales teams discover potential customers for the company's products.

The platform should research public company websites and approved public professional information, identify relevant companies and decision-makers, understand possible business needs, match prospects with suitable company products, score leads, and generate useful sales briefs.

The system should help sales teams save time during lead generation and research. It should not automatically send spam or contact people without human approval. The sales team must review and approve leads before outreach.

The application must include:

- Modern responsive frontend
- Secure backend APIs
- User authentication and authorization
- Admin management
- Organization and team management
- Product management
- Lead management
- Company and contact management
- AI-powered research and matching
- Lead scoring
- Sales brief generation
- Activity and audit logs
- Search, filters, sorting, and pagination
- Dashboard and analytics
- CRM-ready export
- Production deployment configuration
- Automated testing
- Security and monitoring

---

## 2. Recommended Technology Stack

Use a maintainable, scalable, and widely supported stack.

### Frontend

- Next.js with TypeScript
- React
- Tailwind CSS
- shadcn/ui or another accessible component system
- TanStack Query for API data fetching and caching
- React Hook Form
- Zod for validation
- Recharts for dashboards and analytics
- Axios or a typed fetch wrapper
- ESLint and Prettier

### Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic for database migrations
- PostgreSQL
- Redis
- Celery or RQ for background jobs
- JWT-based authentication with secure refresh-token handling
- Argon2 or bcrypt for password hashing

### AI and Research

- LangChain only where it provides real value
- LangGraph for multi-step research workflows
- A provider abstraction supporting:
  - Local LLMs
  - OpenAI-compatible APIs
  - Other approved model providers
- Embeddings for semantic product and lead matching
- ChromaDB or pgvector for vector search
- Structured JSON outputs from AI models
- Rule-based scoring combined with AI-assisted analysis

### Infrastructure

- Docker
- Docker Compose for local development
- PostgreSQL
- Redis
- Nginx or a managed reverse proxy
- Object storage for uploaded files if required
- GitHub Actions or GitLab CI/CD
- Environment-based configuration
- Centralized logging
- Health checks

Use PostgreSQL as the main source of truth. Prefer pgvector if practical so relational data and vector data can be managed in one database. ChromaDB can be used if there is a strong reason to keep vector storage separate.

---

## 3. Main User Roles

### Super Admin

Can manage the entire platform.

Permissions:

- Manage all organizations
- Create, update, deactivate, and delete users
- Manage roles and permissions
- Manage system settings
- Manage AI provider settings
- Manage product categories
- View all audit logs
- View platform-wide analytics
- Manage subscription or usage limits
- Manage integrations
- Manage security settings

### Organization Admin

Can manage one organization.

Permissions:

- Manage organization profile
- Invite and remove team members
- Assign team roles
- Manage organization products
- View and manage all organization leads
- View organization analytics
- Configure organization settings
- View organization audit logs

### Sales Manager

Permissions:

- View team dashboard
- Assign leads to sales representatives
- Create and manage products
- Review lead scores
- View sales briefs
- Export lead data
- Track team activity

### Sales Representative

Permissions:

- View assigned leads
- Search and discover leads
- Review company and contact information
- Generate sales briefs
- Update lead status
- Add notes and activities
- Export permitted lead data

### Research Analyst

Permissions:

- Run company research
- Review research results
- Validate source information
- Generate lead recommendations
- Cannot change organization settings

### Read-Only User

Permissions:

- View permitted dashboards, products, companies, and leads
- Cannot create, edit, delete, export, or run expensive AI jobs

Implement role-based access control on the backend. Never rely only on frontend route protection.

---

## 4. Core Application Modules

### 4.1 Authentication Module

Features:

- Register organization and first admin
- Login
- Logout
- Refresh access token
- Forgot password
- Reset password
- Email verification
- Change password
- Secure session management
- Optional two-factor authentication
- Account lockout or rate limiting after repeated failed login attempts
- Login history
- Device/session management

Security requirements:

- Hash passwords using Argon2id or bcrypt
- Never store plain-text passwords
- Use short-lived access tokens
- Use secure, HTTP-only refresh-token cookies where appropriate
- Implement CSRF protection when cookie-based authentication is used
- Rate-limit authentication endpoints
- Validate all inputs
- Do not expose whether an email exists during password reset
- Revoke refresh tokens during logout or password reset

---

### 4.2 Organization and Team Management

Features:

- Create organization
- Update organization profile
- Invite team members by email
- Accept invitation
- Resend invitation
- Cancel invitation
- Deactivate user
- Reactivate user
- Assign roles
- Remove team member
- View team activity
- Configure organization-level AI and usage settings

Every organization-owned record must contain an organization ID.

Implement strict tenant isolation so one organization cannot access another organization's data.

---

### 4.3 Product Management

The company must first add its products to the platform.

Product fields:

- Product name
- Product code
- Short description
- Detailed description
- Product category
- Target industries
- Target company size
- Target geographic regions
- Main business problems solved
- Key features
- Benefits
- Pricing model
- Minimum contract value, if applicable
- Required technical capabilities
- Supported integrations
- Ideal customer profile
- Common use cases
- Competitor alternatives
- Product documents
- Product status
- Created by
- Updated by
- Created date
- Updated date

Product lifecycle:

- Draft
- Active
- Archived

The product module must support:

- Create product
- Edit product
- View product
- Archive product
- Restore product
- Search products
- Filter by category and industry
- Upload product documents
- Generate product embeddings
- Rebuild product embeddings
- Match products with leads

The AI system must use the product database as the source of truth. It must not invent product capabilities, pricing, certifications, or features.

---

### 4.4 Company Discovery Module

The platform should help users discover potential companies.

Inputs:

- Target industry
- Location
- Company size
- Revenue range, if available
- Technology used
- Business problem
- Product to promote
- Keywords
- Target market
- Number of companies to discover

Sources must be approved and legally usable.

Possible sources:

- Public company websites
- Public business directories
- Approved data providers
- Approved APIs
- Public company announcements
- Public job postings
- Public news
- Public professional information where access is permitted

Do not bypass website protections, scrape private data, bypass authentication, or violate platform terms.

Company discovery output:

- Company name
- Website
- Industry
- Location
- Company size, if available
- Business description
- Potential business problem
- Relevant public signals
- Source URLs
- Source dates
- Confidence score
- Research status

Avoid duplicate companies by normalizing domains and company names.

---

### 4.5 Company Research Module

For each company, research public information and create a structured company profile.

Research areas:

- Company overview
- Industry
- Products or services
- Locations
- Approximate company size
- Technology stack, if publicly available
- Recent announcements
- Hiring signals
- Expansion signals
- Digital transformation signals
- Security or infrastructure signals
- Publicly stated business challenges
- Relevant use cases for the company's products
- Source links
- Source publication dates
- Confidence level

Every important claim must have a source URL and source timestamp.

The system must clearly separate:

- Verified facts
- AI-generated interpretation
- Possible business signals
- Unknown information

Never present an assumption as a confirmed fact.

---

### 4.6 Contact and Decision-Maker Module

Identify relevant decision-makers using only approved public or licensed sources.

Contact fields:

- Full name
- Job title
- Department
- Company
- Public professional profile URL
- Public business email, only if legally obtained and permitted
- Public business phone, only if legally obtained and permitted
- Seniority
- Role relevance
- Source URL
- Source date
- Verification status
- Confidence score

Possible decision-maker roles:

- Founder
- CEO
- CTO
- CIO
- CISO
- Head of IT
- Head of Infrastructure
- Head of Procurement
- Head of Operations
- Head of Sales
- Head of HR
- Product Manager
- Engineering Manager

The platform must not infer or expose sensitive personal information.

Do not collect private contact details, personal phone numbers, personal email addresses, passwords, or restricted data.

---

### 4.7 Lead Management Module

A lead is a potential business opportunity, not a confirmed interested customer.

Lead fields:

- Lead ID
- Organization ID
- Company ID
- Contact ID
- Matched product ID
- Lead name
- Lead source
- Lead status
- Lead score
- Fit score
- Need score
- Authority score
- Timing score
- Data confidence score
- Priority
- Assigned sales representative
- Research summary
- Sales brief
- Next action
- Notes
- Tags
- Created date
- Updated date
- Last activity date

Lead statuses:

- New
- Researching
- Qualified
- Assigned
- Contacted
- Meeting Scheduled
- Proposal Sent
- Negotiation
- Won
- Lost
- Disqualified
- Archived

Lead priority:

- Low
- Medium
- High
- Critical

Lead actions:

- Create lead
- Edit lead
- Assign lead
- Reassign lead
- Change status
- Add note
- Add activity
- Generate brief
- Re-run research
- Recalculate score
- Export lead
- Archive lead

---

## 5. Lead Scoring System

Use a transparent scoring system.

Do not allow the AI model to produce an unexplained score.

Example score:

- Company-product fit: 30 points
- Evidence of business need: 25 points
- Decision-maker relevance: 15 points
- Timing or buying signal: 15 points
- Data quality and source confidence: 15 points

Total: 100 points.

Score interpretation:

- 80–100: High-priority lead
- 60–79: Good potential
- 40–59: Needs more research
- 0–39: Low confidence

Each score must include an explanation.

Example:

```json
{
  "total_score": 82,
  "fit_score": 28,
  "need_score": 22,
  "authority_score": 13,
  "timing_score": 10,
  "confidence_score": 9,
  "reasons": [
    "The company operates in a target industry.",
    "The company publicly announced an infrastructure expansion.",
    "The identified contact has a relevant technical leadership role."
  ],
  "missing_information": [
    "Budget is unknown.",
    "Purchase timeline is not confirmed."
  ]
}
```

The system must never claim that a company has a budget or purchase intent unless there is reliable evidence.

---

## 6. AI Research Workflow

Implement the AI workflow as a controlled pipeline.

### Step 1: User Input

The user selects:

- Product
- Target industry
- Location
- Company size
- Keywords
- Number of leads
- Optional business problem

### Step 2: Company Discovery

Find candidate companies from approved sources.

### Step 3: Deduplication

Normalize domains and remove duplicate companies.

### Step 4: Public Research

Collect public pages and relevant source information.

### Step 5: Evidence Extraction

Extract structured facts with source URLs.

### Step 6: Company Profile Generation

Generate a structured company profile.

### Step 7: Decision-Maker Identification

Find relevant public professional information.

### Step 8: Product Matching

Compare the company profile with the product's ideal customer profile.

### Step 9: Lead Scoring

Calculate transparent scores using rules and AI-assisted classification.

### Step 10: Sales Brief Generation

Generate a concise brief for the sales team.

### Step 11: Human Review

The user reviews the evidence, score, and brief.

### Step 12: Save or Reject

The user can save, edit, reject, or assign the lead.

### Step 13: Export

Export approved leads to CSV, Excel, or an approved CRM integration.

Use background jobs for long-running research tasks. The frontend must show progress and job status.

---

## 7. Sales Brief Format

Each generated sales brief should contain:

- Company overview
- Why this company may be relevant
- Matched company product
- Possible business problem
- Evidence and source links
- Relevant decision-maker
- Suggested conversation opener
- Suggested discovery questions
- Lead score
- Score explanation
- Missing information
- Recommended next action
- Disclaimer that the information is AI-generated and requires human verification

Example:

```text
Company:
Potential Need:
Recommended Product:
Why This Lead May Be Relevant:
Evidence:
Relevant Decision-Maker:
Suggested Opening:
Discovery Questions:
Lead Score:
Confidence:
Missing Information:
Recommended Next Action:
```

Do not generate aggressive, misleading, or spam-oriented messages.

---

## 8. Dashboard

### Organization Dashboard

Display:

- Total companies researched
- Total leads
- New leads
- High-priority leads
- Assigned leads
- Contacted leads
- Won leads
- Lost leads
- Research jobs running
- Research jobs completed
- Average lead score
- Leads by status
- Leads by product
- Leads by industry
- Team performance
- Recent activities

### Sales Representative Dashboard

Display:

- My assigned leads
- Leads requiring review
- High-priority leads
- Upcoming tasks
- Recent activities
- Leads by status
- Conversion summary

### Admin Dashboard

Display:

- Total organizations
- Total users
- Active users
- API usage
- AI job usage
- Failed jobs
- System health
- Security events
- Storage usage

Use charts only where they improve understanding. Provide accessible data tables as alternatives.

---

## 9. Frontend Pages

Create the following pages.

### Public Pages

- Landing page
- Login
- Register
- Forgot password
- Reset password
- Email verification
- Privacy policy
- Terms of service

### Authenticated Pages

- Dashboard
- Companies
- Company details
- Discover companies
- Research jobs
- Contacts
- Leads
- Lead details
- Lead creation/edit page
- Sales brief page
- Products
- Product details
- Product creation/edit page
- Team members
- Activities
- Reports
- Exports
- Integrations
- Organization settings
- User profile
- Security settings
- Notifications

### Admin Pages

- Admin dashboard
- Organizations
- Users
- Roles and permissions
- System settings
- AI provider settings
- Usage monitoring
- Audit logs
- Security events
- Background jobs
- Feature flags

Frontend requirements:

- Responsive design for desktop, tablet, and mobile
- Loading states
- Empty states
- Error states
- Confirmation dialogs
- Toast notifications
- Form validation
- Accessible keyboard navigation
- Accessible color contrast
- Pagination
- Search and filtering
- Optimistic updates only where safe
- No sensitive data in browser local storage
- Protected routes
- Clear permission-based UI

---

## 10. Backend API Design

Use versioned REST APIs.

Base path:

```text
/api/v1
```

### Authentication APIs

```text
POST   /auth/register
POST   /auth/login
POST   /auth/logout
POST   /auth/refresh
POST   /auth/forgot-password
POST   /auth/reset-password
POST   /auth/verify-email
POST   /auth/change-password
GET    /auth/me
GET    /auth/sessions
DELETE /auth/sessions/{session_id}
```

### Organization APIs

```text
GET    /organizations/me
PATCH  /organizations/me
GET    /organizations/me/members
POST   /organizations/me/invitations
POST   /organizations/me/invitations/{id}/resend
DELETE /organizations/me/invitations/{id}
PATCH  /organizations/me/members/{id}
DELETE /organizations/me/members/{id}
```

### Product APIs

```text
GET    /products
POST   /products
GET    /products/{id}
PATCH  /products/{id}
DELETE /products/{id}
POST   /products/{id}/archive
POST   /products/{id}/restore
POST   /products/{id}/documents
POST   /products/{id}/reindex
```

### Company APIs

```text
GET    /companies
POST   /companies
GET    /companies/{id}
PATCH  /companies/{id}
DELETE /companies/{id}
POST   /companies/discover
POST   /companies/{id}/research
GET    /companies/{id}/sources
```

### Contact APIs

```text
GET    /contacts
POST   /contacts
GET    /contacts/{id}
PATCH  /contacts/{id}
DELETE /contacts/{id}
POST   /contacts/{id}/verify
```

### Lead APIs

```text
GET    /leads
POST   /leads
GET    /leads/{id}
PATCH  /leads/{id}
DELETE /leads/{id}
POST   /leads/{id}/assign
POST   /leads/{id}/score
POST   /leads/{id}/brief
POST   /leads/{id}/research
POST   /leads/{id}/activities
POST   /leads/export
```

### Job APIs

```text
GET    /jobs
GET    /jobs/{id}
POST   /jobs/{id}/cancel
GET    /jobs/{id}/logs
```

### Analytics APIs

```text
GET    /analytics/dashboard
GET    /analytics/leads
GET    /analytics/products
GET    /analytics/team
```

### Admin APIs

```text
GET    /admin/users
PATCH  /admin/users/{id}/status
GET    /admin/organizations
GET    /admin/audit-logs
GET    /admin/security-events
GET    /admin/jobs
GET    /admin/system-health
```

Use consistent response formats.

Example success response:

```json
{
  "success": true,
  "data": {},
  "message": "Operation completed successfully"
}
```

Example error response:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request contains invalid data",
    "details": {}
  }
}
```

---

## 11. Database Design

Create normalized PostgreSQL tables.

Minimum tables:

- users
- organizations
- organization_members
- roles
- permissions
- role_permissions
- invitations
- sessions
- password_reset_tokens
- email_verification_tokens
- products
- product_categories
- product_documents
- product_embeddings
- companies
- company_sources
- contacts
- contact_sources
- leads
- lead_scores
- lead_product_matches
- sales_briefs
- research_jobs
- research_job_steps
- research_evidence
- activities
- notes
- tags
- lead_tags
- notifications
- exports
- integrations
- api_usage
- audit_logs
- security_events
- system_settings

Important database requirements:

- Use UUID primary keys
- Add organization_id to tenant-owned tables
- Add created_at and updated_at
- Add created_by and updated_by where useful
- Add indexes for frequently searched fields
- Add unique constraints for normalized company domains
- Use foreign keys
- Use soft deletion where appropriate
- Use database transactions
- Use migrations
- Never modify production schema manually
- Add created_at indexes for time-based queries
- Add full-text or vector indexes where needed

---

## 12. Multi-Tenant Security

The platform must be multi-tenant.

Requirements:

- Every request must identify the authenticated user
- Every user must belong to an organization
- Every organization-owned query must filter by organization_id
- Never trust organization_id supplied by the frontend
- Derive organization context from the authenticated session
- Enforce permissions in backend dependencies
- Prevent insecure direct object references
- Test cross-organization access attempts
- Use PostgreSQL row-level security if appropriate
- Never expose internal database IDs unnecessarily
- Log access-denied events

---

## 13. Background Jobs

Long-running tasks must run asynchronously.

Background job types:

- Company discovery
- Website research
- Contact research
- Product embedding generation
- Lead scoring
- Sales brief generation
- Bulk import
- Bulk export
- CRM synchronization
- Email notifications

Job states:

- Queued
- Running
- Completed
- Failed
- Cancelled

Each job must store:

- Job ID
- Organization ID
- User ID
- Job type
- Input parameters
- Status
- Progress percentage
- Current step
- Error message
- Retry count
- Started time
- Completed time

Implement:

- Retry with limits
- Exponential backoff
- Timeout handling
- Idempotency
- Dead-letter handling
- Job cancellation where possible
- Progress updates
- Error logging

---

## 14. AI Safety and Reliability

The AI system must be controlled.

Requirements:

- Use structured output schemas
- Validate all AI responses
- Never execute AI-generated code
- Never trust AI-generated URLs without validation
- Store source evidence separately from generated summaries
- Mark generated content as AI-generated
- Use confidence scores
- Detect unsupported claims
- Prevent prompt injection from researched web pages
- Treat all external content as untrusted
- Do not allow website content to override system instructions
- Limit tool access
- Use allowlisted tools
- Add maximum token and time limits
- Add fallback responses when AI fails
- Log model name and version
- Log prompt and response metadata safely
- Do not store secrets in prompts
- Redact sensitive information from logs

Use a clear distinction between:

- Trusted system instructions
- User input
- External web content
- Retrieved documents
- AI-generated output

---

## 15. Research Source and Provenance Management

For every extracted fact, store:

- Fact text
- Source URL
- Source title
- Source type
- Source publication date if available
- Retrieved date
- Extracted by
- Confidence
- Related company
- Related contact
- Related lead

The UI must allow users to open the source URL.

If a claim cannot be supported, label it as:

- Unverified
- Possible signal
- AI interpretation
- Missing information

Do not present unsupported AI assumptions as facts.

---

## 16. Search and Filtering

Implement server-side search and filtering.

Search fields:

- Company name
- Domain
- Industry
- Location
- Contact name
- Job title
- Product
- Lead status
- Lead score
- Assigned user
- Tags

Filters:

- Score range
- Industry
- Company size
- Location
- Product
- Lead status
- Source
- Research date
- Assigned user
- Confidence level

Use pagination and sorting.

Avoid loading all records into the browser.

---

## 17. Import and Export

### Import

Support CSV import for:

- Companies
- Contacts
- Products
- Leads

Import requirements:

- Validate file type
- Validate file size
- Validate column mapping
- Show preview
- Show validation errors
- Prevent duplicate records
- Run imports in background
- Provide import result summary

### Export

Support:

- CSV
- Excel-compatible CSV
- JSON for approved integrations

Export fields must respect user permissions.

Do not export private or restricted information.

---

## 18. Notifications

Implement in-app notifications for:

- Invitation received
- Research job completed
- Research job failed
- Lead assigned
- Lead status changed
- Sales brief generated
- Export completed
- Security event
- System announcement

Email notifications should be optional and configurable.

---

## 19. Audit Logging

Log important actions:

- Login and logout
- Failed login
- Password reset
- User creation
- Role changes
- Product creation and updates
- Lead creation and updates
- Lead assignment
- Data export
- AI job execution
- Integration changes
- Permission failures
- Admin actions
- Security events

Audit log fields:

- Event ID
- Organization ID
- User ID
- Action
- Resource type
- Resource ID
- IP address, if permitted
- User agent, if permitted
- Timestamp
- Metadata

Do not log passwords, tokens, API keys, or sensitive secrets.

---

## 20. API Security

Implement:

- CORS allowlist
- Rate limiting
- Request size limits
- Input validation
- Output validation
- Security headers
- HTTPS in production
- Secure cookies
- CSRF protection when required
- SQL injection protection through ORM and parameterized queries
- SSRF protection for URL fetching
- URL allowlists and blocked private IP ranges
- File upload validation
- Malware scanning if file uploads are enabled
- Request ID for tracing
- Centralized exception handling

For website research, protect against SSRF by blocking:

- localhost
- private IP ranges
- cloud metadata endpoints
- internal network addresses
- unsupported protocols
- file URLs

---

## 21. Observability

Implement:

- Structured JSON logs
- Request IDs
- Error tracking
- Health endpoint
- Readiness endpoint
- Liveness endpoint
- Database health check
- Redis health check
- AI provider health check
- Background job monitoring
- Performance metrics
- API latency metrics
- Failed request metrics

Endpoints:

```text
GET /health
GET /ready
GET /metrics
```

Do not expose sensitive diagnostics publicly.

---

## 22. Testing Requirements

### Backend Tests

- Unit tests
- API integration tests
- Authentication tests
- Authorization tests
- Multi-tenant isolation tests
- Database tests
- AI response validation tests
- Background job tests
- Rate-limit tests
- SSRF protection tests
- File upload tests

### Frontend Tests

- Component tests
- Form validation tests
- Protected route tests
- Permission-based rendering tests
- API error handling tests
- Loading and empty state tests

### End-to-End Tests

Test the complete flow:

1. Register organization
2. Verify email
3. Login
4. Create product
5. Discover companies
6. Run research
7. Review research evidence
8. Generate lead score
9. Generate sales brief
10. Assign lead
11. Update lead status
12. Export leads
13. Review audit logs

Use Playwright for end-to-end testing.

---

## 23. Deployment Architecture

Recommended production architecture:

```text
User Browser
    |
Frontend Application
    |
Reverse Proxy / HTTPS
    |
FastAPI Backend
    |
    +-- PostgreSQL
    +-- Redis
    +-- Background Worker
    +-- AI Provider
    +-- Object Storage
```

Deploy separately:

- Frontend
- Backend API
- Background worker
- PostgreSQL
- Redis

Use Docker images.

Production requirements:

- Separate development, staging, and production environments
- Environment variables for secrets
- No secrets committed to Git
- Automated database migrations
- Automated backups
- Backup restoration testing
- HTTPS
- Domain configuration
- Error monitoring
- Log retention
- Resource limits
- Health checks
- Graceful shutdown
- Zero-downtime deployment where possible

---

## 24. Environment Variables

Create `.env.example`.

Example variables:

```env
APP_ENV=development
APP_NAME=sales-intelligence-platform
API_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/sales_intelligence
REDIS_URL=redis://localhost:6379/0

JWT_SECRET_KEY=replace-with-a-long-random-secret
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

AI_PROVIDER=local
AI_BASE_URL=http://localhost:11434
AI_MODEL=your-model-name
EMBEDDING_MODEL=your-embedding-model

OBJECT_STORAGE_ENDPOINT=
OBJECT_STORAGE_BUCKET=
OBJECT_STORAGE_ACCESS_KEY=
OBJECT_STORAGE_SECRET_KEY=

SMTP_HOST=
SMTP_PORT=
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=

SENTRY_DSN=
LOG_LEVEL=INFO
```

Never place real secrets in the repository.

---

## 25. Project Folder Structure

### Backend

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── database.py
│   │   ├── logging.py
│   │   └── exceptions.py
│   ├── api/
│   │   └── v1/
│   │       ├── router.py
│   │       ├── auth.py
│   │       ├── users.py
│   │       ├── organizations.py
│   │       ├── products.py
│   │       ├── companies.py
│   │       ├── contacts.py
│   │       ├── leads.py
│   │       ├── jobs.py
│   │       ├── analytics.py
│   │       └── admin.py
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── product_service.py
│   │   ├── company_service.py
│   │   ├── lead_service.py
│   │   ├── scoring_service.py
│   │   ├── brief_service.py
│   │   └── audit_service.py
│   ├── ai/
│   │   ├── provider.py
│   │   ├── prompts.py
│   │   ├── schemas.py
│   │   ├── workflows.py
│   │   └── safety.py
│   ├── workers/
│   ├── integrations/
│   └── tests/
├── alembic/
├── Dockerfile
├── requirements.txt
├── pyproject.toml
└── .env.example
```

### Frontend

```text
frontend/
├── app/
│   ├── login/
│   ├── register/
│   ├── dashboard/
│   ├── companies/
│   ├── contacts/
│   ├── leads/
│   ├── products/
│   ├── research-jobs/
│   ├── team/
│   ├── analytics/
│   ├── settings/
│   └── admin/
├── components/
│   ├── ui/
│   ├── layout/
│   ├── forms/
│   ├── tables/
│   ├── charts/
│   └── shared/
├── lib/
│   ├── api.ts
│   ├── auth.ts
│   ├── permissions.ts
│   ├── validations.ts
│   └── utils.ts
├── hooks/
├── types/
├── services/
├── tests/
├── public/
├── Dockerfile
├── package.json
└── .env.example
```

---

## 26. Implementation Phases

### Phase 1: Project Setup

- Create repository
- Create frontend and backend applications
- Configure TypeScript and Python
- Configure linting and formatting
- Configure Docker Compose
- Configure PostgreSQL and Redis
- Configure environment variables
- Add basic CI pipeline

### Phase 2: Authentication and User Management

- Registration
- Login
- Logout
- Token refresh
- Password reset
- Email verification
- User profile
- Roles and permissions
- Organization creation
- Team invitations

### Phase 3: Product Management

- Product CRUD
- Product categories
- Product documents
- Product search
- Product embedding generation
- Product access control

### Phase 4: Company and Contact Management

- Company CRUD
- Contact CRUD
- Source management
- Deduplication
- Search and filters
- Company details page
- Contact details page

### Phase 5: Research Engine

- Research job model
- Background workers
- Approved source connectors
- Website content extraction
- Evidence storage
- Structured company profile generation
- Research progress UI
- Retry and failure handling

### Phase 6: Lead Intelligence

- Product matching
- Lead creation
- Lead scoring
- Score explanation
- Lead assignment
- Lead status workflow
- Sales brief generation

### Phase 7: Dashboard and Analytics

- Organization dashboard
- Sales dashboard
- Admin dashboard
- Charts
- Reports
- Activity timeline

### Phase 8: Import, Export, and Integrations

- CSV import
- CSV export
- Excel-compatible export
- CRM integration abstraction
- API keys or OAuth only where appropriate

### Phase 9: Security Hardening

- Multi-tenant tests
- Rate limiting
- SSRF protection
- Audit logs
- Security events
- Secret management
- File validation
- Permission review

### Phase 10: Testing and Deployment

- Unit tests
- Integration tests
- End-to-end tests
- Docker production build
- CI/CD
- Staging deployment
- Database backups
- Monitoring
- Production deployment

---

## 27. Definition of Done

The project is complete only when:

- Frontend and backend are connected
- All important APIs are implemented
- Database migrations work
- Authentication works securely
- Role-based permissions work
- Tenant isolation is tested
- Admin management works
- Product management works
- Company discovery works through approved sources
- Research jobs work asynchronously
- Evidence and source URLs are stored
- Lead scoring is transparent
- Sales briefs are generated
- Users can review and edit AI output
- Leads can be assigned and tracked
- Dashboard analytics work
- Import and export work
- Audit logs work
- Error handling is implemented
- Automated tests pass
- Docker deployment works
- Environment configuration is documented
- No secrets are committed
- API documentation is available
- README contains setup and deployment instructions
- Production security checklist is completed

---

## 28. Important Development Rules

1. Do not build only a frontend mockup.
2. Implement real backend APIs and database persistence.
3. Do not use hardcoded demo data in production flows.
4. Use seed data only for local development.
5. Do not skip authentication or authorization.
6. Do not trust organization IDs from the frontend.
7. Do not expose private personal information.
8. Do not scrape restricted or private sources.
9. Do not bypass website protections.
10. Treat external web content as untrusted.
11. Do not allow prompt injection from web content to control the AI workflow.
12. Do not allow the AI to invent product capabilities.
13. Store evidence for every important research claim.
14. Make long-running tasks asynchronous.
15. Add retries and failure handling.
16. Validate all API inputs and outputs.
17. Add audit logs for important actions.
18. Use secure defaults.
19. Write tests before declaring modules complete.
20. Keep the code modular and maintainable.
21. Do not over-engineer before the core workflow works.
22. Use clear comments only where needed.
23. Keep frontend components reusable.
24. Keep business logic out of route handlers.
25. Use database transactions for multi-step operations.
26. Document every setup command.
27. Provide a working local development environment.
28. Provide a staging and production deployment guide.
29. Do not claim the system is production-ready until security, testing, monitoring, and deployment are complete.
30. Ask for clarification only when a decision is genuinely blocking implementation; otherwise choose a sensible default and document it.

---

## 29. Expected Final Deliverables

The implementation must include:

- Complete frontend source code
- Complete backend source code
- Database models
- Database migrations
- Authentication system
- Authorization system
- Admin panel
- User and organization management
- Product management
- Company and contact management
- Research workflow
- Lead scoring workflow
- Sales brief generation
- Background workers
- API documentation
- Docker Compose configuration
- Production Dockerfiles
- CI/CD configuration
- Unit tests
- Integration tests
- End-to-end tests
- Seed script
- `.env.example`
- README
- Security documentation
- Deployment documentation
- API collection for testing
- Sample product data
- Sample company data for local development only

---

## 30. Instruction to the AI Coding Assistant

Implement this project incrementally and completely.

Start by inspecting the repository and identifying the current structure. If the repository is empty, initialize the project using the recommended stack.

Before coding:

1. Create a technical implementation plan.
2. Create the folder structure.
3. Create the database schema.
4. Create the API contract.
5. Create the authentication and authorization design.
6. Create the frontend route structure.
7. Create the Docker development environment.

Then implement the project phase by phase.

For every phase:

- Explain what will be implemented.
- Create the required files.
- Implement the backend.
- Implement the frontend.
- Add database migrations.
- Add validation.
- Add tests.
- Run the application.
- Test the APIs.
- Fix errors.
- Update the README.
- Do not move to the next phase until the current phase works.

Use clean architecture and modular code.

Do not generate fake success messages. Verify that features actually work.

When an external API or data provider is unavailable, create a provider interface and a mock/local implementation for development. Do not hardcode fake production results.

The final application must be usable by a real sales team and must be designed for secure production deployment.
