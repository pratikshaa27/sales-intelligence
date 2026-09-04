"""Canonical RBAC catalog: role names and their permission codes (spec §3).

Seeded into the database by an Alembic data migration. `is_superadmin` on the user
row (not a role here) gates the platform-wide /admin/* APIs across all organizations.
"""

SUPER_ADMIN = "super_admin"
ORG_ADMIN = "org_admin"
SALES_MANAGER = "sales_manager"
SALES_REPRESENTATIVE = "sales_representative"
RESEARCH_ANALYST = "research_analyst"
READ_ONLY = "read_only"

ALL_ROLES = [
    SUPER_ADMIN,
    ORG_ADMIN,
    SALES_MANAGER,
    SALES_REPRESENTATIVE,
    RESEARCH_ANALYST,
    READ_ONLY,
]

PERMISSIONS = [
    "organizations.manage",
    "organizations.view",
    "members.invite",
    "members.remove",
    "members.assign_role",
    "members.view",
    "products.create",
    "products.edit",
    "products.view",
    "products.archive",
    "products.delete",
    "companies.create",
    "companies.edit",
    "companies.view",
    "companies.delete",
    "companies.discover",
    "companies.research",
    "contacts.create",
    "contacts.edit",
    "contacts.view",
    "contacts.delete",
    "contacts.verify",
    "leads.create",
    "leads.edit",
    "leads.view",
    "leads.assign",
    "leads.export",
    "leads.delete",
    "leads.score",
    "leads.brief",
    "analytics.view_team",
    "analytics.view_org",
    "audit_logs.view",
]

_READ_ONLY_PERMS = [
    "organizations.view",
    "members.view",
    "products.view",
    "companies.view",
    "contacts.view",
    "leads.view",
    "analytics.view_team",
]

ROLE_PERMISSIONS: dict[str, list[str]] = {
    SUPER_ADMIN: list(PERMISSIONS),
    ORG_ADMIN: list(PERMISSIONS),
    SALES_MANAGER: [
        "organizations.view",
        "members.view",
        "products.create",
        "products.edit",
        "products.view",
        "products.archive",
        "companies.view",
        "companies.research",
        "contacts.view",
        "leads.create",
        "leads.edit",
        "leads.view",
        "leads.assign",
        "leads.export",
        "leads.score",
        "leads.brief",
        "analytics.view_team",
        "analytics.view_org",
    ],
    SALES_REPRESENTATIVE: [
        "organizations.view",
        "products.view",
        "companies.view",
        "companies.discover",
        "contacts.view",
        "leads.create",
        "leads.edit",
        "leads.view",
        "leads.export",
        "leads.brief",
        "analytics.view_team",
    ],
    RESEARCH_ANALYST: [
        "organizations.view",
        "products.view",
        "companies.view",
        "companies.discover",
        "companies.research",
        "contacts.view",
        "contacts.verify",
        "leads.view",
        "leads.score",
    ],
    READ_ONLY: _READ_ONLY_PERMS,
}
