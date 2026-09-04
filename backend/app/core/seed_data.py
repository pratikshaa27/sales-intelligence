"""Reference seed data shared between Alembic migrations and the test suite's schema bootstrap
(see app/tests/conftest.py), so both stay in sync without duplicating the literal list.
"""

DEFAULT_PRODUCT_CATEGORIES = [
    "CRM & Sales",
    "Marketing",
    "IT Infrastructure",
    "Security",
    "HR & People",
    "Finance & Accounting",
    "Analytics & BI",
    "Customer Support",
    "Other",
]
