"""seed roles and permissions catalog

Revision ID: 0002_seed_rbac
Revises: 0001_baseline
Create Date: 2026-09-03

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rbac_data import PERMISSIONS, ROLE_PERMISSIONS

revision: str = "0002_seed_rbac"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

roles_table = sa.table(
    "roles",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("name", sa.String),
    sa.column("description", sa.Text),
)
permissions_table = sa.table(
    "permissions",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("code", sa.String),
    sa.column("description", sa.Text),
)
role_permissions_table = sa.table(
    "role_permissions",
    sa.column("role_id", postgresql.UUID(as_uuid=True)),
    sa.column("permission_id", postgresql.UUID(as_uuid=True)),
)


def upgrade() -> None:
    role_ids = {name: uuid.uuid4() for name in ROLE_PERMISSIONS}
    permission_ids = {code: uuid.uuid4() for code in PERMISSIONS}

    op.bulk_insert(
        roles_table,
        [{"id": role_ids[name], "name": name, "description": ""} for name in ROLE_PERMISSIONS],
    )
    op.bulk_insert(
        permissions_table,
        [{"id": permission_ids[code], "code": code, "description": ""} for code in PERMISSIONS],
    )

    links = []
    for role_name, perm_codes in ROLE_PERMISSIONS.items():
        for code in perm_codes:
            links.append({"role_id": role_ids[role_name], "permission_id": permission_ids[code]})
    op.bulk_insert(role_permissions_table, links)


def downgrade() -> None:
    op.execute("DELETE FROM role_permissions")
    op.execute("DELETE FROM permissions")
    op.execute("DELETE FROM roles")
